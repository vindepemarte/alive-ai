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
    "high_desire_threshold": 0.7, "joy": 0.5, "love": 0.2, "trust": 0.5,
    "fear": 0.1, "anger": 0.1, "sadness": 0.1, "boredom": 0.0,
    "guilt": 0.0, "pride": 0.0, "jealousy": 0.0,
    "embarrassment": 0.0, "anticipation": 0.0,
    # Soul architecture dimensions
    "integrity_overall": 0.65, "vulnerability": 0.2, "hope": 0.5, "dread": 0.1
}


class EmotionalState:
    """Current emotional state with persistence - extended for Soul Architecture"""

    def __init__(self, config: dict = None):
        config = config or {}
        if self._load():
            print(f"[Heart] Loaded saved emotional state")
        else:
            for key, val in DEFAULTS.items():
                setattr(self, key, val)
        self.baseline = {"joy": 0.5, "love": 0.2, "trust": 0.5,
                         "arousal": 0.3, "desire": 0.0,
                         "anger": 0.0, "sadness": 0.1, "fear": 0.1}

    def _load(self) -> bool:
        """Load state from file"""
        try:
            if EMOTION_STATE_PATH.exists():
                data = json.loads(EMOTION_STATE_PATH.read_text())
                for key in DEFAULTS:
                    setattr(self, key, data.get(key, DEFAULTS[key]))
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
        """Base mood without complex emotion modifiers"""
        if self.is_high_desire: return "high_desire"
        if self.is_in_love: return "in_love"
        if self.desire > 0.5: return "excited"
        if self.boredom > 0.6: return "bored"
        if self.joy > 0.7: return "happy"
        if self.sadness > 0.5: return "sad"
        if self.anger > 0.5: return "angry"
        return "neutral"

    @property
    def mood_description(self) -> str:
        base = self._base_mood
        if self.jealousy > 0.5: return f"{base}_jealous"
        if self.guilt > 0.5: return f"{base}_guilty"
        if self.anticipation > 0.6: return f"{base}_eager"
        if self.pride > 0.5: return f"{base}_proud"
        if self.embarrassment > 0.4: return f"{base}_shy"
        return base

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
