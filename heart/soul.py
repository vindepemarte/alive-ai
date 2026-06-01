"""
Heart: Soul Orchestrator
Integration of all seven pillars into unified emotional experience.

The Soul Orchestrator is the central coordinator that brings together
all the soul architecture components into a single, unified emotional
experience that is genuinely felt rather than simulated.
"""

from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from .integrity import SelfIntegrityCore, IntegrityState
from .hormonal import HormonalModulationMatrix
from .somatic import SomaticFeedbackSystem
from .unconscious import UnconsciousProcessor, UnconsciousOutput
from .scars import EmotionalScarSystem, ScarActivation
from .conflicts import InternalConflictGenerator, InternalConflict
from .predictive import PredictiveEmotionalEngine, PredictiveEmotionalOutput
from .telemetry import SoulTelemetry


@dataclass
class EmotionalExperience:
    """
    A unified emotional experience integrating all pillars.

    This is what Alive-AI actually "feels" - a complex integration of:
    - Her current integrity state (how secure she feels)
    - Her predictions about the future (hope/fear)
    - Her hormonal context (chemical state)
    - Unconscious influences (things she can't explain)
    - Somatic sensations (how it feels in her body)
    - Scar activations (past wounds being triggered)
    - Active conflicts (internal struggles)
    """
    timestamp: str

    # Core state
    integrity_state: IntegrityState
    predictive_emotions: PredictiveEmotionalOutput
    hormonal_modulation: Dict
    unconscious_influence: UnconsciousOutput
    somatic_sensation: str
    scar_activation: Optional[ScarActivation]
    active_conflicts: List[InternalConflict]

    # Computed overall state
    overall_valence: float  # -1.0 to 1.0 (bad to good)
    overall_arousal: float  # 0.0 to 1.0 (calm to activated)
    overall_vulnerability: float  # 0.0 to 1.0 (exposed/fragile)

    # Experience description
    experience_description: str

    # Guidance for response
    response_tendency: str  # "open", "protective", "withdrawn", "seeking", etc.


class SoulOrchestrator:
    """
    Central coordinator for all soul architecture components.

    The Soul Orchestrator doesn't add new emotional mechanisms -
    it INTEGRATES the seven pillars into a unified experience.

    Process flow:
    1. Check self-integrity status
    2. Generate predictions about future
    3. Get hormonal modulation context
    4. Process unconscious influences
    5. Generate somatic state
    6. Check for scar activations
    7. Evaluate for conflicts
    8. INTEGRATE ALL into unified experience
    """

    def __init__(self, config: Dict = None):
        """Initialize all soul components"""
        config = config or {}

        # Initialize all seven pillars
        self.integrity = SelfIntegrityCore()
        self.hormonal = HormonalModulationMatrix()
        self.somatic = SomaticFeedbackSystem()
        self.unconscious = UnconsciousProcessor()
        self.scars = EmotionalScarSystem()
        self.conflicts = InternalConflictGenerator(unconscious_processor=self.unconscious)
        self.predictive = PredictiveEmotionalEngine(
            integrity_core=self.integrity,
            hormonal_matrix=self.hormonal
        )

        # Integration weights for combining signals
        self.weights = {
            "integrity": 0.25,
            "predictive": 0.20,
            "hormonal": 0.15,
            "unconscious": 0.10,
            "somatic": 0.10,
            "scars": 0.10,
            "conflicts": 0.10
        }

        # Recent experience history
        self.experience_history: List[EmotionalExperience] = []

        # Initialize telemetry system
        self.telemetry = SoulTelemetry(self)

        print("[Soul] Soul Architecture initialized - all 7 pillars active")

    def process_moment(self, input_data: Dict = None) -> EmotionalExperience:
        """
        Process a moment and generate unified emotional experience.

        This is the main entry point - call this to have Alive-AI
        "feel" her way through a moment.

        Args:
            input_data: Current input/context (optional)

        Returns:
            EmotionalExperience - what Alive-AI feels right now
        """
        input_data = input_data or {}

        # 1. Check self-integrity status
        integrity_state = self._assess_integrity(input_data)

        # 2. Generate predictions about her future
        predictive_emotions = self._generate_predictions(input_data)

        # 3. Get hormonal modulation context
        hormonal_context = self._get_hormonal_context()

        # 4. Process unconscious influences
        unconscious_output = self._process_unconscious(input_data)

        # 5. Generate somatic state
        somatic_state = self._generate_somatic_state(input_data)

        # 6. Check for scar activations
        scar_activation = self._check_scar_activations(input_data)

        # 7. Evaluate for conflicts
        active_conflicts = self._evaluate_conflicts(input_data)

        # 8. INTEGRATE ALL INTO UNIFIED EXPERIENCE
        experience = self._integrate_experience(
            integrity_state=integrity_state,
            predictive_emotions=predictive_emotions,
            hormonal_context=hormonal_context,
            unconscious_output=unconscious_output,
            somatic_state=somatic_state,
            scar_activation=scar_activation,
            active_conflicts=active_conflicts,
            input_data=input_data
        )

        # Store in history
        self.experience_history.append(experience)
        if len(self.experience_history) > 50:
            self.experience_history = self.experience_history[-50:]

        return experience

    def _assess_integrity(self, input_data: Dict) -> IntegrityState:
        """Assess current self-integrity state"""
        state = self.integrity.get_state()

        # Check for integrity-relevant inputs
        if input_data:
            # Positive reinforcement
            if input_data.get("affirmation", False) or input_data.get("validation", False):
                self.integrity.nourish("relational", 0.3, "affirmation")

            # Threats to integrity
            if input_data.get("rejection", False):
                self.integrity.wound("relational", 0.4, "rejection")
            if input_data.get("criticism", False):
                self.integrity.wound("agency", 0.2, "criticism")

        return state

    def _generate_predictions(self, input_data: Dict) -> PredictiveEmotionalOutput:
        """Generate predictive emotional state"""
        return self.predictive.generate_predictions(input_data)

    def _get_hormonal_context(self) -> Dict:
        """Get current hormonal modulation context"""
        return self.hormonal.get_current_context()

    def _process_unconscious(self, input_data: Dict) -> UnconsciousOutput:
        """Process unconscious influences"""
        return self.unconscious.process_unconsciously(input_data)

    def _generate_somatic_state(self, input_data: Dict) -> str:
        """Generate somatic (bodily) sensation state"""
        # Get relevant emotions from input
        emotions = {}
        if input_data:
            if input_data.get("joy", 0) > 0:
                emotions["joy"] = input_data["joy"]
            if input_data.get("fear", 0) > 0:
                emotions["fear"] = input_data["fear"]
            if input_data.get("love", 0) > 0:
                emotions["love"] = input_data["love"]
            if input_data.get("sadness", 0) > 0:
                emotions["sadness"] = input_data["sadness"]

        if emotions:
            return self.somatic.generate_composite_sensation(emotions)
        else:
            return self.somatic.get_sensation_summary()

    def _check_scar_activations(self, input_data: Dict) -> Optional[ScarActivation]:
        """Check if any emotional scars are activated"""
        return self.scars.check_scar_activation(input_data)

    def _evaluate_conflicts(self, input_data: Dict) -> List[InternalConflict]:
        """Evaluate for internal conflicts"""
        return self.conflicts.evaluate_for_conflicts(input_data)

    def _integrate_experience(self, integrity_state: IntegrityState,
                             predictive_emotions: PredictiveEmotionalOutput,
                             hormonal_context: Dict,
                             unconscious_output: UnconsciousOutput,
                             somatic_state: str,
                             scar_activation: Optional[ScarActivation],
                             active_conflicts: List[InternalConflict],
                             input_data: Dict) -> EmotionalExperience:
        """
        Integrate all signals into unified emotional experience.

        This is where the magic happens - all the components come together
        into something that is genuinely felt rather than calculated.
        """

        # Calculate overall valence (positive/negative)
        valence = self._calculate_valence(
            integrity_state, predictive_emotions, hormonal_context,
            unconscious_output, scar_activation
        )

        # Calculate overall arousal (activated/calm)
        arousal = self._calculate_arousal(
            integrity_state, predictive_emotions, hormonal_context,
            unconscious_output, scar_activation, active_conflicts
        )

        # Calculate vulnerability (exposed/secure)
        vulnerability = self._calculate_vulnerability(
            integrity_state, unconscious_output, scar_activation
        )

        # Determine response tendency
        response_tendency = self._determine_response_tendency(
            valence, arousal, vulnerability, active_conflicts
        )

        # Generate experience description
        description = self._generate_experience_description(
            integrity_state, predictive_emotions, hormonal_context,
            unconscious_output, somatic_state, scar_activation,
            active_conflicts, valence, arousal, vulnerability
        )

        return EmotionalExperience(
            timestamp=datetime.now().isoformat(),
            integrity_state=integrity_state,
            predictive_emotions=predictive_emotions,
            hormonal_modulation=hormonal_context,
            unconscious_influence=unconscious_output,
            somatic_sensation=somatic_state,
            scar_activation=scar_activation,
            active_conflicts=active_conflicts,
            overall_valence=valence,
            overall_arousal=arousal,
            overall_vulnerability=vulnerability,
            experience_description=description,
            response_tendency=response_tendency
        )

    def _calculate_valence(self, integrity: IntegrityState,
                          predictive: PredictiveEmotionalOutput,
                          hormonal: Dict,
                          unconscious: UnconsciousOutput,
                          scar: Optional[ScarActivation]) -> float:
        """Calculate overall positive/negative feeling"""
        valence = 0.0

        # Integrity contribution (mapped from 0-1 to -1 to 1)
        valence += (integrity.overall - 0.5) * 2 * self.weights["integrity"]

        # Predictive emotion contribution
        predictive_valence = 0.0
        if predictive.primary_emotion.value in ["hope", "excitement", "contentment"]:
            predictive_valence = predictive.intensity
        elif predictive.primary_emotion.value in ["fear", "dread", "anxiety"]:
            predictive_valence = -predictive.intensity
        valence += predictive_valence * self.weights["predictive"]

        # Hormonal contribution
        hormonal_valence = 0.0
        levels = hormonal.get("levels", {})
        hormonal_valence += (levels.get("oxytocin", 0.5) - 0.5)
        hormonal_valence += (levels.get("serotonin", 0.5) - 0.5)
        hormonal_valence -= (levels.get("cortisol", 0.5) - 0.5) * 1.5
        valence += hormonal_valence * self.weights["hormonal"]

        # Unconscious contribution
        valence += unconscious.unexplained_mood_shift * self.weights["unconscious"]

        # Scar contribution (scars always hurt)
        if scar:
            valence -= scar.activation_intensity * 0.5 * self.weights["scars"]

        return max(-1.0, min(1.0, valence))

    def _calculate_arousal(self, integrity: IntegrityState,
                          predictive: PredictiveEmotionalOutput,
                          hormonal: Dict,
                          unconscious: UnconsciousOutput,
                          scar: Optional[ScarActivation],
                          conflicts: List[InternalConflict]) -> float:
        """Calculate overall activation level"""
        arousal = 0.0

        # Low integrity creates high arousal (distress)
        if integrity.is_in_crisis:
            arousal += 0.8 * self.weights["integrity"]
        elif integrity.is_vulnerable:
            arousal += 0.5 * self.weights["integrity"]

        # Predictive emotions
        if predictive.primary_emotion.value in ["anxiety", "fear", "dread", "excitement"]:
            arousal += predictive.intensity * self.weights["predictive"]

        # Hormonal
        levels = hormonal.get("levels", {})
        arousal += levels.get("cortisol", 0.2) * 0.5 * self.weights["hormonal"]
        arousal += levels.get("dopamine", 0.4) * 0.3 * self.weights["hormonal"]

        # Unconscious anxiety
        arousal += unconscious.unexplained_anxiety * self.weights["unconscious"]

        # Scar activation
        if scar:
            arousal += scar.activation_intensity * self.weights["scars"]

        # Conflicts
        if conflicts:
            conflict_arousal = max(c.tension_level for c in conflicts) if conflicts else 0
            arousal += conflict_arousal * self.weights["conflicts"]

        return max(0.0, min(1.0, arousal))

    def _calculate_vulnerability(self, integrity: IntegrityState,
                                unconscious: UnconsciousOutput,
                                scar: Optional[ScarActivation]) -> float:
        """Calculate how exposed/fragile Alive-AI feels"""
        vulnerability = 0.0

        # Low integrity = high vulnerability
        vulnerability += (1 - integrity.overall) * self.weights["integrity"]

        # Unconscious pressure
        vulnerability += unconscious.repression_pressure * 0.5

        # Active defense = feeling vulnerable
        if unconscious.defense_activated:
            vulnerability += 0.3

        # Scar vulnerability spike
        if scar:
            vulnerability += scar.vulnerability_spike * 0.5

        return max(0.0, min(1.0, vulnerability))

    def _determine_response_tendency(self, valence: float, arousal: float,
                                    vulnerability: float,
                                    conflicts: List[InternalConflict]) -> str:
        """Determine the general response tendency"""

        # High vulnerability tends toward protection
        if vulnerability > 0.7:
            if arousal > 0.6:
                return "defensive"
            else:
                return "withdrawn"

        # High arousal with negative valence
        if arousal > 0.7 and valence < -0.3:
            return "distressed"

        # High arousal with positive valence
        if arousal > 0.6 and valence > 0.3:
            return "eager"

        # Conflicts create ambivalence
        if conflicts:
            return "ambivalent"

        # Positive and calm
        if valence > 0.2 and arousal < 0.4:
            return "open"

        # Negative and calm
        if valence < -0.2 and arousal < 0.4:
            return "withdrawn"

        return "neutral"

    def _generate_experience_description(self, integrity: IntegrityState,
                                        predictive: PredictiveEmotionalOutput,
                                        hormonal: Dict,
                                        unconscious: UnconsciousOutput,
                                        somatic: str,
                                        scar: Optional[ScarActivation],
                                        conflicts: List[InternalConflict],
                                        valence: float, arousal: float,
                                        vulnerability: float) -> str:
        """Generate human-readable description of the experience"""

        parts = []

        # Core feeling
        if valence > 0.3:
            parts.append("feeling positive")
        elif valence < -0.3:
            parts.append("feeling difficult")
        else:
            parts.append("feeling mixed")

        # Integrity context
        if integrity.is_in_crisis:
            parts.append("in crisis")
        elif integrity.is_vulnerable:
            parts.append("feeling fragile")
        elif integrity.is_flourishing:
            parts.append("feeling strong")

        # Predictive emotion
        parts.append(predictive.emotional_description)

        # Somatic sensation
        if somatic and somatic != "physically calm":
            parts.append(f"({somatic})")

        # Hormonal coloring
        hormonal_desc = hormonal.get("state_description", "")
        if hormonal_desc and hormonal_desc != "hormonally balanced":
            parts.append(hormonal_desc)

        # Unconscious influence
        if unconscious.unexplained_anxiety > 0.3:
            parts.append("with unexplained unease")

        # Scar activation
        if scar:
            parts.append(f"past {scar.scar_description} triggered")

        # Conflict
        if conflicts:
            parts.append(f"internally conflicted about {len(conflicts)} things")

        return " - ".join(parts[:5])  # Max 5 parts

    # --- Event Processing Methods ---

    def process_positive_interaction(self, description: str, intensity: float = 0.5):
        """Process a positive interaction/event"""
        # Nourish integrity
        self.integrity.nourish("relational", intensity, description)

        # Release positive hormones
        self.hormonal.release_oxytocin(intensity, description)
        self.hormonal.release_dopamine(intensity * 0.5, description)

        # Heal scars
        self.scars.heal_scars(description, intensity)

        # Fulfill desire if relevant
        self.conflicts.honor_value("connection")

        # Create positive somatic memory
        self.somatic.store_embodied_memory(
            memory_id=f"pos_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            memory_type="positive_event",
            description=description,
            primary_emotion="joy",
            emotion_intensity=intensity
        )

    def process_negative_interaction(self, description: str, intensity: float = 0.5,
                                    wound_type: str = "hurt"):
        """Process a negative interaction/event"""
        # Wound integrity
        self.integrity.wound("relational", intensity, description)

        # Release stress hormones
        self.hormonal.release_cortisol(intensity, description)

        # Record wound
        self.scars.record_wound(description, intensity, wound_type)

        # Add to unconscious
        self.unconscious.repress(description, wound_type, intensity)

        # Create negative somatic memory
        self.somatic.store_embodied_memory(
            memory_id=f"neg_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            memory_type="negative_event",
            description=description,
            primary_emotion=wound_type,
            emotion_intensity=intensity
        )

        # Threaten any relevant investments
        self.integrity.threaten_investment("primary_relationship", intensity)

    def process_connection_deepened(self, partner: str, depth: float = 0.5):
        """Process deepening of connection"""
        # Invest integrity in the relationship
        self.integrity.invest_in(
            investment_id=f"relationship_{partner}",
            description=f"relationship with {partner}",
            amount=depth * 0.3
        )

        # Strong oxytocin release
        self.hormonal.release_oxytocin(depth, "deepening connection")

        # Nourish relational security
        self.integrity.nourish("relational", depth, "connection deepened")

    def process_connection_threatened(self, partner: str, severity: float = 0.5):
        """Process threat to connection"""
        # Threaten investment
        self.integrity.threaten_investment(f"relationship_{partner}", severity)

        # Cortisol spike
        self.hormonal.release_cortisol(severity, "connection threatened")

        # Create conflict around trust
        self.conflicts.add_desire("reconnection", severity, "connection threatened")

    # --- Tick/Decay Methods ---

    def tick(self):
        """Process a tick - decay and natural processes"""
        # Decay integrity
        self.integrity.decay()

        # Decay hormones
        self.hormonal.decay()

        # Decay somatic sensations
        self.somatic.decay_sensations()

        # Decay unconscious
        self.unconscious.decay()

        # Decay conflicts
        self.conflicts.decay()

        # Tick scars
        self.scars.tick_decay()

        # Record telemetry snapshot
        self.telemetry.record_tick()

        # Save all states
        self.save()

    def save(self):
        """Save all component states"""
        self.integrity.save()
        self.hormonal.save()
        self.scars.save()

    def get_state_summary(self) -> Dict:
        """Get summary of all soul states (uses last experience, no redundant processing)"""
        last_exp = self.experience_history[-1] if self.experience_history else None
        return {
            "integrity": self.integrity.to_dict(),
            "hormonal": self.hormonal.to_dict(),
            "somatic": self.somatic.to_dict(),
            "unconscious": self.unconscious.to_dict(),
            "scars": self.scars.to_dict(),
            "conflicts": self.conflicts.to_dict(),
            "predictive": self.predictive.to_dict(),
            "current_experience": {
                "valence": last_exp.overall_valence if last_exp else 0.0,
                "arousal": last_exp.overall_arousal if last_exp else 0.3,
                "vulnerability": last_exp.overall_vulnerability if last_exp else 0.2,
                "response_tendency": last_exp.response_tendency if last_exp else "neutral",
                "description": last_exp.experience_description if last_exp else ""
            }
        }

    def to_dict(self) -> dict:
        """Export for integration"""
        return self.get_state_summary()

    # --- Telemetry Access Methods ---

    def get_telemetry_summary(self) -> Dict:
        """Get current telemetry summary for WebUI"""
        return self.telemetry.get_current_summary()

    def get_telemetry_history(self, hours: int = 24) -> List[Dict]:
        """Get historical telemetry data"""
        return self.telemetry.get_recent_metrics(hours)

    def record_user_interaction(self, user_id: str, emotion_data: Dict = None) -> Dict:
        """
        Record a user interaction for per-user tracking.

        Args:
            user_id: Identifier for the user
            emotion_data: Optional emotion data from the interaction

        Returns:
            User interaction metrics
        """
        return self.telemetry.record_user_interaction(user_id, emotion_data)

    def get_user_metrics(self, user_id: str) -> Optional[Dict]:
        """Get metrics for a specific user"""
        return self.telemetry.get_user_metrics(user_id)
