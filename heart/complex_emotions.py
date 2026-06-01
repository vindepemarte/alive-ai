"""
Heart: Complex Emotions
Secondary emotions that blend with base emotions - guilt, pride, jealousy, etc.
"""

from dataclasses import dataclass


@dataclass
class ComplexEmotion:
    """A complex emotion with blend factors"""
    value: float = 0.0
    trigger_count: int = 0
    last_intensity: float = 0.0


class ComplexEmotions:
    """Secondary emotions that add depth to emotional responses"""

    # Trigger words for complex emotions
    GUILT_TRIGGERS = [
        "you hurt me", "you forgot", "you lied", "you promised",
        "you should have", "why didn't you", "your fault",
        "you made me feel bad", "you disappointed me", "you ignored me"
    ]

    PRIDE_TRIGGERS = [
        "proud of you", "you did great", "amazing job", "well done",
        "accomplished", "achievement", "success", "you're so good"
    ]

    JEALOUSY_TRIGGERS = [
        "other girl", "she's", "my ex", "talking to", "with someone",
        "her name", "another woman", "met this girl", "friend who's a girl"
    ]

    EMBARRASSMENT_TRIGGERS = [
        "awkward", "cringe", "embarrassing", "lol at you", "haha you",
        "everyone saw", "in public", "so embarrassed"
    ]

    ANTICIPATION_TRIGGERS = [
        "can't wait", "excited for", "looking forward", "counting down",
        "soon", "tomorrow", "this weekend", "planned", "surprise"
    ]

    def __init__(self):
        self.guilt = ComplexEmotion()
        self.pride = ComplexEmotion()
        self.jealousy = ComplexEmotion()
        self.embarrassment = ComplexEmotion()
        self.anticipation = ComplexEmotion()

    def load_from_state(self, state):
        """Hydrate complex emotions from a persisted EmotionalState."""
        for name in ("guilt", "pride", "jealousy", "embarrassment", "anticipation"):
            if hasattr(state, name):
                getattr(self, name).value = max(0.0, min(1.0, float(getattr(state, name))))

    def process(self, message: str) -> dict:
        """Process message for complex emotion triggers"""
        msg = message.lower()
        changes = {}

        # Check each complex emotion
        if any(t in msg for t in self.GUILT_TRIGGERS):
            self.guilt.value = min(1.0, self.guilt.value + 0.3)
            self.guilt.trigger_count += 1
            changes["guilt"] = 0.3

        if any(t in msg for t in self.PRIDE_TRIGGERS):
            self.pride.value = min(1.0, self.pride.value + 0.25)
            self.pride.trigger_count += 1
            changes["pride"] = 0.25

        if any(t in msg for t in self.JEALOUSY_TRIGGERS):
            self.jealousy.value = min(1.0, self.jealousy.value + 0.35)
            self.jealousy.trigger_count += 1
            changes["jealousy"] = 0.35

        if any(t in msg for t in self.EMBARRASSMENT_TRIGGERS):
            self.embarrassment.value = min(1.0, self.embarrassment.value + 0.25)
            self.embarrassment.trigger_count += 1
            changes["embarrassment"] = 0.25

        if any(t in msg for t in self.ANTICIPATION_TRIGGERS):
            self.anticipation.value = min(1.0, self.anticipation.value + 0.3)
            self.anticipation.trigger_count += 1
            changes["anticipation"] = 0.3

        return changes

    def decay(self):
        """Natural decay of complex emotions"""
        rate = 0.03
        self.guilt.value = max(0, self.guilt.value - rate)
        self.pride.value = max(0, self.pride.value - rate * 0.5)  # Pride lingers
        self.jealousy.value = max(0, self.jealousy.value - rate * 0.7)  # Jealousy lingers
        self.embarrassment.value = max(0, self.embarrassment.value - rate * 1.5)  # Fades faster
        self.anticipation.value = max(0, self.anticipation.value - rate * 0.3)  # Very sticky

    def get_blended_mood(self, base_mood: str) -> str:
        """Blend complex emotions into mood description"""
        if self.jealousy.value > 0.5:
            return f"{base_mood}_jealous"
        if self.guilt.value > 0.5:
            return f"{base_mood}_guilty"
        if self.anticipation.value > 0.6:
            return f"{base_mood}_excited"
        if self.pride.value > 0.5:
            return f"{base_mood}_proud"
        return base_mood

    def to_dict(self) -> dict:
        return {
            "guilt": self.guilt.value,
            "pride": self.pride.value,
            "jealousy": self.jealousy.value,
            "embarrassment": self.embarrassment.value,
            "anticipation": self.anticipation.value
        }
