from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────────────────

class Severity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IncidentStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    CONTAINED = "CONTAINED"
    CLOSED = "CLOSED"


class Category(str, enum.Enum):
    MEC = "MEC"
    PRO = "PRO"
    CAL = "CAL"
    SEG = "SEG"
    LOG = "LOG"
    OPS = "OPS"


# ── Catalog template (parsed from markdown) ───────────────────────────

class IncidentTemplate(BaseModel):
    code: str
    category: Category
    sub_category: str = ""
    name: str
    description: str
    impact: str = ""
    severity: Severity
    immediate_action: str = ""
    responsible_area: str = ""


# ── User profile ───────────────────────────────────────────────────────

class UserProfile(BaseModel):
    phone_number: str
    name: str = ""
    area: str = ""
    shift: str = ""
    role: str = ""
    line: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# ── Incident record (saved to DB) ─────────────────────────────────────

class IncidentRecord(BaseModel):
    id: Optional[int] = None
    incident_code: str
    incident_name: str
    category: Category
    sub_category: str = ""
    severity: Severity
    date_time_reported: datetime = Field(default_factory=datetime.now)
    reported_by: str  # phone_number FK
    plant: str = ""
    line: str = ""
    work_cell: str = ""
    shift: str = ""
    machine: Optional[str] = None
    production_order: Optional[str] = None
    lot_number: Optional[str] = None
    description: str = ""
    immediate_action: str = ""
    status: IncidentStatus = IncidentStatus.OPEN
    root_cause: Optional[str] = None
    corrective_action: Optional[str] = None
    preventive_action: Optional[str] = None
    closed_by: Optional[str] = None
    closed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
