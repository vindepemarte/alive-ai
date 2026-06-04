"""Known nervous-system event names and lightweight payload type hints."""

from __future__ import annotations

from typing import Any, TypedDict


MESSAGE_RECEIVED = "message_received"
GROUP_MESSAGE_RECEIVED = "group_message_received"
THINKING_START = "thinking_start"
THINKING_DONE = "thinking_done"
EMOTION_UPDATE = "emotion_update"
MEMORY_SAVE = "memory_save"
SEND_TEXT = "send_text"
SEND_VOICE_FILE = "send_voice_file"
SEND_IMAGE = "send_image"
SEND_VIDEO = "send_video"
SEND_REACTION = "send_reaction"
TIMER_TICK = "timer_tick"


class MessageReceivedPayload(TypedDict, total=False):
    user_id: str
    chat_id: str | int
    text: str
    message_id: str
    source: str


class SendTextPayload(TypedDict, total=False):
    text: str
    chat_id: str | int
    user_id: str
    message_id: str


class MemorySavePayload(TypedDict, total=False):
    type: str
    user_id: str
    user_message: str
    ai_response: str
    emotion: dict[str, Any]


class ThinkingPayload(TypedDict, total=False):
    user_id: str
    text: str
    response: str
