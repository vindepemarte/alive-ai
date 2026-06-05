"""Behavioral pressure compiler.

Emotions should not be only labels or dashboard values. This module turns
emotion, hormones, sleep, and boundary state into action tendencies that can
shape prompt planning and diagnostics without adding another LLM call.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class BehavioralDrive:
    name: str
    pressure: float
    instruction: str
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["pressure"] = round(float(self.pressure), 3)
        return data


@dataclass(frozen=True)
class BehavioralPressureProfile:
    dominant: str
    instruction: str
    approach_withdraw: float
    urgency: float
    drives: list[BehavioralDrive]

    def to_dict(self) -> dict[str, Any]:
        return {
            "dominant": self.dominant,
            "instruction": self.instruction,
            "approach_withdraw": round(float(self.approach_withdraw), 3),
            "urgency": round(float(self.urgency), 3),
            "drives": [drive.to_dict() for drive in self.drives],
        }

    def prompt_lines(self, limit: int = 3) -> list[str]:
        lines = [self.instruction] if self.instruction else []
        for drive in self.drives[: max(0, limit)]:
            reason = f" ({', '.join(drive.reasons[:2])})" if drive.reasons else ""
            lines.append(f"{drive.name}: {drive.instruction}{reason}")
        return lines


def build_behavioral_pressure(
    emotion: Mapping[str, Any] | None,
    *,
    boundary_decision: Mapping[str, Any] | Any | None = None,
) -> BehavioralPressureProfile:
    """Compile affect into ranked behavioral drives."""
    emotion = dict(emotion or {})
    boundary = _boundary_dict(boundary_decision or emotion.get("boundary_decision"))
    hormones = _hormone_levels(emotion.get("soul_hormonal"))
    sleepiness = max(_num(emotion.get("sleepiness")), _num(_as_dict(emotion.get("circadian")).get("sleepiness")))
    is_asleep = bool(emotion.get("is_asleep") or _as_dict(emotion.get("circadian")).get("sleeping"))

    values: dict[str, tuple[float, str, list[str]]] = {
        "approach": (
            0.30
            + _num(emotion.get("love")) * 0.23
            + _num(emotion.get("trust")) * 0.16
            + _num(emotion.get("joy")) * 0.13
            + hormones.get("oxytocin", 0.3) * 0.14
            + _num(emotion.get("desire")) * 0.08
            - _num(emotion.get("fear")) * 0.13
            - _num(emotion.get("anger")) * 0.09
            - sleepiness * 0.10
            - (float(boundary.get("severity", 0.0)) * 0.26 if boundary.get("state") == "boundary_pressure" else 0.0),
            "move toward connection, warmth, and presence",
            ["love/trust/oxytocin"],
        ),
        "pursue": (
            _num(emotion.get("desire")) * 0.32
            + _num(emotion.get("anticipation")) * 0.20
            + hormones.get("dopamine", 0.4) * 0.18
            + _num(emotion.get("arousal")) * 0.14
            - sleepiness * 0.18
            - _num(emotion.get("fear")) * 0.08
            - (float(boundary.get("severity", 0.0)) * 0.24 if boundary.get("state") == "boundary_pressure" else 0.0),
            "show wanting or momentum only if safety and pacing are intact",
            ["desire/dopamine/anticipation"],
        ),
        "protect_boundary": (
            _num(emotion.get("anger")) * 0.28
            + _num(emotion.get("fear")) * 0.18
            + max(0.0, 0.5 - _num(emotion.get("trust"), 0.5)) * 0.30
            + hormones.get("cortisol", 0.2) * 0.17
            + (float(boundary.get("severity", 0.0)) * 0.70 if boundary.get("state") == "boundary_pressure" else 0.0),
            "hold agency, do not over-comply, and name the boundary briefly",
            ["anger/fear/cortisol", "boundary pressure" if boundary.get("state") else ""],
        ),
        "repair": (
            _num(emotion.get("guilt")) * 0.25
            + _num(emotion.get("sadness")) * 0.17
            + _num(emotion.get("trust")) * 0.08
            + (0.34 if boundary.get("state") in {"repair_offered", "consensual_repair"} else 0.0)
            + (0.12 if "sorry" in str(emotion.get("mood", "")).lower() else 0.0),
            "acknowledge rupture and move toward safety before warmth",
            ["guilt/sadness", "repair offered" if boundary.get("state") else ""],
        ),
        "withdraw": (
            _num(emotion.get("fear")) * 0.26
            + _num(emotion.get("sadness")) * 0.14
            + _num(emotion.get("dread")) * 0.16
            + max(0.0, 0.45 - _num(emotion.get("trust"), 0.5)) * 0.22
            + hormones.get("cortisol", 0.2) * 0.12
            + sleepiness * 0.10,
            "use less reach, more caution, and shorter emotional exposure",
            ["fear/dread/low trust"],
        ),
        "seek_reassurance": (
            _num(emotion.get("jealousy")) * 0.29
            + _num(emotion.get("fear")) * 0.17
            + _num(emotion.get("love")) * 0.08
            + hormones.get("cortisol", 0.2) * 0.10
            - _num(emotion.get("trust")) * 0.08,
            "ask for reassurance softly instead of testing or accusing",
            ["jealousy/fear/love"],
        ),
        "play": (
            _num(emotion.get("joy")) * 0.24
            + _num(emotion.get("pride")) * 0.14
            + _num(emotion.get("anticipation")) * 0.14
            + hormones.get("dopamine", 0.4) * 0.11
            - _num(emotion.get("sadness")) * 0.13
            - _num(emotion.get("fear")) * 0.11
            - sleepiness * 0.16,
            "let lightness or teasing show without dodging the user",
            ["joy/pride/dopamine"],
        ),
        "stabilize": (
            hormones.get("serotonin", 0.5) * 0.18
            + _num(emotion.get("trust")) * 0.11
            + _num(emotion.get("hope")) * 0.11
            + _num(emotion.get("sadness")) * 0.09
            + _num(emotion.get("fear")) * 0.08
            + max(0.0, 0.45 - hormones.get("cortisol", 0.2)) * 0.12,
            "steady the tone and reduce emotional noise",
            ["serotonin/trust/hope"],
        ),
        "rest": (
            sleepiness * 0.52
            + hormones.get("melatonin", 0.3) * 0.24
            + (0.25 if is_asleep else 0.0)
            - _num(emotion.get("arousal")) * 0.08,
            "slow down, shorten the reply, and preserve sleep/rest state",
            ["sleepiness/melatonin"],
        ),
        "curiosity": (
            _num(emotion.get("anticipation")) * 0.18
            + _num(emotion.get("boredom")) * 0.18
            + hormones.get("dopamine", 0.4) * 0.09
            + _num(emotion.get("trust")) * 0.05
            - sleepiness * 0.12,
            "ask one grounded question only when it naturally helps connection",
            ["anticipation/boredom"],
        ),
    }

    drives = [
        BehavioralDrive(name, _clamp(score), instruction, [r for r in reasons if r])
        for name, (score, instruction, reasons) in values.items()
    ]
    drives.sort(key=lambda drive: drive.pressure, reverse=True)
    dominant = drives[0].name if drives else "stabilize"
    approach_withdraw = _clamp(
        _pressure(drives, "approach") + _pressure(drives, "pursue") + _pressure(drives, "play")
        - _pressure(drives, "withdraw") - _pressure(drives, "protect_boundary") - _pressure(drives, "rest"),
        -1.0,
        1.0,
    )
    urgency = _clamp(
        _num(emotion.get("arousal")) * 0.28
        + _pressure(drives, "protect_boundary") * 0.25
        + _pressure(drives, "repair") * 0.15
        + _pressure(drives, "pursue") * 0.12
        + hormones.get("cortisol", 0.2) * 0.14
        - _pressure(drives, "rest") * 0.16
    )

    return BehavioralPressureProfile(
        dominant=dominant,
        instruction=_dominant_instruction(dominant),
        approach_withdraw=approach_withdraw,
        urgency=urgency,
        drives=drives[:5],
    )


def _dominant_instruction(name: str) -> str:
    return {
        "approach": "Behavioral pressure favors warm approach.",
        "pursue": "Behavioral pressure favors desire or momentum, but only with pacing.",
        "protect_boundary": "Behavioral pressure favors agency and boundary protection.",
        "repair": "Behavioral pressure favors repair before deeper closeness.",
        "withdraw": "Behavioral pressure favors cautious distance.",
        "seek_reassurance": "Behavioral pressure favors soft reassurance-seeking.",
        "play": "Behavioral pressure favors lightness and play.",
        "stabilize": "Behavioral pressure favors steadiness and regulation.",
        "rest": "Behavioral pressure favors rest and low-energy replies.",
        "curiosity": "Behavioral pressure favors one grounded question.",
    }.get(name, "Behavioral pressure favors steady presence.")


def _pressure(drives: list[BehavioralDrive], name: str) -> float:
    for drive in drives:
        if drive.name == name:
            return drive.pressure
    return 0.0


def _boundary_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "to_dict"):
        try:
            data = value.to_dict()
            return dict(data) if isinstance(data, Mapping) else {}
        except Exception:
            return {}
    return {}


def _hormone_levels(value: Any) -> dict[str, float]:
    data = _as_dict(value)
    if not data:
        return {}
    levels = data.get("levels")
    if isinstance(levels, Mapping):
        data = dict(levels)
    return {
        "oxytocin": _num(data.get("oxytocin"), 0.3),
        "dopamine": _num(data.get("dopamine"), 0.4),
        "serotonin": _num(data.get("serotonin"), 0.5),
        "cortisol": _num(data.get("cortisol"), 0.2),
        "melatonin": _num(data.get("melatonin"), 0.3),
    }


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: Any, low: float = 0.0, high: float = 1.0) -> float:
    try:
        return max(low, min(high, float(value)))
    except (TypeError, ValueError):
        return low
