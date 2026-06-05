"""Read-only Alive body snapshot.

The snapshot composes scattered runtime state into one compact object that can
be routed through the inner-state compiler. It should not mutate subsystem
state, append memory text, or replace the existing memory context compiler.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping

from .behavioral_pressure import build_behavioral_pressure
from .inner_state import StateSignal


SNAPSHOT_VERSION = "body-v1"


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "to_dict"):
        try:
            data = value.to_dict()
            return dict(data) if isinstance(data, Mapping) else {}
        except Exception:
            return {}
    return {}


def _clamp(value: Any, low: float = 0.0, high: float = 1.0) -> float:
    try:
        return max(low, min(high, float(value)))
    except (TypeError, ValueError):
        return low


def _top_emotions(emotion: Mapping[str, Any], threshold: float = 0.38) -> dict[str, float]:
    keys = [
        "love", "joy", "desire", "sadness", "fear", "anger", "trust",
        "boredom", "guilt", "jealousy", "embarrassment", "hope", "dread",
    ]
    values = {
        key: round(_clamp(emotion.get(key, 0.0)), 3)
        for key in keys
        if _clamp(emotion.get(key, 0.0)) >= threshold
    }
    return dict(sorted(values.items(), key=lambda item: item[1], reverse=True)[:5])


def _context_trace_summary(context: Mapping[str, Any] | None) -> dict[str, Any]:
    context = context or {}
    cards = context.get("context_cards") or []
    trace = context.get("context_trace") or {}
    card_summaries: list[dict[str, Any]] = []
    for card in cards[:5]:
        if isinstance(card, Mapping):
            card_summaries.append({
                "id": str(card.get("id") or "")[:16],
                "type": str(card.get("type") or ""),
                "importance": round(_clamp(card.get("importance", 0.0)), 3),
                "emotional_weight": round(_clamp(card.get("emotional_weight", 0.0)), 3),
            })
    return {
        "selected_count": len(cards),
        "top_cards": card_summaries,
        "trace": {
            "available_cards": trace.get("available_cards", 0) if isinstance(trace, Mapping) else 0,
            "selected_cards": trace.get("selected_cards", len(cards)) if isinstance(trace, Mapping) else len(cards),
        },
    }


@dataclass(frozen=True)
class AliveBodySnapshot:
    version: str
    generated_at: str
    user_id: str
    mood: dict[str, Any] = field(default_factory=dict)
    affect: dict[str, Any] = field(default_factory=dict)
    hormones: dict[str, Any] = field(default_factory=dict)
    circadian: dict[str, Any] = field(default_factory=dict)
    attachment: dict[str, Any] = field(default_factory=dict)
    narrative: dict[str, Any] = field(default_factory=dict)
    somatic: dict[str, Any] = field(default_factory=dict)
    interoception: dict[str, Any] = field(default_factory=dict)
    memory_context: dict[str, Any] = field(default_factory=dict)
    behavioral_pressure: dict[str, Any] = field(default_factory=dict)
    prompt_guidance: list[str] = field(default_factory=list)
    response_bias: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "generated_at": self.generated_at,
            "user_id": self.user_id,
            "mood": dict(self.mood),
            "affect": dict(self.affect),
            "hormones": dict(self.hormones),
            "circadian": dict(self.circadian),
            "attachment": dict(self.attachment),
            "narrative": dict(self.narrative),
            "somatic": dict(self.somatic),
            "interoception": dict(self.interoception),
            "memory_context": dict(self.memory_context),
            "behavioral_pressure": dict(self.behavioral_pressure),
            "prompt_guidance": list(self.prompt_guidance),
            "response_bias": dict(self.response_bias),
        }

    def to_prompt_section(self, max_chars: int = 900) -> str:
        top = self.affect.get("top_emotions") or {}
        emotion_bits = ", ".join(f"{k}={v:.2f}" for k, v in top.items()) or "steady"
        guidance = "; ".join(self.prompt_guidance[:4])
        if not guidance:
            guidance = self.response_bias.get("style_hint") or "stay natural and concise"
        lines = [
            f"mood={self.mood.get('label', 'neutral')}; tendency={self.mood.get('response_tendency', 'neutral')}",
            f"affect={emotion_bits}; valence={self.affect.get('valence', 0.5):.2f}; arousal={self.affect.get('arousal', 0.5):.2f}",
            f"sleep={self.circadian.get('phase', 'unknown')}; sleepiness={self.circadian.get('sleepiness', 0.0):.2f}; asleep={self.circadian.get('sleeping', False)}",
            f"attachment={self.attachment.get('style', 'unknown')}; security={self.attachment.get('security_score', 0.5):.2f}; relationship={self.attachment.get('relationship_status', 'unknown')}",
            f"narrative={self.narrative.get('phase_name', self.narrative.get('phase', 'unknown'))}; messages={self.narrative.get('message_count', 0)}",
            f"body={self.somatic.get('summary', 'quiet')}; interoception={self.interoception.get('primary_feeling', 'steady')}",
            f"pressure={self.behavioral_pressure.get('dominant', 'stabilize')}; approach_withdraw={_clamp(self.behavioral_pressure.get('approach_withdraw', 0.0), -1.0, 1.0):.2f}; urgency={_clamp(self.behavioral_pressure.get('urgency', 0.0)):.2f}",
            f"memory_cards={self.memory_context.get('selected_count', 0)}; guidance={guidance}",
        ]
        text = "ALIVE BODY SNAPSHOT\n" + "\n".join(f"- {line}" for line in lines)
        if len(text) > max_chars:
            return text[: max(0, max_chars - 3)].rstrip() + "..."
        return text

    def to_signal(self, priority: float = 0.86) -> StateSignal:
        sleepiness = _clamp(self.circadian.get("sleepiness", 0.0))
        intensity = max(
            sleepiness,
            max((_clamp(v) for v in (self.affect.get("top_emotions") or {}).values()), default=0.45),
            0.55,
        )
        return StateSignal(
            source="alive_body_snapshot",
            kind="body_state",
            content=self.to_prompt_section(),
            intensity=intensity,
            priority=priority,
        )


def build_alive_body_snapshot(
    *,
    user_id: str,
    emotion: Mapping[str, Any] | None = None,
    heart: Any = None,
    context: Mapping[str, Any] | None = None,
) -> AliveBodySnapshot:
    emotion = dict(emotion or {})
    context = context or {}
    circadian = _as_dict(emotion.get("circadian"))
    soul_hormonal = _as_dict(emotion.get("soul_hormonal"))
    soul_integrity = _as_dict(emotion.get("soul_integrity"))

    hormones = {
        "levels": soul_hormonal.get("hormones") or soul_hormonal.get("levels") or {},
        "dominant": soul_hormonal.get("dominant_hormone") or soul_hormonal.get("dominant") or "",
        "state_description": soul_hormonal.get("state_description") or soul_hormonal.get("description") or "",
        "runtime_effects": soul_hormonal.get("effects") or soul_hormonal.get("runtime_effects") or {},
    }

    attachment = {
        "relationship_status": emotion.get("attachment_status", ""),
        "interaction_count": emotion.get("interaction_count", 0),
        "style": "",
        "security_score": 0.5,
        "trend": "",
    }
    try:
        from heart.attachment import get_attachment_engine

        engine = get_attachment_engine()
        attachment.update({
            "style": engine.get_attachment_style(),
            "security_score": round(_clamp(getattr(engine, "security_score", 0.5)), 3),
            "trend": engine.get_recent_trend(),
        })
    except Exception:
        pass

    narrative = {}
    try:
        from brain.narrative import get_narrative_engine

        engine = get_narrative_engine()
        if hasattr(engine, "get_current_phase"):
            narrative = _as_dict(engine.get_current_phase(user_id))
    except Exception:
        narrative = {}

    interoception = {}
    try:
        from heart.interoception import get_interoceptive_system

        system = get_interoceptive_system()
        interoception = _as_dict(system)
        if hasattr(system, "get_state_values"):
            interoception.setdefault("values", system.get_state_values())
        if hasattr(system, "get_dominant_feeling"):
            interoception.setdefault("primary_feeling", str(system.get_dominant_feeling()))
    except Exception:
        pass

    somatic = {
        "summary": str(emotion.get("soul_somatic") or "quiet"),
        "integrity": soul_integrity,
    }

    sleepiness = _clamp(emotion.get("sleepiness", circadian.get("sleepiness", 0.0)))
    top = _top_emotions(emotion)
    guidance: list[str] = []
    if sleepiness >= 0.65 or emotion.get("is_asleep"):
        guidance.append("sleep pressure should shorten and soften the reply")
    if top:
        guidance.append("let the strongest feeling color the wording without listing internal systems")
    if attachment.get("style"):
        guidance.append(f"attachment style is {attachment['style']}; keep pacing coherent")
    if context.get("boundary_decision"):
        guidance.append("respect active boundary and repair obligations")

    pressure = emotion.get("behavioral_pressure")
    if not isinstance(pressure, Mapping):
        pressure = build_behavioral_pressure(
            emotion,
            boundary_decision=context.get("boundary_decision"),
        ).to_dict()
    if pressure.get("instruction"):
        guidance.append(str(pressure["instruction"]))

    response_bias = {
        "intent_hint": "sleepy_return" if sleepiness >= 0.7 or emotion.get("is_asleep") else "present",
        "style_hint": "brief, warm, slower" if sleepiness >= 0.65 else "natural, emotionally continuous",
        "length_bias": "short" if sleepiness >= 0.65 else "normal",
        "approach_withdraw": pressure.get("approach_withdraw", 0.0),
        "dominant_pressure": pressure.get("dominant", "stabilize"),
        "private_reveal": "low" if sleepiness >= 0.7 else "moderate",
    }

    return AliveBodySnapshot(
        version=SNAPSHOT_VERSION,
        generated_at=datetime.now().isoformat(),
        user_id=str(user_id or "default"),
        mood={
            "label": str(emotion.get("mood") or "neutral"),
            "response_tendency": str(emotion.get("response_tendency") or "neutral"),
            "is_high_desire": _clamp(emotion.get("desire", 0.0)) >= 0.68,
            "is_in_love": _clamp(emotion.get("love", 0.0)) >= 0.55,
            "is_asleep": bool(emotion.get("is_asleep")),
        },
        affect={
            "valence": _clamp(emotion.get("valence", 0.5)),
            "arousal": _clamp(emotion.get("arousal", 0.5)),
            "dominance": _clamp(emotion.get("dominance", 0.5)),
            "top_emotions": top,
        },
        hormones=hormones,
        circadian={
            "phase": circadian.get("phase") or circadian.get("current_phase") or "",
            "sleeping": bool(circadian.get("sleeping", emotion.get("is_asleep", False))),
            "sleepiness": sleepiness,
            "sleep_debt": _clamp(circadian.get("sleep_debt", 0.0), 0.0, 2.0),
            "woke_from_sleep": bool(emotion.get("woke_from_sleep") or circadian.get("woke_from_sleep")),
            "last_transition_reason": circadian.get("last_transition_reason") or "",
        },
        attachment=attachment,
        narrative=narrative,
        somatic=somatic,
        interoception=interoception,
        memory_context=_context_trace_summary(context),
        behavioral_pressure=dict(pressure),
        prompt_guidance=guidance,
        response_bias=response_bias,
    )
