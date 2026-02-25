"""Bridge between WhatsApp messages and the LangGraph agent.

Manages per-user threads and translates multimedia into graph inputs.
"""
from __future__ import annotations

import logging
import sqlite3
import uuid
from typing import Any

from langchain_core.messages import AIMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from src.config import CHECKPOINT_DB_PATH
from src.graph.builder import build_graph
from src.media.processor import (
    analyze_image,
    save_media_file,
    transcribe_audio,
)
from src.whatsapp.client import IncomingMessage, download_media

logger = logging.getLogger(__name__)


class GraphAdapter:
    """Stateful adapter that routes WhatsApp messages into the LangGraph agent."""

    def __init__(self) -> None:
        conn = sqlite3.connect(str(CHECKPOINT_DB_PATH), check_same_thread=False)
        self._checkpointer = SqliteSaver(conn)
        self._checkpointer.setup()
        self._graph = build_graph().copy()
        # Patch the checkpointer onto the compiled graph
        self._graph.checkpointer = self._checkpointer
        # phone_number → bool (whether the thread has been started)
        self._known_threads: dict[str, bool] = {}

    # ── public API ──────────────────────────────────────────────────

    async def handle_message(self, msg: IncomingMessage) -> str:
        """Process an incoming WhatsApp message and return the reply text."""
        thread_id = msg.from_number
        config: dict[str, Any] = {
            "configurable": {"thread_id": thread_id}
        }

        # Build the input value (text + optional media)
        input_value = await self._build_input(msg)

        if not self._is_thread_started(thread_id):
            # First message from this user → invoke from START
            result = self._graph.invoke(
                {"user_phone": thread_id},
                config=config,
            )
            self._known_threads[thread_id] = True

            # The graph pauses at the first interrupt — now resume with input
            result = self._graph.invoke(
                Command(resume=input_value),
                config=config,
            )
        else:
            # Subsequent message → resume the paused graph
            result = self._graph.invoke(
                Command(resume=input_value),
                config=config,
            )

        return self._extract_reply(result)

    # ── private helpers ─────────────────────────────────────────────

    def _is_thread_started(self, thread_id: str) -> bool:
        """Check if a thread already exists (has checkpoint state)."""
        if thread_id in self._known_threads:
            return True
        # Check the checkpointer for existing state
        config = {"configurable": {"thread_id": thread_id}}
        state = self._graph.get_state(config)
        if state and state.values:
            self._known_threads[thread_id] = True
            return True
        return False

    async def _build_input(self, msg: IncomingMessage) -> str | dict:
        """Convert an IncomingMessage into the value for Command(resume=...).

        - Text only → returns plain string (backward compatible)
        - With media → returns dict with text + media list
        """
        media_items: list[dict] = []

        if msg.type == "audio" and msg.media_id:
            audio_bytes, content_type = await download_media(msg.media_id)
            transcription = await transcribe_audio(
                audio_bytes, msg.mime_type or content_type
            )
            logger.info("Audio transcribed: %s...", transcription[:80])
            # Use transcription as text if no caption
            text = msg.text or transcription
            media_items.append(
                {
                    "type": "audio",
                    "filename": f"{msg.message_id}.ogg",
                    "description": transcription,
                    "bytes": audio_bytes,
                }
            )

        elif msg.type == "image" and msg.media_id:
            image_bytes, content_type = await download_media(msg.media_id)
            description = await analyze_image(
                image_bytes, context=msg.text or ""
            )
            logger.info("Image analyzed: %s...", description[:80])
            text = msg.text or ""

            ext = ".jpg"
            if "png" in (msg.mime_type or content_type):
                ext = ".png"
            elif "webp" in (msg.mime_type or content_type):
                ext = ".webp"

            media_items.append(
                {
                    "type": "image",
                    "filename": f"{msg.message_id}{ext}",
                    "description": description,
                    "bytes": image_bytes,
                }
            )
        else:
            text = msg.text or ""

        if not media_items:
            return text

        return {"text": text, "media": media_items}

    @staticmethod
    def _extract_reply(result: dict) -> str:
        """Extract the last AIMessage text from the graph result."""
        messages = result.get("messages", [])
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content:
                return msg.content
        return "No pude generar una respuesta. Intenta de nuevo."
