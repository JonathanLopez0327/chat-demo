"""CRUD repositories for users, incidents, conversation log, and conversations."""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime
from typing import Optional

from src.models import (
    Conversation,
    ConversationStatus,
    IncidentRecord,
    IncidentStatus,
    UserProfile,
)


class UserRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def get(self, phone_number: str) -> Optional[UserProfile]:
        row = self.conn.execute(
            "SELECT * FROM users WHERE phone_number = ?", (phone_number,)
        ).fetchone()
        if row is None:
            return None
        return UserProfile(**dict(row))

    def delete(self, phone_number: str) -> bool:
        """Delete a user by phone number. Returns True if a row was deleted."""
        cur = self.conn.execute(
            "DELETE FROM users WHERE phone_number = ?", (phone_number,)
        )
        self.conn.commit()
        return cur.rowcount > 0

    def ensure_exists(self, phone_number: str) -> None:
        """Create a minimal user record if one doesn't exist yet."""
        self.conn.execute(
            """INSERT OR IGNORE INTO users (phone_number, name, created_at, updated_at)
               VALUES (?, '', ?, ?)
            """,
            (phone_number, datetime.now().isoformat(), datetime.now().isoformat()),
        )
        self.conn.commit()

    def upsert(self, profile: UserProfile) -> None:
        self.conn.execute(
            """INSERT INTO users (phone_number, name, area, shift, role, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(phone_number) DO UPDATE SET
                 name=excluded.name, area=excluded.area, shift=excluded.shift,
                 role=excluded.role, updated_at=excluded.updated_at
            """,
            (
                profile.phone_number,
                profile.name,
                profile.area,
                profile.shift,
                profile.role,
                profile.created_at.isoformat(),
                datetime.now().isoformat(),
            ),
        )
        self.conn.commit()


class IncidentRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def save(self, record: IncidentRecord) -> int:
        cur = self.conn.execute(
            """INSERT INTO incidents
               (incident_code, incident_name, category, sub_category, severity,
                ticket_type, sla, date_time_reported, reported_by, agency,
                shift, description, status, root_cause, corrective_action,
                preventive_action, closed_by, closed_at, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                record.incident_code,
                record.incident_name,
                record.category.value,
                record.sub_category,
                record.severity.value,
                record.ticket_type.value,
                record.sla,
                record.date_time_reported.isoformat(),
                record.reported_by,
                record.agency,
                record.shift,
                record.description,
                record.status.value,
                record.root_cause,
                record.corrective_action,
                record.preventive_action,
                record.closed_by,
                record.closed_at.isoformat() if record.closed_at else None,
                record.created_at.isoformat(),
            ),
        )
        self.conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def get_recent_by_user(
        self, phone_number: str, limit: int = 5
    ) -> list[dict]:
        rows = self.conn.execute(
            """SELECT * FROM incidents
               WHERE reported_by = ?
               ORDER BY date_time_reported DESC
               LIMIT ?""",
            (phone_number, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def update_status(
        self, incident_id: int, status: IncidentStatus
    ) -> None:
        self.conn.execute(
            "UPDATE incidents SET status = ? WHERE id = ?",
            (status.value, incident_id),
        )
        self.conn.commit()

    def delete_by_user(self, phone_number: str) -> int:
        """Delete all incidents (and their attachments) for a user. Returns count deleted."""
        # Delete attachments for this user's incidents first
        self.conn.execute(
            """DELETE FROM incident_attachments
               WHERE incident_id IN (SELECT id FROM incidents WHERE reported_by = ?)""",
            (phone_number,),
        )
        cur = self.conn.execute(
            "DELETE FROM incidents WHERE reported_by = ?", (phone_number,)
        )
        self.conn.commit()
        return cur.rowcount


class AttachmentRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def save(
        self,
        incident_id: int,
        file_path: str,
        media_type: str,
        original_name: str | None = None,
        description: str | None = None,
    ) -> int:
        cur = self.conn.execute(
            """INSERT INTO incident_attachments
               (incident_id, file_path, media_type, original_name, description)
               VALUES (?, ?, ?, ?, ?)""",
            (incident_id, file_path, media_type, original_name, description),
        )
        self.conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def get_by_incident(self, incident_id: int) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM incident_attachments WHERE incident_id = ? ORDER BY id",
            (incident_id,),
        ).fetchall()
        return [dict(r) for r in rows]


class ConversationLogRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def append(
        self,
        thread_id: str,
        role: str,
        content: str,
        conversation_id: Optional[str] = None,
    ) -> None:
        self.conn.execute(
            "INSERT INTO conversation_log (thread_id, role, content, conversation_id) VALUES (?, ?, ?, ?)",
            (thread_id, role, content, conversation_id),
        )
        self.conn.commit()

    def get_thread(self, thread_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM conversation_log WHERE thread_id = ? ORDER BY id",
            (thread_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_thread(self, thread_id: str) -> None:
        """Delete all conversation log entries for a thread."""
        self.conn.execute(
            "DELETE FROM conversation_log WHERE thread_id = ?", (thread_id,)
        )
        self.conn.commit()


class ConversationRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create(self, thread_id: str) -> Conversation:
        """Create a new conversation session and return it."""
        conv = Conversation(id=str(uuid.uuid4()), thread_id=thread_id)
        self.conn.execute(
            """INSERT INTO conversations (id, thread_id, started_at, status, outcome, total_messages)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                conv.id,
                conv.thread_id,
                conv.started_at.isoformat(),
                conv.status.value,
                conv.outcome,
                conv.total_messages,
            ),
        )
        self.conn.commit()
        return conv

    def get_active(self, thread_id: str) -> Optional[Conversation]:
        """Return the active conversation for a thread, if any."""
        row = self.conn.execute(
            "SELECT * FROM conversations WHERE thread_id = ? AND status = 'ACTIVE' ORDER BY started_at DESC LIMIT 1",
            (thread_id,),
        ).fetchone()
        if row is None:
            return None
        return Conversation(**dict(row))

    def finish(
        self,
        conversation_id: str,
        status: ConversationStatus,
        outcome: str = "",
        incident_id: Optional[int] = None,
    ) -> None:
        """Mark a conversation as finished."""
        self.conn.execute(
            """UPDATE conversations
               SET ended_at = ?, status = ?, outcome = ?, incident_id = COALESCE(?, incident_id)
               WHERE id = ?""",
            (
                datetime.now().isoformat(),
                status.value,
                outcome,
                incident_id,
                conversation_id,
            ),
        )
        self.conn.commit()

    def increment_messages(self, conversation_id: str) -> None:
        """Increment the total_messages counter by 1."""
        self.conn.execute(
            "UPDATE conversations SET total_messages = total_messages + 1 WHERE id = ?",
            (conversation_id,),
        )
        self.conn.commit()
