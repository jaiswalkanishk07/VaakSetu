"""
VaakSetu Backend — Firebase Firestore Database Layer

Uses firebase-admin for database access. Collections:
  • agents           — Dynamic agent configurations (replaces static YAML)
  • sessions         — Conversation sessions tied to agents
  • messages         — Individual messages in each session
  • extracted_fields — Structured data extracted per session
"""

import json
import os
import logging
from pathlib import Path
from datetime import datetime, timezone
import firebase_admin
from firebase_admin import credentials, firestore

logger = logging.getLogger("vaaksetu.database")

PROJECT_ROOT = Path(__file__).resolve().parent.parent

_db = None

async def init_db():
    """Initialize the Firebase Admin SDK."""
    global _db
    if not firebase_admin._apps:
        # Load from .env variable or default local path
        cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", str(PROJECT_ROOT / "firebase_credentials.json"))
        try:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            logger.info(f"Firebase initialized using credentials at {cred_path}")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            raise
    _db = firestore.client()

async def get_db():
    """Returns the Firestore client."""
    global _db
    if _db is None:
        await init_db()
    return _db

async def close_db(db=None):
    """No-op for Firebase."""
    pass

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Agent CRUD
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def create_agent(agent_data: dict) -> dict:
    """Insert a new agent into the database."""
    db = await get_db()
    now = datetime.now(timezone.utc).isoformat()
    agent_id = agent_data["id"]
    
    doc_ref = db.collection("agents").document(agent_id)
    doc_data = {
        "id": agent_id,
        "name": agent_data["name"],
        "domain": agent_data["domain"],
        "customDomain": agent_data.get("customDomain", ""),
        "inputs": agent_data.get("inputs", ["Voice"]),
        "fields": agent_data.get("fields", []),
        "prompt": agent_data.get("prompt", ""),
        "greeting": agent_data.get("greeting", ""),
        "triggers": agent_data.get("triggers", []),
        "escalation": agent_data.get("escalation", {}),
        "escalation_message": agent_data.get("escalation_message", ""),
        "default_language": agent_data.get("default_language", "hi-IN"),
        "created_at": now,
        "updated_at": now,
    }
    doc_ref.set(doc_data)
    return await get_agent(agent_id)

async def get_agent(agent_id: str) -> dict | None:
    """Fetch a single agent by ID."""
    db = await get_db()
    doc = db.collection("agents").document(agent_id).get()
    if doc.exists:
        return doc.to_dict()
    return None

async def list_agents() -> list[dict]:
    """List all agents ordered by creation date (newest first)."""
    db = await get_db()
    docs = db.collection("agents").order_by("created_at", direction=firestore.Query.DESCENDING).stream()
    return [doc.to_dict() for doc in docs]

async def update_agent(agent_id: str, agent_data: dict) -> dict | None:
    """Update an existing agent."""
    db = await get_db()
    now = datetime.now(timezone.utc).isoformat()
    
    update_data = {
        "name": agent_data["name"],
        "domain": agent_data["domain"],
        "customDomain": agent_data.get("customDomain", ""),
        "inputs": agent_data.get("inputs", ["Voice"]),
        "fields": agent_data.get("fields", []),
        "prompt": agent_data.get("prompt", ""),
        "greeting": agent_data.get("greeting", ""),
        "triggers": agent_data.get("triggers", []),
        "escalation": agent_data.get("escalation", {}),
        "escalation_message": agent_data.get("escalation_message", ""),
        "default_language": agent_data.get("default_language", "hi-IN"),
        "updated_at": now,
    }
    
    doc_ref = db.collection("agents").document(agent_id)
    doc_ref.update(update_data)
    return await get_agent(agent_id)

async def delete_agent(agent_id: str) -> bool:
    """Delete an agent (Note: does not delete subcollections/sessions automatically in Firestore)."""
    db = await get_db()
    doc_ref = db.collection("agents").document(agent_id)
    if doc_ref.get().exists:
        doc_ref.delete()
        return True
    return False

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Session CRUD
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def create_session(session_id: str, agent_id: str) -> dict:
    """Create a new conversation session."""
    db = await get_db()
    now = datetime.now(timezone.utc).isoformat()
    doc_ref = db.collection("sessions").document(session_id)
    
    session_data = {
        "id": session_id,
        "agent_id": agent_id,
        "status": "active",
        "collected_fields": {},
        "is_complete": False,
        "turn_count": 0,
        "created_at": now,
        "ended_at": None,
        "reward_scores": None,
    }
    doc_ref.set(session_data)
    return await get_session(session_id)

async def get_session(session_id: str) -> dict | None:
    """Fetch a session by ID."""
    db = await get_db()
    doc = db.collection("sessions").document(session_id).get()
    if doc.exists:
        return doc.to_dict()
    return None

async def update_session(session_id: str, **kwargs) -> dict | None:
    """Update session fields dynamically."""
    db = await get_db()
    doc_ref = db.collection("sessions").document(session_id)
    
    if not kwargs:
        return await get_session(session_id)
        
    update_data = {}
    for key, val in kwargs.items():
        if key == "is_complete":
            update_data[key] = bool(val)
        else:
            update_data[key] = val
            
    doc_ref.update(update_data)
    return await get_session(session_id)

async def get_sessions_for_agent(agent_id: str) -> list[dict]:
    """List all sessions for an agent."""
    db = await get_db()
    docs = db.collection("sessions").where("agent_id", "==", agent_id).order_by("created_at", direction=firestore.Query.DESCENDING).stream()
    return [doc.to_dict() for doc in docs]

async def list_sessions() -> list[dict]:
    """List all sessions ordered by creation date (newest first)."""
    db = await get_db()
    docs = db.collection("sessions").order_by("created_at", direction=firestore.Query.DESCENDING).stream()
    return [doc.to_dict() for doc in docs]

async def delete_session(session_id: str) -> bool:
    """Delete a session."""
    db = await get_db()
    doc_ref = db.collection("sessions").document(session_id)
    if doc_ref.get().exists:
        doc_ref.delete()
        return True
    return False

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Message CRUD
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def add_message(session_id: str, role: str, content: str, turn_number: int) -> dict:
    """Add a message to a session."""
    db = await get_db()
    now = datetime.now(timezone.utc).isoformat()
    
    msg_data = {
        "session_id": session_id,
        "role": role,
        "content": content,
        "turn_number": turn_number,
        "created_at": now,
    }
    
    # Firestore creates random ID for messages
    doc_ref = db.collection("messages").document()
    msg_data["id"] = doc_ref.id
    doc_ref.set(msg_data)
    
    return msg_data

async def get_messages(session_id: str) -> list[dict]:
    """Get all messages for a session ordered by turn number."""
    db = await get_db()
    docs = db.collection("messages").where("session_id", "==", session_id).stream()
    messages = [doc.to_dict() for doc in docs]
    # Sort in memory to avoid requiring a Firebase composite index
    messages.sort(key=lambda x: x.get("turn_number", 0))
    return messages
