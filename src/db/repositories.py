"""CRUD repositories for users, incidents, and conversation log."""
from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Optional

from src.models import IncidentRecord, IncidentStatus, UserProfile


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

    def upsert(self, profile: UserProfile) -> None:
        self.conn.execute(
            """INSERT INTO users (phone_number, name, area, shift, role, line, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(phone_number) DO UPDATE SET
                 name=excluded.name, area=excluded.area, shift=excluded.shift,
                 role=excluded.role, line=excluded.line, updated_at=excluded.updated_at
            """,
            (
                profile.phone_number,
                profile.name,
                profile.area,
                profile.shift,
                profile.role,
                profile.line,
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
                date_time_reported, reported_by, plant, line, work_cell, shift,
                machine, production_order, lot_number, description,
                immediate_action, status, root_cause, corrective_action,
                preventive_action, closed_by, closed_at, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                record.incident_code,
                record.incident_name,
                record.category.value,
                record.sub_category,
                record.severity.value,
                record.date_time_reported.isoformat(),
                record.reported_by,
                record.plant,
                record.line,
                record.work_cell,
                record.shift,
                record.machine,
                record.production_order,
                record.lot_number,
                record.description,
                record.immediate_action,
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

    def append(self, thread_id: str, role: str, content: str) -> None:
        self.conn.execute(
            "INSERT INTO conversation_log (thread_id, role, content) VALUES (?, ?, ?)",
            (thread_id, role, content),
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
