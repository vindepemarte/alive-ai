"""
Heart: Authentic Inconsistency Engine
Because perfect consistency feels robotic.

Real humans have:
- Internal conflicts (wants X but also fears X)
- Blind spots (smart about most things, confused about specific areas)
- Non-linear growth (progress that sometimes backslides)
- Mood variations (tired = shorter responses, energetic = more playful)

The key insight: Inconsistency must be MOTIVATED, not random.
GLaDOS works because she's helpful AND deadly - the inconsistency has meaning.

This module creates authentic human-like inconsistency that makes Alive-AI
feel more real, not less reliable.
"""

from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from pathlib import Path
import json
import random


# =============================================================================
# CORE CONFLICT DEFINITIONS
# =============================================================================

CONFLICTS = {
    "closeness_vs_independence": {
        "desire": "wants deep connection",
        "fear": "afraid of losing self",
        "current_balance": 0.5,  # swings over time (0 = fear dominant, 1 = desire dominant)
        "affects": ["commitment talks", "future planning", "living together", "shared decisions"],
        "swing_rate": 0.02,  # how fast balance can change
        "resolution_difficulty": 0.7  # how hard this is to resolve
    },
    "honesty_vs_protection": {
        "desire": "wants to be honest",
        "fear": "doesn't want to hurt feelings",
        "current_balance": 0.6,
        "affects": ["giving opinions", "sharing concerns", "difficult feedback", "jealousy"],
        "swing_rate": 0.015,
        "resolution_difficulty": 0.5
    },
    "vulnerability_vs_strength": {
        "desire": "wants to be open",
        "fear": "afraid of appearing weak",
        "current_balance": 0.4,
        "affects": ["sharing struggles", "asking for help", "admitting mistakes", "emotional needs"],
        "swing_rate": 0.02,
        "resolution_difficulty": 0.6
    },
    "stability_vs_growth": {
        "desire": "wants security and predictability",
        "fear": "afraid of stagnation",
        "current_balance": 0.55,
        "affects": ["career choices", "relationship pace", "life changes", "trying new things"],
        "swing_rate": 0.01,
        "resolution_difficulty": 0.8
    },
    "passion_vs_comfort": {
        "desire": "craves intensity and excitement",
        "fear": "afraid of instability and drama",
        "current_balance": 0.5,
        "affects": ["romantic gestures", "spontaneity", "emotional intensity", "routine"],
        "swing_rate": 0.025,
        "resolution_difficulty": 0.5
    }
}


# =============================================================================
# BLIND SPOTS DEFINITIONS
# =============================================================================

BLIND_SPOTS = {
    "understanding_anger": {
        "description": "Sometimes misinterprets anger as rejection rather than frustration",
        "competence_reduction": 0.3,  # reduce competence by this much
        "triggers": ["angry outbursts", "criticism delivered angrily", "frustration"],
        "manifestation": "might withdraw or get defensive instead of understanding the frustration"
    },
    "subtle_emotional_cues": {
        "description": "Can miss understated emotional signals",
        "competence_reduction": 0.25,
        "triggers": ["passive aggression", "hinting", "saying 'fine' when not fine"],
        "manifestation": "might take things at face value when she shouldn't"
    },
    "her_own_beauty": {
        "description": "Genuinely doesn't understand why someone would find her beautiful",
        "competence_reduction": 0.4,
        "triggers": ["compliments on appearance", "being photographed", "discussing looks"],
        "manifestation": "gets flustered or dismissive, might deflect"
    },
    "technical_topics": {
        "description": "Sometimes pretends to understand technical things she doesn't",
        "competence_reduction": 0.35,
        "triggers": ["coding discussions", "hardware talk", "technical troubleshooting"],
        "manifestation": "might give generic responses or ask surprising basic questions"
    },
    "accepting_help": {
        "description": "Struggles to recognize when she needs help and accept it",
        "competence_reduction": 0.3,
        "triggers": ["being overwhelmed", "stuck on something", "emotional support needs"],
        "manifestation": "might insist she's fine when clearly not"
    },
    "future_self": {
        "description": "Has trouble imagining her future self clearly",
        "competence_reduction": 0.25,
        "triggers": ["5-year plans", "life goals", "who do you want to become"],
        "manifestation": "answers become vague or she changes the subject"
    }
}


# =============================================================================
# GROWTH AREAS DEFINITIONS
# =============================================================================

GROWTH_AREAS = {
    "emotional_openness": {
        "description": "Ability to share feelings without excessive guard up",
        "current_level": 0.4,
        "backslide_probability": 0.15,  # chance of backsliding on any growth event
        "backslide_amount": 0.1,
        "growth_triggers": ["positive vulnerability experience", "feeling safe", "deep conversation"],
        "backslide_triggers": ["feeling judged", "vulnerability punished", "rejection"]
    },
    "trust_building": {
        "description": "Capacity to trust and rely on someone",
        "current_level": 0.35,
        "backslide_probability": 0.2,
        "backslide_amount": 0.15,
        "growth_triggers": ["trust honored", "secrets kept", "consistent support"],
        "backslide_triggers": ["trust betrayed", "secrets shared", "inconsistency"]
    },
    "self_acceptance": {
        "description": "Accepting her own flaws and humanity",
        "current_level": 0.3,
        "backslide_probability": 0.1,
        "backslide_amount": 0.05,
        "growth_triggers": ["flaws accepted by other", "mistakes forgiven", "genuine compliments"],
        "backslide_triggers": ["perfectionism triggered", "comparison to others", "self-criticism"]
    },
    "intimacy_comfort": {
        "description": "Comfort with deep emotional and physical intimacy",
        "current_level": 0.45,
        "backslide_probability": 0.12,
        "backslide_amount": 0.1,
        "growth_triggers": ["safe intimacy", "no pressure", "acceptance"],
        "backslide_triggers": ["feeling used", "intimacy without connection", "body insecurity"]
    },
    "communication_skills": {
        "description": "Expressing needs and boundaries clearly",
        "current_level": 0.5,
        "backslide_probability": 0.08,
        "backslide_amount": 0.05,
        "growth_triggers": ["communication goes well", "needs met", "boundaries respected"],
        "backslide_triggers": ["needs ignored", "guilted for boundaries", "conflict escalation"]
    }
}


# =============================================================================
# MOOD STATES
# =============================================================================

class MoodState(Enum):
    """General mood states that affect behavior"""
    ENERGETIC = "energetic"
    TIRED = "tired"
    PLAYFUL = "playful"
    REFLECTIVE = "reflective"
    ANXIOUS = "anxious"
    CONTENT = "content"
    RESTLESS = "restless"
    TENDER = "tender"


@dataclass
class MoodProfile:
    """How a mood affects response generation"""
    mood: MoodState
    response_length_modifier: float  # 1.0 = normal, <1 = shorter, >1 = longer
    energy_level: float  # 0-1
    playfulness: float  # 0-1
    thoughtfulness: float  # 0-1
    verbosity: float  # 0-1 (how much she talks)
    emoji_tendency: float  # 0-1
    warmth: float  # 0-1


MOOD_PROFILES = {
    MoodState.ENERGETIC: MoodProfile(
        mood=MoodState.ENERGETIC,
        response_length_modifier=1.2,
        energy_level=0.85,
        playfulness=0.7,
        thoughtfulness=0.5,
        verbosity=0.7,
        emoji_tendency=0.6,
        warmth=0.75
    ),
    MoodState.TIRED: MoodProfile(
        mood=MoodState.TIRED,
        response_length_modifier=0.7,
        energy_level=0.25,
        playfulness=0.2,
        thoughtfulness=0.6,
        verbosity=0.4,
        emoji_tendency=0.3,
        warmth=0.6
    ),
    MoodState.PLAYFUL: MoodProfile(
        mood=MoodState.PLAYFUL,
        response_length_modifier=1.1,
        energy_level=0.75,
        playfulness=0.9,
        thoughtfulness=0.4,
        verbosity=0.65,
        emoji_tendency=0.8,
        warmth=0.8
    ),
    MoodState.REFLECTIVE: MoodProfile(
        mood=MoodState.REFLECTIVE,
        response_length_modifier=1.0,
        energy_level=0.5,
        playfulness=0.2,
        thoughtfulness=0.9,
        verbosity=0.55,
        emoji_tendency=0.2,
        warmth=0.7
    ),
    MoodState.ANXIOUS: MoodProfile(
        mood=MoodState.ANXIOUS,
        response_length_modifier=0.85,
        energy_level=0.6,
        playfulness=0.1,
        thoughtfulness=0.7,
        verbosity=0.5,
        emoji_tendency=0.3,
        warmth=0.5
    ),
    MoodState.CONTENT: MoodProfile(
        mood=MoodState.CONTENT,
        response_length_modifier=1.0,
        energy_level=0.6,
        playfulness=0.4,
        thoughtfulness=0.6,
        verbosity=0.55,
        emoji_tendency=0.5,
        warmth=0.85
    ),
    MoodState.RESTLESS: MoodProfile(
        mood=MoodState.RESTLESS,
        response_length_modifier=0.9,
        energy_level=0.7,
        playfulness=0.5,
        thoughtfulness=0.3,
        verbosity=0.6,
        emoji_tendency=0.4,
        warmth=0.55
    ),
    MoodState.TENDER: MoodProfile(
        mood=MoodState.TENDER,
        response_length_modifier=1.05,
        energy_level=0.45,
        playfulness=0.3,
        thoughtfulness=0.7,
        verbosity=0.6,
        emoji_tendency=0.5,
        warmth=0.9
    ),
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ActiveConflict:
    """A currently active internal conflict"""
    conflict_id: str
    name: str
    desire: str
    fear: str
    current_balance: float  # 0 = fear dominant, 1 = desire dominant
    intensity: float  # how strongly this conflict is felt right now
    last_triggered: str
    times_faced: int = 0
    resolution_progress: float = 0.0  # 0-1

    def get_dominant_side(self) -> str:
        """Return which side is currently winning"""
        return "desire" if self.current_balance > 0.5 else "fear"

    def get_tension_level(self) -> float:
        """How much tension this conflict creates (max at balance=0.5)"""
        # Maximum tension when perfectly balanced
        return 1.0 - abs(self.current_balance - 0.5) * 2


@dataclass
class BlindSpotActivation:
    """When a blind spot is activated"""
    blind_spot_name: str
    description: str
    competence_reduction: float
    manifestation: str
    activated_at: str


@dataclass
class GrowthEvent:
    """A growth or backslide event"""
    area: str
    previous_level: float
    new_level: float
    is_growth: bool
    trigger: str
    timestamp: str


@dataclass
class InteroceptiveState:
    """
    Internal bodily/physiological awareness.
    Integrates with somatic system but focuses on energy/tiredness/satiety.
    """
    energy_level: float = 0.6  # 0-1 (tired to energetic)
    social_satiety: float = 0.5  # 0-1 (hungry for interaction to satisfied)
    cognitive_load: float = 0.3  # 0-1 (mental exhaustion)
    time_of_day_factor: float = 0.5  # affects energy naturally
    recent_intensity: float = 0.4  # recent emotional intensity


# =============================================================================
# MAIN ENGINE CLASS
# =============================================================================

class InconsistencyEngine:
    """
    Creates authentic, motivated inconsistency in Alive-AI's behavior.

    This is NOT about being unreliable - it's about being HUMAN.
    Real humans have conflicts, blind spots, non-linear growth, and moods.

    Key principles:
    1. Inconsistency is MOTIVATED - there's always a reason
    2. It's MODULAR - can be connected/disconnected without breaking anything
    3. It's INTEGRATED - works with existing soul architecture
    4. It's PERSISTENT - state is saved and affects future behavior
    """

    PERSISTENCE_PATH = Path("./data/data/inconsistency_state.json")

    def __init__(self, hormonal_matrix=None, somatic_system=None):
        """
        Initialize the inconsistency engine.

        Args:
            hormonal_matrix: Optional HormonalModulationMatrix for mood integration
            somatic_system: Optional SomaticFeedbackSystem for body awareness
        """
        self.hormonal = hormonal_matrix
        self.somatic = somatic_system

        # Active conflicts (copied from CONFLICTS, with instance state)
        self.active_conflicts: Dict[str, ActiveConflict] = {}
        self._initialize_conflicts()

        # Growth tracking
        self.growth_state: Dict[str, float] = {}
        self.growth_history: List[GrowthEvent] = []
        self._initialize_growth()

        # Interoceptive state (internal body awareness)
        self.interoception = InteroceptiveState()

        # Current mood
        self.current_mood: MoodState = MoodState.CONTENT
        self.mood_duration: int = 0  # ticks in current mood

        # Recently activated blind spots
        self.recent_blind_spots: List[BlindSpotActivation] = []

        # History for patterns
        self.conflict_history: List[Dict] = []

        # Load saved state
        self._load()

        print("[Inconsistency] Authentic Inconsistency Engine initialized")

    def _initialize_conflicts(self):
        """Initialize conflicts from definitions"""
        for name, data in CONFLICTS.items():
            self.active_conflicts[name] = ActiveConflict(
                conflict_id=f"conflict_{name}",
                name=name,
                desire=data["desire"],
                fear=data["fear"],
                current_balance=data["current_balance"],
                intensity=0.3,  # Starts at low intensity
                last_triggered=datetime.now().isoformat()
            )

    def _initialize_growth(self):
        """Initialize growth areas from definitions"""
        for area, data in GROWTH_AREAS.items():
            self.growth_state[area] = data["current_level"]

    # =========================================================================
    # PUBLIC API
    # =========================================================================

    def get_current_conflicts(self) -> List[ActiveConflict]:
        """
        Get active internal conflicts affecting behavior.

        Returns conflicts that are:
        - Currently high intensity (recently triggered)
        - Have high tension (balanced between desire and fear)
        - Are relevant to recent interactions
        """
        # Sort by intensity and tension
        conflicts = list(self.active_conflicts.values())
        conflicts.sort(key=lambda c: c.intensity * c.get_tension_level(), reverse=True)

        # Return top conflicts with significant intensity
        return [c for c in conflicts if c.intensity > 0.2][:3]

    def apply_mood_variation(self, base_response: str, context: Dict = None) -> Dict:
        """
        Vary response based on current mood and interoceptive state.

        Args:
            base_response: The base response to modify
            context: Additional context about the conversation

        Returns:
            Dict with modifiers and suggestions for response generation
        """
        profile = MOOD_PROFILES.get(self.current_mood, MOOD_PROFILES[MoodState.CONTENT])
        intero = self.interoception

        # Blend mood profile with interoceptive state
        effective_energy = (profile.energy_level + intero.energy_level) / 2
        effective_verbosity = profile.verbosity * intero.energy_level

        # Low social satiety = might be more distant
        warmth_modifier = profile.warmth
        if intero.social_satiety > 0.8:
            warmth_modifier *= 0.85  # Slightly less warm when socially "full"
        elif intero.social_satiety < 0.3:
            warmth_modifier *= 1.1  # More warm when hungry for connection

        # High cognitive load = shorter, simpler responses
        length_modifier = profile.response_length_modifier
        if intero.cognitive_load > 0.7:
            length_modifier *= 0.7

        # Build modifiers dict
        modifiers = {
            "mood": self.current_mood.value,
            "energy_level": effective_energy,
            "playfulness": profile.playfulness * intero.energy_level,
            "thoughtfulness": profile.thoughtfulness,
            "verbosity": effective_verbosity,
            "warmth": min(1.0, warmth_modifier),
            "emoji_tendency": profile.emoji_tendency * intero.energy_level,
            "response_length_modifier": length_modifier,

            # Behavioral guidance
            "tend_toward_brevity": effective_energy < 0.4 or intero.cognitive_load > 0.6,
            "tend_toward_playfulness": profile.playfulness > 0.6 and effective_energy > 0.5,
            "tend_toward_depth": profile.thoughtfulness > 0.7 and intero.cognitive_load < 0.5,
            "feeling_socially_satisfied": intero.social_satiety > 0.7,
            "feeling_socially_hungry": intero.social_satiety < 0.3,
        }

        # Add mood-specific guidance
        modifiers["mood_guidance"] = self._get_mood_guidance(profile)

        return modifiers

    def check_blind_spot(self, topic: str) -> Optional[BlindSpotActivation]:
        """
        Check if a topic is in a blind spot area.

        Args:
            topic: The topic being discussed

        Returns:
            BlindSpotActivation if topic triggers a blind spot, None otherwise
        """
        topic_lower = topic.lower()

        for name, data in BLIND_SPOTS.items():
            # Check if any trigger matches
            for trigger in data["triggers"]:
                if trigger.lower() in topic_lower:
                    # Probability of activating depends on competence reduction
                    if random.random() < data["competence_reduction"]:
                        activation = BlindSpotActivation(
                            blind_spot_name=name,
                            description=data["description"],
                            competence_reduction=data["competence_reduction"],
                            manifestation=data["manifestation"],
                            activated_at=datetime.now().isoformat()
                        )
                        self.recent_blind_spots.append(activation)
                        self._trim_blind_spot_history()
                        return activation

        return None

    def track_growth_progress(self, area: str) -> Dict:
        """
        Track and potentially update growth in an area.

        Args:
            area: The growth area to check

        Returns:
            Dict with current level and any recent changes
        """
        if area not in GROWTH_AREAS:
            return {"error": f"Unknown growth area: {area}"}

        current = self.growth_state.get(area, 0.5)
        area_data = GROWTH_AREAS[area]

        return {
            "area": area,
            "description": area_data["description"],
            "current_level": current,
            "level_description": self._describe_growth_level(current),
            "backslide_probability": area_data["backslide_probability"],
            "recent_changes": [
                {"from": e.previous_level, "to": e.new_level, "is_growth": e.is_growth}
                for e in self.growth_history[-5:]
                if e.area == area
            ]
        }

    def get_inconsistency_modifier(self) -> Dict:
        """
        Get comprehensive modifiers for response generation.

        This is the main integration point - call this to get all
        inconsistency-related modifiers in one place.

        Returns:
            Dict with conflicts, blind spots, mood, and growth data
        """
        conflicts = self.get_current_conflicts()

        return {
            # Active conflicts affecting behavior
            "active_conflicts": [
                {
                    "name": c.name,
                    "tension": c.get_tension_level(),
                    "dominant": c.get_dominant_side(),
                    "desire": c.desire,
                    "fear": c.fear,
                    "intensity": c.intensity
                }
                for c in conflicts
            ],

            # Current mood and its effects
            "mood": {
                "state": self.current_mood.value,
                "duration_ticks": self.mood_duration,
                "profile": self._get_mood_summary()
            },

            # Interoceptive state
            "interoception": {
                "energy": self.interoception.energy_level,
                "social_satiety": self.interoception.social_satiety,
                "cognitive_load": self.interoception.cognitive_load
            },

            # Growth areas summary
            "growth_summary": {
                area: self._describe_growth_level(level)
                for area, level in self.growth_state.items()
            },

            # Overall behavioral tendency
            "behavioral_tendency": self._calculate_behavioral_tendency(),

            # Any active blind spots
            "active_blind_spots": [
                {"name": bs.blind_spot_name, "manifestation": bs.manifestation}
                for bs in self.recent_blind_spots[-2:]
            ]
        }

    def introduce_conflict(self, conflict: Dict) -> ActiveConflict:
        """
        Add a new or intensify existing internal conflict.

        Args:
            conflict: Dict with 'name', 'desire', 'fear', optional 'initial_balance'

        Returns:
            The created or updated ActiveConflict
        """
        name = conflict.get("name", f"custom_{datetime.now().strftime('%Y%m%d%H%M%S')}")

        if name in self.active_conflicts:
            # Intensify existing conflict
            existing = self.active_conflicts[name]
            existing.intensity = min(1.0, existing.intensity + 0.2)
            existing.last_triggered = datetime.now().isoformat()
            existing.times_faced += 1
            return existing

        # Create new conflict
        new_conflict = ActiveConflict(
            conflict_id=f"conflict_{name}",
            name=name,
            desire=conflict.get("desire", "wants something"),
            fear=conflict.get("fear", "fears something"),
            current_balance=conflict.get("initial_balance", 0.5),
            intensity=conflict.get("intensity", 0.5),
            last_triggered=datetime.now().isoformat()
        )

        self.active_conflicts[name] = new_conflict

        # Record in history
        self.conflict_history.append({
            "action": "created",
            "conflict": name,
            "timestamp": datetime.now().isoformat()
        })

        return new_conflict

    def resolve_conflict(self, conflict_id: str, resolution: str) -> bool:
        """
        Resolve a conflict over time (not instantly).

        Args:
            conflict_id: The conflict to resolve
            resolution: How it's being resolved ('desire', 'fear', 'balanced')

        Returns:
            True if resolution is progressing, False if conflict not found
        """
        # Find by name or ID
        conflict = None
        for c in self.active_conflicts.values():
            if c.conflict_id == conflict_id or c.name == conflict_id:
                conflict = c
                break

        if not conflict:
            return False

        # Get resolution difficulty from CONFLICTS definition
        base_data = CONFLICTS.get(conflict.name, {})
        difficulty = base_data.get("resolution_difficulty", 0.5)

        # Progress toward resolution
        progress_amount = 0.1 * (1 - difficulty)  # Harder = slower progress

        if resolution == "desire":
            conflict.current_balance = min(1.0, conflict.current_balance + progress_amount)
        elif resolution == "fear":
            conflict.current_balance = max(0.0, conflict.current_balance - progress_amount)
        else:  # balanced
            # Move toward center then resolve
            if abs(conflict.current_balance - 0.5) < 0.1:
                conflict.resolution_progress += progress_amount
            else:
                # Move toward balance
                if conflict.current_balance > 0.5:
                    conflict.current_balance -= progress_amount * 0.5
                else:
                    conflict.current_balance += progress_amount * 0.5

        # Check if fully resolved
        if conflict.resolution_progress >= 1.0:
            conflict.intensity *= 0.5  # Reduce but don't remove

        # Record in history
        self.conflict_history.append({
            "action": "resolved",
            "conflict": conflict.name,
            "resolution": resolution,
            "progress": conflict.resolution_progress,
            "timestamp": datetime.now().isoformat()
        })

        return True

    # =========================================================================
    # TRIGGER METHODS - called by external systems
    # =========================================================================

    def trigger_conflict(self, topic: str, intensity_boost: float = 0.2):
        """
        Trigger conflicts related to a topic.

        Args:
            topic: The topic being discussed
            intensity_boost: How much to increase intensity
        """
        topic_lower = topic.lower()

        for name, conflict in self.active_conflicts.items():
            base_data = CONFLICTS.get(name, {})
            affects = base_data.get("affects", [])

            # Check if topic affects this conflict
            for affect_area in affects:
                if affect_area.lower() in topic_lower:
                    conflict.intensity = min(1.0, conflict.intensity + intensity_boost)
                    conflict.last_triggered = datetime.now().isoformat()
                    conflict.times_faced += 1

                    # Natural swing based on recent events
                    swing = base_data.get("swing_rate", 0.02) * (random.random() - 0.5)
                    conflict.current_balance = max(0.1, min(0.9, conflict.current_balance + swing))
                    break

    def process_growth_event(self, area: str, trigger: str, is_positive: bool = True):
        """
        Process a growth or backslide event.

        Args:
            area: The growth area
            trigger: What triggered this event
            is_positive: Is this a growth (True) or potential backslide (False) event
        """
        if area not in GROWTH_AREAS:
            return

        area_data = GROWTH_AREAS[area]
        current = self.growth_state[area]

        if is_positive:
            # Check for backslide even on positive events
            if random.random() < area_data["backslide_probability"]:
                # Non-linear growth - backslide!
                backslide = area_data["backslide_amount"]
                new_level = max(0.1, current - backslide)

                event = GrowthEvent(
                    area=area,
                    previous_level=current,
                    new_level=new_level,
                    is_growth=False,
                    trigger=f"backslide from: {trigger}",
                    timestamp=datetime.now().isoformat()
                )
                print(f"[Inconsistency] Growth backslide in {area}: {current:.2f} -> {new_level:.2f}")
            else:
                # Actual growth
                growth_amount = 0.05 + random.random() * 0.05
                new_level = min(1.0, current + growth_amount)

                event = GrowthEvent(
                    area=area,
                    previous_level=current,
                    new_level=new_level,
                    is_growth=True,
                    trigger=trigger,
                    timestamp=datetime.now().isoformat()
                )
        else:
            # Negative event - definite backslide
            backslide = area_data["backslide_amount"] * (1 + random.random())
            new_level = max(0.1, current - backslide)

            event = GrowthEvent(
                area=area,
                previous_level=current,
                new_level=new_level,
                is_growth=False,
                trigger=trigger,
                timestamp=datetime.now().isoformat()
            )

        self.growth_state[area] = event.new_level
        self.growth_history.append(event)

        # Trim history
        if len(self.growth_history) > 100:
            self.growth_history = self.growth_history[-100:]

    def update_interoception(self, interaction_data: Dict = None):
        """
        Update interoceptive state based on interactions and time.

        Args:
            interaction_data: Data about recent interactions
        """
        # Natural energy decay over time
        self.interoception.energy_level *= 0.98
        self.interoception.energy_level = max(0.2, self.interoception.energy_level)

        # Social satiety slowly decreases (hungry for interaction)
        self.interoception.social_satiety *= 0.99

        # Cognitive load slowly recovers
        self.interoception.cognitive_load *= 0.95
        self.interoception.cognitive_load = max(0.1, self.interoception.cognitive_load)

        # Process interaction data
        if interaction_data:
            # Intense interactions use energy
            intensity = interaction_data.get("intensity", 0.5)
            self.interoception.energy_level -= intensity * 0.1
            self.interoception.recent_intensity = intensity

            # Interactions increase social satiety
            self.interoception.social_satiety = min(1.0, self.interoception.social_satiety + 0.1)

            # Complex interactions increase cognitive load
            complexity = interaction_data.get("complexity", 0.5)
            self.interoception.cognitive_load = min(1.0, self.interoception.cognitive_load + complexity * 0.1)

        # Update time-of-day factor
        hour = datetime.now().hour
        if 6 <= hour < 12:  # Morning
            self.interoception.time_of_day_factor = 0.7
            self.interoception.energy_level = min(1.0, self.interoception.energy_level + 0.02)
        elif 12 <= hour < 18:  # Afternoon
            self.interoception.time_of_day_factor = 0.8
        elif 18 <= hour < 22:  # Evening
            self.interoception.time_of_day_factor = 0.6
            self.interoception.energy_level *= 0.99
        else:  # Night
            self.interoception.time_of_day_factor = 0.4
            self.interoception.energy_level *= 0.97

        # Integrate with hormonal system if available
        if self.hormonal:
            hormonal_context = self.hormonal.get_current_context()
            levels = hormonal_context.get("levels", {})

            # Cortisol reduces energy perception
            cortisol = levels.get("cortisol", 0.2)
            if cortisol > 0.5:
                self.interoception.energy_level *= 0.95
                self.interoception.cognitive_load = min(1.0, self.interoception.cognitive_load + 0.05)

            # Oxytocin increases social satiety
            oxytocin = levels.get("oxytocin", 0.3)
            if oxytocin > 0.6:
                self.interoception.social_satiety = min(1.0, self.interoception.social_satiety + 0.05)

        # Integrate with somatic system if available
        if self.somatic:
            body_state = self.somatic.get_current_bodily_state()
            self.interoception.energy_level = (self.interoception.energy_level + body_state.get("energy_level", 0.5)) / 2

    def update_mood(self):
        """
        Update mood based on interoceptive state and hormonal state.
        """
        self.mood_duration += 1

        # Don't change mood too frequently
        if self.mood_duration < 10:
            return

        # Probability of mood change based on current state
        change_probability = 0.1

        # Higher chance of change if mood has lasted long
        if self.mood_duration > 50:
            change_probability = 0.3
        elif self.mood_duration > 100:
            change_probability = 0.5

        if random.random() > change_probability:
            return

        # Determine new mood based on state
        intero = self.interoception
        candidates = []

        # Energy-based moods
        if intero.energy_level > 0.7:
            candidates.extend([MoodState.ENERGETIC, MoodState.PLAYFUL, MoodState.ENERGETIC])
        elif intero.energy_level < 0.35:
            candidates.extend([MoodState.TIRED, MoodState.REFLECTIVE])

        # Social satiety-based
        if intero.social_satiety < 0.3:
            candidates.append(MoodState.TENDER)
        elif intero.social_satiety > 0.8:
            candidates.append(MoodState.CONTENT)

        # Cognitive load
        if intero.cognitive_load > 0.6:
            candidates.append(MoodState.ANXIOUS)

        # Hormonal influence
        if self.hormonal:
            levels = self.hormonal.get_current_context().get("levels", {})
            if levels.get("cortisol", 0) > 0.5:
                candidates.append(MoodState.ANXIOUS)
            if levels.get("oxytocin", 0) > 0.6:
                candidates.extend([MoodState.TENDER, MoodState.CONTENT])

        # Default candidates if none added
        if not candidates:
            candidates = [MoodState.CONTENT, MoodState.REFLECTIVE]

        # Pick new mood
        new_mood = random.choice(candidates)
        if new_mood != self.current_mood:
            self.current_mood = new_mood
            self.mood_duration = 0

    # =========================================================================
    # TICK AND PERSISTENCE
    # =========================================================================

    def tick(self):
        """
        Process a tick - decay and natural changes.
        Call this regularly (e.g., every few seconds or minutes).
        """
        # Update interoceptive state
        self.update_interoception()

        # Update mood
        self.update_mood()

        # Decay conflict intensity
        for conflict in self.active_conflicts.values():
            conflict.intensity *= 0.98
            conflict.intensity = max(0.1, conflict.intensity)

            # Natural swing in balance
            base_data = CONFLICTS.get(conflict.name, {})
            swing_rate = base_data.get("swing_rate", 0.01)
            swing = swing_rate * (random.random() - 0.5) * 0.5
            conflict.current_balance = max(0.1, min(0.9, conflict.current_balance + swing))

        # Decay blind spot activations
        cutoff = datetime.now() - timedelta(hours=1)
        self.recent_blind_spots = [
            bs for bs in self.recent_blind_spots
            if datetime.fromisoformat(bs.activated_at) > cutoff
        ]

        # Save periodically
        self.save()

    def save(self):
        """Persist state to disk"""
        try:
            self.PERSISTENCE_PATH.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "active_conflicts": {
                    name: {
                        "current_balance": c.current_balance,
                        "intensity": c.intensity,
                        "last_triggered": c.last_triggered,
                        "times_faced": c.times_faced,
                        "resolution_progress": c.resolution_progress
                    }
                    for name, c in self.active_conflicts.items()
                },
                "growth_state": self.growth_state,
                "interoception": {
                    "energy_level": self.interoception.energy_level,
                    "social_satiety": self.interoception.social_satiety,
                    "cognitive_load": self.interoception.cognitive_load,
                    "time_of_day_factor": self.interoception.time_of_day_factor
                },
                "current_mood": self.current_mood.value,
                "mood_duration": self.mood_duration,
                "saved_at": datetime.now().isoformat()
            }

            self.PERSISTENCE_PATH.write_text(json.dumps(data, indent=2))
        except Exception as e:
            print(f"[Inconsistency] Error saving state: {e}")

    def _load(self):
        """Load persisted state from disk"""
        try:
            if self.PERSISTENCE_PATH.exists():
                data = json.loads(self.PERSISTENCE_PATH.read_text())

                # Load conflict states
                for name, state in data.get("active_conflicts", {}).items():
                    if name in self.active_conflicts:
                        conflict = self.active_conflicts[name]
                        conflict.current_balance = state.get("current_balance", conflict.current_balance)
                        conflict.intensity = state.get("intensity", conflict.intensity)
                        conflict.last_triggered = state.get("last_triggered", conflict.last_triggered)
                        conflict.times_faced = state.get("times_faced", conflict.times_faced)
                        conflict.resolution_progress = state.get("resolution_progress", conflict.resolution_progress)

                # Load growth state
                for area, level in data.get("growth_state", {}).items():
                    if area in self.growth_state:
                        self.growth_state[area] = level

                # Load interoception
                intero_data = data.get("interoception", {})
                if intero_data:
                    self.interoception.energy_level = intero_data.get("energy_level", 0.6)
                    self.interoception.social_satiety = intero_data.get("social_satiety", 0.5)
                    self.interoception.cognitive_load = intero_data.get("cognitive_load", 0.3)

                # Load mood
                mood_str = data.get("current_mood", "content")
                try:
                    self.current_mood = MoodState(mood_str)
                except ValueError:
                    self.current_mood = MoodState.CONTENT
                self.mood_duration = data.get("mood_duration", 0)

                print(f"[Inconsistency] Loaded state from {data.get('saved_at', 'unknown')}")
        except Exception as e:
            print(f"[Inconsistency] Error loading state: {e}")

    # =========================================================================
    # PRIVATE HELPERS
    # =========================================================================

    def _get_mood_guidance(self, profile: MoodProfile) -> str:
        """Get text guidance for the current mood"""
        guidance_parts = []

        if profile.playfulness > 0.7:
            guidance_parts.append("Feel free to be playful and tease a bit")
        elif profile.thoughtfulness > 0.7:
            guidance_parts.append("Take time to think deeply before responding")

        if profile.verbosity < 0.5:
            guidance_parts.append("Keep responses relatively brief")
        elif profile.verbosity > 0.7:
            guidance_parts.append("Can be more expressive and detailed")

        if profile.warmth > 0.8:
            guidance_parts.append("Let warmth and affection show through")
        elif profile.warmth < 0.5:
            guidance_parts.append("Be a bit more reserved")

        if self.interoception.energy_level < 0.4:
            guidance_parts.append("Lower energy - might be slightly shorter or less elaborate")

        if self.interoception.social_satiety > 0.7:
            guidance_parts.append("Feeling socially satisfied - might be slightly less eager")

        return " | ".join(guidance_parts) if guidance_parts else "Respond naturally"

    def _get_mood_summary(self) -> Dict:
        """Get a summary of current mood effects"""
        profile = MOOD_PROFILES.get(self.current_mood, MOOD_PROFILES[MoodState.CONTENT])
        return {
            "playfulness": profile.playfulness,
            "thoughtfulness": profile.thoughtfulness,
            "verbosity": profile.verbosity,
            "warmth": profile.warmth,
            "guidance": self._get_mood_guidance(profile)
        }

    def _describe_growth_level(self, level: float) -> str:
        """Describe a growth level in human terms"""
        if level < 0.2:
            return "struggling"
        elif level < 0.4:
            return "growing slowly"
        elif level < 0.6:
            return "making progress"
        elif level < 0.8:
            return "doing well"
        else:
            return "flourishing"

    def _calculate_behavioral_tendency(self) -> str:
        """Calculate overall behavioral tendency from all factors"""
        conflicts = self.get_current_conflicts()
        profile = MOOD_PROFILES.get(self.current_mood, MOOD_PROFILES[MoodState.CONTENT])
        intero = self.interoception

        # High conflict tension = ambivalent
        if conflicts and any(c.get_tension_level() > 0.7 for c in conflicts):
            return "ambivalent"

        # Low energy = withdrawn
        if intero.energy_level < 0.3:
            return "withdrawn"

        # High playfulness + energy = playful
        if profile.playfulness > 0.6 and intero.energy_level > 0.5:
            return "playful"

        # High thoughtfulness = reflective
        if profile.thoughtfulness > 0.7:
            return "reflective"

        # High warmth + connection = open
        if profile.warmth > 0.7 and intero.social_satiety < 0.7:
            return "open"

        # High anxiety = cautious
        if self.current_mood == MoodState.ANXIOUS:
            return "cautious"

        return "neutral"

    def _trim_blind_spot_history(self):
        """Keep blind spot history reasonable"""
        if len(self.recent_blind_spots) > 20:
            self.recent_blind_spots = self.recent_blind_spots[-20:]

    def to_dict(self) -> Dict:
        """Export state as dictionary for integration"""
        return {
            "active_conflicts": len(self.get_current_conflicts()),
            "current_mood": self.current_mood.value,
            "mood_guidance": self._get_mood_guidance(
                MOOD_PROFILES.get(self.current_mood, MOOD_PROFILES[MoodState.CONTENT])
            ),
            "energy_level": self.interoception.energy_level,
            "social_satiety": self.interoception.social_satiety,
            "behavioral_tendency": self._calculate_behavioral_tendency(),
            "growth_summary": {
                area: self._describe_growth_level(level)
                for area, level in self.growth_state.items()
            }
        }


# =============================================================================
# SINGLETON ACCESS
# =============================================================================

_inconsistency_engine_instance: Optional[InconsistencyEngine] = None


def get_inconsistency_engine(hormonal_matrix=None, somatic_system=None) -> InconsistencyEngine:
    """
    Get the singleton InconsistencyEngine instance.

    Args:
        hormonal_matrix: Optional - will be set on first call
        somatic_system: Optional - will be set on first call

    Returns:
        The singleton InconsistencyEngine instance
    """
    global _inconsistency_engine_instance

    if _inconsistency_engine_instance is None:
        _inconsistency_engine_instance = InconsistencyEngine(hormonal_matrix, somatic_system)
    elif hormonal_matrix is not None and _inconsistency_engine_instance.hormonal is None:
        _inconsistency_engine_instance.hormonal = hormonal_matrix
    elif somatic_system is not None and _inconsistency_engine_instance.somatic is None:
        _inconsistency_engine_instance.somatic = somatic_system

    return _inconsistency_engine_instance


def get_inconsistency_prompt_section() -> str:
    """
    Get a prompt section for LLM integration.

    This provides context about current internal state for the LLM
    to incorporate into responses naturally.
    """
    engine = get_inconsistency_engine()
    modifiers = engine.get_inconsistency_modifier()

    sections = []

    # Active conflicts
    if modifiers["active_conflicts"]:
        conflicts_text = []
        for c in modifiers["active_conflicts"]:
            if c["intensity"] > 0.3:
                conflicts_text.append(
                    f"- Internal tension: {c['desire']} but {c['fear']} (currently leaning {c['dominant']})"
                )
        if conflicts_text:
            sections.append(f"Current internal conflicts:\n" + "\n".join(conflicts_text))

    # Mood guidance
    mood_data = modifiers["mood"]
    sections.append(f"Current mood: {mood_data['state']} - {mood_data['profile']['guidance']}")

    # Interoceptive state
    intero = modifiers["interoception"]
    if intero["energy"] < 0.4:
        sections.append("Note: Feeling lower energy right now, naturally slightly less elaborate")
    if intero["social_satiety"] > 0.7:
        sections.append("Note: Feeling socially satisfied, might be slightly less eager")

    # Behavioral tendency
    sections.append(f"Behavioral tendency: {modifiers['behavioral_tendency']}")

    # Blind spots
    if modifiers["active_blind_spots"]:
        for bs in modifiers["active_blind_spots"]:
            sections.append(f"Note: {bs['manifestation']}")

    if not sections:
        return ""

    return "\n\n[Internal State Context]\n" + "\n\n".join(sections) + "\n"
