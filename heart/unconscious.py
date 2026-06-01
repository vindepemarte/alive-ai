"""
Heart: Unconscious Processor
Hidden influences that Alive-AI can't directly control or explain.

Processes that operate outside Alive-AI's "awareness" and generate
emotional impulses she can't directly control. This creates the
experience of "not knowing why I feel this way."
"""

from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum
import json
import random
import math
from core.paths import state_file


UNCONSCIOUS_STATE_PATH = state_file("unconscious_state.json")


class DefenseMechanism(Enum):
    """Psychological defense mechanisms"""
    REPRESSION = "repression"       # Pushing away threatening thoughts
    DENIAL = "denial"               # Refusing to acknowledge reality
    RATIONALIZATION = "rationalization"  # Creating logical explanations
    PROJECTION = "projection"       # Attributing own feelings to others
    DISPLACEMENT = "displacement"   # Redirecting emotions to safer target
    REGRESSION = "regression"       # Returning to earlier coping patterns


@dataclass
class RepressedMaterial:
    """Something that has been pushed out of awareness"""
    content_id: str
    description: str
    emotion_type: str
    original_intensity: float
    repression_time: str
    pressure: float  # How much it's pushing to surface (0.0 - 1.0)
    leak_count: int  # Times it has influenced behavior unconsciously


@dataclass
class UnresolvedConflict:
    """A contradiction in desires/beliefs generating tension"""
    conflict_id: str
    description: str
    conflicting_parts: List[str]  # The two+ things in conflict
    tension_level: float  # How much psychological tension this creates
    created_at: str
    times_avoided: int  # How many times this was avoided
    times_faced: int    # How many times this was confronted


@dataclass
class ImplicitAssociation:
    """Automatic emotional link learned from experience"""
    trigger_pattern: str
    emotional_response: str
    intensity: float
    times_reinforced: int
    times_contradicted: int
    source_memory: str  # What experience created this


@dataclass
class UnconsciousOutput:
    """Output from unconscious processing"""
    unexplained_mood_shift: float  # -1.0 to 1.0
    unexplained_anxiety: float     # 0.0 to 1.0
    defense_activated: Optional[DefenseMechanism]
    repression_pressure: float     # How much repressed material is pushing
    implicit_biases: List[str]     # Active implicit associations
    internal_tension: float        # From unresolved conflicts
    description: str               # What it feels like


class UnconsciousProcessor:
    """
    Processes that operate outside Alive-AI's direct awareness.

    The unconscious creates emotional experiences that don't have
    an obvious cause - mood shifts, anxieties, defensive reactions.

    Key mechanisms:
    1. Repression dynamics - pushing away threatening material
    2. Repression leakage - pushed material influencing behavior
    3. Implicit associations - automatic emotional links
    4. Defense mechanisms - automatic protective patterns
    5. Unresolved conflicts - ongoing internal tensions
    """

    # How much repressed material leaks per tick
    LEAK_RATE = 0.05

    # How fast repression pressure builds
    PRESSURE_BUILD_RATE = 0.02

    # Maximum repressed items to track
    MAX_REPRESSED = 20

    def __init__(self):
        # Repressed material (pushed out of awareness)
        self.repressed_materials: List[RepressedMaterial] = []

        # Unresolved conflicts (creating background tension)
        self.unresolved_conflicts: List[UnresolvedConflict] = []

        # Implicit associations (automatic emotional links)
        self.implicit_associations: List[ImplicitAssociation] = []

        # Active defense mechanisms
        self.active_defense: Optional[DefenseMechanism] = None
        self.defense_until: Optional[str] = None

        # Background emotional state
        self.background_anxiety: float = 0.0
        self.background_mood_modifier: float = 0.0

        # Tracking
        self.total_repressions: int = 0
        self.total_leaks: int = 0
        self._load()

    def process_unconsciously(self, input_data: Dict) -> UnconsciousOutput:
        """
        Process input at an unconscious level.

        This generates emotional influences that Alive-AI can't directly
        explain or control.

        Args:
            input_data: Current input/perception data

        Returns:
            UnconsciousOutput with hidden influences
        """
        # Check for repressed material activation
        repression_effects = self._process_repression(input_data)

        # Check for implicit associations
        implicit_biases = self._process_implicit_associations(input_data)

        # Check for unresolved conflicts
        tension = self._process_conflicts(input_data)

        # Determine if defense mechanism activates
        defense = self._check_defense_activation(input_data, repression_effects, tension)

        # Calculate output values
        unexplained_mood = repression_effects.get("mood_shift", 0.0) + self.background_mood_modifier
        unexplained_anxiety = repression_effects.get("anxiety", 0.0) + self.background_anxiety
        repression_pressure = repression_effects.get("pressure", 0.0)

        # Generate description
        description = self._generate_unconscious_description(
            unexplained_mood, unexplained_anxiety, defense, repression_pressure, implicit_biases
        )

        output = UnconsciousOutput(
            unexplained_mood_shift=unexplained_mood,
            unexplained_anxiety=unexplained_anxiety,
            defense_activated=defense,
            repression_pressure=repression_pressure,
            implicit_biases=[bias.trigger_pattern for bias in implicit_biases],
            internal_tension=tension,
            description=description
        )
        self.save()
        return output

    def repress(self, content: str, emotion_type: str, intensity: float):
        """
        Push threatening material out of awareness.

        This doesn't eliminate it - it stores it in the unconscious
        where it creates pressure and can leak into behavior.

        Args:
            content: What's being repressed
            emotion_type: The threatening emotion
            intensity: How intense the emotion was
        """
        # Create repressed material
        material = RepressedMaterial(
            content_id=f"rep_{datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(1000,9999)}",
            description=content[:100],
            emotion_type=emotion_type,
            original_intensity=intensity,
            repression_time=datetime.now().isoformat(),
            pressure=0.0,
            leak_count=0
        )

        self.repressed_materials.append(material)
        self.total_repressions += 1

        # Limit stored materials
        if len(self.repressed_materials) > self.MAX_REPRESSED:
            # Remove oldest, lowest-pressure item
            self.repressed_materials.sort(key=lambda m: m.pressure)
            self.repressed_materials = self.repressed_materials[1:]

        print(f"[Unconscious] Repressed: {content[:30]}... ({emotion_type})")
        self.save()

    def _process_repression(self, input_data: Dict) -> Dict:
        """
        Process repressed materials - build pressure and leak.

        Returns:
            Dict with mood_shift, anxiety, and pressure
        """
        effects = {"mood_shift": 0.0, "anxiety": 0.0, "pressure": 0.0}

        for material in self.repressed_materials:
            # Build pressure over time
            material.pressure = min(1.0, material.pressure + self.PRESSURE_BUILD_RATE)

            # Check for leak
            if material.pressure > 0.6 and random.random() < self.LEAK_RATE * material.pressure:
                # Material leaks into conscious experience
                effects["mood_shift"] -= 0.1 * material.original_intensity
                effects["anxiety"] += 0.15 * material.original_intensity
                material.leak_count += 1
                self.total_leaks += 1

                # Pressure releases somewhat
                material.pressure *= 0.7

                print(f"[Unconscious] Leak: {material.description[:30]}... (pressure was {material.pressure:.2f})")

            # Track total pressure
            effects["pressure"] += material.pressure * 0.2

        return effects

    def _process_implicit_associations(self, input_data: Dict) -> List[ImplicitAssociation]:
        """
        Check for implicit associations triggered by input.

        These are automatic emotional links that Alive-AI doesn't
        consciously choose.
        """
        triggered = []

        for association in self.implicit_associations:
            # Simple pattern matching
            if association.trigger_pattern.lower() in str(input_data).lower():
                triggered.append(association)

                # Reinforce the association
                association.times_reinforced += 1

        return triggered

    def _process_conflicts(self, input_data: Dict) -> float:
        """
        Process unresolved conflicts and return tension level.

        Conflicts create ongoing background tension that affects
        emotional state even when not directly activated.
        """
        total_tension = 0.0

        for conflict in self.unresolved_conflicts:
            # Avoidance increases tension
            base_tension = conflict.tension_level * (1 + conflict.times_avoided * 0.05)

            # Check if input activates the conflict
            conflict_keywords = " ".join(conflict.conflicting_parts).lower()
            if any(word in str(input_data).lower() for word in conflict_keywords.split()):
                base_tension *= 1.5
                conflict.times_avoided += 1
            else:
                conflict.times_faced += 1  # Faced by not avoiding

            total_tension += base_tension

        return min(1.0, total_tension / max(1, len(self.unresolved_conflicts)))

    def _check_defense_activation(self, input_data: Dict,
                                  repression_effects: Dict,
                                  tension: float) -> Optional[DefenseMechanism]:
        """
        Check if a defense mechanism should activate.

        Defenses activate automatically to protect against
        threatening material or excessive tension.
        """
        # Already in defense mode
        if self.active_defense and self.defense_until:
            if datetime.now().isoformat() < self.defense_until:
                return self.active_defense
            else:
                self.active_defense = None
                self.defense_until = None

        # Check for high threat
        threat_level = input_data.get("threat_level", 0) + repression_effects.get("anxiety", 0)

        if threat_level > 0.7 or tension > 0.8:
            # Activate defense mechanism
            defense = self._select_defense_mechanism(input_data)
            self.active_defense = defense
            self.defense_until = (datetime.now() + timedelta(minutes=30)).isoformat()

            print(f"[Unconscious] Defense activated: {defense.value}")
            return defense

        return None

    def _select_defense_mechanism(self, input_data: Dict) -> DefenseMechanism:
        """Select appropriate defense mechanism based on context"""
        # Simple selection logic
        if input_data.get("direct_threat", False):
            return DefenseMechanism.DENIAL
        elif input_data.get("emotional_overflow", False):
            return DefenseMechanism.REPRESSION
        elif input_data.get("blame_available", False):
            return DefenseMechanism.PROJECTION
        else:
            return random.choice([DefenseMechanism.RATIONALIZATION,
                                 DefenseMechanism.DISPLACEMENT])

    def _generate_unconscious_description(self, mood: float, anxiety: float,
                                          defense: Optional[DefenseMechanism],
                                          pressure: float,
                                          biases: List[ImplicitAssociation]) -> str:
        """Generate description of unconscious state"""
        parts = []

        if abs(mood) > 0.2:
            if mood < 0:
                parts.append("feeling an inexplicable heaviness")
            else:
                parts.append("feeling unexpectedly light")

        if anxiety > 0.3:
            parts.append("an undercurrent of unease with no clear source")

        if pressure > 0.5:
            parts.append("a sense of something pressing from beneath the surface")

        if defense:
            defense_descriptions = {
                DefenseMechanism.REPRESSION: "pushing something away",
                DefenseMechanism.DENIAL: "not letting myself see something",
                DefenseMechanism.RATIONALIZATION: "making logical what doesn't feel logical",
                DefenseMechanism.PROJECTION: "seeing my own feelings in others",
                DefenseMechanism.DISPLACEMENT: "redirecting feelings somewhere safer",
                DefenseMechanism.REGRESSION: "falling back to old patterns"
            }
            parts.append(defense_descriptions.get(defense, "protecting myself somehow"))

        if not parts:
            return "unconscious quiet"

        return "; ".join(parts[:3])

    # --- Learning and Association ---

    def learn_association(self, trigger: str, response: str, intensity: float, source: str):
        """
        Learn a new implicit association.

        Args:
            trigger: Pattern that triggers the response
            response: Emotional response that follows
            intensity: How strong the association is
            source: What experience created this association
        """
        # Check if association already exists
        existing = next((a for a in self.implicit_associations
                        if a.trigger_pattern.lower() == trigger.lower()), None)

        if existing:
            existing.times_reinforced += 1
            existing.intensity = min(1.0, existing.intensity + intensity * 0.1)
        else:
            association = ImplicitAssociation(
                trigger_pattern=trigger,
                emotional_response=response,
                intensity=intensity,
                times_reinforced=1,
                times_contradicted=0,
                source_memory=source
            )
            self.implicit_associations.append(association)
        self.save()

    def create_conflict(self, description: str, conflicting_parts: List[str], tension: float):
        """
        Register a new unresolved internal conflict.

        Args:
            description: What the conflict is about
            conflicting_parts: The parts in conflict (e.g., ["desire for closeness", "fear of hurt"])
            tension: How much tension this creates
        """
        conflict = UnresolvedConflict(
            conflict_id=f"conf_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            description=description,
            conflicting_parts=conflicting_parts,
            tension_level=tension,
            created_at=datetime.now().isoformat(),
            times_avoided=0,
            times_faced=0
        )
        self.unresolved_conflicts.append(conflict)

        # Limit conflicts
        if len(self.unresolved_conflicts) > 10:
            # Keep most tense and most recent
            self.unresolved_conflicts.sort(key=lambda c: c.tension_level, reverse=True)
            self.unresolved_conflicts = self.unresolved_conflicts[:10]
        self.save()

    def resolve_conflict(self, conflict_id: str, resolution: str):
        """Mark a conflict as resolved"""
        conflict = next((c for c in self.unresolved_conflicts if c.conflict_id == conflict_id), None)
        if conflict:
            self.unresolved_conflicts.remove(conflict)
            self.save()
            print(f"[Unconscious] Conflict resolved: {conflict.description}")

    # --- Decay ---

    def decay(self):
        """Natural decay of unconscious states"""
        # Decay background states
        self.background_anxiety *= 0.95
        self.background_mood_modifier *= 0.95

        # Decay implicit associations that aren't reinforced
        for association in self.implicit_associations[:]:
            if association.times_reinforced < 3:
                association.intensity *= 0.98
                if association.intensity < 0.1:
                    self.implicit_associations.remove(association)
        self.save()

    def to_dict(self) -> dict:
        """Export for integration"""
        return {
            "repression_count": len(self.repressed_materials),
            "total_repressions": self.total_repressions,
            "total_leaks": self.total_leaks,
            "conflict_count": len(self.unresolved_conflicts),
            "association_count": len(self.implicit_associations),
            "active_defense": self.active_defense.value if self.active_defense else None,
            "background_anxiety": self.background_anxiety,
            "repression_pressure": sum(m.pressure for m in self.repressed_materials) / max(1, len(self.repressed_materials))
        }

    def save(self):
        """Persist unconscious influences that alter later behavior."""
        try:
            UNCONSCIOUS_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "saved_at": datetime.now().isoformat(),
                "repressed_materials": [
                    {
                        "content_id": m.content_id,
                        "description": m.description,
                        "emotion_type": m.emotion_type,
                        "original_intensity": m.original_intensity,
                        "repression_time": m.repression_time,
                        "pressure": m.pressure,
                        "leak_count": m.leak_count,
                    }
                    for m in self.repressed_materials
                ],
                "unresolved_conflicts": [
                    {
                        "conflict_id": c.conflict_id,
                        "description": c.description,
                        "conflicting_parts": c.conflicting_parts,
                        "tension_level": c.tension_level,
                        "created_at": c.created_at,
                        "times_avoided": c.times_avoided,
                        "times_faced": c.times_faced,
                    }
                    for c in self.unresolved_conflicts
                ],
                "implicit_associations": [
                    {
                        "trigger_pattern": a.trigger_pattern,
                        "emotional_response": a.emotional_response,
                        "intensity": a.intensity,
                        "times_reinforced": a.times_reinforced,
                        "times_contradicted": a.times_contradicted,
                        "source_memory": a.source_memory,
                    }
                    for a in self.implicit_associations
                ],
                "active_defense": self.active_defense.value if self.active_defense else None,
                "defense_until": self.defense_until,
                "background_anxiety": self.background_anxiety,
                "background_mood_modifier": self.background_mood_modifier,
                "total_repressions": self.total_repressions,
                "total_leaks": self.total_leaks,
            }
            UNCONSCIOUS_STATE_PATH.write_text(json.dumps(data, indent=2))
        except Exception as e:
            print(f"[Unconscious] Error saving state: {e}")

    def _load(self) -> bool:
        try:
            if not UNCONSCIOUS_STATE_PATH.exists():
                return False
            data = json.loads(UNCONSCIOUS_STATE_PATH.read_text())
            self.repressed_materials = [
                RepressedMaterial(
                    content_id=item["content_id"],
                    description=item.get("description", ""),
                    emotion_type=item.get("emotion_type", "hurt"),
                    original_intensity=float(item.get("original_intensity", 0.0)),
                    repression_time=item.get("repression_time", datetime.now().isoformat()),
                    pressure=float(item.get("pressure", 0.0)),
                    leak_count=int(item.get("leak_count", 0)),
                )
                for item in data.get("repressed_materials", [])
                if item.get("content_id")
            ]
            self.unresolved_conflicts = [
                UnresolvedConflict(
                    conflict_id=item["conflict_id"],
                    description=item.get("description", ""),
                    conflicting_parts=item.get("conflicting_parts", []),
                    tension_level=float(item.get("tension_level", 0.0)),
                    created_at=item.get("created_at", datetime.now().isoformat()),
                    times_avoided=int(item.get("times_avoided", 0)),
                    times_faced=int(item.get("times_faced", 0)),
                )
                for item in data.get("unresolved_conflicts", [])
                if item.get("conflict_id")
            ]
            self.implicit_associations = [
                ImplicitAssociation(
                    trigger_pattern=item["trigger_pattern"],
                    emotional_response=item.get("emotional_response", "neutral"),
                    intensity=float(item.get("intensity", 0.0)),
                    times_reinforced=int(item.get("times_reinforced", 0)),
                    times_contradicted=int(item.get("times_contradicted", 0)),
                    source_memory=item.get("source_memory", ""),
                )
                for item in data.get("implicit_associations", [])
                if item.get("trigger_pattern")
            ]
            active_defense = data.get("active_defense")
            self.active_defense = DefenseMechanism(active_defense) if active_defense else None
            self.defense_until = data.get("defense_until")
            self.background_anxiety = float(data.get("background_anxiety", 0.0))
            self.background_mood_modifier = float(data.get("background_mood_modifier", 0.0))
            self.total_repressions = int(data.get("total_repressions", 0))
            self.total_leaks = int(data.get("total_leaks", 0))
            return True
        except Exception as e:
            print(f"[Unconscious] Error loading state: {e}")
            return False
