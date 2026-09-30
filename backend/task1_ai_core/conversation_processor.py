import asyncio
import logging
from task1_ai_core.graph_agent import ConversationalGraphAgent, ConversationState

logger = logging.getLogger(__name__)

class StreamConversationProcessor:
    """
    Handles streaming/incremental conversation chunk processing using the 
    LangGraph Conversational Intelligence Engine.
    """
    def __init__(self):
        self.agent = ConversationalGraphAgent()
        # Mock Redis: In-memory store for states (Mapped by session)
        self._session_store = {}

    def get_session_state(self, session_id: str, domain: str = "general") -> ConversationState:
        if session_id not in self._session_store:
            self._session_store[session_id] = ConversationState({
                "session_id": session_id,
                "domain": domain,
                "turn_count": 0,
                "transcript_history": [],
                "speaker_map": {},
                "narrative": "",
                "structured_data": {}
            })
        return self._session_store[session_id]

    async def ingest_chunk(self, session_id: str, domain: str, text_chunk: str) -> dict:
        """
        Takes a new transcript chunk string, runs it through the graph agent, 
        and updates the central state.
        
        Returns a dict of updates for the websocket to push to the client.
        """
        state = self.get_session_state(session_id, domain)
        if not text_chunk.strip():
            logger.warning(f"Empty chunk received for session {session_id}")
            return {"status": "empty"}

        # Push to transcript history (simulated queue)
        state["transcript_history"].append(text_chunk)
        
        # Process the turn through the graph
        logger.info(f"Processing turn for session {session_id} - Graph nodes invoking...")
        try:
            new_state = await self.agent.process_turn(state)
            self._session_store[session_id] = new_state
            
            return {
                "status": "success",
                "narrative": new_state.get("narrative", ""),
                "structured_data": new_state.get("structured_data", {}),
                "speaker_map": new_state.get("speaker_map", {})
            }
        except Exception as e:
            logger.error(f"Graph agent failed on chunk ingestion: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

class ConversationProcessor:
    """
    Offline/Batch processor for full conversation audio files.
    """
    def __init__(self, asr_pipeline, agent):
        self.asr = asr_pipeline
        # ConversationalGraphAgent handles full context processing (narrative, data extraction)
        from task1_ai_core.graph_agent import ConversationalGraphAgent
        self.graph_agent = ConversationalGraphAgent()
        self._diarizer = None

    def _get_diarizer(self):
        if self._diarizer is None:
            from task1_ai_core.diarization import SpeakerDiarizer
            self._diarizer = SpeakerDiarizer()
        return self._diarizer

    async def process_conversation(self, audio_path: str, agent_config: dict, num_speakers: int = 2) -> dict:
        import os
        import tempfile
        import uuid
        from pydub import AudioSegment

        diarizer = self._get_diarizer()
        try:
            logger.info(f"Diarizing {audio_path}")
            segments = await diarizer.diarize(audio_path, num_speakers=num_speakers)
            
            audio = AudioSegment.from_file(audio_path)
            transcript_turns = []
            
            for seg in segments:
                start_ms = int(seg["start"] * 1000)
                end_ms = int(seg["end"] * 1000)
                speaker = seg["speaker"]
                
                chunk = audio[start_ms:end_ms]
                
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    chunk.export(tmp.name, format="wav")
                    tmp_path = tmp.name
                    
                try:
                    result = await self.asr.transcribe(tmp_path)
                    transcript = result.transcript
                    if transcript.strip():
                        transcript_turns.append(f"{speaker}: {transcript}")
                finally:
                    os.unlink(tmp_path)
                    
            full_transcript = "\n".join(transcript_turns)
            
            session_id = f"batch-{uuid.uuid4().hex[:8]}"
            state = {
                "session_id": session_id,
                "domain": agent_config.get("domain", "general") if agent_config else "general",
                "turn_count": 0,
                "transcript_history": [full_transcript],
                "speaker_map": {},
                "narrative": "",
                "structured_data": {}
            }
            
            new_state = await self.graph_agent.process_turn(state)
            
            return {
                "transcript": full_transcript,
                "narrative": new_state.get("narrative", ""),
                "structured_data": new_state.get("structured_data", {}),
                "speaker_map": new_state.get("speaker_map", {})
            }
            
        except Exception as e:
            logger.error(f"Error in ConversationProcessor: {e}")
            return {"error": str(e)}
