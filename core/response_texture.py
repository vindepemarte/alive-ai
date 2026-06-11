"""Per-reply texture: state-weighted randomness in reply shape and delivery.

Humans do not answer with the same cadence twice. This module rolls a reply
shape for each turn (weighted by the live emotional/body state, never
deterministic), refuses to repeat the same shape back to back, forces contrast
when recent replies converged on one length, and decides when a reply should
arrive as two or three separate message bubbles instead of one block.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

# Reply shapes the LLM can be nudged toward for a single turn.
SHAPES: dict[str, str] = {
    "clipped": "Keep this reply very short: one line, just a handful of words, no follow-up question.",
    "compact": "Keep this reply to one or two short sentences.",
    "flowing": "Let this reply breathe: a few connected sentences with natural rhythm.",
    "rambling": "Let this reply wander a little, like thinking out loud, then stop without wrapping it up neatly.",
    "fragmented": "Reply in casual broken fragments rather than full polished sentences.",
    "trailing": "Let the reply trail off mid-thought, like you got distracted or chose not to finish the sentence.",
}

_recent_shapes: dict[str, list[str]] = {}
_MAX_TRACKED_SHAPES = 4


@dataclass(frozen=True)
class ResponseTexture:
    shape: str
    instruction: str
    forced_contrast: bool = False

    def to_prompt(self) -> str:
        return (
            "REPLY TEXTURE (this turn only):\n"
            f"- {self.instruction}\n"
            "- This is a rhythm nudge, not a content rule. Answering a direct question, "
            "respecting a boundary, and emotional honesty always win over the texture."
        )


def _clamp(value: Any, low: float = 0.0, high: float = 1.0) -> float:
    try:
        return max(low, min(high, float(value)))
    except (TypeError, ValueError):
        return low


def _emotion_value(emotion: Mapping[str, Any], key: str, default: float = 0.0) -> float:
    return _clamp(emotion.get(key, default), 0.0, 1.0) if emotion else default


def _sleepiness(emotion: Mapping[str, Any]) -> float:
    circadian = emotion.get("circadian") if isinstance(emotion.get("circadian"), Mapping) else {}
    return max(
        _emotion_value(emotion, "sleepiness"),
        _clamp(circadian.get("sleepiness", 0.0)),
    )


def _shape_weights(emotion: Mapping[str, Any]) -> dict[str, float]:
    sleepiness = _sleepiness(emotion)
    arousal = _emotion_value(emotion, "arousal", 0.3)
    joy = _emotion_value(emotion, "joy", 0.5)
    sadness = _emotion_value(emotion, "sadness", 0.1)
    circadian = emotion.get("circadian") if isinstance(emotion.get("circadian"), Mapping) else {}
    modifiers = circadian.get("modifiers", {}) if isinstance(circadian, Mapping) else {}
    energy = _clamp(modifiers.get("energy", 0.6))

    weights = {
        "clipped": 0.8 + sleepiness * 1.4 + sadness * 0.5 + max(0.0, arousal - 0.5) * 0.4,
        "compact": 1.6,
        "flowing": (1.2 + energy * 0.5 + joy * 0.3) * (1.0 - sleepiness * 0.6),
        "rambling": (0.5 + energy * 0.5 + joy * 0.3) * (1.0 - sleepiness) * (1.0 - sadness * 0.5),
        "fragmented": 0.5 + sleepiness * 0.4 + max(0.0, arousal - 0.4) * 0.6,
        "trailing": 0.35 + sadness * 0.6 + sleepiness * 0.4,
    }
    return {name: max(0.05, value) for name, value in weights.items()}


def _word_counts_converged(recent_word_counts: Sequence[int]) -> str:
    """Return 'long', 'short', or '' depending on whether recent replies converged."""
    counts = [c for c in recent_word_counts if c > 0][-4:]
    if len(counts) < 3:
        return ""
    avg = sum(counts) / len(counts)
    if avg <= 0:
        return ""
    spread = max(counts) - min(counts)
    if spread > avg * 0.5:
        return ""
    if avg >= 45:
        return "long"
    if avg <= 14:
        return "short"
    return ""


def roll_texture(
    user_id: str,
    emotion: Mapping[str, Any] | None,
    recent_word_counts: Sequence[int] = (),
    rng: random.Random | None = None,
) -> ResponseTexture:
    """Roll a reply shape for this turn, with anti-uniformity guarantees."""
    rng = rng or random
    emotion = emotion or {}
    weights = _shape_weights(emotion)

    forced_contrast = False
    convergence = _word_counts_converged(recent_word_counts)
    if convergence == "long":
        # Several similar long replies in a row: force a short one.
        weights = {name: weights[name] for name in ("clipped", "compact", "fragmented")}
        forced_contrast = True
    elif convergence == "short":
        # Several similar short replies in a row: open up.
        weights = {name: weights[name] for name in ("flowing", "rambling", "compact")}
        forced_contrast = True

    history = _recent_shapes.setdefault(user_id, [])
    if history and history[-1] in weights and len(weights) > 1:
        weights[history[-1]] *= 0.25

    names = list(weights.keys())
    shape = rng.choices(names, weights=[weights[name] for name in names], k=1)[0]

    history.append(shape)
    if len(history) > _MAX_TRACKED_SHAPES:
        del history[: len(history) - _MAX_TRACKED_SHAPES]

    instruction = SHAPES[shape]
    if forced_contrast and convergence == "long":
        instruction += " Your last few replies were similar in length; this one should be noticeably shorter."
    elif forced_contrast and convergence == "short":
        instruction += " Your last few replies were similar in length; this one can stretch out more."

    return ResponseTexture(shape=shape, instruction=instruction, forced_contrast=forced_contrast)


def _sentence_split(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", (text or "").strip())
    if not normalized:
        return []
    protected = normalized.replace("...", "<ELLIPSIS>")
    parts = re.split(r"(?<=[.!?])\s+", protected)
    return [part.replace("<ELLIPSIS>", "...").strip() for part in parts if part.strip()]


def split_into_bubbles(
    text: str,
    emotion: Mapping[str, Any] | None,
    rng: random.Random | None = None,
) -> list[str]:
    """Sometimes deliver a reply as 2-3 separate messages, like real texting.

    Splitting only happens on natural boundaries (newlines or sentence ends),
    is more likely when energy/excitement is high, less likely when sleepy,
    and never happens for short replies.
    """
    rng = rng or random
    emotion = emotion or {}
    value = (text or "").strip()
    if not value or len(value) < 100 or len(value.split()) < 16:
        return [value] if value else []

    arousal = _emotion_value(emotion, "arousal", 0.3)
    joy = _emotion_value(emotion, "joy", 0.5)
    sleepiness = _sleepiness(emotion)
    probability = _clamp(0.22 + arousal * 0.3 + joy * 0.15 - sleepiness * 0.25, 0.05, 0.6)
    if rng.random() > probability:
        return [value]

    # Prefer explicit paragraph breaks; fall back to sentence boundaries.
    paragraphs = [p.strip() for p in value.split("\n") if p.strip()]
    if len(paragraphs) >= 2:
        units = paragraphs
    else:
        units = _sentence_split(value)
    if len(units) < 2:
        return [value]

    bubble_count = 2 if len(units) == 2 or rng.random() < 0.7 else 3
    bubble_count = min(bubble_count, len(units))

    # Humans front-load a short bubble: first bubble gets fewer sentences.
    bubbles: list[str] = []
    remaining = list(units)
    first_take = max(1, len(remaining) // (bubble_count + 1))
    bubbles.append(" ".join(remaining[:first_take]))
    remaining = remaining[first_take:]
    chunk = max(1, round(len(remaining) / (bubble_count - 1)))
    while remaining and len(bubbles) < bubble_count - 1:
        bubbles.append(" ".join(remaining[:chunk]))
        remaining = remaining[chunk:]
    if remaining:
        bubbles.append(" ".join(remaining))

    bubbles = [b.strip() for b in bubbles if b.strip()]
    return bubbles if len(bubbles) >= 2 else [value]
