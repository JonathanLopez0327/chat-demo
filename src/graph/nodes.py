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
    "plant": {"description": "¿En qué planta fue?", "example": "Planta Norte"},
    "line": {"description": "¿En qué línea?", "example": "Línea 1"},
    "work_cell": {"description": "¿En qué celda o estación?", "example": "Estación de empaque"},
    "shift": {"description": "¿Qué turno?", "example": "Mañana, Tarde o Noche"},
    "description": {"description": "Dame más detalle de lo que pasó", "example": "Se atascaron huevos en la curva de la banda 3"},
}

OPTIONAL_FIELDS: dict[str, dict] = {
    "machine": {"description": "¿Qué máquina? (si aplica)", "example": "Clasificadora MOBA"},
    "lot_number": {"description": "¿Número de lote? (si aplica)", "example": "LOT-20260224-001"},
    "production_order": {"description": "¿Orden de producción? (si aplica)", "example": "OP-2026-0451"},
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
        first_name = profile.name.split()[0]
        greeting_text = f"Hola {first_name}, ¿cómo va el turno?"
        if recent:
            last = recent[0]
            greeting_text += (
                f"\nVi que el último reporte fue por *{last['incident_name']}*."
            )
        greeting_text += (
            "\n\nCuéntame qué pasó y te ayudo a levantar el reporte. "
            "Puedes escribirme, mandarme una foto o una nota de voz."
        )

        return {
            "messages": [
                SystemMessage(content=system_prompt),
                AIMessage(content=greeting_text),
            ],
            "user_profile": profile.model_dump(),
            "current_node": "greeting",
            "awaiting_input": "incident_description",
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
                    content="Hola, soy el asistente de planta. "
                    "Te ayudo a reportar incidentes de forma rápida.\n\n"
                    "No te tengo registrado aún. ¿Cómo te llamas?"
                ),
            ],
            "user_profile": None,
            "current_node": "greeting_new",
            "awaiting_input": "user_name",
            "current_incident": {"reported_by": phone},
        }


# ─── Register User ────────────────────────────────────────────────────

def register_user_node(state: dict) -> dict:
    """Interrupt to get user's name, extract profile, save to DB."""
    phone = state.get("user_phone", "")

    name_input = _parse_input(interrupt("Esperando nombre del usuario"))["text"]

    extraction_prompt = (
        "Del siguiente mensaje del usuario, extrae ÚNICAMENTE su nombre propio "
        "(nombre y apellido si los da). No incluyas frases como 'mi nombre es', "
        "'me llamo', 'soy', etc. Solo el nombre limpio.\n"
        "Si también menciona área, turno, línea o rol, extráelos.\n"
        f'Mensaje: "{name_input}"\n'
        "Ejemplos:\n"
        '  "Mi nombre es Juan Pérez" → {"name": "Juan Pérez", ...}\n'
        '  "Soy María" → {"name": "María", ...}\n'
        '  "Pedro, de la línea 2, turno mañana" → {"name": "Pedro", "line": "Línea 2", "shift": "Mañana", ...}\n'
        'Responde SOLO con JSON: {"name": "...", "area": "...", "shift": "...", "line": "...", "role": "..."}\n'
        "Usa string vacío para campos no mencionados."
    )
    resp = _get_llm().invoke([HumanMessage(content=extraction_prompt)])
    try:
        extracted = json.loads(resp.content.strip())
    except json.JSONDecodeError:
        extracted = {"name": name_input.strip()}

    name = extracted.get("name", "").strip()
    # Clean up common prefixes the LLM might leave in
    for prefix in ("mi nombre es ", "me llamo ", "soy "):
        if name.lower().startswith(prefix):
            name = name[len(prefix):]
    name = name.strip().title()

    if not name:
        return {
            "messages": [
                HumanMessage(content=name_input),
                AIMessage(
                    content="No alcancé a captar tu nombre. ¿Cómo te llamas?"
                ),
            ],
            "current_node": "greeting_new",
            "awaiting_input": "user_name",
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
                content=f"Listo {name}, ya te tengo registrado.\n\n"
                "Cuéntame, ¿qué pasó? Puedes escribirme o mandarme una foto o nota de voz."
            ),
        ],
        "user_profile": profile.model_dump(),
        "current_node": "registered",
        "awaiting_input": "incident_description",
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
        "awaiting_input": None,  # next node (classify) has no interrupt
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
                AIMessage(
                    content="No logré ubicar el tipo de incidente con esa información. "
                    "¿Me puedes dar más detalles de lo que pasó?"
                )
            ],
            "current_node": "classify_failed",
            "classification_candidates": [],
        }

    lines = ["Ok, esto podría ser:\n"]
    for i, c in enumerate(candidates, 1):
        lines.append(f"{i}. *{c['code']}* – {c['name']}")
        reason = c.get("reason", "")
        if reason:
            lines.append(f"   _{reason}_\n")
    lines.append("¿Cuál es? Dime el número, o *ninguno* si no aplica.")

    return {
        "messages": [AIMessage(content="\n".join(lines))],
        "classification_candidates": candidates,
        "current_node": "classify",
        "awaiting_input": "classification_selection",
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
                AIMessage(
                    content="Entendido. ¿Me puedes dar más detalles para ubicarlo mejor?"
                ),
            ],
            "current_node": "retry_description",
            "awaiting_input": "incident_description",
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
                AIMessage(
                    content="No te entendí. ¿Me dices el número (1, 2 o 3) o *ninguno*?"
                ),
            ],
            "current_node": "retry_classify",
            "awaiting_input": "classification_selection",
        }

    code = selected["code"]
    template = _catalog_by_code.get(code)
    if not template:
        return {
            "messages": [
                HumanMessage(content=selection),
                AIMessage(content=f"No encontré el código {code} en el catálogo. ¿Puedes elegir de nuevo?"),
            ],
            "current_node": "retry_classify",
            "awaiting_input": "classification_selection",
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
                content=f"Perfecto: *{template.code}* – {template.name}\n"
                f"Severidad: {template.severity.value}\n\n"
                "Necesito unos datos más para completar el reporte."
            ),
        ],
        "current_incident": incident,
        "selected_code": code,
        "missing_fields": missing,
        "current_field": missing[0] if missing else None,
        "awaiting_input": f"field:{missing[0]}" if missing else None,
        "current_node": "confirmed",
    }


# ─── Collect Fields ────────────────────────────────────────────────────

def collect_fields_node(state: dict) -> dict:
    """Collect one missing field per invocation via interrupt.

    The graph loops back here until all fields are filled.
    Uses ``current_field`` and ``awaiting_input`` to guarantee
    the answer is stored in the correct field.
    """
    missing = list(state.get("missing_fields", []))
    incident = dict(state.get("current_incident", {}))

    if not missing:
        return {
            "current_incident": incident,
            "missing_fields": [],
            "current_field": None,
            "awaiting_input": None,
            "current_node": "fields_done",
        }

    # Determine the field we are about to ask for.
    # If current_field is already set (from a previous node or loop iteration),
    # honour it; otherwise pick the first missing field.
    target_field = state.get("current_field") or missing[0]
    if target_field not in missing:
        target_field = missing[0]

    field_info = REQUIRED_FIELDS.get(target_field, OPTIONAL_FIELDS.get(target_field, {}))

    question = field_info.get("description", target_field)
    if field_info.get("example"):
        question += f"\n_(Ej: {field_info['example']})_"

    # ── interrupt — graph pauses here ──
    answer = _parse_input(interrupt(question))["text"]

    # Store the answer in the field that was explicitly requested
    incident[target_field] = answer.strip()
    remaining = [f for f in missing if f != target_field]

    # Prepare next field info for state so the next iteration knows
    next_field = remaining[0] if remaining else None

    return {
        "messages": [AIMessage(content=question), HumanMessage(content=answer)],
        "current_incident": incident,
        "missing_fields": remaining,
        "current_field": next_field,
        "awaiting_input": f"field:{next_field}" if next_field else None,
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
        "Listo, este es el resumen:\n",
        f"*{incident.get('incident_code', '')}* – {incident.get('incident_name', '')}",
        f"Severidad: {incident.get('severity', '')}",
        f"Planta: {incident.get('plant', '')} · Línea: {incident.get('line', '')} · Celda: {incident.get('work_cell', '')}",
        f"Turno: {incident.get('shift', '')}",
        f"Descripción: {incident.get('description', '')}",
        f"Acción inmediata: {incident.get('immediate_action', '')}",
    ]
    if incident.get("machine"):
        lines.append(f"Máquina: {incident['machine']}")
    if incident.get("lot_number"):
        lines.append(f"Lote: {incident['lot_number']}")
    if incident.get("production_order"):
        lines.append(f"Orden: {incident['production_order']}")

    lines.append("\n¿Lo guardo así?\n1. Sí, guardar\n2. Quiero editar algo\n3. Cancelar")

    return {
        "messages": [AIMessage(content="\n".join(lines))],
        "current_incident": incident,
        "current_node": "confirmation",
        "awaiting_input": "confirm_save",
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
            "awaiting_input": None,
        }
    elif edit_kw:
        return {
            "messages": [
                HumanMessage(content=response),
                AIMessage(
                    content="Dale, ¿qué dato corrijo? "
                    "(planta, línea, celda, turno, descripción, máquina, lote u orden)"
                ),
            ],
            "confirmed": False,
            "current_node": "edit",
            "awaiting_input": "edit_field_name",
        }
    else:
        return {
            "messages": [
                HumanMessage(content=response),
                AIMessage(
                    content="Ok, cancelado. Si después necesitas reportar algo, aquí estoy."
                ),
            ],
            "confirmed": False,
            "current_node": "cancelled",
            "awaiting_input": None,
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
            "current_field": field,
            "awaiting_input": f"field:{field}",
            "current_node": "edit_ok",
        }

    return {
        "messages": [
            HumanMessage(content=field_input),
            AIMessage(
                content="No ubico ese campo. "
                "Dime: planta, línea, celda, turno, descripción, máquina, lote u orden."
            ),
        ],
        "current_node": "edit_retry",
        "awaiting_input": "edit_field_name",
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
            "messages": [
                AIMessage(
                    content=f"Hubo un problema al guardar: {e}\n"
                    "Intenta de nuevo o escríbeme para empezar uno nuevo."
                )
            ],
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
                content=f"Listo, quedó registrado con folio *{incident_id}*.\n"
                f"{record.incident_code} – {record.incident_name} (Severidad: {record.severity.value})\n\n"
                "Ya lo tiene el equipo. Si pasa algo más, mándame mensaje."
            )
        ],
        "current_node": "saved",
        "error": None,
    }
