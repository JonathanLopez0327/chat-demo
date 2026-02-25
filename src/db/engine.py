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
    line         TEXT DEFAULT '',
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
    date_time_reported TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    reported_by        TEXT NOT NULL REFERENCES users(phone_number),
    plant              TEXT DEFAULT '',
    line               TEXT DEFAULT '',
    work_cell          TEXT DEFAULT '',
    shift              TEXT DEFAULT '',
    machine            TEXT,
    production_order   TEXT,
    lot_number         TEXT,
    description        TEXT DEFAULT '',
    immediate_action   TEXT DEFAULT '',
    status             TEXT NOT NULL DEFAULT 'OPEN',
    root_cause         TEXT,
    corrective_action  TEXT,
    preventive_action  TEXT,
    closed_by          TEXT,
    closed_at          TEXT,
    created_at         TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS conversation_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id  TEXT NOT NULL,
    role       TEXT NOT NULL,
    content    TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
"""


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    path = str(db_path or DB_PATH)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: Path | str | None = None) -> None:
    conn = get_connection(db_path)
    conn.executescript(_DDL)
    conn.close()
