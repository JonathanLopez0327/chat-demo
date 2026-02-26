"""FastAPI webhook server for WhatsApp Cloud API integration."""
from __future__ import annotations

import logging

from fastapi import BackgroundTasks, FastAPI, Query, Request
from fastapi.responses import PlainTextResponse

from src.config import WHATSAPP_VERIFY_TOKEN
from src.db.engine import init_db
from src.whatsapp.client import parse_webhook_message, send_text_message
from src.whatsapp.graph_adapter import GraphAdapter

logger = logging.getLogger(__name__)

app = FastAPI(title="WhatsApp Incident Bot")

_adapter: GraphAdapter | None = None


def _get_adapter() -> GraphAdapter:
    global _adapter
    if _adapter is None:
        init_db()
        _adapter = GraphAdapter()
    return _adapter


@app.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
) -> PlainTextResponse:
    """Webhook verification endpoint required by Meta."""
    if hub_mode == "subscribe" and hub_verify_token == WHATSAPP_VERIFY_TOKEN:
        logger.info("Webhook verified successfully")
        return PlainTextResponse(content=hub_challenge)
    logger.warning("Webhook verification failed: invalid token")
    return PlainTextResponse(content="Forbidden", status_code=403)


@app.post("/webhook")
async def receive_message(
    request: Request, background_tasks: BackgroundTasks
) -> dict:
    """Receive incoming WhatsApp messages.

    Returns 200 immediately (Meta requires <5s response) and
    processes the message in a background task.
    """
    payload = await request.json()
    messages = parse_webhook_message(payload)

    for msg in messages:
        background_tasks.add_task(_process_message, msg)

    return {"status": "ok"}


@app.post("/reset/{phone_number}")
async def reset_thread(phone_number: str) -> dict:
    """Reset a user's conversation thread so the next message starts fresh.

    Usage: POST /reset/5215512345678
    """
    adapter = _get_adapter()
    adapter.reset_thread(phone_number)
    return {"status": "ok", "phone": phone_number, "message": "Thread reset"}


async def _process_message(msg) -> None:
    """Process a single incoming message in the background."""
    try:
        adapter = _get_adapter()
        reply = await adapter.handle_message(msg)
        await send_text_message(msg.from_number, reply)
        logger.info("Replied to %s: %s...", msg.from_number, reply[:80])
    except Exception:
        logger.exception("Error processing message from %s", msg.from_number)
        try:
            await send_text_message(
                msg.from_number,
                "Ocurrió un error procesando tu mensaje. Intenta de nuevo.",
            )
        except Exception:
            logger.exception("Failed to send error reply")
