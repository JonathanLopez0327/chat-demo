"""LangGraph conversation state definition."""
from __future__ import annotations

from typing import Annotated, Optional

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class ConversationState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    user_phone: str
    user_description: str           # free-text description from user
    current_incident: dict          # incident data (auto-filled by classify)
    current_node: str               # for routing
    error: Optional[str]
    media_attachments: list[dict]   # [{bytes, filename, type, description}]
    classify_attempts: int          # number of classification attempts (for retry limit)
