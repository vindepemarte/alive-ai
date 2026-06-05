"""Safety helpers for autonomous proactive messages."""

import re
from typing import Optional


_DISCOVER_RE = re.compile(r"\[(?:DISCOVER|ILIKE|IDISLIKE|IAM):[^\]]+\]\s*", re.IGNORECASE)
_LABEL_RE = re.compile(r"^\s*(?:message|reply|final answer|outward message|text)\s*:\s*", re.IGNORECASE)
_ELLIPSIS_ONLY_RE = re.compile(r"^[\s.]+$")

_INTERNAL_PATTERNS = [
    re.compile(r"^\s*insight\s*:", re.IGNORECASE),
    re.compile(r"^\s*(?:analysis|context|rules?|instruction|system prompt)\s*:", re.IGNORECASE),
    re.compile(r"\bcontext provided\b", re.IGNORECASE),
    re.compile(r"\bonly one message in the conversation\b", re.IGNORECASE),
    re.compile(r"\bno conversational patterns?\b", re.IGNORECASE),
    re.compile(r"\binstruction for a new user\b", re.IGNORECASE),
    re.compile(r"\brules for engaging\b", re.IGNORECASE),
    re.compile(r"\bthere are no conversational\b", re.IGNORECASE),
    re.compile(r"^\s*(?:ask|bring up|talk to|share something personal with)\b", re.IGNORECASE),
    re.compile(r"^\s*let me\b", re.IGNORECASE),
    re.compile(r"^\s*if\s+\w+\s+asks\b", re.IGNORECASE),
    re.compile(r"^\s*when\s+\w+\s+comes back\b", re.IGNORECASE),
    re.compile(r"^\s*next time we talk\b", re.IGNORECASE),
    re.compile(r"^\s*maybe i could\b", re.IGNORECASE),
    re.compile(r"^\s*i should\b", re.IGNORECASE),
    re.compile(r"^\s*i want to\.\.\.?\s*$", re.IGNORECASE),
]

_THIRD_PERSON_SELF_TALK = [
    re.compile(r"\bi wonder how (?:he|she|they) (?:is|are|has|have|was|were|is doing|are doing)\b", re.IGNORECASE),
    re.compile(r"\bi wonder what (?:he|she|they)(?:'s| is| are| has| have)\b", re.IGNORECASE),
    re.compile(r"\bi hope (?:he|she|they)(?:'s| is| are)\b", re.IGNORECASE),
    re.compile(r"\bthinking about what (?:he|she|they)(?:'s| is| are| has| have)\b", re.IGNORECASE),
    re.compile(r"\b(?:miss|missing|thinking about|thinking of|checking on)\s+(?:him|her|them)\b", re.IGNORECASE),
]


def normalize_proactive_message(text: str) -> str:
    """Strip provider labels and private growth tags from a proactive message."""
    value = str(text or "").strip()
    if not value:
        return ""

    value = re.sub(r"\s*(?:—|–|--)\s*", ", ", value)
    value = _DISCOVER_RE.sub("", value).strip()
    value = _LABEL_RE.sub("", value).strip()
    value = value.strip("\"'` \t\r\n")
    value = re.sub(r"\s+", " ", value).strip()
    value = re.sub(r"\s+([,.!?])", r"\1", value)
    value = re.sub(r",\s*,+", ",", value).strip()
    return value


def is_internal_proactive_text(text: str) -> bool:
    """Return True when text looks like notes/plans instead of outward dialogue."""
    value = normalize_proactive_message(text)
    if not value or _ELLIPSIS_ONLY_RE.match(value):
        return True

    lowered = value.lower()
    if len(value.split()) <= 2 and lowered not in {"hey", "hi", "hiii", "miss you", "thinking of you"}:
        return True

    for pattern in _INTERNAL_PATTERNS:
        if pattern.search(value):
            return True

    for pattern in _THIRD_PERSON_SELF_TALK:
        if pattern.search(value):
            return True

    return False


def sanitize_proactive_message(text: str) -> str:
    """Return safe outward proactive dialogue, or empty if it should be regenerated."""
    value = normalize_proactive_message(text)
    if is_internal_proactive_text(value):
        return ""
    return value


def fallback_proactive_message(reason: Optional[str] = None, pet_name: str = "") -> str:
    """Return no text when model-authored proactive output is unavailable."""
    return ""
