"""LangGraph node functions for the simplified incident reporting flow.

4 nodes, 1 user interaction:
1. greeting_node      — saludo genérico (no interrupt)
2. collect_description — recibe descripción del usuario (interrupt)
3. classify_node      — clasifica automáticamente con LLM (no interrupt)
4. save_node          — guarda en BD (no interrupt)
"""
from __future__ import annotations

import json
from datetime import datetime

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.types import interrupt

from src.catalog.parser import load_catalog_text, parse_catalog
from src.config import CATALOG_PATH, MODEL_NAME, MODEL_TEMPERATURE
from src.content_safety import check_content_safety
from src.db.engine import get_connection
from src.db.repositories import AttachmentRepository, IncidentRepository, UserRepository
from src.models import (
    Category,
    IncidentRecord,
    IncidentStatus,
    Severity,
    TicketType,
)
from src.prompts.loader import render

_llm: ChatOpenAI | None = None


def _get_llm() -> ChatOpenAI:
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(model=MODEL_NAME, temperature=MODEL_TEMPERATURE)
    return _llm


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
    """Simple greeting. No user lookup, no interrupt."""
    phone = state.get("user_phone", "")

    system_prompt = render("system.j2", user_profile=None, recent_incidents=[])
    greeting_text = (
        "Hola, soy el asistente de soporte. "
        "Cuéntame qué pasó — escríbeme, mándame una foto o una nota de voz."
    )

    return {
        "messages": [
            SystemMessage(content=system_prompt),
            AIMessage(content=greeting_text),
        ],
        "current_node": "greeting",
        "current_incident": {"reported_by": phone},
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
    """Classify automatically using LLM. Top-1 only, no user selection.

    Generates a summary and asks user to confirm.
    If confidence < 0.5 or JSON parse fails → ask for more details (max 2 attempts).
    After 2 failed attempts → reject as unhandled incident.
    """
    user_desc = state.get("user_description", "")
    attempts = state.get("classify_attempts", 0) + 1

    # Message shown when max retries are exhausted
    _UNHANDLED_MSG = (
        "No parece un incidente relacionado con los sistemas o equipos de la agencia.\n\n"
        "Si necesitas reportar un problema técnico (computadoras, red, sistema de apuestas, etc.), "
        "dime y te ayudo.\n\n"
        "Si se trata de otro tipo de situación, puede que debas comunicarte con el área correspondiente."
    )
    _MAX_CLASSIFY_ATTEMPTS = 2

    # ── Content Safety Check ──────────────────────────────────────
    media_descriptions = [
        m.get("description", "")
        for m in state.get("media_attachments", [])
        if m.get("description")
    ]
    safety_result = check_content_safety(user_desc, media_descriptions)

    if not safety_result.is_safe:
        if attempts >= _MAX_CLASSIFY_ATTEMPTS:
            return {
                "messages": [AIMessage(content=_UNHANDLED_MSG)],
                "current_node": "unhandled",
                "classify_attempts": attempts,
            }
        return {
            "messages": [
                AIMessage(
                    content="Ese contenido no está relacionado con operaciones de agencia. "
                    "¿Tienes algún problema con tu terminal, impresora o algún equipo? "
                    "Cuéntame y te ayudo."
                )
            ],
            "current_node": "classify_failed",
            "classify_attempts": attempts,
        }

    # ── Classification ────────────────────────────────────────────
    # Pass the explicit list of valid codes to the prompt
    valid_codes = ", ".join(sorted(_catalog_by_code.keys()))
    prompt = render(
        "classify.j2",
        catalog_text=_catalog_text,
        user_description=user_desc,
        valid_codes=valid_codes,
    )
    resp = _get_llm().invoke([HumanMessage(content=prompt)])

    try:
        data = json.loads(resp.content.strip())
        candidate = data.get("candidate", {})
        confidence = candidate.get("confidence", 0)
    except (json.JSONDecodeError, AttributeError):
        if attempts >= _MAX_CLASSIFY_ATTEMPTS:
            return {
                "messages": [AIMessage(content=_UNHANDLED_MSG)],
                "current_node": "unhandled",
                "classify_attempts": attempts,
            }
        return {
            "messages": [
                AIMessage(
                    content="No logré ubicar el tipo de incidente con esa información. "
                    "¿Me puedes dar más detalles de lo que pasó?"
                )
            ],
            "current_node": "classify_failed",
            "classify_attempts": attempts,
        }

    if confidence < 0.5 or not candidate.get("code"):
        if attempts >= _MAX_CLASSIFY_ATTEMPTS:
            return {
                "messages": [AIMessage(content=_UNHANDLED_MSG)],
                "current_node": "unhandled",
                "classify_attempts": attempts,
            }
        return {
            "messages": [
                AIMessage(
                    content="No estoy seguro de qué tipo de incidente es. "
                    "¿Me puedes dar más detalles?"
                )
            ],
            "current_node": "classify_failed",
            "classify_attempts": attempts,
        }

    code = candidate["code"]
    template = _catalog_by_code.get(code)
    if not template:
        if attempts >= _MAX_CLASSIFY_ATTEMPTS:
            return {
                "messages": [AIMessage(content=_UNHANDLED_MSG)],
                "current_node": "unhandled",
                "classify_attempts": attempts,
            }
        return {
            "messages": [
                AIMessage(
                    content="No encontré ese código en el catálogo. "
                    "¿Me puedes describir el problema con otras palabras?"
                )
            ],
            "current_node": "classify_failed",
            "classify_attempts": attempts,
        }

    # Auto-fill incident ALWAYS from the catalog template (never from LLM output)
    # This ensures we never store hallucinated names or data
    incident = dict(state.get("current_incident", {}))
    incident.update({
        "incident_code": template.code,
        "incident_name": template.name,       # Always from catalog, never from LLM
        "category": template.category.value,
        "sub_category": template.sub_category,
        "severity": template.severity.value,
        "ticket_type": template.ticket_type.value,
        "sla": template.sla,
        "description": user_desc,
        "date_time_reported": datetime.now().isoformat(),
        "status": IncidentStatus.OPEN.value,
    })

    return {
        "current_incident": incident,
        "current_node": "classify_ok",
        "classify_attempts": attempts,
    }




# ─── Save ──────────────────────────────────────────────────────────────

def save_node(state: dict) -> dict:
    """Persist incident to DB. No interrupt."""
    incident_data = state.get("current_incident", {})

    try:
        record = IncidentRecord(
            incident_code=incident_data.get("incident_code", ""),
            incident_name=incident_data.get("incident_name", ""),
            category=Category(incident_data.get("category", "POS")),
            sub_category=incident_data.get("sub_category", ""),
            severity=Severity(incident_data.get("severity", "MEDIUM")),
            ticket_type=TicketType(incident_data.get("ticket_type", "Incidente")),
            sla=incident_data.get("sla", ""),
            reported_by=incident_data.get("reported_by", ""),
            agency=incident_data.get("agency", ""),
            shift=incident_data.get("shift", ""),
            description=incident_data.get("description", ""),
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
    # Ensure user exists in DB to satisfy FK constraint
    UserRepository(conn).ensure_exists(record.reported_by)
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

    conn.close()

    return {
        "messages": [
            AIMessage(
                content=f"Listo, registré tu reporte con folio *{incident_id}* "
                f"(*{record.incident_code}* – {record.incident_name}). "
                "El equipo de soporte ya lo tiene y le dará seguimiento."
                "Si el equipo sigue fallando o pasa algo más, escríbeme por aquí."
            )
        ],
        "current_node": "saved",
        "error": None,
    }
