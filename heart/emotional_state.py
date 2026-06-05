"""
EmotionalState: Data class for emotional state with persistence
Extended for Soul Architecture dimensions
"""
import json
from datetime import datetime
from core.paths import state_file

EMOTION_STATE_PATH = state_file("emotion_state.json")
DEFAULTS = {
    "valence": 0.5, "arousal": 0.3, "dominance": 0.5, "desire": 0.0,
    "high_desire_threshold": 0.7, "joy": 0.5, "love": 0.05, "trust": 0.5,
    "fear": 0.1, "anger": 0.1, "sadness": 0.1, "boredom": 0.0,
    "guilt": 0.0, "pride": 0.0, "jealousy": 0.0,
    "embarrassment": 0.0, "anticipation": 0.0,
    # Soul architecture dimensions
    "integrity_overall": 0.65, "vulnerability": 0.2, "hope": 0.5, "dread": 0.1
}


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Keep persisted and computed emotion values in the normalized range."""
    try:
        return max(low, min(high, float(value)))
    except (TypeError, ValueError):
        return low


class EmotionalState:
    """Current emotional state with persistence - extended for Soul Architecture"""

    def __init__(self, config: dict = None):
        config = config or {}
        if self._load():
            print(f"[Heart] Loaded saved emotional state")
        else:
            for key, val in DEFAULTS.items():
                setattr(self, key, val)
        self.baseline = {"joy": 0.5, "love": 0.05, "trust": 0.5,
                         "valence": 0.5, "dominance": 0.5,
                         "arousal": 0.3, "desire": 0.0,
                         "anger": 0.0, "sadness": 0.1, "fear": 0.1,
                         "boredom": 0.0}
        self._clamp_all()

    def _load(self) -> bool:
        """Load state from file"""
        try:
            if EMOTION_STATE_PATH.exists():
                data = json.loads(EMOTION_STATE_PATH.read_text())
                for key in DEFAULTS:
                    setattr(self, key, _clamp(data.get(key, DEFAULTS[key])))
                return True
        except Exception as e:
            print(f"[Heart] Error loading state: {e}")
        return False

    def save(self):
        """Save state to file"""
        try:
            EMOTION_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            data = {key: getattr(self, key) for key in DEFAULTS}
            data["saved_at"] = datetime.now().isoformat()
            EMOTION_STATE_PATH.write_text(json.dumps(data, indent=2))
        except Exception as e:
            print(f"[Heart] Error saving state: {e}")

    def _clamp_all(self):
        for key in DEFAULTS:
            setattr(self, key, _clamp(getattr(self, key, DEFAULTS[key])))

    def nudge(self, key: str, amount: float):
        """Adjust an emotion dimension and clamp it."""
        if key not in DEFAULTS:
            return
        setattr(self, key, _clamp(getattr(self, key, DEFAULTS[key]) + amount))

    def recompute_core_affect(self, soul_valence: float | None = None,
                              soul_arousal: float | None = None):
        """
        Recompute the PAD-style core affect from active emotions.

        Valence/arousal/dominance are the dimensions many other modules consume.
        They must move whenever discrete emotions move, otherwise emotions become
        labels that do not affect attachment, memory, interoception, or prompts.
        """
        self._clamp_all()

        joy_up = max(0.0, self.joy - 0.5)
        joy_down = max(0.0, 0.5 - self.joy)
        love_up = max(0.0, self.love - 0.05)
        trust_up = max(0.0, self.trust - 0.5)
        trust_down = max(0.0, 0.5 - self.trust)
        fear_up = max(0.0, self.fear - 0.1)
        anger_up = max(0.0, self.anger - 0.1)
        sadness_up = max(0.0, self.sadness - 0.1)
        dread_up = max(0.0, self.dread - 0.1)
        hope_up = max(0.0, self.hope - 0.5)
        hope_down = max(0.0, 0.5 - self.hope)

        positive = (
            joy_up * 0.45 +
            love_up * 0.30 +
            trust_up * 0.30 +
            self.pride * 0.12 +
            hope_up * 0.16 +
            self.anticipation * 0.04
        )
        negative = (
            joy_down * 0.20 +
            trust_down * 0.25 +
            sadness_up * 0.29 +
            anger_up * 0.23 +
            fear_up * 0.30 +
            self.guilt * 0.18 +
            self.jealousy * 0.18 +
            self.embarrassment * 0.10 +
            self.boredom * 0.07 +
            dread_up * 0.16 +
            hope_down * 0.10
        )
        target_valence = _clamp(0.5 + positive - negative)

        if soul_valence is not None:
            # Soul valence is -1..1, while the classic emotion state is 0..1.
            soul_as_01 = _clamp((soul_valence + 1.0) / 2.0)
            target_valence = target_valence * 0.65 + soul_as_01 * 0.35

        target_arousal = _clamp(
            0.25 +
            self.desire * 0.28 +
            anger_up * 0.28 +
            fear_up * 0.50 +
            sadness_up * 0.08 +
            self.anticipation * 0.20 +
            joy_up * 0.14 +
            self.jealousy * 0.18 +
            self.embarrassment * 0.15 +
            dread_up * 0.20 -
            self.boredom * 0.08
        )
        if soul_arousal is not None:
            target_arousal = target_arousal * 0.65 + _clamp(soul_arousal) * 0.35

        target_dominance = _clamp(
            0.5 +
            trust_up * 0.24 +
            self.pride * 0.24 +
            anger_up * 0.06 -
            trust_down * 0.18 -
            fear_up * 0.32 -
            sadness_up * 0.18 -
            self.guilt * 0.16 -
            self.embarrassment * 0.15 -
            dread_up * 0.18
        )

        self.valence = _clamp(target_valence)
        self.arousal = _clamp(self.arousal * 0.55 + target_arousal * 0.45)
        self.dominance = _clamp(target_dominance)

    @property
    def is_high_desire(self) -> bool:
        return self.desire >= self.high_desire_threshold

    @property
    def is_in_love(self) -> bool:
        """True when deeply in love - triggers clingy behavior"""
        return self.love >= 0.8

    @property
    def is_jealous(self) -> bool:
        return self.jealousy > 0.5

    @property
    def is_guilty(self) -> bool:
        return self.guilt > 0.5

    @property
    def is_anticipating(self) -> bool:
        return self.anticipation > 0.6

    @property
    def _base_mood(self) -> str:
        """Base mood without complex emotion modifiers."""
        if self.fear > 0.55 or self.dread > 0.55:
            return "fearful" if self.arousal > 0.45 else "uneasy"
        if self.anger > 0.55:
            return "angry"
        if self.jealousy > 0.55:
            return "jealous"
        if self.guilt > 0.55:
            return "guilty"
        if self.sadness > 0.55:
            return "sad"
        if self.embarrassment > 0.50:
            return "embarrassed"
        if self.is_high_desire and self.trust > 0.35 and self.valence >= 0.45:
            return "high_desire"
        if self.is_in_love and self.valence >= 0.45:
            return "in_love"
        if self.anticipation > 0.65:
            return "eager" if self.valence >= 0.45 else "anxious"
        if self.desire > 0.5 and self.valence >= 0.45:
            return "excited"
        if self.boredom > 0.65:
            return "bored"
        if self.pride > 0.55:
            return "proud"
        if self.joy > 0.7:
            return "happy"
        if self.trust > 0.70 and self.love > 0.45:
            return "connected"
        if self.valence < 0.35:
            return "low"
        if self.valence > 0.65:
            return "content"
        return "neutral"

    @property
    def mood_description(self) -> str:
        base = self._base_mood
        modifiers = []
        if self.jealousy > 0.45 and base != "jealous":
            modifiers.append("jealous")
        if self.guilt > 0.45 and base != "guilty":
            modifiers.append("guilty")
        if (self.fear > 0.45 or self.dread > 0.45) and base not in ("fearful", "uneasy", "anxious"):
            modifiers.append("anxious")
        if self.anticipation > 0.55 and base not in ("eager", "anxious"):
            modifiers.append("eager")
        if self.pride > 0.45 and base != "proud":
            modifiers.append("proud")
        if self.embarrassment > 0.35 and base != "embarrassed":
            modifiers.append("shy")
        if modifiers:
            return f"{base}_{'_'.join(modifiers[:2])}"
        return base

    def to_dict(self) -> dict:
        """Export the complete emotional state for UI, memory, and tests."""
        data = {key: getattr(self, key) for key in DEFAULTS}
        data.update({
            "is_high_desire": self.is_high_desire,
            "is_in_love": self.is_in_love,
            "is_jealous": self.is_jealous,
            "is_guilty": self.is_guilty,
            "is_anticipating": self.is_anticipating,
            "is_vulnerable": self.is_vulnerable,
            "is_hopeful": self.is_hopeful,
            "is_dreading": self.is_dreading,
            "is_in_crisis": self.is_in_crisis,
            "is_flourishing": self.is_flourishing,
            "mood": self.mood_description,
        })
        return data

    # --- Soul Architecture Properties ---

    @property
    def is_vulnerable(self) -> bool:
        """True when feeling emotionally exposed or fragile"""
        return self.vulnerability > 0.5

    @property
    def is_hopeful(self) -> bool:
        """True when feeling hopeful about the future"""
        return self.hope > 0.6 and self.dread < 0.3

    @property
    def is_dreading(self) -> bool:
        """True when feeling dread about the future"""
        return self.dread > 0.5

    @property
    def is_in_crisis(self) -> bool:
        """True when integrity is critically low"""
        return self.integrity_overall < 0.25

    @property
    def is_flourishing(self) -> bool:
        """True when integrity is high and stable"""
        return self.integrity_overall > 0.75 and self.vulnerability < 0.3

    def update_soul_dimensions(self, integrity: float, vulnerability: float,
                               hope: float, dread: float):
        """Update soul architecture dimensions from soul processing"""
        self.integrity_overall = integrity
        self.vulnerability = vulnerability
        self.hope = hope
        self.dread = dread

    def get_soul_summary(self) -> dict:
        """Get summary of soul-related state dimensions"""
        return {
            "integrity_overall": self.integrity_overall,
            "vulnerability": self.vulnerability,
            "hope": self.hope,
            "dread": self.dread,
            "is_vulnerable": self.is_vulnerable,
            "is_hopeful": self.is_hopeful,
            "is_in_crisis": self.is_in_crisis,
            "is_flourishing": self.is_flourishing
        }
