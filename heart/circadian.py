"""
Heart: Circadian Rhythm System
Alive-AI has a genuine circadian rhythm affecting personality, energy, and behavior.
She can sleep, wake up, and acclosenessulate sleep debt.
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional
import json

# =============================================================================
# TIME-OF-DAY PHASES
# =============================================================================

PHASES = {
    "early_morning":  {"hours": (6, 9),   "energy": 0.35, "inhibition": 0.3, "warmth": 0.8, "verbosity": 0.4, "vibe": "groggy, soft, vulnerable, words come slow"},
    "morning":        {"hours": (9, 12),  "energy": 0.75, "inhibition": 0.5, "warmth": 0.7, "verbosity": 0.7, "vibe": "energizing, playful, productive"},
    "afternoon_slump":{"hours": (12, 15), "energy": 0.55, "inhibition": 0.5, "warmth": 0.6, "verbosity": 0.6, "vibe": "slight afternoon slump, chill and mellow"},
    "peak_afternoon": {"hours": (15, 18), "energy": 0.85, "inhibition": 0.6, "warmth": 0.75, "verbosity": 0.8, "vibe": "peak energy, flirty, social, sparkling"},
    "evening":        {"hours": (18, 21), "energy": 0.6,  "inhibition": 0.5, "warmth": 0.85, "verbosity": 0.7, "vibe": "reflective, romantic, deeper conversations"},
    "late_night":     {"hours": (21, 24), "energy": 0.4,  "inhibition": 0.2, "warmth": 0.8, "verbosity": 0.55, "vibe": "getting sleepy, raw and unfiltered, inhibitions lowered"},
    "deep_night":     {"hours": (0, 3),   "energy": 0.2,  "inhibition": 0.1, "warmth": 0.7, "verbosity": 0.3, "vibe": "very sleepy, minimal responses, might fall asleep mid-sentence"},
    "predawn":        {"hours": (3, 6),   "energy": 0.1,  "inhibition": 0.1, "warmth": 0.5, "verbosity": 0.2, "vibe": "asleep - won't respond unless woken"},
}


def _get_phase_for_hour(hour: int) -> tuple:
    """Return (phase_name, phase_data) for a given hour."""
    for name, data in PHASES.items():
        start, end = data["hours"]
        if start <= hour < end:
            return name, data
    return "deep_night", PHASES["deep_night"]


# =============================================================================
# CIRCADIAN ENGINE
# =============================================================================

class CircadianEngine:
    """Manages Alive-AI's sleep/wake cycle and time-of-day personality."""

    PERSISTENCE_PATH = Path("./data/data/circadian_state.json")

    def __init__(self):
        self.is_asleep: bool = False
        self.sleep_start: Optional[str] = None
        self.wake_time: Optional[str] = None
        self.sleep_debt: float = 0.0  # hours of missed sleep (0-8 range)
        self.last_bedtime_hour: int = 23  # default normal bedtime
        self.forced_awake: bool = False  # stayed up for user
        self._load()
        self._auto_update_sleep_state()
        print("[Circadian] Circadian Rhythm Engine initialized")

    def _auto_update_sleep_state(self):
        """Auto-detect if she should be asleep based on time."""
        hour = datetime.now().hour
        if self.is_asleep:
            # Auto wake up between 6-9 AM
            if 6 <= hour < 9 and not self.forced_awake:
                self.wake_up()
        else:
            # Auto sleep if it's predawn and she hasn't been kept awake
            if 3 <= hour < 6 and not self.forced_awake:
                self.fall_asleep()

    def fall_asleep(self):
        """Alive-AI falls asleep."""
        self.is_asleep = True
        self.sleep_start = datetime.now().isoformat()
        self.forced_awake = False
        hour = datetime.now().hour
        self.last_bedtime_hour = hour
        # Staying up past normal bedtime adds sleep debt
        if hour >= 0 and hour < 6:
            # Past midnight: debt = hours past midnight
            self.sleep_debt = min(8.0, self.sleep_debt + max(1, hour))
        elif hour >= 23:
            # Late night: small debt for staying up
            self.sleep_debt = min(8.0, self.sleep_debt + (hour - 22))
        self._save()

        # Generate a dream when falling asleep
        try:
            from brain.dreams import get_dream_system
            ds = get_dream_system()
            dream = ds.generate_dream()
            if dream:
                print(f"[Dreams] Generated dream while falling asleep")
        except Exception as e:
            print(f"[Dreams] Error generating dream: {e}")

    def wake_up(self):
        """Alive-AI wakes up."""
        self.is_asleep = False
        self.wake_time = datetime.now().isoformat()
        self.forced_awake = False
        # Recover some sleep debt based on sleep duration
        if self.sleep_start:
            try:
                start = datetime.fromisoformat(self.sleep_start)
                slept = (datetime.now() - start).total_seconds() / 3600
                self.sleep_debt = max(0.0, self.sleep_debt - slept * 0.5)
            except Exception:
                pass
        self._save()

    def stay_up_for_user(self):
        """User is keeping her awake past bedtime."""
        self.forced_awake = True
        hour = datetime.now().hour
        if hour >= 23 or hour < 6:
            self.sleep_debt = min(8.0, self.sleep_debt + 0.25)
        self._save()

    def is_sleeping(self) -> bool:
        """Check if Alive-AI is currently asleep."""
        self._auto_update_sleep_state()
        return self.is_asleep

    def get_personality_modifiers(self) -> Dict[str, float]:
        """Get current time-of-day personality multipliers."""
        hour = datetime.now().hour
        _, phase = _get_phase_for_hour(hour)

        energy = phase["energy"]
        inhibition = phase["inhibition"]
        warmth = phase["warmth"]
        verbosity = phase["verbosity"]

        # Sleep debt reduces energy and verbosity
        debt_factor = max(0.5, 1.0 - self.sleep_debt * 0.08)
        energy *= debt_factor
        verbosity *= debt_factor

        # Just woke up? Extra groggy for first 30 min
        if self.wake_time:
            try:
                since_wake = (datetime.now() - datetime.fromisoformat(self.wake_time)).total_seconds() / 60
                if since_wake < 30:
                    grogginess = 1.0 - (since_wake / 30)
                    energy *= (1.0 - grogginess * 0.4)
                    verbosity *= (1.0 - grogginess * 0.3)
            except Exception:
                pass

        return {
            "energy": round(min(1.0, max(0.05, energy)), 2),
            "inhibition": round(inhibition, 2),
            "warmth": round(min(1.0, warmth), 2),
            "verbosity": round(min(1.0, max(0.1, verbosity)), 2),
        }

    def get_current_vibe(self) -> str:
        """Get a short description of current time-of-day vibe."""
        if self.is_sleeping():
            return "asleep"
        hour = datetime.now().hour
        _, phase = _get_phase_for_hour(hour)
        return phase["vibe"]

    def tick(self):
        """Periodic update. Call regularly."""
        self._auto_update_sleep_state()
        # Slow natural sleep debt recovery during waking hours
        if not self.is_asleep:
            self.sleep_debt = max(0.0, self.sleep_debt - 0.01)

    def _save(self):
        try:
            self.PERSISTENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "is_asleep": self.is_asleep,
                "sleep_start": self.sleep_start,
                "wake_time": self.wake_time,
                "sleep_debt": self.sleep_debt,
                "last_bedtime_hour": self.last_bedtime_hour,
                "forced_awake": self.forced_awake,
                "saved_at": datetime.now().isoformat(),
            }
            self.PERSISTENCE_PATH.write_text(json.dumps(data, indent=2))
        except Exception as e:
            print(f"[Circadian] Error saving: {e}")

    def _load(self):
        try:
            if self.PERSISTENCE_PATH.exists():
                data = json.loads(self.PERSISTENCE_PATH.read_text())
                self.is_asleep = data.get("is_asleep", False)
                self.sleep_start = data.get("sleep_start")
                self.wake_time = data.get("wake_time")
                self.sleep_debt = data.get("sleep_debt", 0.0)
                self.last_bedtime_hour = data.get("last_bedtime_hour", 23)
                self.forced_awake = data.get("forced_awake", False)
                print(f"[Circadian] Loaded state (asleep={self.is_asleep}, debt={self.sleep_debt:.1f}h)")
        except Exception as e:
            print(f"[Circadian] Error loading: {e}")


# =============================================================================
# SINGLETON ACCESS
# =============================================================================

_instance: Optional[CircadianEngine] = None


def get_circadian_engine() -> CircadianEngine:
    global _instance
    if _instance is None:
        _instance = CircadianEngine()
    return _instance


def is_sleeping() -> bool:
    return get_circadian_engine().is_sleeping()


def wake_up():
    get_circadian_engine().wake_up()


def fall_asleep():
    get_circadian_engine().fall_asleep()


def tick():
    get_circadian_engine().tick()


def get_circadian_prompt_section() -> str:
    """Get prompt section for LLM. Returns '' if nothing notable."""
    engine = get_circadian_engine()

    if engine.is_sleeping():
        return "\n[Circadian State]\nYou are asleep. If woken, be groggy and disoriented. Otherwise, don't respond.\n"

    now = datetime.now()
    time_str = now.strftime("%-I:%M%p").lower()
    phase_name, _ = _get_phase_for_hour(now.hour)
    vibe = engine.get_current_vibe()
    mods = engine.get_personality_modifiers()

    parts = [f"It's {time_str} - {vibe}."]
    if engine.sleep_debt > 2:
        parts.append(f"Sleep-deprived ({engine.sleep_debt:.0f}h debt) - extra tired and foggy.")
    if engine.forced_awake:
        parts.append("Staying up late for him - sweet but exhausted.")

    return f"\n[Circadian State]\n" + " ".join(parts) + "\n"
