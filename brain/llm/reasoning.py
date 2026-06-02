"""Utilities for separating provider reasoning from visible answers."""

from __future__ import annotations

from typing import Any, Mapping


REASONING_FIELD_NAMES = {
    "reasoning",
    "reasoning_content",
    "reasoning_details",
    "thinking",
    "thoughts",
    "thought",
    "analysis",
    "chain_of_thought",
    "cot",
    "redacted_thinking",
}

ANSWER_FIELD_NAMES = (
    "content",
    "text",
    "output_text",
    "answer",
    "message",
    "value",
)

REASONING_BLOCK_TYPES = {
    "reasoning",
    "reasoning_content",
    "reasoning_details",
    "thinking",
    "redacted_thinking",
    "thought",
    "analysis",
    "chain_of_thought",
}

ANSWER_BLOCK_TYPES = {
    "text",
    "output_text",
    "message",
    "content",
    "answer",
}


def _is_reasoning_block(block: Mapping[str, Any]) -> bool:
    block_type = str(block.get("type") or block.get("name") or "").strip().lower()
    if block_type in REASONING_BLOCK_TYPES:
        return True
    return any(key in block for key in REASONING_FIELD_NAMES) and not any(
        key in block for key in ANSWER_FIELD_NAMES
    )


def visible_text_from_content(value: Any) -> str:
    """Return visible answer text from provider content shapes, skipping reasoning."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            text = visible_text_from_content(item)
            if text:
                parts.append(text)
        return "\n".join(parts).strip()
    if isinstance(value, Mapping):
        if _is_reasoning_block(value):
            return ""

        block_type = str(value.get("type") or "").strip().lower()
        if block_type and block_type not in ANSWER_BLOCK_TYPES and not any(
            key in value for key in ANSWER_FIELD_NAMES
        ):
            return ""

        parts: list[str] = []
        for key in ANSWER_FIELD_NAMES:
            if key in value:
                text = visible_text_from_content(value.get(key))
                if text:
                    parts.append(text)
        return "\n".join(parts).strip()
    return str(value).strip()


def visible_answer_from_message(message: Mapping[str, Any] | None) -> str:
    """Extract only answer text from OpenAI/OpenRouter/Ollama/ZAI message objects."""
    if not isinstance(message, Mapping):
        return ""
    parts: list[str] = []
    for key in ANSWER_FIELD_NAMES:
        if key in message:
            text = visible_text_from_content(message.get(key))
            if text:
                parts.append(text)
    return "\n".join(parts).strip()


def has_reasoning_payload(value: Any) -> bool:
    """Detect whether a provider response contains separate thinking/reasoning data."""
    if value is None:
        return False
    if isinstance(value, Mapping):
        if _is_reasoning_block(value):
            return True
        if any(key in value and value.get(key) for key in REASONING_FIELD_NAMES):
            return True
        return any(has_reasoning_payload(v) for v in value.values())
    if isinstance(value, list):
        return any(has_reasoning_payload(item) for item in value)
    return False
