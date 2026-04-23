"""Global WebSocket connection registry for real-time messaging."""
from __future__ import annotations

import logging
from fastapi import WebSocket

logger = logging.getLogger(__name__)

_user_connections: dict[str, WebSocket] = {}


def register_user(conversation_id: str, ws: WebSocket) -> None:
    _user_connections[conversation_id] = ws
    logger.debug("WS registered: %s (total: %d)", conversation_id, len(_user_connections))


def unregister_user(conversation_id: str) -> None:
    _user_connections.pop(conversation_id, None)
    logger.debug("WS unregistered: %s (total: %d)", conversation_id, len(_user_connections))


def get_user_ws(conversation_id: str) -> WebSocket | None:
    return _user_connections.get(conversation_id)
