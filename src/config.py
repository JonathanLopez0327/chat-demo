from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CATALOG_PATH = PROJECT_ROOT / "catalog" / "incident_catalog.md"
DB_PATH = DATA_DIR / "chatbot.db"
CHECKPOINT_DB_PATH = DATA_DIR / "checkpoints" / "langgraph.db"

# ── OpenAI ─────────────────────────────────────────────────────────────
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
MODEL_NAME: str = os.getenv("MODEL_NAME", "gpt-4o-mini")
MODEL_TEMPERATURE: float = float(os.getenv("MODEL_TEMPERATURE", "0.1"))

# ── Ensure runtime dirs exist ──────────────────────────────────────────
DATA_DIR.mkdir(parents=True, exist_ok=True)
(DATA_DIR / "checkpoints").mkdir(parents=True, exist_ok=True)
