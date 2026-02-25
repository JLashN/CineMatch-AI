"""
CineMatch AI — Session Manager (Module 6 / T-600 – T-603)

In-memory session store for multi-turn conversations.
Stores context, entities and past recommendations per session.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from app.models import (
    ConversationTurn,
    ExtractedEntities,
    RecommendationItem,
    SessionContext,
)

# ── In-memory store ───────────────────────────────────────

_sessions: Dict[str, SessionContext] = {}
_timestamps: Dict[str, datetime] = {}
_SESSION_TTL = timedelta(hours=2)


def get_or_create_session(session_id: Optional[str] = None) -> SessionContext:
    """Return existing session or create a new one."""
    if session_id and session_id in _sessions:
        _timestamps[session_id] = datetime.utcnow()
        return _sessions[session_id]

    new_id = session_id or str(uuid.uuid4())
    ctx = SessionContext(session_id=new_id)
    _sessions[new_id] = ctx
    _timestamps[new_id] = datetime.utcnow()
    return ctx


def save_turn(
    session_id: str,
    user_msg: str,
    assistant_msg: str,
    entities: Optional[ExtractedEntities] = None,
    recommendations: Optional[List[RecommendationItem]] = None,
) -> None:
    """Append a conversation turn and update session state."""
    ctx = _sessions.get(session_id)
    if not ctx:
        return

    ctx.turns.append(ConversationTurn(role="user", content=user_msg))
    ctx.turns.append(ConversationTurn(role="assistant", content=assistant_msg))

    if entities:
        ctx.last_entities = entities
    if recommendations:
        ctx.last_recommendations = recommendations

    # Compress history if it gets too long (keep last 10 turns)
    if len(ctx.turns) > 20:
        ctx.turns = ctx.turns[-20:]


def get_session(session_id: str) -> Optional[SessionContext]:
    """Get a session by ID."""
    return _sessions.get(session_id)


def delete_session(session_id: str) -> bool:
    """Delete a session. Returns True if it existed."""
    existed = session_id in _sessions
    _sessions.pop(session_id, None)
    _timestamps.pop(session_id, None)
    return existed


def cleanup_expired() -> int:
    """Remove sessions older than TTL. Returns count removed."""
    now = datetime.utcnow()
    expired = [sid for sid, ts in _timestamps.items() if now - ts > _SESSION_TTL]
    for sid in expired:
        _sessions.pop(sid, None)
        _timestamps.pop(sid, None)
    return len(expired)
