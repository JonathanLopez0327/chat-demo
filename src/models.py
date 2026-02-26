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
    POS = "POS"   # Terminales / POS
    IMP = "IMP"   # Impresoras / Tickets
    NET = "NET"   # Internet / Conectividad
    ELE = "ELE"   # Electricidad / Energía
    EQU = "EQU"   # Equipos de Cómputo
    INF = "INF"   # Local / Infraestructura
    MAT = "MAT"   # Materiales / Suministros
    VEN = "VEN"   # Operación de Ventas
    PAG = "PAG"   # Pagos y Premios
    CON = "CON"   # Contabilidad / Cuadres
    FRA = "FRA"   # Seguridad / Fraude
    REC = "REC"   # Reclamos de Clientes


class TicketType(str, enum.Enum):
    INCIDENTE = "Incidente"
    ALERTA = "Alerta"
    RECLAMO = "Reclamo"


class ConversationStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    ERROR = "ERROR"


# ── Catalog template (parsed from Excel) ─────────────────────────────

class IncidentTemplate(BaseModel):
    code: str
    category: Category
    sub_category: str = ""
    name: str
    description: str
    severity: Severity
    ticket_type: TicketType = TicketType.INCIDENTE
    sla: str = ""
    requires_image: bool = False


# ── User profile ───────────────────────────────────────────────────────

class UserProfile(BaseModel):
    phone_number: str
    name: str = ""
    area: str = ""
    shift: str = ""
    role: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# ── Incident record (saved to DB) ─────────────────────────────────────

# ── Conversation session ──────────────────────────────────────────────

class Conversation(BaseModel):
    id: str
    thread_id: str
    started_at: datetime = Field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    status: ConversationStatus = ConversationStatus.ACTIVE
    outcome: str = ""
    incident_id: Optional[int] = None
    total_messages: int = 0


# ── Incident record (saved to DB) ─────────────────────────────────────

class IncidentRecord(BaseModel):
    id: Optional[int] = None
    incident_code: str
    incident_name: str
    category: Category
    sub_category: str = ""
    severity: Severity
    ticket_type: TicketType = TicketType.INCIDENTE
    sla: str = ""
    date_time_reported: datetime = Field(default_factory=datetime.now)
    reported_by: str  # phone_number FK
    agency: str = ""
    shift: str = ""
    description: str = ""
    status: IncidentStatus = IncidentStatus.OPEN
    root_cause: Optional[str] = None
    corrective_action: Optional[str] = None
    preventive_action: Optional[str] = None
    closed_by: Optional[str] = None
    closed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
