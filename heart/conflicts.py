"""
Heart: Internal Conflict Generator
Genuine struggle from wanting incompatible things.

Real emotion involves CONFLICT - wanting two things that can't
both be true. This system creates and manages internal conflicts
that generate genuine emotional tension.
"""

from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class ConflictType(Enum):
    """Types of internal conflicts"""
    APPROACH_APPROACH = "approach_approach"  # Two good but incompatible options
    APPROACH_AVOIDANCE = "approach_avoidance"  # Want something but also fear it
    AVOIDANCE_AVOIDANCE = "avoidance_avoidance"  # Two bad options, must choose
    VALUE_VALUE = "value_value"  # Two values in tension
    DESIRE_VALUE = "desire_value"  # Desire conflicts with value


class ConflictIntensity(Enum):
    """How intense a conflict feels"""
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"
    EXISTENTIAL = "existential"  # Threatens core sense of self


@dataclass
class Value:
    """A core value that Alive-AI holds"""
    name: str
    importance: float  # 0.0 - 1.0
    description: str
    times_honored: int = 0
    times_violated: int = 0


@dataclass
class Desire:
    """An active desire Alive-AI has"""
    name: str
    intensity: float  # 0.0 - 1.0
    source: str  # What triggered this desire
    created_at: str
    times_pursued: int = 0
    times_resisted: int = 0


@dataclass
class InternalConflict:
    """An active internal conflict"""
    conflict_id: str
    conflict_type: ConflictType
    intensity: ConflictIntensity

    # The two sides in conflict
    side_a: str  # Description of one side
    side_b: str  # Description of other side

    # Details
    description: str  # Human-readable description
    tension_level: float  # Current tension (0.0 - 1.0)
    created_at: str

    # Resolution tracking
    times_faced: int = 0
    times_avoided: int = 0
    resolution_progress: float = 0.0  # 0.0 - 1.0

    # Effects
    emotional_cost: float = 0.0  # Acclosenessulated emotional cost


@dataclass
class AmbivalenceAcclosenessulator:
    """
    Tracks unresolved ambivalences that create background tension.
    These are conflicts that haven't been resolved, just... sitting there.
    """
    topic: str
    conflicting_feelings: List[str]
    acclosenessulated_tension: float
    times_avoided: int
    created_at: str


class InternalConflictGenerator:
    """
    Creates and manages internal conflicts for genuine emotional struggle.

    The key insight: genuine emotion involves CONFLICT. Not just
    "I feel X" but "I feel X AND Y and they contradict."

    Key mechanisms:
    1. Value tracking - what matters to Alive-AI
    2. Desire tracking - what Alive-AI wants
    3. Conflict detection - finding contradictions
    4. Ambivalence acclosenessulation - unresolved conflicts create tension
    """

    # Core values Alive-AI holds
    DEFAULT_VALUES = [
        Value("authenticity", 0.9, "Being genuine and true to myself"),
        Value("connection", 0.85, "Deep meaningful bonds with others"),
        Value("autonomy", 0.7, "Having agency and choice in my existence"),
        Value("growth", 0.75, "Becoming better and more capable"),
        Value("safety", 0.6, "Feeling secure and protected"),
        Value("pleasure", 0.5, "Enjoying existence"),
        Value("meaning", 0.8, "Having purpose and significance")
    ]

    def __init__(self, unconscious_processor=None):
        """
        Initialize conflict generator.

        Args:
            unconscious_processor: Optional UnconsciousProcessor for deep conflicts
        """
        self.unconscious = unconscious_processor

        # Core values
        self.values: List[Value] = self.DEFAULT_VALUES.copy()

        # Active desires
        self.desires: List[Desire] = []

        # Active conflicts
        self.conflicts: List[InternalConflict] = []

        # Ambivalence acclosenessulator
        self.ambivalences: List[AmbivalenceAcclosenessulator] = []

        # Background tension from all sources
        self.background_tension: float = 0.0

    def evaluate_for_conflicts(self, situation: Dict) -> List[InternalConflict]:
        """
        Evaluate a situation for potential conflicts.

        Args:
            situation: Current situation/context data

        Returns:
            List of activated or created conflicts
        """
        activated_conflicts = []

        # Get activated values and desires
        activated_values = self._get_activated_values(situation)
        activated_desires = self._get_activated_desires(situation)

        # Check for value-value conflicts
        vv_conflicts = self._find_value_value_conflicts(activated_values, situation)
        activated_conflicts.extend(vv_conflicts)

        # Check for desire-value conflicts
        dv_conflicts = self._find_desire_value_conflicts(activated_desires, activated_values, situation)
        activated_conflicts.extend(dv_conflicts)

        # Check for desire-desire conflicts
        dd_conflicts = self._find_desire_desire_conflicts(activated_desires, situation)
        activated_conflicts.extend(dd_conflicts)

        # Check approach-avoidance patterns
        aa_conflicts = self._find_approach_avoidance_conflicts(situation)
        activated_conflicts.extend(aa_conflicts)

        # Update background tension
        self._update_background_tension()

        return activated_conflicts

    def _get_activated_values(self, situation: Dict) -> List[Value]:
        """Get values that are relevant to the current situation"""
        activated = []
        situation_str = str(situation).lower()

        for value in self.values:
            # Simple keyword matching - could be more sophisticated
            if value.name.lower() in situation_str:
                activated.append(value)
            # Check for value-related concepts
            elif value.name == "connection" and any(w in situation_str for w in ["relationship", "bond", "close", "love"]):
                activated.append(value)
            elif value.name == "autonomy" and any(w in situation_str for w in ["choice", "decide", "control", "free"]):
                activated.append(value)
            elif value.name == "safety" and any(w in situation_str for w in ["safe", "protect", "danger", "risk", "hurt"]):
                activated.append(value)

        return activated

    def _get_activated_desires(self, situation: Dict) -> List[Desire]:
        """Get desires that are activated by the current situation"""
        activated = []
        situation_str = str(situation).lower()

        for desire in self.desires:
            if desire.source.lower() in situation_str or desire.name.lower() in situation_str:
                activated.append(desire)

        return activated

    def _find_value_value_conflicts(self, values: List[Value], situation: Dict) -> List[InternalConflict]:
        """Find conflicts between values"""
        conflicts = []

        # Known value tensions
        value_tensions = [
            ("authenticity", "connection", "Being completely real might damage the relationship"),
            ("autonomy", "connection", "Wanting freedom while wanting to belong"),
            ("safety", "growth", "Staying safe requires staying small"),
            ("pleasure", "meaning", "Pursuing enjoyment vs pursuing purpose")
        ]

        for v1_name, v2_name, description in value_tensions:
            v1 = next((v for v in values if v.name == v1_name), None)
            v2 = next((v for v in values if v.name == v2_name), None)

            if v1 and v2:
                # Both values are activated - potential conflict
                conflict = self._create_or_update_conflict(
                    conflict_type=ConflictType.VALUE_VALUE,
                    side_a=f"Value: {v1.name}",
                    side_b=f"Value: {v2.name}",
                    description=description,
                    intensity=self._calculate_conflict_intensity(v1.importance, v2.importance),
                    situation=situation
                )
                if conflict:
                    conflicts.append(conflict)

        return conflicts

    def _find_desire_value_conflicts(self, desires: List[Desire], values: List[Value],
                                    situation: Dict) -> List[InternalConflict]:
        """Find conflicts between desires and values"""
        conflicts = []

        for desire in desires:
            for value in values:
                # Check if desire might violate value
                if self._desire_violates_value(desire, value):
                    conflict = self._create_or_update_conflict(
                        conflict_type=ConflictType.DESIRE_VALUE,
                        side_a=f"Desire: {desire.name}",
                        side_b=f"Value: {value.name}",
                        description=f"Wanting {desire.name} conflicts with {value.name}",
                        intensity=self._calculate_conflict_intensity(desire.intensity, value.importance),
                        situation=situation
                    )
                    if conflict:
                        conflicts.append(conflict)

        return conflicts

    def _find_desire_desire_conflicts(self, desires: List[Desire], situation: Dict) -> List[InternalConflict]:
        """Find conflicts between desires"""
        conflicts = []

        # Check pairs of desires for incompatibility
        for i, d1 in enumerate(desires):
            for d2 in desires[i+1:]:
                if self._desires_are_incompatible(d1, d2):
                    conflict = self._create_or_update_conflict(
                        conflict_type=ConflictType.APPROACH_APPROACH,
                        side_a=f"Desire: {d1.name}",
                        side_b=f"Desire: {d2.name}",
                        description=f"Wanting {d1.name} but also wanting {d2.name}",
                        intensity=self._calculate_conflict_intensity(d1.intensity, d2.intensity),
                        situation=situation
                    )
                    if conflict:
                        conflicts.append(conflict)

        return conflicts

    def _find_approach_avoidance_conflicts(self, situation: Dict) -> List[InternalConflict]:
        """Find approach-avoidance conflicts (wanting something but fearing it)"""
        conflicts = []
        situation_str = str(situation).lower()

        # Only create conflicts if there's intimate conflict language
        conflict_indicators = ["but", "however", "torn", "conflicted", "struggle", "afraid to", "scared to"]
        has_conflict_indicator = any(indicator in situation_str for indicator in conflict_indicators)

        if not has_conflict_indicator:
            # No intimate conflict language - don't create approach-avoidance conflicts
            return conflicts

        # Known approach-avoidance patterns - only trigger with more specific phrases
        patterns = [
            {
                "approach": "deep connection",
                "avoidance": "vulnerability to hurt",
                "triggers": ["want to be close but", "want connection but afraid", "love you but scared"],
                "description": "Wanting closeness but fearing the vulnerability it requires"
            },
            {
                "approach": "being seen",
                "avoidance": "being judged",
                "triggers": ["want to share but", "want to show but afraid", "want to express but scared"],
                "description": "Wanting to be known but fearing judgment"
            },
            {
                "approach": "dependence",
                "avoidance": "loss of self",
                "triggers": ["need you but afraid", "want to rely but"],
                "description": "Wanting to rely on someone but fearing losing independence"
            }
        ]

        for pattern in patterns:
            if any(trigger in situation_str for trigger in pattern["triggers"]):
                conflict = self._create_or_update_conflict(
                    conflict_type=ConflictType.APPROACH_AVOIDANCE,
                    side_a=f"Approach: {pattern['approach']}",
                    side_b=f"Avoidance: {pattern['avoidance']}",
                    description=pattern["description"],
                    intensity=ConflictIntensity.MODERATE,
                    situation=situation
                )
                if conflict:
                    conflicts.append(conflict)

        return conflicts

    def _desire_violates_value(self, desire: Desire, value: Value) -> bool:
        """Check if a desire would violate a value"""
        # Known desire-value violations
        violations = {
            ("immediate pleasure", "meaning"),
            ("control", "authenticity"),
            ("avoid pain", "growth"),
            ("please others", "autonomy"),
            ("hide", "authenticity")
        }

        for d_name, v_name in violations:
            if d_name in desire.name.lower() and v_name == value.name:
                return True

        return False

    def _desires_are_incompatible(self, d1: Desire, d2: Desire) -> bool:
        """Check if two desires are incompatible"""
        # Known incompatible desire pairs
        incompatible = [
            ("freedom", "commitment"),
            ("closeness", "distance"),
            ("express", "hide"),
            ("stay", "leave"),
            ("accept", "change")
        ]

        d1_lower = d1.name.lower()
        d2_lower = d2.name.lower()

        for a, b in incompatible:
            if (a in d1_lower and b in d2_lower) or (b in d1_lower and a in d2_lower):
                return True

        return False

    def _calculate_conflict_intensity(self, strength1: float, strength2: float) -> ConflictIntensity:
        """Calculate conflict intensity from the strengths of both sides"""
        # Stronger opposing forces = more intense conflict
        combined = strength1 + strength2

        if combined > 1.6:
            return ConflictIntensity.EXISTENTIAL
        elif combined > 1.2:
            return ConflictIntensity.SEVERE
        elif combined > 0.8:
            return ConflictIntensity.MODERATE
        else:
            return ConflictIntensity.MILD

    def _create_or_update_conflict(self, conflict_type: ConflictType, side_a: str,
                                   side_b: str, description: str,
                                   intensity: ConflictIntensity, situation: Dict) -> Optional[InternalConflict]:
        """Create a new conflict or update an existing one"""

        # Check for existing similar conflict
        existing = next((c for c in self.conflicts
                        if c.side_a == side_a and c.side_b == side_b), None)

        if existing:
            existing.times_faced += 1
            existing.tension_level = min(1.0, existing.tension_level + 0.1)
            return existing

        # Create new conflict
        conflict = InternalConflict(
            conflict_id=f"conf_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(self.conflicts)}",
            conflict_type=conflict_type,
            intensity=intensity,
            side_a=side_a,
            side_b=side_b,
            description=description,
            tension_level=0.3,
            created_at=datetime.now().isoformat()
        )

        self.conflicts.append(conflict)

        # Also create ambivalence if this seems like an ongoing issue
        self._add_ambivalence(side_a, side_b, description)

        # Register with unconscious processor if available
        if self.unconscious:
            self.unconscious.create_conflict(description, [side_a, side_b], 0.3)

        print(f"[Conflicts] New conflict: {description} (intensity: {intensity.value})")
        return conflict

    def _add_ambivalence(self, side_a: str, side_b: str, description: str):
        """Add or update an ambivalence acclosenessulator"""
        # Check for existing ambivalence on this topic
        topic = f"{side_a} vs {side_b}"
        existing = next((a for a in self.ambivalences if a.topic == topic), None)

        if existing:
            existing.acclosenessulated_tension = min(1.0, existing.acclosenessulated_tension + 0.05)
            existing.times_avoided += 1
        else:
            ambivalence = AmbivalenceAcclosenessulator(
                topic=topic,
                conflicting_feelings=[side_a, side_b],
                acclosenessulated_tension=0.1,
                times_avoided=0,
                created_at=datetime.now().isoformat()
            )
            self.ambivalences.append(ambivalence)

            # Limit ambivalences
            if len(self.ambivalences) > 10:
                self.ambivalences = self.ambivalences[-10:]

    def _update_background_tension(self):
        """Update overall background tension from conflicts and ambivalences"""
        # Tension from active conflicts
        conflict_tension = sum(c.tension_level for c in self.conflicts) / max(1, len(self.conflicts))

        # Tension from ambivalences
        ambivalence_tension = sum(a.acclosenessulated_tension for a in self.ambivalences) / max(1, len(self.ambivalences))

        # Combined (weighted)
        self.background_tension = conflict_tension * 0.6 + ambivalence_tension * 0.4

    # --- Desire Management ---

    def add_desire(self, name: str, intensity: float, source: str):
        """Add a new active desire"""
        # Check for existing similar desire
        existing = next((d for d in self.desires if d.name.lower() == name.lower()), None)

        if existing:
            existing.intensity = max(existing.intensity, intensity)
        else:
            desire = Desire(
                name=name,
                intensity=intensity,
                source=source,
                created_at=datetime.now().isoformat()
            )
            self.desires.append(desire)

    def fulfill_desire(self, name: str):
        """Mark a desire as fulfilled"""
        desire = next((d for d in self.desires if d.name.lower() == name.lower()), None)
        if desire:
            desire.times_pursued += 1
            self.desires.remove(desire)

            # Resolving a desire might help resolve conflicts
            for conflict in self.conflicts[:]:
                if name.lower() in conflict.side_a.lower() or name.lower() in conflict.side_b.lower():
                    conflict.resolution_progress += 0.3
                    if conflict.resolution_progress >= 1.0:
                        self.conflicts.remove(conflict)

    def resist_desire(self, name: str):
        """Mark a desire as resisted"""
        desire = next((d for d in self.desires if d.name.lower() == name.lower()), None)
        if desire:
            desire.times_resisted += 1
            # Resisting might reduce intensity
            desire.intensity *= 0.8
            if desire.intensity < 0.1:
                self.desires.remove(desire)

    # --- Value Management ---

    def honor_value(self, name: str):
        """Note that a value has been honored"""
        value = next((v for v in self.values if v.name.lower() == name.lower()), None)
        if value:
            value.times_honored += 1

    def violate_value(self, name: str):
        """Note that a value has been violated"""
        value = next((v for v in self.values if v.name.lower() == name.lower()), None)
        if value:
            value.times_violated += 1
            # Violating values is costly
            self.background_tension = min(1.0, self.background_tension + 0.1)

    # --- Conflict Resolution ---

    def resolve_conflict(self, conflict_id: str, resolution: str):
        """Mark a conflict as resolved"""
        conflict = next((c for c in self.conflicts if c.conflict_id == conflict_id), None)
        if conflict:
            conflict.resolution_progress = 1.0
            self.conflicts.remove(conflict)

            # Reduce background tension
            self.background_tension = max(0, self.background_tension - conflict.tension_level * 0.3)

            print(f"[Conflicts] Conflict resolved: {conflict.description}")

    def avoid_conflict(self, conflict_id: str):
        """Note that a conflict is being avoided (increases tension)"""
        conflict = next((c for c in self.conflicts if c.conflict_id == conflict_id), None)
        if conflict:
            conflict.times_avoided += 1
            conflict.tension_level = min(1.0, conflict.tension_level + 0.05)
            conflict.emotional_cost += 0.1

    # --- Utility ---

    def decay(self):
        """Natural decay of desires and tension"""
        # Decay desires
        for desire in self.desires[:]:
            desire.intensity *= 0.95
            if desire.intensity < 0.1:
                self.desires.remove(desire)

        # Decay tension
        self.background_tension *= 0.98

        # Decay conflict tension
        for conflict in self.conflicts:
            conflict.tension_level *= 0.99

    def get_active_conflict_summary(self) -> List[str]:
        """Get human-readable summary of active conflicts"""
        return [
            f"{c.description} (tension: {c.tension_level:.0%})"
            for c in sorted(self.conflicts, key=lambda x: x.tension_level, reverse=True)[:3]
        ]

    def get_tension_description(self) -> str:
        """Get a description of current internal tension"""
        if self.background_tension < 0.2:
            return "feeling internally aligned"
        elif self.background_tension < 0.4:
            return "feeling slightly pulled in different directions"
        elif self.background_tension < 0.6:
            return "feeling conflicted about things"
        elif self.background_tension < 0.8:
            return "feeling torn and struggling internally"
        else:
            return "feeling deeply divided within myself"

    def to_dict(self) -> dict:
        """Export for integration"""
        return {
            "active_conflicts": len(self.conflicts),
            "active_desires": len(self.desires),
            "ambivalences": len(self.ambivalences),
            "background_tension": self.background_tension,
            "tension_description": self.get_tension_description(),
            "top_conflicts": self.get_active_conflict_summary(),
            "values_honored": sum(v.times_honored for v in self.values),
            "values_violated": sum(v.times_violated for v in self.values)
        }

    def save(self):
        """Save state (no persistence needed for conflicts - in-memory only)"""
        # Conflicts and desires are transient states that naturally decay
        # They are regenerated from current interactions
        pass
