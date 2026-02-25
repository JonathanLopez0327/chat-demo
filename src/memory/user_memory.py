"""Load user profile and recent history from app DB."""
from __future__ import annotations

import sqlite3
from typing import Optional

from src.db.repositories import IncidentRepository, UserRepository
from src.models import UserProfile


def load_user_context(
    conn: sqlite3.Connection, phone_number: str
) -> tuple[Optional[UserProfile], list[dict]]:
    """Return (profile_or_None, recent_incidents) for the given phone."""
    user_repo = UserRepository(conn)
    incident_repo = IncidentRepository(conn)

    profile = user_repo.get(phone_number)
    recent = incident_repo.get_recent_by_user(phone_number, limit=5)
    return profile, recent
