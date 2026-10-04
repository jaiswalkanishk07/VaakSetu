import operator
import logging
from typing import Annotated, TypedDict, Dict, Any, List, Optional
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
import asyncio

from task1_ai_core.config import (
    SARVAM_API_KEY,
    SARVAM_CHAT_MODEL,
    SARVAM_CHAT_BASE_URL,
    SARVAM_CHAT_TEMPERATURE
)
from task2_backend.domain_config import domain_manager

logger = logging.getLogger(__name__)

# --- State Schema ---
class ConversationState(TypedDict):
    session_id: str
    domain: str
    turn_count: int
    transcript_history: Annotated[List[str], operator.add]
    speaker_map: Dict[str, str]           # role map (e.g. {"SPEAKER_00": "Doctor"})
    narrative: str
    structured_data: Dict[str, Any]
    # Theme 5: Multimodal Grounding
    video_frames: List[str]
    # Theme 5: Frame Alteration signal
    # If True, this turn was triggered by an interruption — skip Slow Path extraction
    frame_altered: bool
    # Latency tracking for RLAIF evaluation
    last_fast_path_ms: Optional[float]
    last_slow_path_ms: Optional[float]

class ConversationalGraphAgent:
    """
    Stateful conversational agent using LangGraph.
    Addresses limitations of single-pass summarisation by keeping active context.
    """
    def __init__(self):
        from task1_ai_core.llm_factory import LLMFactory
        self._llm = LLMFactory.get_robust_langchain_llm(temperature=0.7)
        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(ConversationState)

        # ── Nodes ────────────────────────────────────────────────
        builder.add_node("ingest", self.node_ingest)
        builder.add_node("classify_roles", self.node_classify_roles)
        # SLOW PATH: Full structured extraction (expensive, ~2-4s)
        builder.add_node("slow_path_extract", self.node_extract_structured)
        # FAST PATH: Immediate narrative acknowledgment, no extraction
        builder.add_node("fast_path_respond", self.node_fast_path_respond)
        builder.add_node("update_narrative", self.node_update_narrative)

        # ── Edges ────────────────────────────────────────────────
        builder.add_edge(START, "ingest")

        # After ingest: route based on frame_altered signal + role status
        builder.add_conditional_edges(
            "ingest",
            self.route_after_ingest,
            {
                "classify_roles": "classify_roles",
                "slow_path_extract": "slow_path_extract",
                "fast_path_respond": "fast_path_respond",
            }
        )

        # Slow path: classify → extract → narrative
        builder.add_edge("classify_roles", "slow_path_extract")
        builder.add_edge("slow_path_extract", "update_narrative")

        # Fast path: skip extraction entirely, go straight to narrative
        builder.add_edge("fast_path_respond", "update_narrative")

        builder.add_edge("update_narrative", END)

        return builder.compile()

    def route_after_ingest(self, state: ConversationState) -> str:
        """
        Frame Alteration Router (Theme 5 core).

        FAST PATH  → frame_altered=True (user interrupted previous turn)
                     Skips extraction. Only updates narrative.
        SLOW PATH  → Normal stable frame, runs full structured extraction.
        CLASSIFY   → First 5 turns, role classification not yet done.
        """
        # Roles not yet established: always classify first regardless of interruption
        if not state.get("speaker_map") and state.get("turn_count", 0) <= 5:
            logger.info(f"[{state['session_id']}] Routing → classify_roles (roles unresolved)")
            return "classify_roles"

        # Frame Alteration: interrupted turn takes Fast Path
        if state.get("frame_altered", False):
            logger.info(f"[{state['session_id']}] Routing → fast_path_respond (FRAME ALTERED — skipping extraction)")
            return "fast_path_respond"

        # Every 5 stable turns: run full Slow Path extraction
        if state.get("turn_count", 0) % 5 == 0:
            logger.info(f"[{state['session_id']}] Routing → slow_path_extract (stable frame, turn {state['turn_count']})")
            return "slow_path_extract"

        # Default: Fast Path for intermediate stable turns
        logger.info(f"[{state['session_id']}] Routing → fast_path_respond (interim stable frame)")
        return "fast_path_respond"

    def node_ingest(self, state: ConversationState) -> Dict:
        """
        Ingest node: increment turn count.
        frame_altered flag is set externally by routes_live_mic.py
        before calling process_turn — it is NOT cleared here so the router can read it.
        """
        return {"turn_count": state.get("turn_count", 0) + 1}

    def node_classify_roles(self, state: ConversationState) -> Dict:
        """Uses first few turns to identify who is the agent vs user."""
        recent_text = "\n".join(state.get("transcript_history", [])[-5:])
        prompt = f"""
        Analyze this initial conversation and map the speaker tags (e.g. SPEAKER_00, SPEAKER_01) 
        to logical roles based on the '{state.get('domain', 'general')}' domain (e.g. Doctor/Patient, Agent/Customer).
        Return ONLY valid JSON format mapping speakers to roles. Example: {{"SPEAKER_00": "Agent", "SPEAKER_01": "Customer"}}
        
        Transcript:
        {recent_text}
        """
        try:
            res = self._llm.invoke([SystemMessage(content="You are a helpful role-classification assistant. Output valid JSON only."), HumanMessage(content=prompt)])
            import json
            import re
            
            # Extract JSON from potential markdown wrapping
            text = res.content
            json_str = re.search(r'\{.*\}', text, re.DOTALL)
            if json_str:
                speaker_map = json.loads(json_str.group())
                return {"speaker_map": speaker_map}
        except Exception as e:
            logger.error(f"Role classification failed: {e}")
        return {"speaker_map": {}}

    def node_fast_path_respond(self, state: ConversationState) -> Dict:
        """
        FAST PATH NODE (Theme 5).

        Does NOT run extraction. Returns immediately so the narrative can be
        updated with minimal latency. Used for:
          - Interrupted frames (frame_altered=True)
          - Intermediate stable turns between extraction cycles

        Resets frame_altered to False so next turn starts clean.
        """
        import time
        start = time.monotonic()
        logger.info(f"[{state['session_id']}] Fast path executed. Extraction skipped.")
        elapsed_ms = (time.monotonic() - start) * 1000
        # Clear interruption flag for next turn
        return {
            "frame_altered": False,
            "last_fast_path_ms": elapsed_ms,
        }

    def node_extract_structured(self, state: ConversationState) -> Dict:
        """
        SLOW PATH NODE (Theme 5).

        Full structured Pydantic extraction using the domain schema.
        Only runs on stable frames every N turns — never on interrupted frames.
        Resets frame_altered to False after completion.
        """
        import time
        start = time.monotonic()
        domain = state.get("domain", "general")
        schema = domain_manager.get_structured_schema(domain)

        # Attach structured output constraint
        llm_with_schema = self._llm.with_structured_output(schema)

        prompt = f"""
        Extract relevant {domain} details from this conversation history.
        Update missing portions only — preserve existing values.
        If images are provided, use them to ground and clarify any ambiguity in the dialogue (e.g. if the user says "this part hurts", look at the image to extract the body part).
        Transcript:
        {chr(10).join(state.get("transcript_history", []))}
        """
        
        # Theme 5: Multimodal Grounding
        content_parts = [{"type": "text", "text": prompt}]
        frames = state.get("video_frames", [])
        for b64_frame in frames:
            content_parts.append({
                "type": "image_url", 
                "image_url": {"url": f"data:image/jpeg;base64,{b64_frame}"}
            })

        try:
            extracted = llm_with_schema.invoke([HumanMessage(content=content_parts)])
            current_data = state.get("structured_data", {})
            new_data = extracted.model_dump(exclude_unset=True, exclude_none=True)
            current_data.update(new_data)
            elapsed_ms = (time.monotonic() - start) * 1000
            logger.info(f"[{state['session_id']}] Slow path extraction complete in {elapsed_ms:.0f}ms.")
            return {
                "structured_data": current_data,
                "frame_altered": False,
                "last_slow_path_ms": elapsed_ms,
            }
        except Exception as e:
            logger.error(f"Structured extraction failed: {e}")
            return {"frame_altered": False}

    def node_update_narrative(self, state: ConversationState) -> Dict:
        """Incrementally updates the third-person narrative."""
        current_narrative = state.get("narrative", "")
        recent_turns = "\n".join(state.get("transcript_history", [])[-5:])
        
        prompt = f"""
        You are a third-person observer writing a professional summary.
        Existing Narrative:
        {current_narrative if current_narrative else '[No existing narrative]'}
        
        New Dialogue:
        {recent_turns}
        
        Update the narrative incrementally based on the new dialogue. 
        Do not rewrite from scratch unless necessary. Add the new events factually.
        """
        try:
            res = self._llm.invoke([HumanMessage(content=prompt)])
            return {"narrative": res.content.strip()}
        except Exception as e:
            logger.error(f"Narrative update failed: {e}")
            return {"narrative": current_narrative}

    async def process_turn(self, state: ConversationState) -> ConversationState:
        """Run the graph asynchronously."""
        final_state = await asyncio.to_thread(self.graph.invoke, state)
        return final_state
