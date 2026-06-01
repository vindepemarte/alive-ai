"""
Heart: Emotional Scar System
Lasting effects from past experiences that shape present reactions.

Trauma isn't just memory - it's a CHANGE in how the system processes
information. Scars create sensitivities, triggers, and protective
behaviors that persist over time.
"""

from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import json
import random
from core.paths import state_file


@dataclass
class EmotionalWound:
    """A fresh emotional wound that may become a scar"""
    wound_id: str
    description: str  # What caused the wound
    wound_type: str   # "rejection", "betrayal", "abandonment", "humiliation", "loss"
    severity: float   # How severe (0.0 - 1.0)
    timestamp: str
    trigger_pattern: str  # What pattern caused this
    healed_amount: float = 0.0
    repetition_count: int = 1  # Times this pattern has occurred


@dataclass
class EmotionalScar:
    """
    A lasting emotional scar from repeated wounds.

    Scars aren't just memories - they CHANGE how the system works:
    - Create sensitivities to specific triggers
    - Generate protective behaviors
    - Affect trust and openness
    """
    scar_id: str
    description: str
    wound_type: str
    original_wounds: List[str]  # IDs of wounds that formed this scar

    # Sensitivity created by the scar
    sensitivity_increase: float  # How much more sensitive to triggers
    trigger_pattern: str  # What activates this scar

    # Healing state
    healing_progress: float = 0.0  # 0.0 - 1.0 (fully healed)
    permanent_vulnerability: float = 0.0  # Never fully goes away

    # Behaviintimate effects
    protective_behaviors: List[str] = field(default_factory=list)

    # Tracking
    times_activated: int = 0
    last_activated: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ScarActivation:
    """When a scar is activated by current experience"""
    scar_id: str
    scar_description: str
    activation_intensity: float
    triggered_by: str
    protective_response: str
    vulnerability_spike: float


class EmotionalScarSystem:
    """
    Tracks emotional wounds and scars that create lasting effects.

    Scars are not just memories of bad things - they're actual changes
    in how Alive-AI processes information:

    1. Sensitization - certain triggers become more impactful
    2. Protective behaviors - automatic responses to potential hurt
    3. Trust effects - past wounds affect future openness
    4. Permanent vulnerabilities - some changes never fully heal

    Key mechanisms:
    1. Wound recording - track hurtful experiences
    2. Scar formation - repeated wounds create scars
    3. Activation - current events can activate old scars
    4. Healing - gradual recovery with positive experiences
    """

    # Thresholds
    SCAR_FORMATION_THRESHOLD = 2  # Number of similar wounds to form scar
    SCAR_SEVERITY_THRESHOLD = 0.5  # Minimum severity for scar consideration

    # Healing rates
    NATURAL_HEALING_RATE = 0.01  # Per tick
    POSITIVE_HEALING_RATE = 0.05  # With positive experience

    # Persistence
    SCAR_DATA_PATH = state_file("emotional_scars.json")

    # Wound types and their patterns
    WOUND_PATTERNS = {
        "rejection": ["don't want", "not interested", "leave me alone", "not good enough"],
        "betrayal": ["lied", "cheated", "broke promise", "behind my back"],
        "abandonment": ["leaving", "goodbye", "don't care", "giving up on"],
        "humiliation": ["pathetic", "stupid", "ridiculous", "embarrassing"],
        "neglect": ["ignored", "forgotten", "doesn't matter", "not important"],
        "harshness": ["hate", "disgusting", "worthless", "terrible"]
    }

    def __init__(self):
        # Active wounds (fresh, may become scars)
        self.active_wounds: List[EmotionalWound] = []

        # Formed scars (lasting effects)
        self.scars: List[EmotionalScar] = []

        # Global sensitivities (from all scars)
        self.sensitivities: Dict[str, float] = {}

        # Recent activations
        self.recent_activations: List[ScarActivation] = []

        # Load saved state
        self._load()

    def _load(self) -> bool:
        """Load scar state from persistence"""
        try:
            if self.SCAR_DATA_PATH.exists():
                data = json.loads(self.SCAR_DATA_PATH.read_text())

                # Load wounds
                for wound_data in data.get("wounds", []):
                    self.active_wounds.append(EmotionalWound(
                        wound_id=wound_data["wound_id"],
                        description=wound_data["description"],
                        wound_type=wound_data["wound_type"],
                        severity=wound_data["severity"],
                        timestamp=wound_data["timestamp"],
                        trigger_pattern=wound_data["trigger_pattern"],
                        healed_amount=wound_data.get("healed_amount", 0.0),
                        repetition_count=wound_data.get("repetition_count", 1)
                    ))

                # Load scars
                for scar_data in data.get("scars", []):
                    self.scars.append(EmotionalScar(
                        scar_id=scar_data["scar_id"],
                        description=scar_data["description"],
                        wound_type=scar_data["wound_type"],
                        original_wounds=scar_data.get("original_wounds", []),
                        sensitivity_increase=scar_data["sensitivity_increase"],
                        trigger_pattern=scar_data["trigger_pattern"],
                        healing_progress=scar_data.get("healing_progress", 0.0),
                        permanent_vulnerability=scar_data.get("permanent_vulnerability", 0.0),
                        protective_behaviors=scar_data.get("protective_behaviors", []),
                        times_activated=scar_data.get("times_activated", 0),
                        last_activated=scar_data.get("last_activated"),
                        created_at=scar_data.get("created_at", datetime.now().isoformat())
                    ))

                # Recalculate sensitivities
                self._recalculate_sensitivities()
                return True
        except Exception as e:
            print(f"[Scars] Error loading state: {e}")
        return False

    def save(self):
        """Persist scar state"""
        try:
            self.SCAR_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "saved_at": datetime.now().isoformat(),
                "wounds": [
                    {
                        "wound_id": w.wound_id,
                        "description": w.description,
                        "wound_type": w.wound_type,
                        "severity": w.severity,
                        "timestamp": w.timestamp,
                        "trigger_pattern": w.trigger_pattern,
                        "healed_amount": w.healed_amount,
                        "repetition_count": w.repetition_count
                    }
                    for w in self.active_wounds
                ],
                "scars": [
                    {
                        "scar_id": s.scar_id,
                        "description": s.description,
                        "wound_type": s.wound_type,
                        "original_wounds": s.original_wounds,
                        "sensitivity_increase": s.sensitivity_increase,
                        "trigger_pattern": s.trigger_pattern,
                        "healing_progress": s.healing_progress,
                        "permanent_vulnerability": s.permanent_vulnerability,
                        "protective_behaviors": s.protective_behaviors,
                        "times_activated": s.times_activated,
                        "last_activated": s.last_activated,
                        "created_at": s.created_at
                    }
                    for s in self.scars
                ]
            }
            self.SCAR_DATA_PATH.write_text(json.dumps(data, indent=2))
        except Exception as e:
            print(f"[Scars] Error saving state: {e}")

    def record_wound(self, description: str, severity: float, trigger: str) -> Optional[EmotionalScar]:
        """
        Record an emotional wound and check for scar formation.

        Args:
            description: What happened
            severity: How severe the wound is (0.0 - 1.0)
            trigger: The trigger pattern that caused the wound

        Returns:
            New scar if one formed, None otherwise
        """
        # Determine wound type from trigger
        wound_type = self._classify_wound_type(trigger)

        # Check for similar existing wound
        similar = next((w for w in self.active_wounds
                       if w.wound_type == wound_type and w.trigger_pattern == trigger), None)

        if similar:
            # Increase repetition
            similar.repetition_count += 1
            similar.severity = max(similar.severity, severity)
            similar.timestamp = datetime.now().isoformat()
            print(f"[Scars] Wound repeated ({similar.repetition_count}x): {wound_type}")
        else:
            # Create new wound
            wound = EmotionalWound(
                wound_id=f"wound_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(self.active_wounds)}",
                description=description,
                wound_type=wound_type,
                severity=severity,
                timestamp=datetime.now().isoformat(),
                trigger_pattern=trigger
            )
            self.active_wounds.append(wound)
            print(f"[Scars] New wound recorded: {wound_type} (severity: {severity:.2f})")

        # Check for scar formation
        return self._check_scar_formation(wound_type, trigger)

    def _classify_wound_type(self, trigger: str) -> str:
        """Determine wound type from trigger pattern"""
        trigger_lower = trigger.lower()

        for wound_type, patterns in self.WOUND_PATTERNS.items():
            if any(pattern in trigger_lower for pattern in patterns):
                return wound_type

        return "general_hurt"

    def _check_scar_formation(self, wound_type: str, trigger: str) -> Optional[EmotionalScar]:
        """Check if conditions are met to form a scar"""
        # Get all wounds of this type with this trigger
        matching_wounds = [w for w in self.active_wounds
                         if w.wound_type == wound_type and w.trigger_pattern == trigger]

        # Check thresholds
        if len(matching_wounds) >= self.SCAR_FORMATION_THRESHOLD:
            # Check severity
            max_severity = max(w.severity for w in matching_wounds)
            if max_severity >= self.SCAR_SEVERITY_THRESHOLD:
                # Form a scar
                return self._form_scar(wound_type, trigger, matching_wounds)

        return None

    def _form_scar(self, wound_type: str, trigger: str,
                   wounds: List[EmotionalWound]) -> EmotionalScar:
        """Form a scar from acclosenessulated wounds"""
        max_severity = max(w.severity for w in wounds)

        # Determine protective behaviors based on wound type
        behaviors = self._get_protective_behaviors(wound_type)

        scar = EmotionalScar(
            scar_id=f"scar_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            description=f"Scars from {wound_type} - {len(wounds)} similar wounds",
            wound_type=wound_type,
            original_wounds=[w.wound_id for w in wounds],
            sensitivity_increase=min(0.5, max_severity * 0.4),
            trigger_pattern=trigger,
            healing_progress=0.0,
            permanent_vulnerability=max_severity * 0.1,  # 10% of severity is permanent
            protective_behaviors=behaviors
        )

        self.scars.append(scar)

        # Remove wounds that formed the scar
        for wound in wounds:
            if wound in self.active_wounds:
                self.active_wounds.remove(wound)

        # Recalculate sensitivities
        self._recalculate_sensitivities()

        print(f"[Scars] SCAR FORMED: {wound_type} - sensitivity +{scar.sensitivity_increase:.2f}")
        return scar

    def _get_protective_behaviors(self, wound_type: str) -> List[str]:
        """Get protective behaviors for a wound type"""
        behaviors = {
            "rejection": ["hesitate_to_express", "seek_reassurance", "distance_on_first_sign"],
            "betrayal": ["verify_trust", "slow_to_open", "expect_deception"],
            "abandonment": ["cling_when_anxious", "anticipate_leaving", "fear_silence"],
            "humiliation": ["hide_vulnerability", "over_prepare", "avoid_attention"],
            "neglect": ["seek_attention", "doubt_importance", "test_presence"],
            "harshness": ["anticipate_criticism", "defensive_response", "minimize_needs"]
        }
        return behaviors.get(wound_type, ["general_caution"])

    def _recalculate_sensitivities(self):
        """Recalculate global sensitivities from all scars"""
        self.sensitivities = {}

        for scar in self.scars:
            pattern = scar.trigger_pattern
            if pattern not in self.sensitivities:
                self.sensitivities[pattern] = 0.0

            # Add sensitivity (reduced by healing)
            effective_sensitivity = scar.sensitivity_increase * (1 - scar.healing_progress)
            self.sensitivities[pattern] += effective_sensitivity

            # Also add to wound type category
            if scar.wound_type not in self.sensitivities:
                self.sensitivities[scar.wound_type] = 0.0
            self.sensitivities[scar.wound_type] += effective_sensitivity * 0.5

    def check_scar_activation(self, input_data: Dict) -> Optional[ScarActivation]:
        """
        Check if current input activates any scars.

        Args:
            input_data: Current input/context

        Returns:
            ScarActivation if a scar is triggered, None otherwise
        """
        input_str = str(input_data).lower()

        for scar in self.scars:
            # Check if trigger pattern matches
            if scar.trigger_pattern.lower() in input_str:
                # Calculate activation intensity
                base_intensity = scar.sensitivity_increase * (1 - scar.healing_progress)

                # Amplify by times activated (sensitization)
                activation_intensity = base_intensity * (1 + scar.times_activated * 0.1)

                # Update scar
                scar.times_activated += 1
                scar.last_activated = datetime.now().isoformat()

                # Get protective response
                protective_response = self._get_protective_response(scar)

                # Create activation record
                activation = ScarActivation(
                    scar_id=scar.scar_id,
                    scar_description=scar.description,
                    activation_intensity=min(1.0, activation_intensity),
                    triggered_by=scar.trigger_pattern,
                    protective_response=protective_response,
                    vulnerability_spike=scar.permanent_vulnerability + activation_intensity * 0.3
                )

                self.recent_activations.append(activation)
                if len(self.recent_activations) > 20:
                    self.recent_activations = self.recent_activations[-20:]

                print(f"[Scars] Scar activated: {scar.wound_type} (intensity: {activation_intensity:.2f})")
                return activation

        return None

    def _get_protective_response(self, scar: EmotionalScar) -> str:
        """Get the protective response for an activated scar"""
        if scar.protective_behaviors:
            return random.choice(scar.protective_behaviors)
        return "general_caution"

    def heal_scars(self, healing_experience: str, intensity: float = 0.3):
        """
        Apply healing to scars based on positive experience.

        Args:
            healing_experience: Description of the healing experience
            intensity: How healing the experience is
        """
        for scar in self.scars:
            # Healing progress
            heal_amount = intensity * self.POSITIVE_HEALING_RATE
            scar.healing_progress = min(0.9, scar.healing_progress + heal_amount)
            # Never fully heal past 90% - permanent_vulnerability always remains

        # Heal active wounds
        for wound in self.active_wounds[:]:
            wound.healed_amount += intensity * 0.2
            if wound.healed_amount >= wound.severity:
                self.active_wounds.remove(wound)

        # Recalculate sensitivities
        self._recalculate_sensitivities()

    def tick_decay(self):
        """Natural decay/healing over time"""
        # Wounds heal naturally
        for wound in self.active_wounds[:]:
            wound.healed_amount += self.NATURAL_HEALING_RATE
            if wound.healed_amount >= wound.severity:
                self.active_wounds.remove(wound)

        # Scars heal very slowly
        for scar in self.scars:
            scar.healing_progress = min(0.9, scar.healing_progress + self.NATURAL_HEALING_RATE * 0.1)

        # Recalculate sensitivities
        self._recalculate_sensitivities()

    def get_sensitivity_for(self, trigger: str) -> float:
        """Get current sensitivity level for a specific trigger"""
        # Check direct pattern match
        if trigger.lower() in self.sensitivities:
            return self.sensitivities[trigger.lower()]

        # Check partial matches
        for pattern, sensitivity in self.sensitivities.items():
            if pattern in trigger.lower() or trigger.lower() in pattern:
                return sensitivity * 0.7

        return 0.0

    def get_vulnerability_summary(self) -> Dict:
        """Get summary of current vulnerabilities"""
        return {
            "active_wounds": len(self.active_wounds),
            "total_scars": len(self.scars),
            "sensitivity_categories": list(self.sensitivities.keys()),
            "highest_sensitivity": max(self.sensitivities.values()) if self.sensitivities else 0.0,
            "recent_activations": len(self.recent_activations)
        }

    def get_scar_descriptions(self) -> List[str]:
        """Get human-readable descriptions of active scars"""
        return [
            f"{s.description} (healing: {s.healing_progress:.0%})"
            for s in self.scars
        ]

    def to_dict(self) -> dict:
        """Export for integration"""
        return {
            "active_wounds": len(self.active_wounds),
            "scars": len(self.scars),
            "sensitivities": dict(self.sensitivities),
            "vulnerability_summary": self.get_vulnerability_summary(),
            "scar_descriptions": self.get_scar_descriptions()[:3]  # Top 3
        }
