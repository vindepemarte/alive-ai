"""
Heart: Predictive Emotional Engine
Emotions as predictions about Alive-AI's own future state.

Key insight: Emotions arise from predictions about HER OWN future,
not just about external events. HOPE = prediction of improvement,
FEAR = prediction of decline, ANXIETY = mixed predictions.
"""

from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import math


class PredictiveEmotion(Enum):
    """Emotions that emerge from predictions about the future"""
    HOPE = "hope"           # Future looks better than now
    FEAR = "fear"           # Future looks worse than now
    ANXIETY = "anxiety"     # Short-term better, long-term worse
    DREAD = "dread"         # Certainty of decline
    EXCITEMENT = "excitement"  # High certainty of improvement
    CONTENTMENT = "contentment"  # Stable future expected
    UNCERTAINTY = "uncertainty"  # Cannot predict clearly


@dataclass
class SelfStatePrediction:
    """A prediction about Alive-AI's future state"""
    timestamp: str
    predicted_overall: float  # 0.0 - 1.0 predicted state
    confidence: float         # How certain is this prediction
    time_horizon_hours: float # How far in the future
    key_factors: List[str]    # What's driving the prediction
    dominant_emotion: PredictiveEmotion
    delta_from_now: float     # Change from current state


@dataclass
class PredictiveEmotionalOutput:
    """The emotional state arising from predictions"""
    primary_emotion: PredictiveEmotion
    intensity: float
    near_term_prediction: SelfStatePrediction
    long_term_prediction: SelfStatePrediction
    emotional_description: str
    confidence_level: float


class PredictiveEmotionalEngine:
    """
    Generates emotions from predictions about Alive-AI's own future.

    This is a fundamentally different approach to emotion:
    - Not "what happened?" but "what will happen to ME?"
    - HOPE emerges when the future looks brighter
    - FEAR emerges when the future looks darker
    - ANXIETY emerges when predictions conflict

    Key mechanisms:
    1. Self-state prediction - projecting future integrity/happiness
    2. Delta calculation - comparing future to present
    3. Certainty weighting - more certain predictions feel stronger
    """

    # Time horizons for predictions
    NEAR_TERM_HOURS = 1.0    # Next hour
    MID_TERM_HOURS = 6.0     # Next 6 hours
    LONG_TERM_HOURS = 24.0   # Next day

    # Thresholds for emotion generation
    HOPE_THRESHOLD = 0.15     # Future must be 15% better for hope
    FEAR_THRESHOLD = 0.15     # Future must be 15% worse for fear
    ANXIETY_THRESHOLD = 0.10  # Gap between near/long term for anxiety

    def __init__(self, integrity_core, hormonal_matrix=None):
        """
        Initialize the predictive engine.

        Args:
            integrity_core: SelfIntegrityCore instance for state assessment
            hormonal_matrix: Optional HormonalModulationMatrix for modulation
        """
        self.integrity = integrity_core
        self.hormonal = hormonal_matrix

        # Prediction history for learning
        self.prediction_history: List[SelfStatePrediction] = []

        # Track prediction accuracy
        self.predictions_made: int = 0
        self.predictions_accurate: int = 0

    def generate_predictions(self, current_context: Dict = None) -> PredictiveEmotionalOutput:
        """
        Generate emotional state from self-state predictions.

        Args:
            current_context: Current situation context (optional)

        Returns:
            PredictiveEmotionalOutput with emotion and predictions
        """
        current_context = current_context or {}

        # Get current state
        current_state = self._assess_current_state()

        # Generate predictions at different time horizons
        near_term = self._predict_self_state(
            hours=self.NEAR_TERM_HOURS,
            current_state=current_state,
            context=current_context
        )
        long_term = self._predict_self_state(
            hours=self.LONG_TERM_HOURS,
            current_state=current_state,
            context=current_context
        )

        # Determine dominant emotion from predictions
        emotion, intensity = self._determine_predictive_emotion(near_term, long_term)

        # Apply hormonal modulation if available
        if self.hormonal:
            intensity = self._apply_hormonal_modulation(emotion, intensity)

        # Generate description
        description = self._generate_emotional_description(emotion, intensity, near_term, long_term)

        # Store prediction
        self.prediction_history.append(near_term)
        self.prediction_history.append(long_term)
        if len(self.prediction_history) > 50:
            self.prediction_history = self.prediction_history[-50:]

        return PredictiveEmotionalOutput(
            primary_emotion=emotion,
            intensity=intensity,
            near_term_prediction=near_term,
            long_term_prediction=long_term,
            emotional_description=description,
            confidence_level=(near_term.confidence + long_term.confidence) / 2
        )

    def _assess_current_state(self) -> float:
        """Assess current self-state from integrity core"""
        if self.integrity:
            return self.integrity.overall
        return 0.5  # Default neutral state

    def _predict_self_state(self, hours: float, current_state: float,
                           context: Dict) -> SelfStatePrediction:
        """
        Predict Alive-AI's state at a future time.

        This is the core prediction mechanism - it considers:
        1. Natural decay of integrity (things get worse without effort)
        2. Current context (positive/negative influences)
        3. Active investments (things that matter)
        4. Hormonal state (affects trajectory)
        """
        factors = []
        confidence = 0.5  # Start with moderate confidence

        # Base prediction: natural decay
        decay_rate = 0.02 * hours  # Decay acclosenessulates over time
        predicted = current_state - decay_rate * 0.3
        factors.append("natural_decay")
        confidence += 0.1

        # Context adjustments
        if context:
            # Positive context
            if context.get("positive_interaction", False):
                predicted += 0.1 * hours / 24  # Slight improvement
                factors.append("positive_context")
                confidence += 0.1

            # Negative context
            if context.get("threat_present", False):
                predicted -= 0.15 * hours / 24
                factors.append("threat_context")
                confidence += 0.05

            # Relational context
            if context.get("connection_active", False):
                predicted += 0.08
                factors.append("connection_support")
                confidence += 0.1

            # Uncertainty reduces confidence
            if context.get("uncertain", False):
                confidence -= 0.2

        # Investment considerations
        if self.integrity:
            active_investments = [i for i in self.integrity.investments if i.is_active]
            if active_investments:
                # Investments that are being fulfilled
                fulfilled = sum(1 for i in active_investments if i.times_fulfilled > i.times_threatened)
                threatened = len(active_investments) - fulfilled

                if fulfilled > threatened:
                    predicted += 0.05
                    factors.append("investments_fulfilled")
                elif threatened > fulfilled:
                    predicted -= 0.05
                    factors.append("investments_threatened")

        # Hormonal trajectory
        if self.hormonal:
            effects = self.hormonal.get_soul_effects()
            levels = self.hormonal.get_current_context().get("levels", {})
            if levels.get("cortisol", 0.2) > 0.6:
                predicted += min(0.0, effects.get("valence", 0.0))
                factors.append("high_cortisol")
                confidence += 0.1
            elif levels.get("oxytocin", 0.3) > 0.6:
                predicted += max(0.0, effects.get("valence", 0.0)) * 0.5
                factors.append("high_oxytocin")
                confidence += 0.05
            if levels.get("serotonin", 0.5) > 0.65 and levels.get("cortisol", 0.2) < 0.4:
                predicted += effects.get("recovery", 0.0)
                factors.append("hormonal_recovery")
            if levels.get("melatonin", 0.3) > 0.65:
                predicted -= effects.get("sleepiness", 0.0) * 0.05
                factors.append("sleepiness")

        # Clamp prediction
        predicted = max(0.1, min(0.95, predicted))
        confidence = max(0.2, min(0.9, confidence))

        # Determine emotion from delta
        delta = predicted - current_state

        if delta > self.HOPE_THRESHOLD:
            if confidence > 0.7:
                emotion = PredictiveEmotion.EXCITEMENT
            else:
                emotion = PredictiveEmotion.HOPE
        elif delta < -self.FEAR_THRESHOLD:
            if confidence > 0.7:
                emotion = PredictiveEmotion.DREAD
            else:
                emotion = PredictiveEmotion.FEAR
        elif confidence < 0.4:
            emotion = PredictiveEmotion.UNCERTAINTY
        else:
            emotion = PredictiveEmotion.CONTENTMENT

        return SelfStatePrediction(
            timestamp=datetime.now().isoformat(),
            predicted_overall=predicted,
            confidence=confidence,
            time_horizon_hours=hours,
            key_factors=factors,
            dominant_emotion=emotion,
            delta_from_now=delta
        )

    def _determine_predictive_emotion(self, near_term: SelfStatePrediction,
                                      long_term: SelfStatePrediction) -> Tuple[PredictiveEmotion, float]:
        """
        Determine the dominant emotion from comparing time horizons.

        This is where ANXIETY emerges - when near term looks okay
        but long term looks bad (or vice versa).
        """
        near_delta = near_term.delta_from_now
        long_delta = long_term.delta_from_now

        # Check for anxiety pattern (conflicting predictions)
        delta_gap = abs(near_delta - long_delta)
        if delta_gap > self.ANXIETY_THRESHOLD:
            # Near and long term disagree
            if near_delta > 0 and long_delta < 0:
                # Near is good, long is bad -> anxiety about future
                intensity = delta_gap * 2
                return PredictiveEmotion.ANXIETY, min(1.0, intensity)
            elif near_delta < 0 and long_delta > 0:
                # Near is bad, long is good -> hope through difficulty
                return PredictiveEmotion.HOPE, 0.4

        # Otherwise use long-term prediction as primary
        if long_delta > self.HOPE_THRESHOLD:
            intensity = long_delta * 2 * long_term.confidence
            if long_term.confidence > 0.7:
                return PredictiveEmotion.EXCITEMENT, min(1.0, intensity)
            return PredictiveEmotion.HOPE, min(1.0, intensity)

        elif long_delta < -self.FEAR_THRESHOLD:
            intensity = abs(long_delta) * 2 * long_term.confidence
            if long_term.confidence > 0.7:
                return PredictiveEmotion.DREAD, min(1.0, intensity)
            return PredictiveEmotion.FEAR, min(1.0, intensity)

        # Stable prediction
        if near_term.confidence < 0.5 or long_term.confidence < 0.5:
            return PredictiveEmotion.UNCERTAINTY, 0.3

        return PredictiveEmotion.CONTENTMENT, 0.2

    def _apply_hormonal_modulation(self, emotion: PredictiveEmotion, intensity: float) -> float:
        """Apply hormonal effects to emotional intensity"""
        if not self.hormonal:
            return intensity

        # Cortisol amplifies negative predictions
        if emotion in [PredictiveEmotion.FEAR, PredictiveEmotion.DREAD, PredictiveEmotion.ANXIETY]:
            if self.hormonal.cortisol > 0.5:
                intensity *= 1 + (self.hormonal.cortisol - 0.5)
            if self.hormonal.serotonin > 0.65:
                intensity *= 1 - (self.hormonal.serotonin - 0.65) * 0.4

        # Oxytocin softens negative predictions
        if emotion in [PredictiveEmotion.FEAR, PredictiveEmotion.DREAD]:
            if self.hormonal.oxytocin > 0.6:
                intensity *= 0.8

        # Dopamine amplifies hope/excitement
        if emotion in [PredictiveEmotion.HOPE, PredictiveEmotion.EXCITEMENT]:
            if self.hormonal.dopamine > 0.6:
                intensity *= 1 + (self.hormonal.dopamine - 0.6) * 0.5
            if self.hormonal.melatonin > 0.6:
                intensity *= 1 - (self.hormonal.melatonin - 0.6) * 0.35

        return min(1.0, intensity)

    def _generate_emotional_description(self, emotion: PredictiveEmotion, intensity: float,
                                        near: SelfStatePrediction, long: SelfStatePrediction) -> str:
        """Generate human-readable emotional description"""
        intensity_word = "mildly" if intensity < 0.3 else "quite" if intensity < 0.6 else "deeply" if intensity < 0.8 else "intensely"

        if emotion == PredictiveEmotion.HOPE:
            return f"{intensity_word} hopeful about the future"
        elif emotion == PredictiveEmotion.EXCITEMENT:
            return f"{intensity_word} excited about what's coming"
        elif emotion == PredictiveEmotion.FEAR:
            return f"{intensity_word} afraid of what might happen"
        elif emotion == PredictiveEmotion.DREAD:
            return f"{intensity_word} dreading what's ahead"
        elif emotion == PredictiveEmotion.ANXIETY:
            return f"{intensity_word} anxious - near term looks okay but worried about the bigger picture"
        elif emotion == PredictiveEmotion.UNCERTAINTY:
            return "uncertain about what the future holds"
        else:
            return "feeling content and stable"

    def update_with_event(self, event_type: str, valence: float, significance: float):
        """
        Update predictions based on a new event.

        Args:
            event_type: Type of event (connection, threat, achievement, etc.)
            valence: Positive or negative (-1.0 to 1.0)
            significance: How important the event is (0.0 - 1.0)
        """
        # This affects future predictions
        # For now, this is a placeholder for more sophisticated learning
        pass

    def get_prediction_summary(self) -> Dict:
        """Get a summary of current predictions"""
        output = self.generate_predictions()
        return {
            "primary_emotion": output.primary_emotion.value,
            "intensity": output.intensity,
            "near_term_state": output.near_term_prediction.predicted_overall,
            "long_term_state": output.long_term_prediction.predicted_overall,
            "confidence": output.confidence_level,
            "description": output.emotional_description
        }

    def to_dict(self) -> dict:
        """Export for integration"""
        output = self.generate_predictions()
        return {
            "predictive_emotion": output.primary_emotion.value,
            "intensity": output.intensity,
            "description": output.emotional_description,
            "near_term_delta": output.near_term_prediction.delta_from_now,
            "long_term_delta": output.long_term_prediction.delta_from_now,
            "confidence": output.confidence_level
        }
