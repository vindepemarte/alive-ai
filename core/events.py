"""
Core: Events - Nervous System
Connects all modules via events. No module depends directly on another.
"""

from __future__ import annotations

import asyncio
import inspect
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from typing import Any, Callable, Deque, Dict, Generic, List, Mapping, TypeVar
import traceback
import uuid


T = TypeVar("T")


class EventPriority(IntEnum):
    LOW = 10
    NORMAL = 50
    HIGH = 80
    CRITICAL = 100


@dataclass(frozen=True, slots=True)
class HistoryOptions:
    record: bool = False
    include_payload: bool = False
    max_events: int = 500


@dataclass(frozen=True, slots=True)
class AuditOptions:
    record: bool = False
    include_payload: bool = False
    redact: tuple[str, ...] = (
        "text", "user_message", "ai_response", "file_path", "content",
        "api_key", "token", "password", "secret", "authorization",
    )


@dataclass(frozen=True, slots=True)
class NervousEvent(Generic[T]):
    name: str
    payload: T
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    priority: EventPriority = EventPriority.NORMAL
    source: str | None = None
    correlation_id: str | None = None
    causation_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    history: HistoryOptions = field(default_factory=HistoryOptions)
    audit: AuditOptions = field(default_factory=AuditOptions)

    def to_dict(self, *, include_payload: bool = True) -> dict[str, Any]:
        data = {
            "name": self.name,
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "priority": int(self.priority),
            "source": self.source,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "metadata": dict(self.metadata),
        }
        if include_payload:
            data["payload"] = self.payload
        return data


@dataclass(slots=True)
class _Listener:
    callback: Callable
    envelope: bool = False
    listener_priority: int = 0


def _priority(value: EventPriority | int | str) -> EventPriority:
    if isinstance(value, EventPriority):
        return value
    try:
        return EventPriority(int(value))
    except Exception:
        return EventPriority.NORMAL


def _redact_payload(payload: Any, redact: tuple[str, ...]) -> Any:
    redact_keys = {str(item).lower() for item in redact}
    if isinstance(payload, Mapping):
        redacted = {}
        for key, value in payload.items():
            if str(key).lower() in redact_keys:
                redacted[key] = "[redacted]"
            else:
                redacted[key] = _redact_payload(value, redact)
        return redacted
    if isinstance(payload, list):
        return [_redact_payload(item, redact) for item in payload]
    return payload


class NervousSystem:
    """Central nervous system - event bus"""

    def __init__(self):
        self.listeners: Dict[str, List[_Listener]] = {}
        self.heart = None  # Reference for reactions
        self._history: Deque[NervousEvent] = deque(maxlen=500)
        self._audit: Deque[dict[str, Any]] = deque(maxlen=500)

    def on(self, event: str, callback: Callable, *, envelope: bool = False, listener_priority: int = 0):
        """Register listener for event.

        Legacy listeners receive the payload dict. New listeners can request
        the full NervousEvent envelope with envelope=True.
        """
        if event not in self.listeners:
            self.listeners[event] = []
        self.listeners[event].append(_Listener(callback, envelope=envelope, listener_priority=listener_priority))
        self.listeners[event].sort(key=lambda item: item.listener_priority, reverse=True)

    def _normalize(
        self,
        event: str | NervousEvent,
        data: dict | None = None,
        *,
        priority: EventPriority | int | str = EventPriority.NORMAL,
        source: str | None = None,
        correlation_id: str | None = None,
        causation_id: str | None = None,
        history: bool | HistoryOptions = False,
        audit: bool | AuditOptions = False,
        metadata: Mapping[str, Any] | None = None,
    ) -> NervousEvent:
        if isinstance(event, NervousEvent):
            return event
        history_options = history if isinstance(history, HistoryOptions) else HistoryOptions(record=bool(history))
        audit_options = audit if isinstance(audit, AuditOptions) else AuditOptions(record=bool(audit))
        return NervousEvent(
            name=str(event),
            payload=data or {},
            priority=_priority(priority),
            source=source,
            correlation_id=correlation_id,
            causation_id=causation_id,
            metadata=dict(metadata or {}),
            history=history_options,
            audit=audit_options,
        )

    async def emit(
        self,
        event: str | NervousEvent,
        data: dict = None,
        *,
        priority: EventPriority | int | str = EventPriority.NORMAL,
        source: str | None = None,
        correlation_id: str | None = None,
        causation_id: str | None = None,
        history: bool | HistoryOptions = False,
        audit: bool | AuditOptions = False,
        metadata: Mapping[str, Any] | None = None,
    ) -> NervousEvent:
        """Emit event to all listeners and return the normalized envelope."""
        envelope = self._normalize(
            event,
            data,
            priority=priority,
            source=source,
            correlation_id=correlation_id,
            causation_id=causation_id,
            history=history,
            audit=audit,
            metadata=metadata,
        )

        if envelope.history.record:
            self._history.append(envelope if envelope.history.include_payload else NervousEvent(
                name=envelope.name,
                payload={},
                id=envelope.id,
                created_at=envelope.created_at,
                priority=envelope.priority,
                source=envelope.source,
                correlation_id=envelope.correlation_id,
                causation_id=envelope.causation_id,
                metadata=envelope.metadata,
            ))
        if envelope.audit.record:
            audit_row = envelope.to_dict(include_payload=envelope.audit.include_payload)
            if envelope.audit.include_payload:
                audit_row["payload"] = _redact_payload(audit_row.get("payload"), envelope.audit.redact)
            self._audit.append(audit_row)

        if envelope.name in self.listeners:
            for listener in list(self.listeners[envelope.name]):
                try:
                    delivered = envelope if listener.envelope else (envelope.payload or {})
                    cb = listener.callback
                    if inspect.iscoroutinefunction(cb):
                        await cb(delivered)
                    else:
                        result = cb(delivered)
                        # Handle sync lambda that returns coroutine
                        if asyncio.iscoroutine(result):
                            await result
                except Exception as e:
                    print(f"[NervousSystem] Error in {envelope.name}: {e}")
                    traceback.print_exc()
        return envelope

    def recent(self, event: str | None = None, limit: int = 50) -> list[NervousEvent]:
        if int(limit) <= 0:
            return []
        rows = list(self._history)
        if event:
            rows = [row for row in rows if row.name == event]
        return rows[-int(limit):]

    def audit_log(self, limit: int = 50) -> list[dict[str, Any]]:
        if int(limit) <= 0:
            return []
        return list(self._audit)[-int(limit):]


# System events:
# - message_received   -> New message from user
# - thinking_start     -> Started thinking
# - thinking_done      -> Finished thinking
# - emotion_update     -> Emotional state changed
# - memory_save        -> Save to memory
# - send_text          -> Send text response
# - send_voice_file    -> Send voice message
# - send_image         -> Send image
# - send_reaction      -> Send emoji reaction
# - timer_tick         -> Minute tick (for decay)
# - self_modify        -> Self-modification request
