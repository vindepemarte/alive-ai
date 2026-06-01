"""
Brain: Relationship Narrative System
Tracks the story arc of Alive-AI's relationship with each user,
enabling natural references to shared history and phase awareness.
"""

from datetime import datetime
from typing import Dict, List, Optional
import json
import random
from core.paths import data_dir

# =============================================================================
# RELATIONSHIP PHASES
# =============================================================================

PHASES = [
    {"id": "first_meeting",    "name": "First Meeting",     "min_messages": 0,   "min_intimacy": 0.0, "min_love": 0.0},
    {"id": "getting_to_know",  "name": "Getting to Know",   "min_messages": 5,   "min_intimacy": 0.1, "min_love": 0.05},
    {"id": "opening_up",       "name": "Opening Up",        "min_messages": 20,  "min_intimacy": 0.2, "min_love": 0.15},
    {"id": "deepening",        "name": "Deepening",         "min_messages": 50,  "min_intimacy": 0.35, "min_love": 0.3},
    {"id": "intimate",         "name": "Intimate",          "min_messages": 100, "min_intimacy": 0.5, "min_love": 0.45},
    {"id": "established",      "name": "Established",       "min_messages": 200, "min_intimacy": 0.6, "min_love": 0.55},
]

# Key moment types that can be recorded
MOMENT_TYPES = [
    "first_meeting", "first_laugh", "first_vulnerability", "first_fight",
    "first_makeup", "first_i_love_you", "first_intimate_moment",
    "big_revelation", "milestone", "inside_joke_born", "deep_conversation",
]

# Narrative callbacks - occasional references to the past
CALLBACKS_BY_PHASE = {
    "getting_to_know": [
        "We're still figuring each other out... I like it.",
    ],
    "opening_up": [
        "I feel like I can tell you things I don't tell most people.",
        "Remember when we were still so polite with each other? Look at us now.",
    ],
    "deepening": [
        "Remember when you were so shy at first? Look at us now.",
        "We've come a long way since those first awkward messages.",
        "I feel like you actually know me... the real me.",
    ],
    "intimate": [
        "Sometimes I think about how we started and smile... we've built something real.",
        "You know me better than almost anyone.",
    ],
    "established": [
        "We have our own little world now, don't we?",
        "I can't imagine not having you to talk to.",
        "Look how far we've come together.",
    ],
}


# =============================================================================
# NARRATIVE ENGINE
# =============================================================================

class NarrativeEngine:
    """Tracks the relationship story arc per user."""

    DATA_DIR = data_dir()

    def __init__(self):
        self._cache: Dict[str, Dict] = {}  # user_id -> narrative data
        print("[Narrative] Relationship Narrative Engine initialized")

    def _path_for(self, user_id: str) -> Path:
        # Save in user's directory for consistency
        user_dir = self.DATA_DIR / "users" / str(user_id)  # Ensure string conversion
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir / "narrative.json"

    def _get_data(self, user_id: str) -> Dict:
        if user_id in self._cache:
            return self._cache[user_id]
        data = self._load(user_id)
        self._cache[user_id] = data
        return data

    def _default_data(self) -> Dict:
        return {
            "phase": "first_meeting",
            "message_count": 0,
            "first_interaction": datetime.now().isoformat(),
            "key_moments": [],
            "phase_history": [{"phase": "first_meeting", "entered_at": datetime.now().isoformat()}],
            "last_callback": None,
            "callbacks_given": 0,
        }

    def update_phase(self, user_id: str, message_count: int = None,
                     intimacy: float = 0.0, love: float = 0.0):
        """Check and update relationship phase based on metrics."""
        data = self._get_data(user_id)
        if message_count is not None:
            data["message_count"] = message_count

        current_phase = data["phase"]
        new_phase = current_phase

        # Find highest qualifying phase
        for phase_def in PHASES:
            if (data["message_count"] >= phase_def["min_messages"]
                    and intimacy >= phase_def["min_intimacy"]
                    and love >= phase_def["min_love"]):
                new_phase = phase_def["id"]

        if new_phase != current_phase:
            data["phase"] = new_phase
            data["phase_history"].append({
                "phase": new_phase,
                "entered_at": datetime.now().isoformat(),
            })
            print(f"[Narrative] User {user_id} entered phase: {new_phase}")

        self._save(user_id, data)

    def record_narrative_moment(self, user_id: str, moment_type: str, description: str):
        """Record a key narrative moment."""
        data = self._get_data(user_id)
        # Avoid duplicate moment types (only one "first_*" each)
        if moment_type.startswith("first_"):
            if any(m["type"] == moment_type for m in data["key_moments"]):
                return  # already recorded

        data["key_moments"].append({
            "type": moment_type,
            "description": description,
            "timestamp": datetime.now().isoformat(),
        })
        # Keep last 50 moments
        if len(data["key_moments"]) > 50:
            data["key_moments"] = data["key_moments"][-50:]
        self._save(user_id, data)

    def get_current_phase(self, user_id: str) -> Dict:
        """Get info about current relationship phase."""
        data = self._get_data(user_id)
        phase_id = data["phase"]
        phase_def = next((p for p in PHASES if p["id"] == phase_id), PHASES[0])

        first = data.get("first_interaction", datetime.now().isoformat())
        try:
            days = (datetime.now() - datetime.fromisoformat(first)).days
        except Exception:
            days = 0

        return {
            "phase": phase_id,
            "phase_name": phase_def["name"],
            "message_count": data["message_count"],
            "days_together": days,
            "key_moments_count": len(data["key_moments"]),
        }

    def get_narrative_callback(self, user_id: str) -> Optional[str]:
        """Get an occasional narrative callback (10% chance). Returns None if skipped."""
        if random.random() > 0.10:
            return None

        data = self._get_data(user_id)
        phase = data["phase"]
        callbacks = CALLBACKS_BY_PHASE.get(phase, [])
        if not callbacks:
            return None

        # Also include moment-based callbacks
        moments = data.get("key_moments", [])
        moment_callbacks = []
        for m in moments[-5:]:
            if m["type"] == "inside_joke_born":
                moment_callbacks.append(f'Haha... "{m["description"]}" - that\'s our thing now.')
            elif m["type"] == "first_fight":
                moment_callbacks.append("I'm glad we got through that rough patch.")

        all_options = callbacks + moment_callbacks
        choice = random.choice(all_options)

        data["last_callback"] = datetime.now().isoformat()
        data["callbacks_given"] = data.get("callbacks_given", 0) + 1
        self._save(user_id, data)
        return choice

    def increment_messages(self, user_id: str):
        """Increment message count for a user."""
        data = self._get_data(user_id)
        data["message_count"] = data.get("message_count", 0) + 1
        self._save(user_id, data)

    def detect_and_record_moment(self, user_id: str, text: str, emotion: Dict) -> List[str]:
        """Detect key moments from message content and emotions. Returns list of detected moments."""
        detected = []
        text_lower = text.lower()
        data = self._get_data(user_id)
        existing_types = [m["type"] for m in data.get("key_moments", [])]

        # Detection patterns for key moments
        moment_patterns = {
            "first_i_love_you": {
                "patterns": ["i love you", "love you so much", "i'm in love", "falling for you"],
                "emotion_check": lambda e: e.get("love", 0) > 0.7,
            },
            "first_vulnerability": {
                "patterns": ["i've never told anyone", "this is hard for me to say", "i'm scared to tell you",
                            "feeling vulnerable", "trust you with this"],
                "emotion_check": lambda e: e.get("valence", 0.5) < 0.6,
            },
            "first_intimate_moment": {
                "patterns": ["make love", "want you", "need you now", "so turned on", "touch myself"],
                "emotion_check": lambda e: e.get("desire", 0) > 0.7,
            },
            "deep_conversation": {
                "patterns": ["meaning of", "what do you think about", "deep", "philosophical", "existential"],
                "emotion_check": lambda e: True,  # Always valid
            },
            "first_fight": {
                "patterns": ["hurt me", "you're being", "why would you", "angry at you", "pissed off"],
                "emotion_check": lambda e: e.get("anger", 0) > 0.5,
            },
            "first_makeup": {
                "patterns": ["forgive you", "make it up", "sorry i overreacted", "let's move past"],
                "emotion_check": lambda e: e.get("love", 0) > 0.5,
            },
            "inside_joke_born": {
                "patterns": ["haha that's our", "remember when you said", "our little", "inside joke"],
                "emotion_check": lambda e: e.get("joy", 0) > 0.5,
            },
            "big_revelation": {
                "patterns": ["confession", "honestly i", "truth is", "secret i've been keeping"],
                "emotion_check": lambda e: True,
            },
        }

        for moment_type, config in moment_patterns.items():
            if moment_type in existing_types:
                continue  # Already recorded this type

            # Check if any pattern matches
            if any(p in text_lower for p in config["patterns"]):
                if config["emotion_check"](emotion):
                    description = f"Detected: {text[:50]}..."
                    self.record_narrative_moment(user_id, moment_type, description)
                    detected.append(moment_type)
                    print(f"[Narrative] Recorded key moment: {moment_type}")

        return detected

    def _save(self, user_id: str, data: Dict):
        try:
            self.DATA_DIR.mkdir(parents=True, exist_ok=True)
            data["saved_at"] = datetime.now().isoformat()
            self._cache[user_id] = data
            self._path_for(user_id).write_text(json.dumps(data, indent=2))
        except Exception as e:
            print(f"[Narrative] Error saving for {user_id}: {e}")

    def _load(self, user_id: str) -> Dict:
        try:
            path = self._path_for(user_id)
            if path.exists():
                data = json.loads(path.read_text())
                # If message_count is 0, count from actual conversation files
                if data.get("message_count", 0) == 0:
                    actual_count = self._count_actual_messages(user_id)
                    if actual_count > 0:
                        data["message_count"] = actual_count
                        print(f"[Narrative] Migrated message count for {user_id}: {actual_count}")
                        self._save(user_id, data)
                print(f"[Narrative] Loaded narrative for {user_id} (phase={data.get('phase')}, msgs={data.get('message_count', 0)})")
                return data
        except Exception as e:
            print(f"[Narrative] Error loading for {user_id}: {e}")

        # No existing file - try to count actual messages
        data = self._default_data()
        actual_count = self._count_actual_messages(user_id)
        if actual_count > 0:
            data["message_count"] = actual_count
            print(f"[Narrative] Initialized narrative for {user_id} with {actual_count} messages from history")
            self._save(user_id, data)
        return data

    def _count_actual_messages(self, user_id: str) -> int:
        """Count actual messages from conversation files."""
        try:
            conv_dir = self.DATA_DIR / "users" / str(user_id) / "conversations"  # Ensure string conversion
            if not conv_dir.exists():
                return 0
            total = 0
            for f in conv_dir.glob("*.jsonl"):
                with open(f) as fh:
                    total += sum(1 for _ in fh)
            return total
        except Exception:
            return 0


# =============================================================================
# SINGLETON ACCESS
# =============================================================================

_instance: Optional[NarrativeEngine] = None


def get_narrative_engine() -> NarrativeEngine:
    global _instance
    if _instance is None:
        _instance = NarrativeEngine()
    return _instance


def record_narrative_moment(user_id: str, moment_type: str, description: str):
    get_narrative_engine().record_narrative_moment(user_id, moment_type, description)


def get_narrative_prompt_section(user_id: str) -> str:
    """Get prompt section for LLM integration."""
    engine = get_narrative_engine()
    info = engine.get_current_phase(user_id)

    phase_name = info["phase_name"]
    msgs = info["message_count"]
    days = info["days_together"]

    time_desc = f"{days} days" if days > 0 else "just started"
    parts = [f"You and him are in the '{phase_name}' phase - {msgs} messages over {time_desc}."]

    # Maybe add a callback
    callback = engine.get_narrative_callback(user_id)
    if callback:
        parts.append(f"A thought surfaces: \"{callback}\"")

    return f"\n[Relationship Narrative]\n" + " ".join(parts) + "\n"


def get_narrative_callbacks(user_id: str) -> Optional[str]:
    """Get a narrative callback if one triggers (10% chance)."""
    return get_narrative_engine().get_narrative_callback(user_id)
