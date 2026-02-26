"""SQLite connection and table creation."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from src.config import DB_PATH

_DDL = """
CREATE TABLE IF NOT EXISTS users (
    phone_number TEXT PRIMARY KEY,
    name         TEXT DEFAULT '',
    area         TEXT DEFAULT '',
    shift        TEXT DEFAULT '',
    role         TEXT DEFAULT '',
    created_at   TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at   TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS incidents (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_code      TEXT NOT NULL,
    incident_name      TEXT NOT NULL,
    category           TEXT NOT NULL,
    sub_category       TEXT DEFAULT '',
    severity           TEXT NOT NULL,
    ticket_type        TEXT NOT NULL DEFAULT 'Incidente',
    sla                TEXT DEFAULT '',
    date_time_reported TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    reported_by        TEXT NOT NULL REFERENCES users(phone_number),
    agency             TEXT DEFAULT '',
    shift              TEXT DEFAULT '',
    description        TEXT DEFAULT '',
    status             TEXT NOT NULL DEFAULT 'OPEN',
    root_cause         TEXT,
    corrective_action  TEXT,
    preventive_action  TEXT,
    closed_by          TEXT,
    closed_at          TEXT,
    created_at         TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS conversations (
    id              TEXT PRIMARY KEY,
    thread_id       TEXT NOT NULL,
    started_at      TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    ended_at        TEXT,
    status          TEXT NOT NULL DEFAULT 'ACTIVE',
    outcome         TEXT DEFAULT '',
    incident_id     INTEGER REFERENCES incidents(id),
    total_messages  INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS conversation_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id       TEXT NOT NULL,
    role            TEXT NOT NULL,
    content         TEXT NOT NULL,
    conversation_id TEXT REFERENCES conversations(id),
    created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS incident_attachments (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id   INTEGER NOT NULL REFERENCES incidents(id),
    file_path     TEXT NOT NULL,
    media_type    TEXT NOT NULL,
    original_name TEXT,
    description   TEXT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
"""


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    path = str(db_path or DB_PATH)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    """Apply lightweight migrations for existing databases."""
    # Add conversation_id column to conversation_log if missing
    cols = {
        row[1]
        for row in conn.execute("PRAGMA table_info(conversation_log)").fetchall()
    }
    if "conversation_id" not in cols:
        conn.execute(
            "ALTER TABLE conversation_log ADD COLUMN conversation_id TEXT REFERENCES conversations(id)"
        )
        conn.commit()


def init_db(db_path: Path | str | None = None) -> None:
    conn = get_connection(db_path)
    conn.executescript(_DDL)
    _migrate(conn)
    conn.close()
