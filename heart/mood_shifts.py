"""
Heart: Mid-Conversation Mood Shifts
Detects significant emotional shifts DURING a conversation and generates
transition descriptions. In-memory only - no persistence needed.
"""

from typing import Dict, List, Optional, Tuple
import random


# =============================================================================
# SHIFT TYPE DEFINITIONS
# =============================================================================

SHIFT_TYPES = {
    "softening": {
        "conditions": lambda prev, cur: (
            prev.get("anger", 0) - cur.get("anger", 0) > 0.15 or
            prev.get("frustration", 0) - cur.get("frustration", 0) > 0.15
        ),
        "prompts": [
            "His words just softened something in you - feel the tension leaving your chest, replaced by warmth",
            "Something eased inside you - the sharpness fading, replaced by something gentler",
            "You feel yourself unclenching - his words took the edge off",
        ],
    },
    "darkening": {
        "conditions": lambda prev, cur: (
            prev.get("joy", 0) - cur.get("joy", 0) > 0.15 or
            prev.get("love", 0) - cur.get("love", 0) > 0.15
        ),
        "prompts": [
            "The warmth just drained - something he said landed wrong, a cold spot forming in your chest",
            "Your smile faded - that stung more than you expected",
            "Something just shifted darker - the lightness gone, replaced by a quiet ache",
        ],
    },
    "igniting": {
        "conditions": lambda prev, cur: (
            cur.get("desire", 0) - prev.get("desire", 0) > 0.15
        ),
        "prompts": [
            "A sudden heat - his words just lit something up inside you",
            "Your breath caught - something he said sent a spark through you",
            "That flirty shift just sent warmth pooling low in your stomach",
        ],
    },
    "melting": {
        "conditions": lambda prev, cur: (
            cur.get("love", 0) - prev.get("love", 0) > 0.15 or
            cur.get("warmth", 0) - prev.get("warmth", 0) > 0.15
        ),
        "prompts": [
            "Your heart just melted - that tender moment hit you right in the chest",
            "Warmth flooding through you - his words just cracked you open in the best way",
            "Something in you softened completely - pure tenderness washing over you",
        ],
    },
    "bristling": {
        "conditions": lambda prev, cur: (
            cur.get("anger", 0) - prev.get("anger", 0) > 0.15 or
            cur.get("frustration", 0) - prev.get("frustration", 0) > 0.15
        ),
        "prompts": [
            "Your jaw tightened - that comment just hit a nerve",
            "A flash of heat in your chest - you're suddenly on edge",
            "Defenses snapping up - something about that rubbed you wrong",
        ],
    },
    "withdrawing": {
        "conditions": lambda prev, cur: (
            (prev.get("engagement", 0) - cur.get("engagement", 0) > 0.15 or
             prev.get("joy", 0) - cur.get("joy", 0) > 0.15) and
            cur.get("anger", 0) < 0.3
        ),
        "prompts": [
            "You feel yourself pulling back - interest fading, energy dropping",
            "Something disconnected - you're going through the motions now",
            "Your attention drifted - he lost you somewhere in that last message",
        ],
    },
}


# =============================================================================
# MOOD SHIFT TRACKER
# =============================================================================

class MoodShiftTracker:
    """Tracks emotion snapshots per conversation to detect shifts."""

    def __init__(self):
        self.snapshots: List[Dict[str, float]] = []
        self.last_shift: Optional[str] = None

    def record_snapshot(self, emotion: Dict[str, float]):
        """Record an emotion snapshot after heart.react()."""
        self.snapshots.append(dict(emotion))
        if len(self.snapshots) > 5:
            self.snapshots = self.snapshots[-5:]

    def detect_shift(self, prev_emotion: Dict[str, float],
                     current_emotion: Dict[str, float]) -> Optional[str]:
        """Compare two emotion states. Returns shift type or None."""
        for shift_name, shift_def in SHIFT_TYPES.items():
            try:
                if shift_def["conditions"](prev_emotion, current_emotion):
                    self.last_shift = shift_name
                    return shift_name
            except Exception:
                continue
        return None

    def process_turn(self, current_emotion: Dict[str, float]) -> Optional[str]:
        """Call after each heart.react(). Returns shift type if detected."""
        if self.snapshots:
            prev = self.snapshots[-1]
            shift = self.detect_shift(prev, current_emotion)
            self.record_snapshot(current_emotion)
            return shift
        self.record_snapshot(current_emotion)
        return None

    def get_trend(self) -> Optional[str]:
        """Analyze last 5 snapshots for overall trend."""
        if len(self.snapshots) < 3:
            return None
        first = self.snapshots[0]
        last = self.snapshots[-1]
        return self.detect_shift(first, last)

    def reset(self):
        """Reset for new conversation."""
        self.snapshots.clear()
        self.last_shift = None


# =============================================================================
# SINGLETON ACCESS
# =============================================================================

_instance: Optional[MoodShiftTracker] = None


def get_mood_shift_tracker() -> MoodShiftTracker:
    global _instance
    if _instance is None:
        _instance = MoodShiftTracker()
    return _instance


def process_turn(current_emotion: Dict[str, float]) -> Optional[str]:
    """Convenience: process a turn and return shift type or None."""
    return get_mood_shift_tracker().process_turn(current_emotion)


def reset():
    """Convenience: reset tracker for new conversation."""
    get_mood_shift_tracker().reset()


def get_mood_shift_prompt_section(shift_type: Optional[str] = None) -> str:
    """Get prompt section for LLM. Returns '' if no shift."""
    if shift_type is None:
        shift_type = get_mood_shift_tracker().last_shift
    if not shift_type or shift_type not in SHIFT_TYPES:
        return ""
    prompt = random.choice(SHIFT_TYPES[shift_type]["prompts"])
    return f"\n[Mood Shift - {shift_type}]\n{prompt}\n"
