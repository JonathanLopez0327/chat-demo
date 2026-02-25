"""Client for Meta's WhatsApp Cloud API (Graph API v21.0)."""
from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from src.config import WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID

logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"


@dataclass
class IncomingMessage:
    from_number: str
    message_id: str
    type: str  # "text" | "image" | "audio"
    text: str | None = None
    media_id: str | None = None
    mime_type: str | None = None
    timestamp: str = ""


async def send_text_message(to: str, body: str) -> dict:
    """Send a text message via WhatsApp Cloud API."""
    url = f"{GRAPH_API_BASE}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "text": {"body": body},
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()


async def download_media(media_id: str) -> tuple[bytes, str]:
    """Download media from WhatsApp.

    1. GET /v21.0/{media_id} → retrieves the download URL
    2. GET {url} with auth header → downloads the bytes

    Returns (file_bytes, content_type).
    """
    headers = {"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"}
    async with httpx.AsyncClient(timeout=60) as client:
        # Step 1: get the media URL
        meta_resp = await client.get(
            f"{GRAPH_API_BASE}/{media_id}", headers=headers
        )
        meta_resp.raise_for_status()
        media_url = meta_resp.json()["url"]

        # Step 2: download the actual file
        file_resp = await client.get(media_url, headers=headers)
        file_resp.raise_for_status()
        content_type = file_resp.headers.get("content-type", "application/octet-stream")
        return file_resp.content, content_type


def parse_webhook_message(payload: dict) -> list[IncomingMessage]:
    """Extract incoming messages from a WhatsApp webhook payload."""
    messages: list[IncomingMessage] = []

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            if "messages" not in value:
                continue
            for msg in value["messages"]:
                msg_type = msg.get("type", "")
                incoming = IncomingMessage(
                    from_number=msg.get("from", ""),
                    message_id=msg.get("id", ""),
                    type=msg_type,
                    timestamp=msg.get("timestamp", ""),
                )
                if msg_type == "text":
                    incoming.text = msg.get("text", {}).get("body", "")
                elif msg_type == "image":
                    img = msg.get("image", {})
                    incoming.media_id = img.get("id")
                    incoming.mime_type = img.get("mime_type")
                    incoming.text = img.get("caption")
                elif msg_type == "audio":
                    aud = msg.get("audio", {})
                    incoming.media_id = aud.get("id")
                    incoming.mime_type = aud.get("mime_type")
                else:
                    # Unsupported type – skip
                    continue
                messages.append(incoming)

    return messages
