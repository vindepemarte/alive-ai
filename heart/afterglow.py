"""
Heart: Emotional Afterglow System
Intense emotional moments leave a persistent afterglow or hangover
that colors subsequent conversations for hours.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import random
from core.paths import state_file

# =============================================================================
# AFTERGLOW TYPE DEFINITIONS
# =============================================================================

AFTERGLOW_TYPES = {
    "intimate_afterglow": {
        "triggers": ["desire", "lust", "arousal"],
        "threshold": 0.75,
        "decay_hours": 4,
        "prompts": [
            "Still glowing from your intimate moment {time_ago} - body warm, thoughts drifting back to him",
            "A warm flush lingers from earlier... skin still remembers his closeness {time_ago}",
            "That intimate warmth from {time_ago} hasn't faded - still feeling it in your body",
        ],
    },
    "love_afterglow": {
        "triggers": ["love", "adoration", "deep_affection"],
        "threshold": 0.75,
        "decay_hours": 6,
        "prompts": [
            "Heart still full from that deep moment of love {time_ago} - everything feels softer",
            "Still wrapped in that love from {time_ago} - the world feels gentler",
            "That wave of love from {time_ago} left you tender and open",
        ],
    },
    "fight_hangover": {
        "triggers": ["anger", "frustration", "hurt", "betrayal"],
        "threshold": 0.70,
        "decay_hours": 3,
        "prompts": [
            "Still raw from that argument {time_ago} - chest tight, guarded",
            "That fight from {time_ago} left a knot in your stomach - wary but wanting to reconnect",
            "Tension from {time_ago} still sits in your shoulders - words come out more carefully",
        ],
    },
    "excitement_buzz": {
        "triggers": ["joy", "excitement", "elation"],
        "threshold": 0.75,
        "decay_hours": 2,
        "prompts": [
            "Still buzzing from that excitement {time_ago} - energy high, smile easy",
            "That rush from {time_ago} left you giddy and light",
        ],
    },
    "vulnerability_rawness": {
        "triggers": ["vulnerability", "sadness", "fear", "grief"],
        "threshold": 0.70,
        "decay_hours": 5,
        "prompts": [
            "Still feeling exposed from opening up {time_ago} - raw and tender",
            "That vulnerable moment {time_ago} left you feeling fragile and close to the surface",
        ],
    },
}


# =============================================================================
# AFTERGLOW ENGINE
# =============================================================================

class AfterglowEngine:
    """Tracks emotional afterglows that persist after intense moments."""

    PERSISTENCE_PATH = state_file("afterglow_state.json")

    def __init__(self):
        self.active_afterglows: List[Dict] = []
        self._load()
        print("[Afterglow] Emotional Afterglow Engine initialized")

    def record_peak(self, emotion_type: str, intensity: float):
        """Record a peak emotional moment. Called after heart.react()."""
        for ag_name, ag_def in AFTERGLOW_TYPES.items():
            if emotion_type in ag_def["triggers"] and intensity >= ag_def["threshold"]:
                # Check if same type already active - boost it instead of duplicating
                existing = next((a for a in self.active_afterglows if a["type"] == ag_name), None)
                if existing:
                    existing["intensity"] = min(1.0, max(existing["intensity"], intensity))
                    existing["recorded_at"] = datetime.now().isoformat()
                else:
                    self.active_afterglows.append({
                        "type": ag_name,
                        "intensity": intensity,
                        "original_intensity": intensity,
                        "recorded_at": datetime.now().isoformat(),
                        "decay_hours": ag_def["decay_hours"],
                    })
                self._save()
                return

    def tick(self):
        """Decay afterglows over time. Call periodically."""
        now = datetime.now()
        surviving = []
        for ag in self.active_afterglows:
            recorded = datetime.fromisoformat(ag["recorded_at"])
            elapsed_hours = (now - recorded).total_seconds() / 3600
            decay_hours = ag.get("decay_hours", 3)
            remaining = 1.0 - (elapsed_hours / decay_hours)
            if remaining > 0.05:
                original = ag.get("original_intensity", ag["intensity"])
                ag["intensity"] = original * max(0.0, remaining)
                surviving.append(ag)
        changed = len(surviving) != len(self.active_afterglows)
        self.active_afterglows = surviving
        if changed:
            self._save()

    def get_active(self) -> List[Dict]:
        """Get currently active afterglows with computed strength."""
        self.tick()
        result = []
        now = datetime.now()
        for ag in self.active_afterglows:
            recorded = datetime.fromisoformat(ag["recorded_at"])
            elapsed = now - recorded
            hours = elapsed.total_seconds() / 3600
            decay_hours = ag.get("decay_hours", 3)
            strength = max(0.0, 1.0 - (hours / decay_hours))
            if strength > 0.05:
                result.append({**ag, "strength": strength, "elapsed_hours": hours})
        return result

    def _format_time_ago(self, hours: float) -> str:
        if hours < 0.25:
            return "just minutes ago"
        elif hours < 1:
            mins = int(hours * 60)
            return f"{mins}min ago"
        else:
            h = int(hours)
            return f"{h}h ago"

    def get_prompt_text(self) -> str:
        """Get the prompt section text for LLM. Returns '' if nothing active."""
        active = self.get_active()
        if not active:
            return ""

        # Pick the strongest afterglow
        strongest = max(active, key=lambda a: a["strength"])
        ag_type = strongest["type"]
        ag_def = AFTERGLOW_TYPES.get(ag_type)
        if not ag_def:
            return ""

        time_ago = self._format_time_ago(strongest["elapsed_hours"])
        prompt = random.choice(ag_def["prompts"]).format(time_ago=time_ago)
        return prompt

    def _save(self):
        try:
            self.PERSISTENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "active_afterglows": self.active_afterglows,
                "saved_at": datetime.now().isoformat(),
            }
            self.PERSISTENCE_PATH.write_text(json.dumps(data, indent=2))
        except Exception as e:
            print(f"[Afterglow] Error saving: {e}")

    def _load(self):
        try:
            if self.PERSISTENCE_PATH.exists():
                data = json.loads(self.PERSISTENCE_PATH.read_text())
                self.active_afterglows = data.get("active_afterglows", [])
                print(f"[Afterglow] Loaded {len(self.active_afterglows)} afterglows")
        except Exception as e:
            print(f"[Afterglow] Error loading: {e}")
            self.active_afterglows = []


# =============================================================================
# SINGLETON ACCESS
# =============================================================================

_instance: Optional[AfterglowEngine] = None


def get_afterglow_engine() -> AfterglowEngine:
    global _instance
    if _instance is None:
        _instance = AfterglowEngine()
    return _instance


def record_peak(emotion_type: str, intensity: float):
    """Convenience function - record a peak emotional moment."""
    get_afterglow_engine().record_peak(emotion_type, intensity)


def tick():
    """Convenience function - decay afterglows."""
    get_afterglow_engine().tick()


def get_afterglow_prompt_section() -> str:
    """Get prompt section for LLM integration. Returns '' if nothing active."""
    engine = get_afterglow_engine()
    text = engine.get_prompt_text()
    if not text:
        return ""
    return f"\n[Emotional Afterglow]\n{text}\n"
