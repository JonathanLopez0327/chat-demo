"""Bridge between WhatsApp messages and the LangGraph agent.

Manages per-user threads and translates multimedia into graph inputs.
"""
from __future__ import annotations

import logging
import sqlite3
import time
from typing import Any

from langchain_core.messages import AIMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from src.config import CHECKPOINT_DB_PATH
from src.db.engine import get_connection
from src.db.repositories import (
    ConversationLogRepository,
    ConversationRepository,
    IncidentRepository,
    UserRepository,
)
from src.models import ConversationStatus
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

    def reset_thread(self, thread_id: str) -> None:
        """Remove all checkpoint data for a thread, forcing a fresh start."""
        self._known_threads.pop(thread_id, None)
        # Delete checkpoints from SQLite directly
        conn = self._checkpointer.conn
        conn.execute("DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,))
        conn.execute("DELETE FROM writes WHERE thread_id = ?", (thread_id,))
        conn.commit()
        logger.info("Thread %s reset", thread_id)

    # Greeting / chitchat patterns that should NOT be treated as input data
    _GREETING_PATTERNS = {
        "hola", "hello", "hi", "hey", "buenos dias", "buenos días",
        "buenas tardes", "buenas noches", "buenas", "buen dia", "buen día",
        "que tal", "qué tal", "ola", "saludos", "holi", "holaa",
    }

    def _is_greeting(self, text: str) -> bool:
        """Check if a message is just a greeting with no real content."""
        normalized = text.strip().lower().rstrip("!.?,;")
        return normalized in self._GREETING_PATTERNS

    def _handle_command(self, text: str, thread_id: str) -> str | None:
        """Check if *text* is a slash command and execute it.

        Returns a response string if it was a command, or ``None`` to
        continue with the normal LangGraph flow.
        """
        stripped = text.strip().lower()
        if not stripped.startswith("/"):
            return None

        cmd = stripped.split()[0]

        if cmd == "/reset":
            return self._exec_db_command(self._cmd_reset, thread_id)

        if cmd == "/borrar":
            return self._exec_db_command(self._cmd_borrar, thread_id)

        if cmd == "/eliminar_usuario":
            return self._exec_db_command(self._cmd_eliminar_usuario, thread_id)

        if cmd == "/ayuda":
            return (
                "Comandos disponibles:\n"
                "  /reset — Reiniciar la conversación actual\n"
                "  /borrar — Eliminar tu perfil y reiniciar el chat\n"
                "  /eliminar_usuario — Eliminar solo tu perfil de la BD\n"
                "  /ayuda — Mostrar esta lista de comandos"
            )

        return (
            f"Comando desconocido: {cmd}\n"
            "Envía /ayuda para ver los comandos disponibles."
        )

    # ── command implementations ────────────────────────────────────

    def _cmd_reset(self, thread_id: str) -> str:
        app_conn = get_connection()
        try:
            conv_repo = ConversationRepository(app_conn)
            active = conv_repo.get_active(thread_id)
            if active:
                conv_repo.finish(active.id, ConversationStatus.CANCELLED, outcome="Reset por usuario")
            self.reset_thread(thread_id)
            ConversationLogRepository(app_conn).delete_thread(thread_id)
        finally:
            app_conn.close()
        return "Conversación reiniciada. Puedes empezar de nuevo enviando un mensaje."

    def _cmd_borrar(self, thread_id: str) -> str:
        app_conn = get_connection()
        try:
            conv_repo = ConversationRepository(app_conn)
            active = conv_repo.get_active(thread_id)
            if active:
                conv_repo.finish(active.id, ConversationStatus.CANCELLED, outcome="Borrado por usuario")
            self.reset_thread(thread_id)
            ConversationLogRepository(app_conn).delete_thread(thread_id)
            IncidentRepository(app_conn).delete_by_user(thread_id)
            UserRepository(app_conn).delete(thread_id)
        finally:
            app_conn.close()
        return (
            "Tu perfil y conversación han sido eliminados. "
            "Si envías un nuevo mensaje, comenzarás desde cero."
        )

    def _cmd_eliminar_usuario(self, thread_id: str) -> str:
        app_conn = get_connection()
        try:
            IncidentRepository(app_conn).delete_by_user(thread_id)
            UserRepository(app_conn).delete(thread_id)
        finally:
            app_conn.close()
        return (
            "Tu perfil ha sido eliminado de la base de datos. "
            "La conversación actual sigue activa."
        )

    @staticmethod
    def _exec_db_command(fn, thread_id: str, max_retries: int = 3) -> str:
        """Execute a DB-writing command with retries on lock errors."""
        for attempt in range(max_retries):
            try:
                return fn(thread_id)
            except sqlite3.OperationalError as exc:
                if "locked" in str(exc) and attempt < max_retries - 1:
                    wait = 0.3 * (attempt + 1)
                    logger.warning("DB locked on attempt %d, retrying in %.1fs…", attempt + 1, wait)
                    time.sleep(wait)
                else:
                    raise
        return "Error interno al procesar el comando. Intenta de nuevo."

    async def handle_message(self, msg: IncomingMessage) -> str:
        """Process an incoming WhatsApp message and return the reply text."""
        thread_id = msg.from_number
        config: dict[str, Any] = {
            "configurable": {"thread_id": thread_id}
        }

        # Check for slash commands before touching the graph
        if msg.text:
            command_reply = self._handle_command(msg.text, thread_id)
            if command_reply is not None:
                return command_reply

        # Build the input value (text + optional media)
        input_value = await self._build_input(msg)

        # --- Conversation tracking setup ---
        app_conn = get_connection()
        conv_repo = ConversationRepository(app_conn)
        log_repo = ConversationLogRepository(app_conn)

        if not self._is_thread_started(thread_id):
            # First message → create a new conversation session
            conversation = conv_repo.create(thread_id)

            # First message from this user → invoke from START
            result = self._graph.invoke(
                {"user_phone": thread_id},
                config=config,
            )
            self._known_threads[thread_id] = True

            # Log the user message
            user_text = input_value if isinstance(input_value, str) else input_value.get("text", "")
            log_repo.append(thread_id, "user", user_text, conversation.id)
            conv_repo.increment_messages(conversation.id)

            # If the first message is a greeting, just return the
            # greeting response — don't feed it as input data
            text_part = input_value if isinstance(input_value, str) else input_value.get("text", "")
            if self._is_greeting(text_part):
                reply = self._extract_reply(result)
                log_repo.append(thread_id, "assistant", reply, conversation.id)
                conv_repo.increment_messages(conversation.id)
                app_conn.close()
                return reply

            # The message has real content → resume immediately
            result = self._graph.invoke(
                Command(resume=input_value),
                config=config,
            )
        else:
            # Get or create conversation for this thread
            conversation = conv_repo.get_active(thread_id)
            if not conversation:
                conversation = conv_repo.create(thread_id)

            # Log the user message
            user_text = input_value if isinstance(input_value, str) else input_value.get("text", "")
            log_repo.append(thread_id, "user", user_text, conversation.id)
            conv_repo.increment_messages(conversation.id)

            # Subsequent message → resume the paused graph
            result = self._graph.invoke(
                Command(resume=input_value),
                config=config,
            )

        reply = self._extract_reply(result)

        # Log the assistant reply
        log_repo.append(thread_id, "assistant", reply, conversation.id)
        conv_repo.increment_messages(conversation.id)

        # If the graph reached a terminal state, finish the conversation
        if self._is_thread_finished(thread_id):
            self._known_threads.pop(thread_id, None)
            # Determine outcome from graph state
            state = self._graph.get_state(config)
            current_node = (state.values or {}).get("current_node", "") if state and state.values else ""
            if current_node == "saved":
                conv_repo.finish(conversation.id, ConversationStatus.COMPLETED, outcome="Incidente creado")
            else:
                conv_repo.finish(conversation.id, ConversationStatus.COMPLETED, outcome="Conversación completada")

        app_conn.close()
        return reply

    # ── private helpers ─────────────────────────────────────────────

    def _is_thread_finished(self, thread_id: str) -> bool:
        """Check if the graph has reached END (no more pending tasks)."""
        config = {"configurable": {"thread_id": thread_id}}
        state = self._graph.get_state(config)
        if not state or not state.values:
            return True
        if not state.next:
            return True
        return False

    def _is_thread_started(self, thread_id: str) -> bool:
        """Check if an active (non-finished) thread exists."""
        if thread_id in self._known_threads:
            return True
        config = {"configurable": {"thread_id": thread_id}}
        state = self._graph.get_state(config)
        if state and state.values:
            if state.next:
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
