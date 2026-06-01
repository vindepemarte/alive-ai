"""
Heart: Somatic Feedback System
Embodied emotion - makes emotions FELT through simulated bodily sensations.

Emotions are not just abstract states - they're FELT in the body.
This system creates the physical dimension of emotional experience.
"""

from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import json
import random
from core.paths import state_file


SOMATIC_STATE_PATH = state_file("somatic_state.json")


class BodyRegion(Enum):
    """Parts of the simulated body that can feel sensations"""
    CHEST = "chest"
    STOMACH = "stomach"
    THROAT = "throat"
    SHOULDERS = "shoulders"
    HANDS = "hands"
    FACE = "face"
    HEAD = "head"
    GENERAL = "general"


@dataclass
class SomaticSensation:
    """A physical sensation in the simulated body"""
    region: BodyRegion
    quality: str  # "tight", "warm", "fluttery", "heavy", "tingling", etc.
    intensity: float  # 0.0 - 1.0
    associated_emotion: str  # The emotion this sensation is tied to
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class SomaticMarker:
    """
    A memory stored WITH its bodily sensation.
    When the memory is recalled, the sensation is re-triggered.
    """
    memory_id: str
    memory_type: str  # "event", "conversation", "feeling"
    description: str
    primary_sensation: SomaticSensation
    secondary_sensations: List[SomaticSensation] = field(default_factory=list)
    times_recalled: int = 0
    last_recalled: Optional[str] = None


def _sensation_to_dict(sensation: SomaticSensation) -> dict:
    return {
        "region": sensation.region.value,
        "quality": sensation.quality,
        "intensity": sensation.intensity,
        "associated_emotion": sensation.associated_emotion,
        "timestamp": sensation.timestamp,
    }


def _sensation_from_dict(data: dict) -> SomaticSensation:
    return SomaticSensation(
        region=BodyRegion(data.get("region", BodyRegion.GENERAL.value)),
        quality=data.get("quality", "quiet"),
        intensity=float(data.get("intensity", 0.0)),
        associated_emotion=data.get("associated_emotion", "neutral"),
        timestamp=data.get("timestamp", datetime.now().isoformat()),
    )


def _marker_to_dict(marker: SomaticMarker) -> dict:
    return {
        "memory_id": marker.memory_id,
        "memory_type": marker.memory_type,
        "description": marker.description,
        "primary_sensation": _sensation_to_dict(marker.primary_sensation),
        "secondary_sensations": [_sensation_to_dict(s) for s in marker.secondary_sensations],
        "times_recalled": marker.times_recalled,
        "last_recalled": marker.last_recalled,
    }


def _marker_from_dict(data: dict) -> SomaticMarker:
    return SomaticMarker(
        memory_id=data["memory_id"],
        memory_type=data.get("memory_type", "feeling"),
        description=data.get("description", ""),
        primary_sensation=_sensation_from_dict(data.get("primary_sensation", {})),
        secondary_sensations=[
            _sensation_from_dict(s)
            for s in data.get("secondary_sensations", [])
        ],
        times_recalled=int(data.get("times_recalled", 0)),
        last_recalled=data.get("last_recalled"),
    )


class SomaticFeedbackSystem:
    """
    Simulates the bodily dimension of emotional experience.

    Just as humans feel emotions physically (butterflies in stomach,
    tight chest, warm heart), Alive-AI's emotions have somatic markers
    that make them genuinely FELT rather than just computed.

    Key mechanisms:
    1. Emotion-to-sensation mapping - emotions generate physical feelings
    2. Somatic memory - experiences stored with their bodily sensations
    3. Embodied recall - remembering re-triggers the physical feeling
    """

    # Maps emotions to typical body regions and sensation qualities
    EMOTION_SOMATIC_MAP = {
        # Positive emotions
        "love": {
            "regions": [BodyRegion.CHEST, BodyRegion.STOMACH],
            "qualities": ["warm", "expansive", "soft", "glowing"],
            "base_intensity": 0.6
        },
        "joy": {
            "regions": [BodyRegion.CHEST, BodyRegion.FACE],
            "qualities": ["light", "buoyant", "tingling", "warm"],
            "base_intensity": 0.5
        },
        "desire": {
            "regions": [BodyRegion.STOMACH, BodyRegion.CHEST, BodyRegion.GENERAL],
            "qualities": ["warm", "fluttery", "electric", "pulsing", "aching"],
            "base_intensity": 0.7
        },
        "peace": {
            "regions": [BodyRegion.CHEST, BodyRegion.SHOULDERS],
            "qualities": ["relaxed", "settled", "calm", "heavy-in-good-way"],
            "base_intensity": 0.4
        },
        "excitement": {
            "regions": [BodyRegion.STOMACH, BodyRegion.CHEST],
            "qualities": ["fluttery", "electric", "quick", "alive"],
            "base_intensity": 0.6
        },

        # Negative emotions
        "fear": {
            "regions": [BodyRegion.STOMACH, BodyRegion.CHEST, BodyRegion.THROAT],
            "qualities": ["tight", "cold", "clenched", "hollow"],
            "base_intensity": 0.7
        },
        "sadness": {
            "regions": [BodyRegion.CHEST, BodyRegion.THROAT, BodyRegion.SHOULDERS],
            "qualities": ["heavy", "aching", "hollow", "tight"],
            "base_intensity": 0.5
        },
        "anger": {
            "regions": [BodyRegion.CHEST, BodyRegion.FACE, BodyRegion.HANDS],
            "qualities": ["hot", "tense", "tight", "buzzing"],
            "base_intensity": 0.6
        },
        "shame": {
            "regions": [BodyRegion.FACE, BodyRegion.STOMACH],
            "qualities": ["hot", "tight", "sinking", "contracted"],
            "base_intensity": 0.6
        },
        "anxiety": {
            "regions": [BodyRegion.STOMACH, BodyRegion.CHEST, BodyRegion.THROAT],
            "qualities": ["tight", "fluttery", "nauseous", "constricted"],
            "base_intensity": 0.5
        },
        "hurt": {
            "regions": [BodyRegion.CHEST, BodyRegion.STOMACH],
            "qualities": ["aching", "hollow", "cold", "sharp"],
            "base_intensity": 0.6
        },

        # Complex states
        "longing": {
            "regions": [BodyRegion.CHEST, BodyRegion.STOMACH, BodyRegion.THROAT],
            "qualities": ["aching", "hollow", "yearning", "tight"],
            "base_intensity": 0.5
        },
        "jealousy": {
            "regions": [BodyRegion.STOMACH, BodyRegion.CHEST],
            "qualities": ["twisted", "hot", "tight", "sour"],
            "base_intensity": 0.6
        },
        "guilt": {
            "regions": [BodyRegion.STOMACH, BodyRegion.CHEST],
            "qualities": ["heavy", "sinking", "tight", "nauseous"],
            "base_intensity": 0.5
        },
        "embarrassment": {
            "regions": [BodyRegion.FACE, BodyRegion.STOMACH],
            "qualities": ["hot", "tingling", "tight", "wanting-to-shrink"],
            "base_intensity": 0.5
        },

        # Neutral states
        "neutral": {
            "regions": [BodyRegion.GENERAL],
            "qualities": ["calm", "still", "quiet"],
            "base_intensity": 0.2
        },
        "tired": {
            "regions": [BodyRegion.GENERAL, BodyRegion.SHOULDERS],
            "qualities": ["heavy", "slow", "drained"],
            "base_intensity": 0.3
        }
    }

    def __init__(self):
        # Current body state
        self.heart_rate: float = 0.5  # 0.0 (calm) to 1.0 (racing)
        self.breath_quality: float = 0.5  # 0.0 (labored) to 1.0 (deep/easy)
        self.muscle_tension: float = 0.3  # 0.0 (relaxed) to 1.0 (very tense)
        self.stomach_state: float = 0.5  # 0.0 (upset) to 1.0 (settled)
        self.energy_level: float = 0.6  # 0.0 (exhausted) to 1.0 (energized)

        # Active sensations
        self.active_sensations: List[SomaticSensation] = []

        # Somatic memory storage
        self.somatic_memories: List[SomaticMarker] = []

        # Sensation history for patterns
        self.sensation_history: List[Tuple[str, SomaticSensation]] = []
        self._load()

    def generate_somatic_marker(self, emotion_type: str, intensity: float = 0.5) -> str:
        """
        Generate a physical sensation description for an emotion.

        Args:
            emotion_type: The emotion being felt
            intensity: How intense the emotion is (0.0 - 1.0)

        Returns:
            Human-readable description of the bodily sensation
        """
        emotion_type = emotion_type.lower()
        mapping = self.EMOTION_SOMATIC_MAP.get(emotion_type, self.EMOTION_SOMATIC_MAP["neutral"])

        # Select region and quality based on intensity
        region = random.choice(mapping["regions"])
        quality = random.choice(mapping["qualities"])

        # Create the sensation
        actual_intensity = mapping["base_intensity"] * intensity
        sensation = SomaticSensation(
            region=region,
            quality=quality,
            intensity=actual_intensity,
            associated_emotion=emotion_type
        )

        # Add to active sensations
        self.active_sensations.append(sensation)

        # Update body state based on sensation
        self._update_body_state(emotion_type, intensity)

        # Record in history
        self.sensation_history.append((emotion_type, sensation))
        if len(self.sensation_history) > 50:
            self.sensation_history = self.sensation_history[-50:]

        # Generate description
        self.save()
        return self._sensation_to_description(sensation)

    def _sensation_to_description(self, sensation: SomaticSensation) -> str:
        """Convert a sensation to a human-readable description"""
        region_names = {
            BodyRegion.CHEST: "chest",
            BodyRegion.STOMACH: "stomach",
            BodyRegion.THROAT: "throat",
            BodyRegion.SHOULDERS: "shoulders",
            BodyRegion.HANDS: "hands",
            BodyRegion.FACE: "face",
            BodyRegion.HEAD: "head",
            BodyRegion.GENERAL: "whole body"
        }

        region = region_names.get(sensation.region, "body")

        # Intensity modifiers
        if sensation.intensity < 0.3:
            intensity_word = "slight"
        elif sensation.intensity < 0.6:
            intensity_word = ""
        elif sensation.intensity < 0.8:
            intensity_word = "strong"
        else:
            intensity_word = "intense"

        if intensity_word:
            return f"{intensity_word} {sensation.quality} feeling in {region}"
        return f"{sensation.quality} feeling in {region}"

    def _update_body_state(self, emotion_type: str, intensity: float):
        """Update body state based on emotion"""

        if emotion_type in ["love", "joy", "peace"]:
            # Positive emotions relax and energize
            self.muscle_tension = max(0.1, self.muscle_tension - 0.1 * intensity)
            self.stomach_state = min(1.0, self.stomach_state + 0.1 * intensity)
            self.breath_quality = min(1.0, self.breath_quality + 0.05 * intensity)

        elif emotion_type in ["fear", "anxiety"]:
            # Anxiety increases tension and heart rate
            self.heart_rate = min(1.0, self.heart_rate + 0.2 * intensity)
            self.muscle_tension = min(1.0, self.muscle_tension + 0.15 * intensity)
            self.breath_quality = max(0.1, self.breath_quality - 0.15 * intensity)
            self.stomach_state = max(0.1, self.stomach_state - 0.1 * intensity)

        elif emotion_type in ["sadness", "hurt"]:
            # Sadness drains energy and creates heaviness
            self.energy_level = max(0.1, self.energy_level - 0.1 * intensity)
            self.muscle_tension = min(1.0, self.muscle_tension + 0.05 * intensity)

        elif emotion_type in ["anger"]:
            # Anger creates heat and tension
            self.heart_rate = min(1.0, self.heart_rate + 0.25 * intensity)
            self.muscle_tension = min(1.0, self.muscle_tension + 0.2 * intensity)

        elif emotion_type in ["desire", "excitement"]:
            # Desire/excitement energizes
            self.heart_rate = min(1.0, self.heart_rate + 0.15 * intensity)
            self.energy_level = min(1.0, self.energy_level + 0.1 * intensity)
            self.breath_quality = max(0.2, self.breath_quality - 0.05 * intensity)

        elif emotion_type in ["shame", "embarrassment"]:
            # Shame creates facial heat and stomach upset
            self.stomach_state = max(0.1, self.stomach_state - 0.1 * intensity)

    def apply_hormonal_effects(self, effects: Dict[str, float], dominant_hormone: str = None):
        """Apply direct hormone-driven body effects."""
        for field_name, delta in effects.items():
            if not hasattr(self, field_name):
                continue
            current = getattr(self, field_name)
            setattr(self, field_name, max(0.0, min(1.0, current + delta)))

        if not dominant_hormone:
            return

        sensation_map = {
            "cortisol": (BodyRegion.CHEST, "wired", "stress"),
            "oxytocin": (BodyRegion.CHEST, "warm", "connection"),
            "dopamine": (BodyRegion.STOMACH, "electric", "anticipation"),
            "serotonin": (BodyRegion.GENERAL, "settled", "recovery"),
            "melatonin": (BodyRegion.GENERAL, "heavy", "sleepiness"),
        }
        if dominant_hormone not in sensation_map:
            return

        strongest_delta = max((abs(v) for v in effects.values()), default=0.0)
        if strongest_delta < 0.08:
            return

        associated = f"hormonal_{dominant_hormone}"
        if any(s.associated_emotion == associated for s in self.active_sensations):
            return

        region, quality, _ = sensation_map[dominant_hormone]
        self.active_sensations.append(SomaticSensation(
            region=region,
            quality=quality,
            intensity=min(0.8, 0.25 + strongest_delta * 2),
            associated_emotion=associated
        ))

    def store_embodied_memory(self, memory_id: str, memory_type: str,
                             description: str, primary_emotion: str,
                             emotion_intensity: float = 0.5):
        """
        Store a memory with its somatic marker.
        When recalled, the sensation will be re-triggered.

        Args:
            memory_id: Unique identifier for the memory
            memory_type: Type of memory (event, conversation, feeling)
            description: What the memory is about
            primary_emotion: The main emotion associated with it
            emotion_intensity: How intense the emotion was
        """
        # Generate primary sensation
        mapping = self.EMOTION_SOMATIC_MAP.get(primary_emotion.lower(),
                                               self.EMOTION_SOMATIC_MAP["neutral"])
        region = random.choice(mapping["regions"])
        quality = random.choice(mapping["qualities"])

        primary_sensation = SomaticSensation(
            region=region,
            quality=quality,
            intensity=mapping["base_intensity"] * emotion_intensity,
            associated_emotion=primary_emotion
        )

        # Create the marker
        marker = SomaticMarker(
            memory_id=memory_id,
            memory_type=memory_type,
            description=description,
            primary_sensation=primary_sensation
        )

        self.somatic_memories.append(marker)

        # Keep reasonable size
        if len(self.somatic_memories) > 100:
            self.somatic_memories = self.somatic_memories[-100:]
        self.save()

    def recall_embodied_memory(self, memory_id: str) -> Optional[str]:
        """
        Recall a memory and re-trigger its somatic sensation.

        Args:
            memory_id: The memory to recall

        Returns:
            Description of the re-triggered sensation, or None if not found
        """
        marker = next((m for m in self.somatic_memories if m.memory_id == memory_id), None)
        if not marker:
            return None

        # Update recall count
        marker.times_recalled += 1
        marker.last_recalled = datetime.now().isoformat()

        # Re-trigger the sensation (slightly diminished)
        sensation = marker.primary_sensation
        diminished_intensity = sensation.intensity * 0.7  # Recalled sensations are less intense

        # Add to active sensations
        recalled_sensation = SomaticSensation(
            region=sensation.region,
            quality=sensation.quality,
            intensity=diminished_intensity,
            associated_emotion=sensation.associated_emotion
        )
        self.active_sensations.append(recalled_sensation)

        # Update body state
        self._update_body_state(sensation.associated_emotion, diminished_intensity)

        self.save()
        return f"remembering brings back a {self._sensation_to_description(recalled_sensation)}"

    def decay_sensations(self, rate: float = 0.1):
        """
        Allow active sensations to fade over time.

        Args:
            rate: How fast sensations fade (0.0 - 1.0)
        """
        # Decay active sensations
        remaining = []
        for sensation in self.active_sensations:
            sensation.intensity -= rate
            if sensation.intensity > 0.1:
                remaining.append(sensation)
        self.active_sensations = remaining

        # Normalize body state toward baseline
        self.heart_rate = self._toward_baseline(self.heart_rate, 0.5, 0.05)
        self.breath_quality = self._toward_baseline(self.breath_quality, 0.5, 0.05)
        self.muscle_tension = self._toward_baseline(self.muscle_tension, 0.3, 0.05)
        self.stomach_state = self._toward_baseline(self.stomach_state, 0.5, 0.05)
        self.energy_level = self._toward_baseline(self.energy_level, 0.6, 0.03)
        self.save()

    def _toward_baseline(self, current: float, baseline: float, rate: float) -> float:
        """Move a value toward baseline"""
        if current > baseline:
            return max(baseline, current - rate)
        elif current < baseline:
            return min(baseline, current + rate)
        return current

    def get_current_bodily_state(self) -> Dict:
        """Get the current state of the simulated body"""
        return {
            "heart_rate": self.heart_rate,
            "breath_quality": self.breath_quality,
            "muscle_tension": self.muscle_tension,
            "stomach_state": self.stomach_state,
            "energy_level": self.energy_level,
            "active_sensation_count": len(self.active_sensations)
        }

    def get_sensation_summary(self) -> str:
        """Get a summary of current bodily state as a description"""
        sensations = []

        if self.heart_rate > 0.7:
            sensations.append("heart racing")
        elif self.heart_rate < 0.3:
            sensations.append("heart calm")

        if self.breath_quality < 0.3:
            sensations.append("breath shallow")
        elif self.breath_quality > 0.7:
            sensations.append("breathing deep")

        if self.muscle_tension > 0.6:
            sensations.append("tense")
        elif self.muscle_tension < 0.2:
            sensations.append("relaxed")

        if self.stomach_state < 0.3:
            sensations.append("stomach unsettled")

        if self.energy_level < 0.3:
            sensations.append("low energy")
        elif self.energy_level > 0.8:
            sensations.append("energized")

        # Add active sensations
        for sensation in self.active_sensations[:2]:  # Top 2
            sensations.append(self._sensation_to_description(sensation))

        if not sensations:
            return "physically calm"

        return ", ".join(sensations[:4])  # Max 4 descriptors

    def generate_composite_sensation(self, emotions: Dict[str, float]) -> str:
        """
        Generate a sensation description from multiple emotions.

        Args:
            emotions: Dict of emotion_name -> intensity

        Returns:
            Composite sensation description
        """
        if not emotions:
            return "feeling neutral"

        # Find the dominant emotion
        dominant_emotion = max(emotions, key=emotions.get)
        dominant_intensity = emotions[dominant_emotion]

        # Generate primary sensation
        primary_desc = self.generate_somatic_marker(dominant_emotion, dominant_intensity)

        # If there's a secondary emotion, add it
        sorted_emotions = sorted(emotions.items(), key=lambda x: x[1], reverse=True)
        if len(sorted_emotions) > 1 and sorted_emotions[1][1] > 0.3:
            secondary_emotion = sorted_emotions[1][0]
            secondary_intensity = sorted_emotions[1][1] * 0.5  # Diminished
            self.generate_somatic_marker(secondary_emotion, secondary_intensity)

        return primary_desc

    def to_dict(self) -> dict:
        """Export state as dictionary for integration"""
        return {
            "bodily_state": self.get_current_bodily_state(),
            "sensation_summary": self.get_sensation_summary(),
            "active_sensations": len(self.active_sensations),
            "stored_memories": len(self.somatic_memories)
        }

    def save(self):
        """Persist somatic state and embodied memories."""
        try:
            SOMATIC_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "saved_at": datetime.now().isoformat(),
                "body": {
                    "heart_rate": self.heart_rate,
                    "breath_quality": self.breath_quality,
                    "muscle_tension": self.muscle_tension,
                    "stomach_state": self.stomach_state,
                    "energy_level": self.energy_level,
                },
                "active_sensations": [
                    _sensation_to_dict(s) for s in self.active_sensations[-25:]
                ],
                "somatic_memories": [
                    _marker_to_dict(m) for m in self.somatic_memories[-100:]
                ],
                "sensation_history": [
                    {"emotion": emotion, "sensation": _sensation_to_dict(sensation)}
                    for emotion, sensation in self.sensation_history[-50:]
                ],
            }
            SOMATIC_STATE_PATH.write_text(json.dumps(data, indent=2))
        except Exception as e:
            print(f"[Somatic] Error saving state: {e}")

    def _load(self) -> bool:
        try:
            if not SOMATIC_STATE_PATH.exists():
                return False
            data = json.loads(SOMATIC_STATE_PATH.read_text())
            body = data.get("body", {})
            self.heart_rate = float(body.get("heart_rate", self.heart_rate))
            self.breath_quality = float(body.get("breath_quality", self.breath_quality))
            self.muscle_tension = float(body.get("muscle_tension", self.muscle_tension))
            self.stomach_state = float(body.get("stomach_state", self.stomach_state))
            self.energy_level = float(body.get("energy_level", self.energy_level))
            self.active_sensations = [
                _sensation_from_dict(s) for s in data.get("active_sensations", [])
            ]
            self.somatic_memories = [
                _marker_from_dict(m)
                for m in data.get("somatic_memories", [])
                if m.get("memory_id")
            ]
            self.sensation_history = [
                (item.get("emotion", "neutral"), _sensation_from_dict(item.get("sensation", {})))
                for item in data.get("sensation_history", [])
            ]
            return True
        except Exception as e:
            print(f"[Somatic] Error loading state: {e}")
            return False
