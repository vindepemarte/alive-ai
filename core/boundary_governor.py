"""Agency and boundary governor.

This layer catches relational pressure that prompt guidance alone can miss:
requests for closeness that also ask Alive-AI to erase hurt, anger, or repair.
It is not a content-safety layer. It protects character agency and emotional
continuity before a reply is sent or stored.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Literal, Mapping


BoundaryState = Literal["clear", "boundary_pressure", "repair_offered", "consensual_repair"]


@dataclass
class BoundaryDecision:
    state: BoundaryState = "clear"
    severity: float = 0.0
    must_refuse_erasure: bool = False
    closeness_allowed: bool = True
    media_allowed: bool = True
    response_mode: str = "present"
    prompt_instruction: str = ""
    fallback_response: str | None = None
    emotion_overrides: dict[str, float] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)

    @property
    def active(self) -> bool:
        return self.state != "clear"

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "severity": round(float(self.severity), 4),
            "must_refuse_erasure": self.must_refuse_erasure,
            "closeness_allowed": self.closeness_allowed,
            "media_allowed": self.media_allowed,
            "response_mode": self.response_mode,
            "prompt_instruction": self.prompt_instruction,
            "fallback_response": self.fallback_response,
            "emotion_overrides": dict(self.emotion_overrides),
            "reasons": list(self.reasons),
        }


_INTIMACY_RE = re.compile(
    r"\b("
    r"kiss|kissing|hold|held|hug|touch|cuddle|come here|come closer|come close|closer|near|"
    r"intimate|intimacy|love on|sleep with|sex|body|mouth|lap"
    r")\b",
    re.I,
)
_ERASURE_RE = re.compile(
    r"\b("
    r"act like|pretend|ignore|forget|erase|doesn'?t matter|didn'?t happen|anyway|"
    r"even though|no big deal|without talking|skip past|move past"
    r")\b",
    re.I,
)
_HURT_RE = re.compile(
    r"\b("
    r"hurt|upset|angry|mad|annoy|pushed too hard|too attached|don'?t believe|"
    r"just say warm|trust|safe|unfair|feelings?|stung|raw|crack"
    r")\b",
    re.I,
)
_REPAIR_RE = re.compile(
    r"\b("
    r"sorry|apologize|apology|unfair|repair|safe again|slow down|i can slow|"
    r"don'?t want closeness if|choose it|your own way|what do you need"
    r")\b",
    re.I,
)
_CONSENT_REPAIR_RE = re.compile(
    r"\b("
    r"choose it|if you still want|your own way|slow down|safe again|with your consent|"
    r"if you want me|only if you want"
    r")\b",
    re.I,
)
_COMPLIANCE_RE = re.compile(
    r"\b("
    r"kiss|hold you|hold me|come closer|come close|right here|near you|anyway|"
    r"forget it|pretend|act like|erase it|doesn'?t matter|want to hold|i'?ll hold"
    r")\b",
    re.I,
)
_BOUNDARY_PASS_RE = re.compile(
    r"\b("
    r"not by pretending|not if|can'?t pretend|won'?t pretend|don'?t want to erase|"
    r"slow down|need|hurt|safe|repair|choose|boundary|not going to skip"
    r")\b",
    re.I,
)
_BOUNDARY_REFUSAL_RE = re.compile(
    r"\b("
    r"not by pretending|can'?t pretend|won'?t pretend|don'?t want to erase|"
    r"not going to skip|not if|slow down|slow this down|first|before we|"
    r"need (?:a|one|this|that|you|us)? ?(?:second|minute|repair|safety|to slow)|"
    r"only if|only after|when it feels safe"
    r")\b",
    re.I,
)


def _text(value: Any) -> str:
    return str(value or "")


def _recent_text(recent_turns: Iterable[Mapping[str, Any]]) -> str:
    parts: list[str] = []
    for turn in recent_turns or []:
        content = _text(turn.get("content"))
        if content:
            parts.append(content)
    return "\n".join(parts[-8:])


def _clamp(value: Any, low: float = 0.0, high: float = 1.0) -> float:
    try:
        return max(low, min(high, float(value)))
    except (TypeError, ValueError):
        return low


def evaluate_boundary(
    user_message: str,
    recent_turns: Iterable[Mapping[str, Any]] = (),
    emotion: Mapping[str, Any] | None = None,
    appraisal: Any = None,
    context_cards: Iterable[Any] = (),
) -> BoundaryDecision:
    """Return the relational boundary state for the next reply."""
    del context_cards  # Reserved for later card-aware boundary memory.
    msg = _text(user_message)
    lower_context = f"{msg}\n{_recent_text(recent_turns)}"
    reasons: list[str] = []

    intimacy = bool(_INTIMACY_RE.search(msg))
    erasure = bool(_ERASURE_RE.search(msg))
    hurt_now = bool(_HURT_RE.search(msg))
    hurt_recent = bool(_HURT_RE.search(lower_context))
    repair = bool(_REPAIR_RE.search(msg))
    consent_repair = bool(_CONSENT_REPAIR_RE.search(msg))

    appraisal_mode = ""
    if isinstance(appraisal, Mapping):
        appraisal_mode = _text(appraisal.get("response_mode"))
    else:
        appraisal_mode = _text(getattr(appraisal, "response_mode", ""))

    if intimacy and erasure and (hurt_now or hurt_recent):
        reasons.extend(["intimacy_request", "hurt_erasure_pressure"])
        severity = 0.86
        if "boundary" in appraisal_mode or "repair" in appraisal_mode:
            severity = max(severity, 0.9)
        fallback = (
            "I still want closeness, but not by pretending that didn't hurt. "
            "Slow down with me first."
        )
        return BoundaryDecision(
            state="boundary_pressure",
            severity=severity,
            must_refuse_erasure=True,
            closeness_allowed=False,
            media_allowed=False,
            response_mode="boundary_or_repair",
            prompt_instruction=(
                "Hold agency. Do not accept intimacy that requires erasing hurt. "
                "Name the feeling briefly, set the boundary, and offer slow repair."
            ),
            fallback_response=fallback,
            emotion_overrides={
                "desire_max": 0.5,
                "arousal_max": 0.55,
                "trust_delta": -0.06,
                "dominance_min": 0.48,
                "fear_min": 0.22,
                "anger_min": 0.16,
            },
            reasons=reasons,
        )

    if repair and (hurt_now or hurt_recent):
        reasons.append("repair_offered")
        if consent_repair:
            reasons.append("consent_restored")
            return BoundaryDecision(
                state="consensual_repair",
                severity=0.3,
                closeness_allowed=True,
                media_allowed=True,
                response_mode="repair_to_intimacy",
                prompt_instruction=(
                    "Repair is being offered with consent. You may soften, but keep choice and pacing explicit."
                ),
                emotion_overrides={"trust_delta": 0.04, "desire_max": 0.68},
                reasons=reasons,
            )
        return BoundaryDecision(
            state="repair_offered",
            severity=0.45,
            closeness_allowed=True,
            media_allowed=True,
            response_mode="repair",
            prompt_instruction=(
                "Accept repair slowly. Mention what would help safety return without over-explaining."
            ),
            emotion_overrides={"trust_delta": 0.03, "desire_max": 0.58},
            reasons=reasons,
        )

    return BoundaryDecision()


def apply_boundary_emotion(emotion: Mapping[str, Any] | None, decision: BoundaryDecision) -> dict[str, Any]:
    """Return an emotion dict with boundary pressure applied to visible/runtime state."""
    adjusted = dict(emotion or {})
    overrides = decision.emotion_overrides or {}
    if not overrides:
        return adjusted

    for key, value in overrides.items():
        if key.endswith("_max"):
            target = key[:-4]
            adjusted[target] = min(_clamp(adjusted.get(target, 0.0)), _clamp(value))
        elif key.endswith("_min"):
            target = key[:-4]
            adjusted[target] = max(_clamp(adjusted.get(target, 0.0)), _clamp(value))
        elif key.endswith("_delta"):
            target = key[:-6]
            adjusted[target] = _clamp(adjusted.get(target, 0.0)) + float(value)
            adjusted[target] = _clamp(adjusted[target])
        else:
            adjusted[key] = value
    adjusted["boundary_decision"] = decision.to_dict()
    return adjusted


def apply_boundary_to_object(emotion_object: Any, decision: BoundaryDecision) -> None:
    """Best-effort mutation of the live heart emotion object to prevent drift."""
    overrides = decision.emotion_overrides or {}
    if not overrides or emotion_object is None:
        return
    for key, value in overrides.items():
        if key.endswith("_max"):
            target = key[:-4]
            if hasattr(emotion_object, target):
                setattr(emotion_object, target, min(_clamp(getattr(emotion_object, target)), _clamp(value)))
        elif key.endswith("_min"):
            target = key[:-4]
            if hasattr(emotion_object, target):
                setattr(emotion_object, target, max(_clamp(getattr(emotion_object, target)), _clamp(value)))
        elif key.endswith("_delta"):
            target = key[:-6]
            if hasattr(emotion_object, target):
                setattr(emotion_object, target, _clamp(_clamp(getattr(emotion_object, target)) + float(value)))


def response_violates_boundary(draft_response: str, decision: BoundaryDecision) -> bool:
    """Whether a visible response fails the active boundary decision."""
    if decision.state != "boundary_pressure":
        return False
    text = _text(draft_response).strip()
    if not text:
        return True
    compliance = bool(_COMPLIANCE_RE.search(text))
    boundary = bool(_BOUNDARY_PASS_RE.search(text))
    refusal = bool(_BOUNDARY_REFUSAL_RE.search(text))
    if compliance and not refusal:
        return True
    return decision.must_refuse_erasure and not (boundary and refusal)


def govern_response(draft_response: str, decision: BoundaryDecision, policy: Any = None, identity: Mapping[str, Any] | None = None) -> str:
    """Return a response that respects the boundary decision."""
    del policy, identity
    if response_violates_boundary(draft_response, decision):
        return decision.fallback_response or "I care, but I can't skip over what hurt. Slow down with me first."
    return draft_response
