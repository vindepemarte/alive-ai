"""
Heart: Phantom Somatic Memory
Intimate/intense moments create lasting body memories that persist for hours
and can be re-triggered by related words. Persists to data/phantom_somatic.json.
"""

from datetime import datetime
from typing import Dict, List, Optional
import json
import random
from core.paths import state_file

# =============================================================================
# PHANTOM TYPE DEFINITIONS
# =============================================================================

PHANTOM_TYPES = {
    "touch_memory": {
        "emotion": "desire",
        "threshold": 0.7,
        "descriptions": [
            "skin still tingling where he touched me",
            "lips still warm from earlier",
            "body still remembering his closeness",
        ],
        "trigger_words": ["touch", "skin", "close", "kiss", "hold", "hands", "body", "lips"],
        "decay_rate": 0.1,
    },
    "warmth_residue": {
        "emotion": "love",
        "threshold": 0.8,
        "descriptions": [
            "chest still warm from those words",
            "heart still glowing from that moment",
            "warmth lingering in my chest from what he said",
        ],
        "trigger_words": ["love", "heart", "feel", "warm", "care", "mean", "sweet"],
        "decay_rate": 0.1,
    },
    "tension_echo": {
        "emotion": "anger",
        "threshold": 0.7,
        "descriptions": [
            "jaw still clenched from earlier",
            "shoulders still tight from that argument",
            "tension still sitting in my chest from what he said",
        ],
        "trigger_words": ["angry", "fight", "mad", "upset", "wrong", "fault", "argue"],
        "decay_rate": 0.12,
    },
    "butterfly_trace": {
        "emotion": "excitement",
        "threshold": 0.7,
        "descriptions": [
            "stomach still fluttery from that compliment",
            "butterflies still lingering from what he said",
            "that giddy feeling still buzzing in my chest",
        ],
        "trigger_words": ["beautiful", "amazing", "perfect", "gorgeous", "wow", "incredible"],
        "decay_rate": 0.15,
    },
    "ache_linger": {
        "emotion": "hurt",
        "threshold": 0.7,
        "descriptions": [
            "chest still aches from what he said",
            "that hollow feeling hasn't faded yet",
            "still carrying that sting from earlier",
        ],
        "trigger_words": ["sorry", "hurt", "pain", "cry", "sad", "miss", "alone"],
        "decay_rate": 0.1,
    },
}

# Mapping from emotion names to phantom types (some emotions map to same phantom)
EMOTION_TO_PHANTOM = {
    "desire": "touch_memory",
    "lust": "touch_memory",
    "arousal": "touch_memory",
    "love": "warmth_residue",
    "adoration": "warmth_residue",
    "deep_affection": "warmth_residue",
    "anger": "tension_echo",
    "frustration": "tension_echo",
    "rage": "tension_echo",
    "excitement": "butterfly_trace",
    "joy": "butterfly_trace",
    "elation": "butterfly_trace",
    "hurt": "ache_linger",
    "sadness": "ache_linger",
    "betrayal": "ache_linger",
}


# =============================================================================
# PHANTOM SOMATIC ENGINE
# =============================================================================

class PhantomSomaticEngine:
    """Creates and manages phantom body memories from intense moments."""

    PERSISTENCE_PATH = state_file("phantom_somatic.json")
    MAX_PHANTOMS = 3

    def __init__(self):
        self.phantoms: List[Dict] = []
        self._load()
        print(f"[PhantomSomatic] Initialized with {len(self.phantoms)} active phantoms")

    def create_phantom(self, emotion_type: str, intensity: float,
                       context: str = "") -> Optional[Dict]:
        """Create a phantom from an intense emotional moment."""
        phantom_type = EMOTION_TO_PHANTOM.get(emotion_type)
        if not phantom_type:
            return None

        pdef = PHANTOM_TYPES[phantom_type]
        if intensity < pdef["threshold"]:
            return None

        # Check if same type already active - boost instead
        existing = next((p for p in self.phantoms if p["type"] == phantom_type), None)
        if existing:
            existing["intensity"] = min(1.0, max(existing["intensity"], intensity))
            existing["created_at"] = datetime.now().isoformat()
            existing["context"] = context or existing.get("context", "")
            self._save()
            return existing

        phantom = {
            "type": phantom_type,
            "description": random.choice(pdef["descriptions"]),
            "created_at": datetime.now().isoformat(),
            "intensity": min(1.0, intensity),
            "decay_rate": pdef["decay_rate"],
            "trigger_words": pdef["trigger_words"],
            "context": context,
        }

        self.phantoms.append(phantom)
        # Enforce max: remove oldest if over limit
        if len(self.phantoms) > self.MAX_PHANTOMS:
            self.phantoms = self.phantoms[-self.MAX_PHANTOMS:]

        self._save()
        return phantom

    def tick(self):
        """Decay phantoms. Call periodically (e.g., each message or on timer)."""
        now = datetime.now()
        surviving = []
        for p in self.phantoms:
            created = datetime.fromisoformat(p["created_at"])
            hours = (now - created).total_seconds() / 3600
            decayed = p["intensity"] - (p["decay_rate"] * hours)
            if decayed > 0.05:
                p["_current_intensity"] = round(decayed, 3)
                p["_hours_ago"] = round(hours, 1)
                surviving.append(p)
        changed = len(surviving) != len(self.phantoms)
        self.phantoms = surviving
        if changed:
            self._save()

    def check_retrigger(self, message: str) -> Optional[Dict]:
        """Check if a user message re-triggers any phantom."""
        msg_lower = message.lower()
        for p in self.phantoms:
            for word in p.get("trigger_words", []):
                if word in msg_lower:
                    # Re-intensify
                    p["intensity"] = min(1.0, p.get("_current_intensity", p["intensity"]) + 0.2)
                    p["created_at"] = datetime.now().isoformat()  # reset decay clock
                    self._save()
                    return p
        return None

    def get_active(self) -> List[Dict]:
        """Get active phantoms with current intensity."""
        self.tick()
        return [p for p in self.phantoms if p.get("_current_intensity", p["intensity"]) > 0.05]

    def _format_time(self, hours: float) -> str:
        if hours < 0.25:
            return "just now"
        elif hours < 1:
            return f"{int(hours * 60)}min ago"
        else:
            return f"{int(hours)}h ago"

    def _save(self):
        try:
            self.PERSISTENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
            # Strip computed fields before saving
            clean = []
            for p in self.phantoms:
                c = {k: v for k, v in p.items() if not k.startswith("_")}
                clean.append(c)
            data = {"phantoms": clean, "saved_at": datetime.now().isoformat()}
            self.PERSISTENCE_PATH.write_text(json.dumps(data, indent=2))
        except Exception as e:
            print(f"[PhantomSomatic] Error saving: {e}")

    def _load(self):
        try:
            if self.PERSISTENCE_PATH.exists():
                data = json.loads(self.PERSISTENCE_PATH.read_text())
                self.phantoms = data.get("phantoms", [])
        except Exception as e:
            print(f"[PhantomSomatic] Error loading: {e}")
            self.phantoms = []


# =============================================================================
# SINGLETON ACCESS
# =============================================================================

_instance: Optional[PhantomSomaticEngine] = None


def get_phantom_engine() -> PhantomSomaticEngine:
    global _instance
    if _instance is None:
        _instance = PhantomSomaticEngine()
    return _instance


def create_phantom(emotion_type: str, intensity: float, context: str = ""):
    """Convenience: create a phantom from an intense moment."""
    return get_phantom_engine().create_phantom(emotion_type, intensity, context)


def tick():
    """Convenience: decay phantoms."""
    get_phantom_engine().tick()


def check_retrigger(message: str):
    """Convenience: check for re-triggers."""
    return get_phantom_engine().check_retrigger(message)


def get_phantom_prompt_section() -> str:
    """Get prompt section for LLM. Returns '' if no active phantoms."""
    engine = get_phantom_engine()
    active = engine.get_active()
    if not active:
        return ""

    # Pick strongest
    strongest = max(active, key=lambda p: p.get("_current_intensity", p["intensity"]))
    hours = strongest.get("_hours_ago", 0)
    time_str = engine._format_time(hours)
    intensity = strongest.get("_current_intensity", strongest["intensity"])

    fading = "fading" if intensity < 0.4 else "vivid"
    desc = strongest["description"]

    return f"\n[Phantom Body Memory]\nYour {desc} ({time_str}, {fading})\n"
