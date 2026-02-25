"""LangGraph node functions for the incident reporting flow.

Nodes that need user input call ``interrupt()`` which pauses execution
and returns control to the LangGraph Platform / Studio.  When the user
responds (via ``Command(resume=value)``), the node resumes and processes
the answer.
"""
from __future__ import annotations

import json
from datetime import datetime

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.types import interrupt

from src.catalog.parser import load_catalog_text, parse_catalog
from src.config import CATALOG_PATH, MODEL_NAME, MODEL_TEMPERATURE
from src.db.engine import get_connection
from src.db.repositories import AttachmentRepository, IncidentRepository, UserRepository
from src.memory.user_memory import load_user_context
from src.models import (
    Category,
    IncidentRecord,
    IncidentStatus,
    Severity,
    UserProfile,
)
from src.prompts.loader import render

_llm: ChatOpenAI | None = None


def _get_llm() -> ChatOpenAI:
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(model=MODEL_NAME, temperature=MODEL_TEMPERATURE)
    return _llm


# Fields the operator must provide (beyond what the catalog auto-fills)
REQUIRED_FIELDS: dict[str, dict] = {
    "plant": {"description": "Planta donde ocurrió el incidente", "example": "Planta Norte"},
    "line": {"description": "Línea de producción", "example": "Línea 1"},
    "work_cell": {"description": "Celda de trabajo o estación", "example": "Estación de empaque"},
    "shift": {"description": "Turno actual", "example": "Mañana / Tarde / Noche"},
    "description": {"description": "Descripción detallada de lo que sucedió", "example": "Se atascaron huevos en la curva de la banda 3"},
}

OPTIONAL_FIELDS: dict[str, dict] = {
    "machine": {"description": "Máquina involucrada (si aplica)", "example": "Clasificadora MOBA"},
    "lot_number": {"description": "Número de lote (si aplica)", "example": "LOT-20260224-001"},
    "production_order": {"description": "Orden de producción (si aplica)", "example": "OP-2026-0451"},
}

_FIELD_MAP = {
    "planta": "plant", "plant": "plant",
    "línea": "line", "linea": "line", "line": "line",
    "celda": "work_cell", "work_cell": "work_cell",
    "turno": "shift", "shift": "shift",
    "descripción": "description", "descripcion": "description",
    "máquina": "machine", "maquina": "machine",
    "lote": "lot_number", "lot": "lot_number",
    "orden": "production_order",
}

# Catalog loaded once at import
_catalog_templates = parse_catalog(CATALOG_PATH)
_catalog_by_code = {t.code: t for t in _catalog_templates}
_catalog_text = load_catalog_text(CATALOG_PATH)


def _parse_input(raw: object) -> dict:
    """Normalize interrupt input for backward compatibility.

    - str  → {"text": raw, "media": []}          (Studio / plain text)
    - dict → expects {"text": ..., "media": [...]}  (WhatsApp adapter)
    """
    if isinstance(raw, str):
        return {"text": raw, "media": []}
    if isinstance(raw, dict):
        return {
            "text": raw.get("text", ""),
            "media": raw.get("media", []),
        }
    return {"text": str(raw), "media": []}


# ─── Greeting ──────────────────────────────────────────────────────────

def greeting_node(state: dict) -> dict:
    """Identify user and greet. No interrupt — output only."""
    phone = state.get("user_phone", "")
    conn = get_connection()
    profile, recent = load_user_context(conn, phone)
    conn.close()

    if profile and profile.name:
        system_prompt = render(
            "system.j2",
            user_profile=profile,
            recent_incidents=recent,
        )
        greeting_text = f"¡Hola {profile.name}! 👋 Soy tu asistente de incidentes."
        if recent:
            last = recent[0]
            greeting_text += f"\nTu último reporte fue: {last['incident_code']} – {last['incident_name']}."
        greeting_text += "\n¿Qué incidente deseas reportar hoy? Descríbelo con tus palabras."

        return {
            "messages": [
                SystemMessage(content=system_prompt),
                AIMessage(content=greeting_text),
            ],
            "user_profile": profile.model_dump(),
            "current_node": "greeting",
            "current_incident": {
                "reported_by": phone,
                "line": profile.line or "",
                "shift": profile.shift or "",
            },
        }
    else:
        system_prompt = render("system.j2", user_profile=None, recent_incidents=[])
        return {
            "messages": [
                SystemMessage(content=system_prompt),
                AIMessage(
                    content="¡Hola! Soy tu asistente de incidentes de la fábrica. "
                    "No te tengo registrado aún.\n¿Cuál es tu nombre?"
                ),
            ],
            "user_profile": None,
            "current_node": "greeting_new",
            "current_incident": {"reported_by": phone},
        }


# ─── Register User ────────────────────────────────────────────────────

def register_user_node(state: dict) -> dict:
    """Interrupt to get user's name, extract profile, save to DB."""
    phone = state.get("user_phone", "")

    name_input = _parse_input(interrupt("Esperando nombre del usuario"))["text"]

    extraction_prompt = (
        "Del siguiente mensaje del usuario, extrae su nombre. "
        "Si también menciona área, turno, línea o rol, extráelos.\n"
        f'Mensaje: "{name_input}"\n'
        'Responde SOLO con JSON: {"name": "...", "area": "...", "shift": "...", "line": "...", "role": "..."}\n'
        "Usa string vacío para campos no mencionados."
    )
    resp = _get_llm().invoke([HumanMessage(content=extraction_prompt)])
    try:
        extracted = json.loads(resp.content.strip())
    except json.JSONDecodeError:
        extracted = {"name": name_input.strip()}

    name = extracted.get("name", "")
    if not name:
        return {
            "messages": [
                HumanMessage(content=name_input),
                AIMessage(content="No pude captar tu nombre. ¿Podrías repetirlo?"),
            ],
            "current_node": "greeting_new",
        }

    profile = UserProfile(
        phone_number=phone,
        name=name,
        area=extracted.get("area", ""),
        shift=extracted.get("shift", ""),
        line=extracted.get("line", ""),
        role=extracted.get("role", ""),
    )

    conn = get_connection()
    UserRepository(conn).upsert(profile)
    conn.close()

    incident = dict(state.get("current_incident", {}))
    incident["reported_by"] = phone
    if profile.line:
        incident["line"] = profile.line
    if profile.shift:
        incident["shift"] = profile.shift

    return {
        "messages": [
            HumanMessage(content=name_input),
            AIMessage(
                content=f"¡Encantado, {name}! Te he registrado. 😊\n"
                "¿Qué incidente deseas reportar? Descríbelo con tus palabras."
            ),
        ],
        "user_profile": profile.model_dump(),
        "current_node": "registered",
        "current_incident": incident,
    }


# ─── Collect Description ──────────────────────────────────────────────

def collect_description_node(state: dict) -> dict:
    """Interrupt to get the free-text incident description.

    Supports multimedia input: if the adapter sends a dict with media
    (image descriptions, audio transcriptions), they are concatenated
    to the text description.
    """
    raw = interrupt("Esperando descripción del incidente")
    parsed = _parse_input(raw)

    description = parsed["text"]
    media_attachments = list(state.get("media_attachments", []))

    # Append media descriptions to the text
    extra_parts: list[str] = []
    for m in parsed.get("media", []):
        if m.get("type") == "image" and m.get("description"):
            extra_parts.append(f"[Descripción visual: {m['description']}]")
        if m.get("type") == "audio" and m.get("description"):
            extra_parts.append(f"[Transcripción de audio: {m['description']}]")
        media_attachments.append(m)

    if extra_parts:
        description = (description + "\n" + "\n".join(extra_parts)).strip()

    display_text = parsed["text"] or description
    return {
        "messages": [HumanMessage(content=display_text)],
        "user_description": description,
        "media_attachments": media_attachments,
        "current_node": "collect_description",
    }


# ─── Classify ─────────────────────────────────────────────────────────

def classify_node(state: dict) -> dict:
    """Send description + catalog to LLM, return top-3 candidates."""
    user_desc = state.get("user_description", "")

    prompt = render("classify.j2", catalog_text=_catalog_text, user_description=user_desc)
    resp = _get_llm().invoke([HumanMessage(content=prompt)])

    try:
        data = json.loads(resp.content.strip())
        candidates = data.get("candidates", [])[:3]
    except json.JSONDecodeError:
        return {
            "messages": [
                AIMessage(content="No pude clasificar el incidente. ¿Puedes describirlo de otra forma?")
            ],
            "current_node": "classify_failed",
            "classification_candidates": [],
        }

    lines = ["He identificado los siguientes incidentes posibles:\n"]
    for i, c in enumerate(candidates, 1):
        conf = int(c.get("confidence", 0) * 100)
        lines.append(f"  {i}. **{c['code']}** – {c['name']} ({conf}% confianza)")
        lines.append(f"     _{c.get('reason', '')}_\n")
    lines.append("¿Cuál es el correcto? Responde con el número (1-3) o escribe 'ninguno' si no aplica.")

    return {
        "messages": [AIMessage(content="\n".join(lines))],
        "classification_candidates": candidates,
        "current_node": "classify",
    }


# ─── Confirm Classification ───────────────────────────────────────────

def confirm_classification_node(state: dict) -> dict:
    """Interrupt for user selection, then fill incident from catalog."""
    candidates = state.get("classification_candidates", [])

    selection = _parse_input(interrupt("Esperando selección (1-3 o ninguno)"))["text"]

    sel = selection.strip().lower()
    selected = None

    if sel in ("1", "2", "3"):
        idx = int(sel) - 1
        if idx < len(candidates):
            selected = candidates[idx]
    elif any(w in sel for w in ("ninguno", "none", "otro", "no")):
        return {
            "messages": [
                HumanMessage(content=selection),
                AIMessage(content="Entendido. ¿Podrías describir el incidente con más detalle?"),
            ],
            "current_node": "retry_description",
            "classification_candidates": [],
            "selected_code": None,
        }

    if not selected:
        interpret_prompt = (
            f'El usuario respondió: "{sel}" a estas opciones:\n'
            + "\n".join(f"{i+1}. {c['code']} – {c['name']}" for i, c in enumerate(candidates))
            + "\n¿Qué opción eligió? Responde SOLO con el número (1, 2, 3) o 'ninguno'."
        )
        resp = _get_llm().invoke([HumanMessage(content=interpret_prompt)])
        choice = resp.content.strip()
        if choice in ("1", "2", "3"):
            idx = int(choice) - 1
            if idx < len(candidates):
                selected = candidates[idx]

    if not selected:
        return {
            "messages": [
                HumanMessage(content=selection),
                AIMessage(content="No entendí tu selección. ¿Puedes indicar el número (1-3) o 'ninguno'?"),
            ],
            "current_node": "retry_classify",
        }

    code = selected["code"]
    template = _catalog_by_code.get(code)
    if not template:
        return {
            "messages": [
                HumanMessage(content=selection),
                AIMessage(content=f"No encontré el código {code}. Intenta de nuevo."),
            ],
            "current_node": "retry_classify",
        }

    # Auto-fill from catalog + user description
    incident = dict(state.get("current_incident", {}))
    incident.update({
        "incident_code": template.code,
        "incident_name": template.name,
        "category": template.category.value,
        "sub_category": template.sub_category,
        "severity": template.severity.value,
        "immediate_action": template.immediate_action,
        "description": state.get("user_description", ""),
    })

    # Determine missing required fields
    missing = [f for f in REQUIRED_FIELDS if not incident.get(f)]

    return {
        "messages": [
            HumanMessage(content=selection),
            AIMessage(
                content=f"✅ Seleccionado: **{template.code}** – {template.name}\n"
                f"Severidad: {template.severity.value} | Categoría: {template.category.value}\n\n"
                "Ahora necesito algunos datos adicionales para completar el reporte."
            ),
        ],
        "current_incident": incident,
        "selected_code": code,
        "missing_fields": missing,
        "current_node": "confirmed",
    }


# ─── Collect Fields ────────────────────────────────────────────────────

def collect_fields_node(state: dict) -> dict:
    """Collect one missing field per invocation via interrupt.
    The graph loops back here until all fields are filled."""
    missing = list(state.get("missing_fields", []))
    incident = dict(state.get("current_incident", {}))

    if not missing:
        return {
            "current_incident": incident,
            "missing_fields": [],
            "current_field": None,
            "current_node": "fields_done",
        }

    next_field = missing[0]
    field_info = REQUIRED_FIELDS.get(next_field, OPTIONAL_FIELDS.get(next_field, {}))

    question = f"📝 {field_info.get('description', next_field)}"
    if field_info.get("example"):
        question += f"\n   (Ejemplo: {field_info['example']})"

    answer = _parse_input(interrupt(question))["text"]

    incident[next_field] = answer.strip()
    remaining = missing[1:]

    return {
        "messages": [AIMessage(content=question), HumanMessage(content=answer)],
        "current_incident": incident,
        "missing_fields": remaining,
        "current_field": next_field,
        "current_node": "collect_fields",
    }


# ─── Confirmation ──────────────────────────────────────────────────────

def confirmation_node(state: dict) -> dict:
    """Generate incident summary for user review. No interrupt."""
    incident = dict(state.get("current_incident", {}))

    if not incident.get("date_time_reported"):
        incident["date_time_reported"] = datetime.now().isoformat()
    if not incident.get("status"):
        incident["status"] = IncidentStatus.OPEN.value

    lines = [
        "📋 **Resumen del incidente:**\n",
        f"- **Código:** {incident.get('incident_code', 'N/A')}",
        f"- **Nombre:** {incident.get('incident_name', 'N/A')}",
        f"- **Categoría:** {incident.get('category', 'N/A')}",
        f"- **Severidad:** {incident.get('severity', 'N/A')}",
        f"- **Planta:** {incident.get('plant', 'N/A')}",
        f"- **Línea:** {incident.get('line', 'N/A')}",
        f"- **Celda de trabajo:** {incident.get('work_cell', 'N/A')}",
        f"- **Turno:** {incident.get('shift', 'N/A')}",
        f"- **Descripción:** {incident.get('description', 'N/A')}",
        f"- **Acción inmediata:** {incident.get('immediate_action', 'N/A')}",
    ]
    if incident.get("machine"):
        lines.append(f"- **Máquina:** {incident['machine']}")
    if incident.get("lot_number"):
        lines.append(f"- **Lote:** {incident['lot_number']}")
    if incident.get("production_order"):
        lines.append(f"- **Orden:** {incident['production_order']}")

    lines.append("\n¿Deseas:\n1. ✅ Confirmar y guardar\n2. ✏️ Editar un campo\n3. ❌ Cancelar")

    return {
        "messages": [AIMessage(content="\n".join(lines))],
        "current_incident": incident,
        "current_node": "confirmation",
    }


# ─── Process Confirmation ─────────────────────────────────────────────

def process_confirmation_node(state: dict) -> dict:
    """Interrupt to get confirm / edit / cancel."""
    response = _parse_input(interrupt("Esperando confirmación (1=confirmar, 2=editar, 3=cancelar)"))["text"]
    resp_lower = response.strip().lower()

    affirm = any(w in resp_lower for w in ("sí", "si", "confirmo", "confirmar", "guardar", "ok", "1", "correcto"))
    edit_kw = any(w in resp_lower for w in ("editar", "cambiar", "modificar", "corregir", "2"))

    if affirm:
        return {
            "messages": [HumanMessage(content=response)],
            "confirmed": True,
            "current_node": "save",
        }
    elif edit_kw:
        return {
            "messages": [
                HumanMessage(content=response),
                AIMessage(content="¿Qué campo deseas editar? (planta, línea, celda, turno, descripción, máquina, lote, orden)"),
            ],
            "confirmed": False,
            "current_node": "edit",
        }
    else:
        return {
            "messages": [
                HumanMessage(content=response),
                AIMessage(content="Reporte cancelado."),
            ],
            "confirmed": False,
            "current_node": "cancelled",
        }


# ─── Edit ──────────────────────────────────────────────────────────────

def edit_node(state: dict) -> dict:
    """Interrupt to ask which field to edit, then route to collect_fields."""
    field_input = _parse_input(interrupt("Esperando campo a editar"))["text"]

    field = _FIELD_MAP.get(field_input.strip().lower())
    if field:
        return {
            "messages": [HumanMessage(content=field_input)],
            "missing_fields": [field],
            "current_field": None,
            "current_node": "edit_ok",
        }

    return {
        "messages": [
            HumanMessage(content=field_input),
            AIMessage(
                content="No reconocí el campo. Opciones: planta, línea, celda, turno, descripción, máquina, lote, orden."
            ),
        ],
        "current_node": "edit_retry",
    }


# ─── Save ──────────────────────────────────────────────────────────────

def save_node(state: dict) -> dict:
    """Persist incident to DB and update user profile. No interrupt."""
    incident_data = state.get("current_incident", {})

    try:
        record = IncidentRecord(
            incident_code=incident_data.get("incident_code", ""),
            incident_name=incident_data.get("incident_name", ""),
            category=Category(incident_data.get("category", "MEC")),
            sub_category=incident_data.get("sub_category", ""),
            severity=Severity(incident_data.get("severity", "MEDIUM")),
            reported_by=incident_data.get("reported_by", ""),
            plant=incident_data.get("plant", ""),
            line=incident_data.get("line", ""),
            work_cell=incident_data.get("work_cell", ""),
            shift=incident_data.get("shift", ""),
            machine=incident_data.get("machine"),
            production_order=incident_data.get("production_order"),
            lot_number=incident_data.get("lot_number"),
            description=incident_data.get("description", ""),
            immediate_action=incident_data.get("immediate_action", ""),
            status=IncidentStatus.OPEN,
        )
    except Exception as e:
        return {
            "messages": [AIMessage(content=f"Error al crear el registro: {e}")],
            "current_node": "error",
            "error": str(e),
        }

    conn = get_connection()
    repo = IncidentRepository(conn)
    incident_id = repo.save(record)

    # Save multimedia attachments
    media_attachments = state.get("media_attachments", [])
    if media_attachments:
        attach_repo = AttachmentRepository(conn)
        for att in media_attachments:
            file_path = att.get("file_path", "")
            if file_path:
                attach_repo.save(
                    incident_id=incident_id,
                    file_path=file_path,
                    media_type=att.get("type", "unknown"),
                    original_name=att.get("filename", ""),
                    description=att.get("description", ""),
                )

    profile_data = state.get("user_profile")
    if profile_data:
        profile = UserProfile(**profile_data)
        updated = False
        if not profile.line and record.line:
            profile.line = record.line
            updated = True
        if not profile.shift and record.shift:
            profile.shift = record.shift
            updated = True
        if updated:
            UserRepository(conn).upsert(profile)

    conn.close()

    return {
        "messages": [
            AIMessage(
                content=f"✅ ¡Incidente guardado exitosamente!\n"
                f"**ID:** {incident_id}\n"
                f"**Código:** {record.incident_code} – {record.incident_name}\n"
                f"**Severidad:** {record.severity.value}\n"
                f"**Estado:** {record.status.value}"
            )
        ],
        "current_node": "saved",
        "error": None,
    }
