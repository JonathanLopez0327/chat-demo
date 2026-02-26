from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CATALOG_PATH = PROJECT_ROOT / "catalog" / "Incidentes.xlsx"
DB_PATH = DATA_DIR / "chatbot.db"
CHECKPOINT_DB_PATH = DATA_DIR / "checkpoints" / "langgraph.db"

# ── OpenAI ─────────────────────────────────────────────────────────────
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
MODEL_NAME: str = os.getenv("MODEL_NAME", "gpt-4o-mini")
MODEL_TEMPERATURE: float = float(os.getenv("MODEL_TEMPERATURE", "0.1"))

# ── WhatsApp (Meta Cloud API) ───────────────────────────────────────
WHATSAPP_VERIFY_TOKEN: str = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
WHATSAPP_ACCESS_TOKEN: str = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")

# ── Media ────────────────────────────────────────────────────────────
MEDIA_DIR = DATA_DIR / "media"
VISION_MODEL: str = os.getenv("VISION_MODEL", "gpt-4o")
WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "whisper-1")

# ── Ensure runtime dirs exist ──────────────────────────────────────────
DATA_DIR.mkdir(parents=True, exist_ok=True)
(DATA_DIR / "checkpoints").mkdir(parents=True, exist_ok=True)
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
