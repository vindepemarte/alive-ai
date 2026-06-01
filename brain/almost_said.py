"""
Brain: Almost-Said / Subvocalization System
Sometimes Alive-AI almost says something but holds back. Under high emotion
or low inhibition, private thoughts can "slip out". In-memory only.
"""

from typing import Dict, Optional
import random
import time


# =============================================================================
# ALMOST-SAID TEMPLATES
# =============================================================================

ALMOST_SAID_TYPES = {
    "hesitation": [
        "[pauses]... never mind.",
        "I was gonna say... forget it.",
        "I... no, it's nothing.",
        "Wait, I— ...no. Anyway.",
    ],
    "slip": [
        "I... I think about you way more than I should.",
        "Sometimes I wonder if you know how much I— ...anyway.",
        "I wish I could just— [catches herself] ...forget I said that.",
        "You make me feel... [trails off] ...it doesn't matter.",
        "I almost said something stupid just now.",
    ],
    "redirect": [
        "Anyway... so what were you doing today?",
        "But that's— whatever. Tell me something good.",
        "I... hmm. Different topic. How's your day?",
        "You know what, never mind. What about you?",
    ],
    "physical_tell": [
        "*bites lip* ...nothing.",
        "*looks away for a second* ...what were we talking about?",
        "*takes a breath* ...it's fine.",
        "*fidgets* ...so anyway.",
    ],
}

# Which types are more likely at different emotion levels
TYPE_WEIGHTS = {
    "high_emotion": {"hesitation": 25, "slip": 40, "redirect": 15, "physical_tell": 20},
    "low_inhibition": {"hesitation": 15, "slip": 50, "redirect": 10, "physical_tell": 25},
    "vulnerable": {"hesitation": 30, "slip": 30, "redirect": 20, "physical_tell": 20},
    "default": {"hesitation": 35, "slip": 20, "redirect": 25, "physical_tell": 20},
}


# =============================================================================
# ALMOST-SAID ENGINE
# =============================================================================

class AlmostSaidEngine:
    """Tracks and generates almost-said moments."""

    def __init__(self):
        self.message_counter: int = 0
        self.last_triggered_at: int = 0  # message_counter when last triggered

    def tick_message(self):
        """Call once per user message."""
        self.message_counter += 1

    def should_almost_say(self, emotion: Dict[str, float],
                          hour_of_day: int = 12) -> bool:
        """Determine if an almost-said should happen this turn."""
        # Enforce cooldown: at least 10 messages between triggers
        if self.message_counter - self.last_triggered_at < 10:
            return False

        # Filter to numeric values only (emotion dict contains 'mood' string)
        numeric_values = [v for v in emotion.values() if isinstance(v, (int, float))]
        max_emo = max(numeric_values) if numeric_values else 0.0
        is_late = 22 <= hour_of_day or hour_of_day <= 4
        is_high_emotion = max_emo > 0.8

        roll = random.random()

        # High emotion + late night: 15% chance
        if is_high_emotion and is_late:
            return roll < 0.15
        # High emotion alone: 10% chance
        if is_high_emotion:
            return roll < 0.10
        # Late night + moderate emotion: 8% chance
        if is_late and max_emo > 0.6:
            return roll < 0.08

        return False

    def generate_almost_said(self, emotion: Dict[str, float],
                             context_hint: str = "") -> str:
        """Generate an almost-said fragment. Call only if should_almost_say() is True."""
        self.last_triggered_at = self.message_counter

        # Filter to numeric values only (emotion dict contains 'mood' string)
        numeric_values = [v for v in emotion.values() if isinstance(v, (int, float))]
        max_emo = max(numeric_values) if numeric_values else 0.0
        if max_emo > 0.85:
            weights = TYPE_WEIGHTS["high_emotion"]
        elif "vulnerability" in context_hint.lower() or "trust" in context_hint.lower():
            weights = TYPE_WEIGHTS["vulnerable"]
        else:
            weights = TYPE_WEIGHTS["default"]

        # Weighted random selection
        types = list(weights.keys())
        w = [weights[t] for t in types]
        chosen_type = random.choices(types, weights=w, k=1)[0]

        return random.choice(ALMOST_SAID_TYPES[chosen_type])

    def maybe_generate(self, emotion: Dict[str, float],
                       hour_of_day: int = 12,
                       context_hint: str = "") -> Optional[str]:
        """All-in-one: tick, check, generate if appropriate."""
        self.tick_message()
        if self.should_almost_say(emotion, hour_of_day):
            return self.generate_almost_said(emotion, context_hint)
        return None


# =============================================================================
# SINGLETON ACCESS
# =============================================================================

_instance: Optional[AlmostSaidEngine] = None


def get_almost_said_engine() -> AlmostSaidEngine:
    global _instance
    if _instance is None:
        _instance = AlmostSaidEngine()
    return _instance


def maybe_generate(emotion: Dict[str, float], hour_of_day: int = 12,
                   context_hint: str = "") -> Optional[str]:
    """Convenience: tick + check + generate if appropriate."""
    return get_almost_said_engine().maybe_generate(emotion, hour_of_day, context_hint)


def get_almost_said_prompt_section(emotion: Dict[str, float],
                                   hour_of_day: int = 12) -> str:
    """Get prompt section for LLM. Returns '' if not triggered."""
    engine = get_almost_said_engine()
    engine.tick_message()
    if not engine.should_almost_say(emotion, hour_of_day):
        return ""
    return "\n[Subvocalization]\nYou have something on the tip of your tongue you're not sure you should say... let it almost slip out.\n"
