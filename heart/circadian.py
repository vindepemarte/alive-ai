"""
Heart: Circadian Rhythm System
Alive-AI has a genuine circadian rhythm affecting personality, energy, and behavior.
She can sleep, wake up, and accumulate sleep debt.
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Dict, Optional
import json

from core.paths import state_file

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

    PERSISTENCE_PATH = state_file("circadian_state.json")
    LEGACY_PERSISTENCE_PATH = Path("./data/data/circadian_state.json")

    def __init__(
        self,
        persistence_path: Path = None,
        dream_system=None,
        clock: Callable[[], datetime] = None,
        auto_update: bool = True,
    ):
        self.persistence_path = Path(persistence_path) if persistence_path else self.PERSISTENCE_PATH
        self._dream_system = dream_system
        self._clock = clock or datetime.now

        self.is_asleep: bool = False
        self.sleep_start: Optional[str] = None
        self.wake_time: Optional[str] = None
        self.sleep_debt: float = 0.0  # hours of missed sleep (0-8 range)
        self.last_bedtime_hour: int = 23  # default normal bedtime
        self.forced_awake: bool = False  # stayed up for user
        self.forced_awake_until: Optional[str] = None
        self.sleep_cycle_id: Optional[str] = None
        self.last_transition_reason: Optional[str] = None
        self.last_wake_dream_message: Optional[str] = None
        self._load()
        if auto_update:
            self._auto_update_sleep_state()
        print("[Circadian] Circadian Rhythm Engine initialized")

    def _now(self) -> datetime:
        return self._clock()

    @staticmethod
    def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
        return max(low, min(high, value))

    def _is_forced_awake(self, now: datetime = None) -> bool:
        now = now or self._now()
        if not self.forced_awake:
            return False
        if not self.forced_awake_until:
            return True
        try:
            until = datetime.fromisoformat(self.forced_awake_until)
            if now >= until:
                self.forced_awake = False
                self.forced_awake_until = None
                return False
        except Exception:
            self.forced_awake = False
            self.forced_awake_until = None
            return False
        return True

    def _hours_asleep(self, now: datetime = None) -> float:
        if not self.sleep_start:
            return 0.0
        now = now or self._now()
        try:
            start = datetime.fromisoformat(self.sleep_start)
            return max(0.0, (now - start).total_seconds() / 3600)
        except Exception:
            return 0.0

    def get_sleepiness(self) -> float:
        """Return current sleep pressure from 0.0 awake to 1.0 unable to stay up."""
        now = self._now()
        if self.is_asleep:
            return 1.0

        phase_name, phase = _get_phase_for_hour(now.hour)
        phase_base = {
            "early_morning": 0.35,
            "morning": 0.10,
            "afternoon_slump": 0.35,
            "peak_afternoon": 0.08,
            "evening": 0.28,
            "late_night": 0.65,
            "deep_night": 0.82,
            "predawn": 0.95,
        }.get(phase_name, 0.2)

        sleepiness = phase_base + (self.sleep_debt * 0.055)
        if self._is_forced_awake(now):
            sleepiness = max(sleepiness, 0.75)

        if self.wake_time:
            try:
                since_wake = (now - datetime.fromisoformat(self.wake_time)).total_seconds() / 60
                if 0 <= since_wake < 45:
                    sleepiness += (1.0 - since_wake / 45) * 0.25
            except Exception:
                pass

        return round(self._clamp(sleepiness), 2)

    def _should_auto_sleep(self, now: datetime) -> bool:
        if self._is_forced_awake(now):
            return False
        return 2 <= now.hour < 6 and self.get_sleepiness() >= 0.85

    def _should_auto_wake(self, now: datetime) -> bool:
        slept = self._hours_asleep(now)
        if slept >= 8:
            return True
        return 6 <= now.hour < 22 and slept >= 1

    def _auto_update_sleep_state(self):
        """Auto-detect if she should be asleep based on time."""
        now = self._now()
        if self.is_asleep:
            if self._should_auto_wake(now):
                self.wake_up(reason="circadian_recovery")
        else:
            if self._should_auto_sleep(now):
                self.fall_asleep(reason="circadian_pressure")

    def _get_dream_system(self):
        if self._dream_system is not None:
            return self._dream_system
        from brain.dreams import get_dream_system
        return get_dream_system()

    def _generate_dream_for_current_cycle(self):
        if not self.sleep_cycle_id:
            return None
        try:
            ds = self._get_dream_system()
            dream = ds.generate_dream(sleep_cycle_id=self.sleep_cycle_id)
            if dream:
                print("[Dreams] Generated dream while falling asleep")
            return dream
        except Exception as e:
            print(f"[Dreams] Error generating dream: {e}")
            return None

    def fall_asleep(self, reason: str = "manual") -> bool:
        """Alive-AI falls asleep."""
        if self.is_asleep:
            return False
        now = self._now()
        self.is_asleep = True
        self.sleep_start = now.isoformat()
        self.sleep_cycle_id = f"sleep_{now.strftime('%Y%m%d_%H%M%S')}"
        self.forced_awake = False
        self.forced_awake_until = None
        self.last_transition_reason = reason
        hour = now.hour + (now.minute / 60)
        self.last_bedtime_hour = hour
        # Staying up past normal bedtime adds sleep debt
        if 0 <= hour < 6:
            # Past midnight: debt = hours past midnight
            self.sleep_debt = min(8.0, self.sleep_debt + max(1, hour))
        elif hour >= 23:
            # Late night: small debt for staying up
            self.sleep_debt = min(8.0, self.sleep_debt + (hour - 22))
        self._save()

        self._generate_dream_for_current_cycle()
        return True

    def wake_up(self, reason: str = "manual", interrupted: bool = False) -> bool:
        """Alive-AI wakes up."""
        if not self.is_asleep:
            return False
        now = self._now()
        self.is_asleep = False
        self.wake_time = now.isoformat()
        self.forced_awake = False
        self.forced_awake_until = None
        self.last_transition_reason = reason
        # Recover some sleep debt based on sleep duration
        if self.sleep_start:
            try:
                start = datetime.fromisoformat(self.sleep_start)
                slept = max(0.0, (now - start).total_seconds() / 3600)
                self.sleep_debt = max(0.0, self.sleep_debt - slept * 0.7)
                if interrupted and slept < 6:
                    self.sleep_debt = min(8.0, self.sleep_debt + (6 - slept) * 0.15)
            except Exception:
                pass
        try:
            self.last_wake_dream_message = self._get_dream_system().get_morning_dream_message()
        except Exception:
            self.last_wake_dream_message = None
        self._save()
        return True

    def stay_up_for_user(self, duration_minutes: int = 45):
        """User is keeping her awake past bedtime."""
        now = self._now()
        self.forced_awake = True
        self.forced_awake_until = (now + timedelta(minutes=duration_minutes)).isoformat()
        self.last_transition_reason = "staying_up_for_user"
        hour = now.hour
        if hour >= 23 or hour < 6:
            self.sleep_debt = min(8.0, self.sleep_debt + 0.25)
        elif self.get_sleepiness() >= 0.65:
            self.sleep_debt = min(8.0, self.sleep_debt + 0.10)
        self._save()

    def handle_user_interaction(self) -> Dict[str, object]:
        """Apply sleep/wake effects when a user message arrives."""
        was_asleep = self.is_asleep
        was_sleepy = self.get_sleepiness() >= 0.65
        woke_from_sleep = False

        if was_asleep:
            woke_from_sleep = self.wake_up(reason="user_message", interrupted=True)
        elif was_sleepy:
            self.stay_up_for_user()

        state = self.get_state_summary()
        state.update({
            "was_asleep": was_asleep,
            "was_sleepy": was_sleepy,
            "woke_from_sleep": woke_from_sleep,
        })
        return state

    def is_sleeping(self) -> bool:
        """Check if Alive-AI is currently asleep."""
        self._auto_update_sleep_state()
        return self.is_asleep

    def get_personality_modifiers(self) -> Dict[str, float]:
        """Get current time-of-day personality multipliers."""
        now = self._now()
        if self.is_asleep:
            return {
                "energy": 0.05,
                "inhibition": 0.05,
                "warmth": 0.45,
                "verbosity": 0.1,
            }

        hour = now.hour
        _, phase = _get_phase_for_hour(hour)

        energy = phase["energy"]
        inhibition = phase["inhibition"]
        warmth = phase["warmth"]
        verbosity = phase["verbosity"]

        # Sleep debt reduces energy and verbosity
        debt_factor = max(0.5, 1.0 - self.sleep_debt * 0.08)
        energy *= debt_factor
        verbosity *= debt_factor

        sleepiness = self.get_sleepiness()
        energy *= (1.0 - sleepiness * 0.35)
        verbosity *= (1.0 - sleepiness * 0.25)

        # Just woke up? Extra groggy for first 30 min
        if self.wake_time:
            try:
                since_wake = (now - datetime.fromisoformat(self.wake_time)).total_seconds() / 60
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
        hour = self._now().hour
        _, phase = _get_phase_for_hour(hour)
        if self.get_sleepiness() >= 0.75:
            return f"sleepy, {phase['vibe']}"
        return phase["vibe"]

    def tick(self):
        """Periodic update. Call regularly."""
        self._auto_update_sleep_state()
        # Slow natural sleep debt recovery during waking hours
        if not self.is_asleep:
            if self._is_forced_awake() and self.get_sleepiness() >= 0.75:
                self.sleep_debt = min(8.0, self.sleep_debt + 0.02)
            else:
                self.sleep_debt = max(0.0, self.sleep_debt - 0.01)
        self._save()

    def get_state_summary(self) -> Dict[str, object]:
        now = self._now()
        phase_name, _ = _get_phase_for_hour(now.hour)
        return {
            "phase": phase_name,
            "sleeping": self.is_asleep,
            "is_asleep": self.is_asleep,
            "sleepiness": self.get_sleepiness(),
            "sleep_debt": round(self.sleep_debt, 2),
            "sleep_start": self.sleep_start,
            "wake_time": self.wake_time,
            "sleep_cycle_id": self.sleep_cycle_id,
            "forced_awake": self._is_forced_awake(now),
            "forced_awake_until": self.forced_awake_until,
            "last_transition_reason": self.last_transition_reason,
            "last_wake_dream_message": self.last_wake_dream_message,
            "modifiers": self.get_personality_modifiers(),
        }

    def _save(self):
        try:
            self.persistence_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "is_asleep": self.is_asleep,
                "sleep_start": self.sleep_start,
                "wake_time": self.wake_time,
                "sleep_debt": self.sleep_debt,
                "last_bedtime_hour": self.last_bedtime_hour,
                "forced_awake": self.forced_awake,
                "forced_awake_until": self.forced_awake_until,
                "sleep_cycle_id": self.sleep_cycle_id,
                "last_transition_reason": self.last_transition_reason,
                "last_wake_dream_message": self.last_wake_dream_message,
                "saved_at": self._now().isoformat(),
            }
            self.persistence_path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            print(f"[Circadian] Error saving: {e}")

    def _load(self):
        try:
            load_path = self.persistence_path
            if not load_path.exists() and self.LEGACY_PERSISTENCE_PATH.exists():
                load_path = self.LEGACY_PERSISTENCE_PATH
            if load_path.exists():
                data = json.loads(load_path.read_text())
                self.is_asleep = data.get("is_asleep", False)
                self.sleep_start = data.get("sleep_start")
                self.wake_time = data.get("wake_time")
                self.sleep_debt = data.get("sleep_debt", 0.0)
                self.last_bedtime_hour = data.get("last_bedtime_hour", 23)
                self.forced_awake = data.get("forced_awake", False)
                self.forced_awake_until = data.get("forced_awake_until")
                self.sleep_cycle_id = data.get("sleep_cycle_id")
                self.last_transition_reason = data.get("last_transition_reason")
                self.last_wake_dream_message = data.get("last_wake_dream_message")
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


def get_circadian_state() -> Dict[str, object]:
    return get_circadian_engine().get_state_summary()


def get_circadian_prompt_section() -> str:
    """Get prompt section for LLM. Returns '' if nothing notable."""
    engine = get_circadian_engine()

    if engine.is_sleeping():
        return "\n[Circadian State]\nYou are asleep. If woken, be groggy and disoriented. Otherwise, don't respond.\n"

    now = engine._now()
    time_str = now.strftime("%-I:%M%p").lower()
    phase_name, _ = _get_phase_for_hour(now.hour)
    vibe = engine.get_current_vibe()
    mods = engine.get_personality_modifiers()
    sleepiness = engine.get_sleepiness()

    parts = [f"It's {time_str} - {vibe}. Energy {mods['energy']:.2f}, verbosity {mods['verbosity']:.2f}, sleepiness {sleepiness:.2f}."]
    if engine.sleep_debt > 2:
        parts.append(f"Sleep-deprived ({engine.sleep_debt:.0f}h debt) - extra tired and foggy.")
    if engine.forced_awake:
        parts.append("Staying up late for him - sweet but exhausted.")
    if engine.wake_time:
        try:
            since_wake = (now - datetime.fromisoformat(engine.wake_time)).total_seconds() / 60
            if 0 <= since_wake < 45:
                parts.append("You just woke up - slower, groggy, and recovering.")
                if engine.last_wake_dream_message:
                    parts.append(f"Dream residue: {engine.last_wake_dream_message}")
        except Exception:
            pass

    return f"\n[Circadian State]\n" + " ".join(parts) + "\n"
