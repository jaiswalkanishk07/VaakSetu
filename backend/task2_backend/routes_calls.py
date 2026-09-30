"""
VaakSetu — Twilio Call Routes

Handles:
  1. POST /api/calls/outbound         — Initiate an outbound call via Twilio
  2. POST /api/calls/twiml            — TwiML webhook Twilio hits when call connects (returns <Stream>)
  3. POST /api/calls/status            — Twilio status callback (call ended, etc.)
  4. GET  /api/calls/{call_sid}/summary — Retrieve the final summary after a call ends
"""

import logging
import uuid
import os
import tempfile
from datetime import datetime, timezone
import asyncio

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, FileResponse
from pydantic import BaseModel, Field

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from task1_ai_core.twilio_config import (
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_PHONE_NUMBER,
    PUBLIC_BASE_URL,
    validate_twilio_config,
)
from task1_ai_core.llm_factory import LLMFactory
from task1_ai_core.tts import get_tts_pipeline

logger = logging.getLogger("vaaksetu.routes.calls")
router = APIRouter(prefix="/api/calls", tags=["Twilio Calls"])

# Directory to temporarily store generated TTS audio files so Twilio can fetch them
AUDIO_DIR = os.path.join(tempfile.gettempdir(), "vaaksetu_audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

# In-memory store for call metadata & conversation history
_call_registry: dict[str, dict] = {}


# ── Request Models ──────────────────────────────────────────────

class OutboundCallRequest(BaseModel):
    to_number: str = Field(..., description="Phone number to call in E.164 format, e.g. +919876543210")
    domain: str = Field(default="healthcare", description="Domain for structured extraction: healthcare | finance")


# ── 1. Initiate Outbound Call ───────────────────────────────────

@router.post("/outbound")
async def initiate_outbound_call(req: OutboundCallRequest):
    """
    Make an outbound call via Twilio.
    """
    issues = validate_twilio_config()
    if issues:
        raise HTTPException(status_code=500, detail=f"Twilio config issues: {', '.join(issues)}")

    from twilio.rest import Client
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

    twiml_url = f"{PUBLIC_BASE_URL}/api/calls/twiml?domain={req.domain}"
    status_url = f"{PUBLIC_BASE_URL}/api/calls/status"

    try:
        call = client.calls.create(
            to=req.to_number,
            from_=TWILIO_PHONE_NUMBER,
            url=twiml_url,
            status_callback=status_url,
            status_callback_event=["initiated", "ringing", "answered", "completed"],
            status_callback_method="POST",
            record=True,
        )

        sys_msg = SystemMessage(
            content=f"You are VaakSetu AI, an expert agent handling a phone call in the {req.domain} domain. "
                    f"Keep responses conversational, concise, and friendly. Do not use markdown or special characters."
        )

        _call_registry[call.sid] = {
            "call_sid": call.sid,
            "to": req.to_number,
            "from": TWILIO_PHONE_NUMBER,
            "domain": req.domain,
            "status": "initiated",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "ended_at": None,
            "messages": [sys_msg]
        }

        logger.info(f"Outbound call initiated: {call.sid} → {req.to_number}")
        return {
            "status": "ok",
            "call_sid": call.sid,
            "message": f"Call initiated to {req.to_number}.",
        }

    except Exception as e:
        logger.error(f"Failed to initiate call: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── 2. TwiML Webhook (Answered) ─────────────────────────────────

@router.post("/twiml")
async def twiml_webhook(request: Request):
    """
    Twilio hits this URL when the call connects.
    We generate a Kavya TTS greeting, Play it, and Gather response.
    """
    params = request.query_params
    domain = params.get("domain", "healthcare")
    
    form = await request.form()
    call_sid = form.get("CallSid", "unknown")

    greeting_text = "Hello! I am your VaakSetu AI assistant. How can I help you today?"
    
    # Track message
    if call_sid in _call_registry:
        _call_registry[call_sid]["messages"].append(AIMessage(content=greeting_text))

    # Generate Audio for Greeting
    audio_filename = f"{call_sid}_greeting.wav"
    audio_filepath = os.path.join(AUDIO_DIR, audio_filename)
    
    try:
        tts = get_tts_pipeline()
        result = await tts.synthesize(greeting_text, language_code="en-IN")
        if result and result.audio_bytes:
            with open(audio_filepath, "wb") as f:
                f.write(result.audio_bytes)
            play_url = f"{PUBLIC_BASE_URL}/api/calls/audio/{audio_filename}"
            play_tag = f'<Play>{play_url}</Play>'
        else:
            play_tag = f'<Say voice="alice">{greeting_text}</Say>'
    except Exception as e:
        logger.error(f"TTS greeting failed: {e}")
        play_tag = f'<Say voice="alice">{greeting_text}</Say>'

    gather_url = f"{PUBLIC_BASE_URL}/api/calls/gather"
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Gather input="speech" action="{gather_url}" method="POST" speechTimeout="auto" timeout="10" language="en-IN">
        {play_tag}
    </Gather>
</Response>"""

    return Response(content=twiml, media_type="application/xml")


# ── 3. Gather Webhook (User Speaks) ─────────────────────────────

@router.post("/gather")
async def gather_webhook(request: Request):
    """
    Receives SpeechResult from Twilio, sends it to Gemini, gets response,
    synthesizes Kavya TTS, and loops back to Gather.
    """
    form = await request.form()
    call_sid = form.get("CallSid", "")
    speech_result = form.get("SpeechResult", "").strip()
    
    logger.info(f"[{call_sid}] User said: {speech_result}")

    if not speech_result:
        # If Twilio didn't hear anything, ask again
        gather_url = f"{PUBLIC_BASE_URL}/api/calls/gather"
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Gather input="speech" action="{gather_url}" method="POST" speechTimeout="auto" timeout="10" language="en-IN">
        <Say voice="alice">I didn't quite catch that. Could you repeat?</Say>
    </Gather>
</Response>"""
        return Response(content=twiml, media_type="application/xml")

    # Get conversation context
    call_data = _call_registry.get(call_sid)
    if call_data:
        call_data["messages"].append(HumanMessage(content=speech_result))
        messages = call_data["messages"]
    else:
        messages = [HumanMessage(content=speech_result)]

    # 1. Call Gemini LLM
    try:
        llm = LLMFactory.get_robust_langchain_llm(temperature=0.7)
        ai_response = await asyncio.to_thread(llm.invoke, messages)
        reply_text = ai_response.content.strip()
    except Exception as e:
        logger.error(f"LLM failed: {e}")
        reply_text = "I'm having trouble processing that right now. Could you hold on?"

    if call_data:
        call_data["messages"].append(AIMessage(content=reply_text))
        
    logger.info(f"[{call_sid}] AI says: {reply_text}")

    # 2. Synthesize Kavya TTS
    turn_id = uuid.uuid4().hex[:6]
    audio_filename = f"{call_sid}_turn_{turn_id}.wav"
    audio_filepath = os.path.join(AUDIO_DIR, audio_filename)
    
    try:
        tts = get_tts_pipeline()
        result = await tts.synthesize(reply_text, language_code="en-IN")
        if result and result.audio_bytes:
            with open(audio_filepath, "wb") as f:
                f.write(result.audio_bytes)
            play_url = f"{PUBLIC_BASE_URL}/api/calls/audio/{audio_filename}"
            play_tag = f'<Play>{play_url}</Play>'
        else:
            play_tag = f'<Say voice="alice">{reply_text}</Say>'
    except Exception as e:
        logger.error(f"TTS reply failed: {e}")
        play_tag = f'<Say voice="alice">{reply_text}</Say>'

    # 3. Return TwiML
    gather_url = f"{PUBLIC_BASE_URL}/api/calls/gather"
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Gather input="speech" action="{gather_url}" method="POST" speechTimeout="auto" timeout="10" language="en-IN">
        {play_tag}
    </Gather>
</Response>"""

    return Response(content=twiml, media_type="application/xml")


# ── 4. Serve Audio Files ────────────────────────────────────────

@router.get("/audio/{filename}")
async def serve_audio(filename: str):
    """Serve dynamically generated Kavya TTS audio bytes to Twilio."""
    filepath = os.path.join(AUDIO_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Audio not found")
    return FileResponse(filepath, media_type="audio/wav")


# ── 5. Status Callback ─────────────────────────────────────────

@router.post("/status")
async def status_callback(request: Request):
    form = await request.form()
    call_sid = form.get("CallSid", "")
    call_status = form.get("CallStatus", "")
    duration = form.get("CallDuration", "0")

    logger.info(f"Call status update: {call_sid} → {call_status} (duration: {duration}s)")

    if call_sid in _call_registry:
        _call_registry[call_sid]["status"] = call_status
        if call_status == "completed":
            _call_registry[call_sid]["ended_at"] = datetime.now(timezone.utc).isoformat()
            _call_registry[call_sid]["duration_seconds"] = int(duration)

    return {"status": "ok"}


def get_call_registry():
    return _call_registry
