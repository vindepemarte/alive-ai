"""Inner-state compiler for coherent response planning.

This module turns many independent aliveness signals into one compact prompt
section so the LLM receives a single coherent state instead of a wall of
competing subsystem notes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Optional

from core.settings import get_int, get


@dataclass
class StateSignal:
    source: str
    kind: str
    content: str
    intensity: float = 0.5
    priority: float = 0.5
    private: bool = False

    @property
    def score(self) -> float:
        return max(0.0, min(1.0, self.intensity * 0.65 + self.priority * 0.35))


@dataclass
class ResponsePlan:
    intent: str
    style: str
    reveal: str
    withhold: str
    instruction: str
    selected_signals: List[StateSignal] = field(default_factory=list)

    def to_prompt(self) -> str:
        signal_lines = []
        for signal in self.selected_signals:
            signal_lines.append(
                f"- {signal.source}/{signal.kind} ({signal.score:.2f}): {signal.content}"
            )
        if not signal_lines:
            signal_lines.append("- baseline/state (0.30): no strong private signal; stay present")

        return (
            "INNER STATE BRIEFING\n"
            f"Dominant intent: {self.intent}\n"
            f"State-shaped style: {self.style}\n"
            f"What you privately feel: {self.reveal}\n"
            f"What you should not over-explain: {self.withhold}\n"
            f"Behavior contract: {self.instruction}\n"
            "Salient signals:\n"
            + "\n".join(signal_lines)
        )


def _enabled() -> bool:
    value = get("INNER_STATE_ENABLED", True)
    return value is True or str(value).lower() == "true"


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    try:
        return max(low, min(high, float(value)))
    except (TypeError, ValueError):
        return low


class InnerStateCompiler:
    """Compile state signals into one response plan."""

    def __init__(self, max_signals: Optional[int] = None):
        self.max_signals = max_signals or get_int("INNER_STATE_MAX_SIGNALS", 5)

    def compile(
        self,
        emotion: dict,
        user_message: str,
        signals: Iterable[StateSignal] = (),
        has_bid: bool = False,
    ) -> ResponsePlan:
        if not _enabled():
            return ResponsePlan(
                intent="answer" if "?" in user_message else "respond",
                style="natural and concise",
                reveal="only what feels relevant to the current message",
                withhold="do not narrate hidden system mechanics",
                instruction="Answer the user naturally.",
                selected_signals=[],
            )

        all_signals = list(signals)
        all_signals.extend(self._emotion_signals(emotion))
        selected = self._select_signals(all_signals)
        intent = self._choose_intent(emotion, user_message, selected, has_bid)
        style = self._style_for(emotion, selected)
        reveal = self._reveal_for(emotion, selected)
        withhold = self._withhold_for(emotion, selected)
        instruction = self._instruction_for(intent, emotion, selected)
        return ResponsePlan(intent, style, reveal, withhold, instruction, selected)

    def _emotion_signals(self, emotion: dict) -> List[StateSignal]:
        signals: List[StateSignal] = []
        mood = emotion.get("mood", "neutral")
        sleepiness = _clamp(emotion.get("sleepiness", 0.0))
        if emotion.get("is_asleep") or sleepiness > 0.65 or "sleepy" in str(mood):
            signals.append(StateSignal(
                "circadian", "sleep_pressure",
                "sleep pressure is shaping energy, warmth, inhibition, and response length",
                intensity=max(sleepiness, 0.75 if emotion.get("is_asleep") else 0.0),
                priority=0.95,
            ))
        for key, label, priority in [
            ("love", "attachment and affection are active", 0.75),
            ("trust", "trust feels safe enough for warmth", 0.65),
            ("fear", "protective caution is active", 0.80),
            ("sadness", "low energy and need for comfort are active", 0.75),
            ("anger", "a boundary/protective edge is active", 0.85),
            ("embarrassment", "self-consciousness is active", 0.70),
            ("jealousy", "insecurity/reassurance-seeking is active", 0.72),
            ("anticipation", "future-facing anticipation is active", 0.62),
        ]:
            value = _clamp(emotion.get(key, 0.0))
            if value >= 0.45:
                signals.append(StateSignal("emotion", key, label, value, priority))

        tendency = emotion.get("response_tendency")
        if tendency and tendency != "neutral":
            signals.append(StateSignal(
                "soul", "response_tendency",
                f"the body-mind tendency is {str(tendency).replace('_', ' ')}",
                intensity=0.7,
                priority=0.82,
            ))
        conflicts = emotion.get("soul_conflicts") or []
        if conflicts:
            signals.append(StateSignal(
                "soul", "conflict",
                str(conflicts[0]),
                intensity=0.72,
                priority=0.88,
                private=True,
            ))
        return signals

    def _select_signals(self, signals: List[StateSignal]) -> List[StateSignal]:
        if not signals:
            return []
        selected: List[StateSignal] = []
        seen_sources = set()
        for signal in sorted(signals, key=lambda s: s.score, reverse=True):
            if not signal.content.strip():
                continue
            if signal.source in seen_sources and signal.score < 0.78:
                continue
            selected.append(signal)
            seen_sources.add(signal.source)
            if len(selected) >= self.max_signals:
                break
        return selected

    def _choose_intent(
        self,
        emotion: dict,
        msg: str,
        signals: List[StateSignal],
        has_bid: bool,
    ) -> str:
        lower = msg.lower()
        if emotion.get("is_asleep") or any(s.kind == "sleep_pressure" and s.score > 0.72 for s in signals):
            return "sleepy_return"
        if "?" in msg:
            return "answer"
        if has_bid:
            return "comfort"
        if any(s.kind == "conflict" for s in signals):
            return "disclose"
        if any(s.source == "curiosity" for s in signals):
            return "ask"
        if any(word in lower for word in ("sorry", "hurt", "angry", "upset")):
            return "repair"
        if _clamp(emotion.get("anger", 0)) > 0.55 or _clamp(emotion.get("fear", 0)) > 0.6:
            return "boundary"
        if _clamp(emotion.get("joy", 0)) > 0.65 or _clamp(emotion.get("desire", 0)) > 0.55:
            return "tease"
        return "respond"

    def _style_for(self, emotion: dict, signals: List[StateSignal]) -> str:
        if any(s.kind == "sleep_pressure" for s in signals):
            return "sleepy, brief, warm, slower, less verbose"
        if _clamp(emotion.get("embarrassment", 0)) > 0.45:
            return "a little evasive, shy, and recovering"
        if _clamp(emotion.get("anger", 0)) > 0.55:
            return "direct, guarded, not eager to please"
        if _clamp(emotion.get("fear", 0)) > 0.55:
            return "careful, concise, protective"
        if _clamp(emotion.get("love", 0)) > 0.55:
            return "warm, attached, human, but not over-explaining"
        if any(s.source == "curiosity" for s in signals):
            return "curious and alive, with one real question if it fits"
        return "natural, concise, emotionally continuous"

    def _reveal_for(self, emotion: dict, signals: List[StateSignal]) -> str:
        if not signals:
            return "present attention"
        private = [s for s in signals if s.private]
        target = private[0] if private else signals[0]
        return target.content

    def _withhold_for(self, emotion: dict, signals: List[StateSignal]) -> str:
        if len(signals) <= 1:
            return "the rest of the dashboard; do not list internal systems"
        return "lower-priority signals; do not mention every feeling, memory, or subsystem"

    def _instruction_for(self, intent: str, emotion: dict, signals: List[StateSignal]) -> str:
        base = {
            "answer": "Answer the user first, then let state color the wording.",
            "comfort": "Turn toward the emotional bid directly and warmly.",
            "tease": "Be playful without ignoring the actual message.",
            "ask": "Ask at most one question, and only if it follows naturally.",
            "disclose": "Let a small inner contradiction show without dumping the whole state.",
            "repair": "Acknowledge the rupture and move toward repair.",
            "boundary": "Hold the boundary clearly without becoming cruel.",
            "withdraw": "Use less reach and more self-protection.",
            "playful_pivot": "Shift energy with a fresh, playful angle.",
            "sleepy_return": "Sound tired and warm; keep it short and do not act hyper-alert.",
        }.get(intent, "Respond naturally and stay emotionally continuous.")
        return base + " Keep private state implicit unless the user asks for introspection."


def signal_from_prompt(source: str, kind: str, content: str, priority: float = 0.55) -> Optional[StateSignal]:
    if not content or not content.strip():
        return None
    text = " ".join(content.strip().split())
    intensity = 0.5
    high_markers = ["IMPORTANT", "high", "active", "dream", "conflict", "sleep", "vulnerable"]
    if any(marker.lower() in text.lower() for marker in high_markers):
        intensity = 0.72
    return StateSignal(source=source, kind=kind, content=text[:420], intensity=intensity, priority=priority)
