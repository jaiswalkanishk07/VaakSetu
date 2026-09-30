"""
VaakSetu AI Core — Centralized Configuration

Loads all environment variables from .env and exposes them
as typed constants. Import this module anywhere in task1_ai_core
to access settings without re-reading .env.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ── Resolve project paths ──────────────────────────────────────
# task1_ai_core/config.py → project root is two levels up
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIGS_DIR = PROJECT_ROOT / "configs"

# ── Load .env from project root ────────────────────────────────
load_dotenv(PROJECT_ROOT / ".env")

# ── Sarvam AI (ASR + Chat LLM) ─────────────────────────────────
SARVAM_API_KEY: str = os.getenv("SARVAM_API_KEY", "")
SARVAM_STT_MODEL: str = "saaras:v3"        # Latest SOTA model
SARVAM_STT_MODE: str = "transcribe"         # transcribe | translate | codemix
SARVAM_CHAT_MODEL: str = "sarvam-m"         # sarvam-m | sarvam-30b | sarvam-105b
SARVAM_CHAT_BASE_URL: str = "https://api.sarvam.ai/v1"

# ── HuggingFace token for Diarization ─────────────────────────
HF_TOKEN: str = os.getenv("HF_TOKEN", "")
SARVAM_CHAT_TEMPERATURE: float = 0.7
SARVAM_CHAT_MAX_TOKENS: int = 256

# ── Gemini (Multi-Key Setup) ───────────────────────────────────
_gemini_keys = os.getenv("GEMINI_API_KEYS", "")
GEMINI_API_KEYS: list[str] = [k.strip() for k in _gemini_keys.split(",") if k.strip()]
LLM_MODEL_NAME: str = "gemini-2.0-flash"  # Highly stable, better free-tier limits

# ── Redis (Conversation Memory) ────────────────────────────────
REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

# ── Domain Config Defaults ──────────────────────────────────────
DEFAULT_DOMAIN: str = "healthcare"
CONVERSATION_HISTORY_TTL: int = 3600  # seconds (1 hour)
MAX_CONVERSATION_TURNS: int = 20

# ── RLAIF Reward Engine Defaults ────────────────────────────────
REWARD_LLM_WEIGHT: float = 0.6
REWARD_PROGRAMMATIC_WEIGHT: float = 0.4
DPO_THRESHOLD: float = 0.70  # >= this → "chosen", < this → "rejected"
IDEAL_TURN_MIN: int = 4
IDEAL_TURN_MAX: int = 8


def validate_config() -> list[str]:
    """
    Check that critical environment variables are set.
    Returns a list of warning messages (empty = all good).
    """
    warnings = []
    if not SARVAM_API_KEY:
        warnings.append("⚠ SARVAM_API_KEY not set — ASR and Chat will fail. Set it in .env")
    if not GEMINI_API_KEYS:
        warnings.append("⚠ GEMINI_API_KEYS not set — LangGraph and LLM Judge scoring will fail. Set it in .env")
    if not REDIS_URL:
        warnings.append("⚠ REDIS_URL not set — Dialogue Agent memory will fail. Set it in .env")
    return warnings


if __name__ == "__main__":
    # Quick validation when run directly
    print(f"Project Root : {PROJECT_ROOT}")
    print(f"Configs Dir  : {CONFIGS_DIR}")
    print(f"Sarvam Key   : {'✅ set' if SARVAM_API_KEY else '❌ missing'}")
    print(f"Gemini Keys  : {'✅ set' if GEMINI_API_KEYS else '❌ missing'} ({len(GEMINI_API_KEYS)} keys)")
    print(f"Redis URL    : {REDIS_URL}")
    print(f"Chat Model   : {SARVAM_CHAT_MODEL}")
    print(f"Gemini Model : {LLM_MODEL_NAME}")

    issues = validate_config()
    if issues:
        print("\n--- Issues ---")
        for w in issues:
            print(w)
    else:
        print("\n✅ All config validated!")
