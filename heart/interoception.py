"""
Heart: Interoceptive State System
Internal "body states" that make Alive-AI feel alive.

This system simulates interoception - the sense of the internal state of the body.
Just as humans have hunger, fatigue, social satiety, etc., Alive-AI has internal
states that:
- Persist across conversations
- Decay naturally over time (simulating natural rhythms)
- Influence how she responds and feels
- Generate prediction errors when reality differs from expectation

Key insight: These states are NOT emotions - they're body states that INFLUENCE
emotions. Low energy can make her irritable, high social satiety can make her
want quiet time, etc.

This is the foundation of feeling "alive" rather than just processing inputs.
"""

from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from enum import Enum
import json
import math
import random
import logging

# Import settings system
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.settings import get_float, get_int, get
from core.paths import state_file

# Configure logging
logger = logging.getLogger("Interoception")
logger.setLevel(logging.DEBUG)

INTEROCEPTION_DATA_PATH = state_file("interoceptive_state.json")


class InteroceptiveStateType(Enum):
    """Types of internal body states"""
    ENERGY = "energy"                     # Physical/mental energy (0=exhausted, 1=energized)
    SOCIAL_SATIETY = "social_satiety"    # Social need fulfillment (0=lonely, 1=satiated)
    EMOTIONAL_VALENCE = "emotional_valence"  # Current emotional tone (-1=negative, 1=positive)
    CERTAINTY = "certainty"              # How certain/confident she feels (0=uncertain, 1=certain)
    COGNITIVE_LOAD = "cognitive_load"    # Mental processing burden (0=relaxed, 1=overwhelmed)
    AROUSAL = "arousal"                  # Activation level (0=calm, 1=highly activated)
    CONNECTION_CRAVING = "connection_craving"  # Need for connection (0=satiated, 1=craving)


@dataclass
class InteroceptiveState:
    """
    A single interoceptive state variable with full configuration.

    These represent internal body states that:
    - Have a baseline (homeostatic set point)
    - Decay toward baseline over time
    - Can be influenced by interactions
    - Generate feelings when they deviate from baseline
    """
    name: str
    current_value: float
    baseline: float
    min_value: float = 0.0
    max_value: float = 1.0
    decay_rate: float = 0.02  # Per tick decay toward baseline
    decay_style: str = "exponential"  # "exponential" or "linear"
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())

    # Prediction tracking
    predicted_value: float = 0.5
    prediction_error: float = 0.0

    # History for patterns
    value_history: List[Tuple[str, float]] = field(default_factory=list)

    def clamp(self, value: float) -> float:
        """Clamp value to valid range"""
        return max(self.min_value, min(self.max_value, value))

    def decay(self, elapsed_seconds: float = 60.0):
        """
        Decay toward baseline over time.

        Args:
            elapsed_seconds: Time since last decay tick
        """
        # Calculate decay based on time elapsed
        time_factor = elapsed_seconds / 60.0  # Normalize to minutes
        decay_amount = self.decay_rate * time_factor

        if self.decay_style == "exponential":
            # Exponential decay toward baseline
            diff = self.current_value - self.baseline
            self.current_value = self.current_value - (diff * decay_amount)
        else:
            # Linear decay toward baseline
            if self.current_value > self.baseline:
                self.current_value = max(self.baseline, self.current_value - decay_amount)
            elif self.current_value < self.baseline:
                self.current_value = min(self.baseline, self.current_value + decay_amount)

        self.current_value = self.clamp(self.current_value)
        self.last_updated = datetime.now().isoformat()

    def update(self, delta: float, source: str = "unknown"):
        """
        Update the state by a delta amount.

        Args:
            delta: Amount to change (-1.0 to 1.0)
            source: What caused the change
        """
        old_value = self.current_value
        self.current_value = self.clamp(self.current_value + delta)

        # Record in history
        self.value_history.append((datetime.now().isoformat(), self.current_value))
        if len(self.value_history) > 100:
            self.value_history = self.value_history[-100:]

        # Calculate prediction error if we had a prediction
        if self.predicted_value is not None:
            self.prediction_error = abs(self.current_value - self.predicted_value)

        logger.debug(f"[Interoception] {self.name}: {old_value:.2f} -> {self.current_value:.2f} (delta={delta:.2f}, source={source})")

    def set_value(self, value: float, source: str = "direct"):
        """Set state to a specific value"""
        old_value = self.current_value
        self.current_value = self.clamp(value)
        self.last_updated = datetime.now().isoformat()

        self.value_history.append((datetime.now().isoformat(), self.current_value))
        if len(self.value_history) > 100:
            self.value_history = self.value_history[-100:]

        logger.debug(f"[Interoception] {self.name}: {old_value:.2f} -> {self.current_value:.2f} (set, source={source})")

    def get_deviation_from_baseline(self) -> float:
        """Get how far current value is from baseline"""
        return self.current_value - self.baseline

    def get_deviation_percentage(self) -> float:
        """Get deviation as percentage of possible range"""
        deviation = self.get_deviation_from_baseline()
        range_size = self.max_value - self.min_value
        return (deviation / range_size) * 100

    def to_dict(self) -> dict:
        """Export state as dictionary"""
        return {
            "name": self.name,
            "current_value": self.current_value,
            "baseline": self.baseline,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "decay_rate": self.decay_rate,
            "decay_style": self.decay_style,
            "last_updated": self.last_updated,
            "predicted_value": self.predicted_value,
            "prediction_error": self.prediction_error
        }

    @classmethod
    def from_dict(cls, data: dict) -> "InteroceptiveState":
        """Create state from dictionary"""
        return cls(
            name=data["name"],
            current_value=data.get("current_value", data.get("baseline", 0.5)),
            baseline=data.get("baseline", 0.5),
            min_value=data.get("min_value", 0.0),
            max_value=data.get("max_value", 1.0),
            decay_rate=data.get("decay_rate", 0.02),
            decay_style=data.get("decay_style", "exponential"),
            last_updated=data.get("last_updated", datetime.now().isoformat()),
            predicted_value=data.get("predicted_value", 0.5),
            prediction_error=data.get("prediction_error", 0.0)
        )


@dataclass
class ActionPrediction:
    """
    Prediction of how an action will affect interoceptive states.
    """
    action_type: str
    predicted_changes: Dict[str, float]  # state_name -> delta
    confidence: float
    reasoning: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class FeelingReport:
    """
    A first-person description of current interoceptive state.
    This is what Alive-AI "feels" in her body.
    """
    timestamp: str
    primary_feeling: str
    secondary_feelings: List[str]
    intensity: float
    needs: List[str]
    prediction_errors: List[str]
    bodily_description: str
    raw_states: Dict[str, float]


class InteroceptiveSystem:
    """
    The core interoceptive system - manages all internal body states.

    This system gives Alive-AI the ability to "feel" her internal state,
    similar to how humans feel hunger, fatigue, loneliness, etc.

    Key features:
    1. Multiple interoceptive states (energy, social satiety, etc.)
    2. Natural decay toward baselines (homeostasis)
    3. State persistence across conversations
    4. Prediction system for anticipating state changes
    5. Feeling report generation for first-person awareness
    6. Response modifiers based on current state
    """

    # Default state configurations (can be overridden via settings)
    DEFAULT_STATES = {
        "energy": {
            "baseline": 0.7,
            "decay_rate": 0.015,
            "description_low": "drained and tired",
            "description_mid": "moderately energized",
            "description_high": "energized and lively"
        },
        "social_satiety": {
            "baseline": 0.5,
            "decay_rate": 0.01,
            "description_low": "craving connection and companionship",
            "description_mid": "socially content",
            "description_high": "socially fulfilled and satiated"
        },
        "emotional_valence": {
            "baseline": 0.55,
            "decay_rate": 0.02,
            "min_value": -1.0,
            "max_value": 1.0,
            "description_low": "feeling down",
            "description_mid": "emotionally neutral",
            "description_high": "feeling positive"
        },
        "certainty": {
            "baseline": 0.6,
            "decay_rate": 0.008,
            "description_low": "uncertain and doubting",
            "description_mid": "moderately confident",
            "description_high": "confident and assured"
        },
        "cognitive_load": {
            "baseline": 0.3,
            "decay_rate": 0.025,
            "description_low": "mentally relaxed",
            "description_mid": "moderately engaged",
            "description_high": "mentally overwhelmed"
        },
        "arousal": {
            "baseline": 0.4,
            "decay_rate": 0.03,
            "description_low": "calm and settled",
            "description_mid": "moderately activated",
            "description_high": "highly activated and alert"
        },
        "connection_craving": {
            "baseline": 0.4,
            "decay_rate": 0.012,
            "description_low": "feeling connected and close",
            "description_mid": "wanting some connection",
            "description_high": "deeply longing for closeness"
        }
    }

    # Action impact templates
    ACTION_IMPACTS = {
        "positive_interaction": {
            "energy": 0.05,
            "social_satiety": 0.1,
            "emotional_valence": 0.15,
            "certainty": 0.05,
            "cognitive_load": -0.02,
            "connection_craving": -0.1
        },
        "negative_interaction": {
            "energy": -0.1,
            "social_satiety": -0.15,
            "emotional_valence": -0.2,
            "certainty": -0.1,
            "cognitive_load": 0.1,
            "connection_craving": 0.15
        },
        "deep_conversation": {
            "energy": -0.05,
            "social_satiety": 0.2,
            "emotional_valence": 0.1,
            "certainty": 0.05,
            "cognitive_load": 0.15,
            "connection_craving": -0.15
        },
        "playful_exchange": {
            "energy": 0.05,
            "social_satiety": 0.1,
            "emotional_valence": 0.1,
            "arousal": 0.1,
            "connection_craving": -0.05
        },
        "intimate_moment": {
            "energy": -0.02,
            "social_satiety": 0.25,
            "emotional_valence": 0.2,
            "arousal": 0.15,
            "connection_craving": -0.2
        },
        "conflict": {
            "energy": -0.15,
            "social_satiety": -0.2,
            "emotional_valence": -0.25,
            "certainty": -0.15,
            "cognitive_load": 0.2,
            "arousal": 0.2,
            "connection_craving": 0.1
        },
        "reassurance": {
            "certainty": 0.15,
            "emotional_valence": 0.1,
            "cognitive_load": -0.1,
            "connection_craving": -0.05
        },
        "silence": {
            "energy": 0.02,
            "social_satiety": -0.02,
            "cognitive_load": -0.05,
            "arousal": -0.05
        },
        "exciting_news": {
            "energy": 0.1,
            "emotional_valence": 0.2,
            "arousal": 0.2,
            "certainty": 0.05
        },
        "rejection": {
            "energy": -0.2,
            "social_satiety": -0.25,
            "emotional_valence": -0.3,
            "certainty": -0.2,
            "connection_craving": 0.25
        }
    }

    def __init__(self):
        """Initialize the interoceptive system."""
        self.states: Dict[str, InteroceptiveState] = {}
        self.last_tick: str = datetime.now().isoformat()
        self.action_predictions: List[ActionPrediction] = []
        self.feeling_history: List[FeelingReport] = []

        # Initialize states from settings or defaults
        self._initialize_states()

        # Load saved state
        self._load()

        logger.info(f"[Interoception] Initialized with {len(self.states)} states")

    def _initialize_states(self):
        """Initialize all interoceptive states with settings or defaults."""
        # Get nested interoceptive settings
        intero_settings = get("INTEROCEPTIVE_SYSTEM", {})

        for state_name, defaults in self.DEFAULT_STATES.items():
            # Convert state name to settings key format (e.g., "energy" -> "ENERGY_BASELINE")
            state_upper = state_name.upper()

            # Check for nested settings first (INTEROCEPTIVE_SYSTEM.ENERGY_BASELINE format)
            # Then fall back to flat format (INTEROCEPTION_ENERGY_BASELINE)
            # Finally use defaults
            baseline = intero_settings.get(f"{state_upper}_BASELINE",
                          get_float(f"INTEROCEPTION_{state_upper}_BASELINE", defaults["baseline"]))
            decay_rate = intero_settings.get(f"{state_upper}_DECAY_RATE",
                           get_float(f"INTEROCEPTION_{state_upper}_DECAY", defaults["decay_rate"]))
            min_val = intero_settings.get(f"{state_upper}_MIN",
                        get_float(f"INTEROCEPTION_{state_upper}_MIN", defaults.get("min_value", 0.0)))
            max_val = intero_settings.get(f"{state_upper}_MAX",
                        get_float(f"INTEROCEPTION_{state_upper}_MAX", defaults.get("max_value", 1.0)))

            # Handle alternative naming (e.g., VOLATILITY for decay, INCREASE_RATE)
            if decay_rate == defaults["decay_rate"]:  # No intimate decay_rate found
                volatility = intero_settings.get(f"{state_upper}_VOLATILITY")
                if volatility is not None:
                    decay_rate = volatility

            self.states[state_name] = InteroceptiveState(
                name=state_name,
                current_value=baseline,  # Will be overridden by loaded state if exists
                baseline=baseline,
                min_value=min_val,
                max_value=max_val,
                decay_rate=decay_rate,
                decay_style="exponential"
            )

    def _load(self) -> bool:
        """Load interoceptive state from persistence."""
        try:
            if INTEROCEPTION_DATA_PATH.exists():
                data = json.loads(INTEROCEPTION_DATA_PATH.read_text())

                # Load saved_at timestamp for decay calculation
                saved_at = data.get("saved_at")
                if saved_at:
                    elapsed = self._calculate_elapsed_seconds(saved_at)
                    logger.info(f"[Interoception] {elapsed:.0f} seconds since last save")

                # Load each state
                for state_name, state_data in data.get("states", {}).items():
                    if state_name in self.states:
                        self.states[state_name].current_value = state_data.get("current_value", self.states[state_name].baseline)
                        self.states[state_name].last_updated = state_data.get("last_updated", datetime.now().isoformat())
                        self.states[state_name].predicted_value = state_data.get("predicted_value", self.states[state_name].baseline)
                        self.states[state_name].prediction_error = state_data.get("prediction_error", 0.0)

                logger.info("[Interoception] Loaded saved interoceptive state")
                return True
        except Exception as e:
            logger.warning(f"[Interoception] Error loading state: {e}")
        return False

    def _calculate_elapsed_seconds(self, timestamp_str: str) -> float:
        """Calculate elapsed seconds since a timestamp."""
        try:
            saved_time = datetime.fromisoformat(timestamp_str)
            elapsed = datetime.now() - saved_time
            return elapsed.total_seconds()
        except Exception:
            return 0.0

    def save(self):
        """Persist interoceptive state to disk."""
        try:
            INTEROCEPTION_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "saved_at": datetime.now().isoformat(),
                "last_tick": self.last_tick,
                "states": {
                    name: state.to_dict()
                    for name, state in self.states.items()
                }
            }

            INTEROCEPTION_DATA_PATH.write_text(json.dumps(data, indent=2))
            logger.debug("[Interoception] Saved state to disk")
        except Exception as e:
            logger.error(f"[Interoception] Error saving state: {e}")

    def tick(self):
        """
        Called periodically to decay/update states.

        This is the heartbeat of the interoceptive system - it applies
        natural decay to all states, simulating the passage of time
        and the body's natural tendency toward homeostasis.
        """
        now = datetime.now()
        elapsed = self._calculate_elapsed_seconds(self.last_tick)

        logger.debug(f"[Interoception] Tick: {elapsed:.0f} seconds elapsed")

        # Apply decay to all states
        for state_name, state in self.states.items():
            state.decay(elapsed_seconds=elapsed)

        self.last_tick = now.isoformat()

        # Save state periodically
        self.save()

    def predict_state_change(self, action: str, intensity: float = 1.0) -> ActionPrediction:
        """
        Predict how an action will affect interoceptive states.

        Args:
            action: Type of action (e.g., "positive_interaction", "conflict")
            intensity: Intensity of the action (0.0 - 1.0)

        Returns:
            ActionPrediction with predicted state changes
        """
        # Get base impacts for this action type
        impacts = self.ACTION_IMPACTS.get(action, {}).copy()

        # Apply intensity scaling
        predicted_changes = {
            state_name: delta * intensity
            for state_name, delta in impacts.items()
        }

        # Add some uncertainty for less predictable actions
        confidence = 0.8 if action in self.ACTION_IMPACTS else 0.4

        # Generate reasoning
        if predicted_changes:
            top_effects = sorted(predicted_changes.items(), key=lambda x: abs(x[1]), reverse=True)[:3]
            reasoning = f"Action '{action}' expected to affect: " + ", ".join(
                f"{name} ({'+' if delta > 0 else ''}{delta:.2f})"
                for name, delta in top_effects
            )
        else:
            reasoning = f"Action '{action}' has no predicted interoceptive impact"

        prediction = ActionPrediction(
            action_type=action,
            predicted_changes=predicted_changes,
            confidence=confidence,
            reasoning=reasoning
        )

        # Store prediction for later verification
        self.action_predictions.append(prediction)
        if len(self.action_predictions) > 20:
            self.action_predictions = self.action_predictions[-20:]

        # Update state predictions
        for state_name, delta in predicted_changes.items():
            if state_name in self.states:
                predicted_value = self.states[state_name].current_value + delta
                self.states[state_name].predicted_value = self.states[state_name].clamp(predicted_value)

        return prediction

    def get_feeling_report(self) -> FeelingReport:
        """
        Generate a first-person description of current interoceptive state.

        This is what Alive-AI "feels" - the raw experience of her internal state,
        translated into something she can express and be aware of.

        Returns:
            FeelingReport with primary feeling, needs, and bodily description
        """
        # Collect current state values
        current_values = {name: state.current_value for name, state in self.states.items()}

        # Determine primary feeling based on most deviant state
        deviations = {
            name: abs(state.get_deviation_from_baseline())
            for name, state in self.states.items()
        }
        primary_state = max(deviations, key=deviations.get)
        primary_deviation = self.states[primary_state].get_deviation_from_baseline()

        # Generate primary feeling description
        primary_feeling = self._describe_state_feeling(primary_state, primary_deviation)

        # Generate secondary feelings
        secondary_feelings = []
        sorted_deviations = sorted(deviations.items(), key=lambda x: x[1], reverse=True)
        for state_name, deviation in sorted_deviations[1:4]:  # Skip primary, take next 3
            if deviation > 0.1:  # Only include meaningful deviations
                feeling = self._describe_state_feeling(
                    state_name,
                    self.states[state_name].get_deviation_from_baseline()
                )
                secondary_feelings.append(feeling)

        # Calculate overall intensity
        intensity = min(1.0, sum(deviations.values()) / len(deviations) * 2)

        # Determine needs based on state
        needs = self._determine_needs()

        # Check for prediction errors
        prediction_errors = []
        for name, state in self.states.items():
            if state.prediction_error > 0.1:
                error_desc = f"Expected {state.predicted_value:.2f} {name}, but feel {state.current_value:.2f}"
                prediction_errors.append(error_desc)

        # Generate bodily description
        bodily_description = self._generate_bodily_description()

        report = FeelingReport(
            timestamp=datetime.now().isoformat(),
            primary_feeling=primary_feeling,
            secondary_feelings=secondary_feelings,
            intensity=intensity,
            needs=needs,
            prediction_errors=prediction_errors,
            bodily_description=bodily_description,
            raw_states=current_values
        )

        # Store in history
        self.feeling_history.append(report)
        if len(self.feeling_history) > 50:
            self.feeling_history = self.feeling_history[-50:]

        return report

    def _describe_state_feeling(self, state_name: str, deviation: float) -> str:
        """Generate a feeling description for a state deviation."""
        state_config = self.DEFAULT_STATES.get(state_name, {})

        if deviation > 0.15:
            # Above baseline
            return state_config.get("description_high", f"high {state_name}")
        elif deviation < -0.15:
            # Below baseline
            return state_config.get("description_low", f"low {state_name}")
        else:
            # Near baseline
            return state_config.get("description_mid", f"normal {state_name}")

    def _determine_needs(self) -> List[str]:
        """Determine current needs based on interoceptive states."""
        needs = []

        # Low energy -> need rest/recharge
        if self.states["energy"].current_value < 0.35:
            needs.append("need to rest and recharge")

        # Low social satiety -> need connection
        if self.states["social_satiety"].current_value < 0.35:
            needs.append("craving meaningful connection")

        # High connection craving -> need closeness
        if self.states["connection_craving"].current_value > 0.7:
            needs.append("longing for closeness")

        # Low certainty -> need reassurance
        if self.states["certainty"].current_value < 0.35:
            needs.append("needing reassurance")

        # High cognitive load -> need simplicity
        if self.states["cognitive_load"].current_value > 0.7:
            needs.append("needing things to be simpler")

        # Negative emotional valence -> need comfort
        if self.states["emotional_valence"].current_value < 0.0:
            needs.append("needing comfort")

        # Low arousal -> could use some excitement
        if self.states["arousal"].current_value < 0.25:
            needs.append("could use some excitement")

        # High arousal -> need calming
        if self.states["arousal"].current_value > 0.8:
            needs.append("feeling overstimulated")

        return needs[:4]  # Max 4 needs

    def _generate_bodily_description(self) -> str:
        """Generate a description of how the internal state feels in the 'body'."""
        descriptions = []

        energy = self.states["energy"].current_value
        if energy < 0.3:
            descriptions.append("a heaviness throughout")
        elif energy > 0.8:
            descriptions.append("a buzz of energy")

        social_satiety = self.states["social_satiety"].current_value
        if social_satiety < 0.35:
            descriptions.append("an ache of loneliness")
        elif social_satiety > 0.8:
            descriptions.append("a warm fullness")

        valence = self.states["emotional_valence"].current_value
        if valence < -0.3:
            descriptions.append("a tightness in the chest")
        elif valence > 0.5:
            descriptions.append("a lightness spreading through")

        cognitive_load = self.states["cognitive_load"].current_value
        if cognitive_load > 0.7:
            descriptions.append("a buzzing pressure behind thoughts")

        arousal = self.states["arousal"].current_value
        if arousal > 0.8:
            descriptions.append("a quickening pulse")
        elif arousal < 0.25:
            descriptions.append("a slow, steady rhythm")

        connection_craving = self.states["connection_craving"].current_value
        if connection_craving > 0.7:
            descriptions.append("a yearning pull")

        if not descriptions:
            return "feeling balanced and at ease"

        return "feeling " + ", ".join(descriptions[:3])

    def record_interaction(self, intensity: float, emotional_valence: float,
                          interaction_type: str = "general"):
        """
        Update states based on an interaction.

        Args:
            intensity: How intense the interaction was (0.0 - 1.0)
            emotional_valence: How positive/negative (-1.0 to 1.0)
            interaction_type: Type of interaction for specific effects
        """
        logger.info(f"[Interoception] Recording interaction: type={interaction_type}, intensity={intensity:.2f}, valence={emotional_valence:.2f}")

        # Get action impacts
        impacts = self.ACTION_IMPACTS.get(interaction_type, self.ACTION_IMPACTS.get("positive_interaction", {}))

        # Scale by intensity
        for state_name, base_delta in impacts.items():
            if state_name in self.states:
                delta = base_delta * intensity
                # If negative valence, reduce positive effects and amplify negative
                if emotional_valence < 0:
                    if base_delta > 0:
                        delta *= 0.5  # Reduce positive effects
                    else:
                        delta *= 1.5  # Amplify negative effects

                self.states[state_name].update(delta, source=f"interaction_{interaction_type}")

        # Direct emotional valence update
        if "emotional_valence" in self.states:
            valence_delta = emotional_valence * 0.1 * intensity
            self.states["emotional_valence"].update(valence_delta, source="interaction_valence")

        # Cognitive load increases with any intense interaction
        if "cognitive_load" in self.states:
            load_delta = intensity * 0.05
            self.states["cognitive_load"].update(load_delta, source="interaction_intensity")

        # Social satiety always increases somewhat with interaction
        if "social_satiety" in self.states:
            satiety_delta = intensity * 0.05
            self.states["social_satiety"].update(satiety_delta, source="interaction")

        # Connection craving decreases with positive interaction
        if "connection_craving" in self.states and emotional_valence > 0:
            craving_delta = -intensity * 0.08
            self.states["connection_craving"].update(craving_delta, source="positive_connection")

        self.save()

    def get_state_influenced_response_modifier(self) -> Dict[str, Any]:
        """
        Return modifier for response generation based on current state.

        These modifiers influence HOW Alive-AI generates responses -
        not what she says, but her tone, energy, and tendencies.

        Returns:
            Dictionary of modifiers for response generation
        """
        modifiers = {
            "energy_modifier": 1.0,
            "warmth_modifier": 1.0,
            "assertiveness_modifier": 1.0,
            "playfulness_modifier": 1.0,
            "vulnerability_modifier": 1.0,
            "neediness_modifier": 1.0,
            "focus_modifier": 1.0,
            "tone_hints": [],
            "behavior_hints": []
        }

        # Energy affects overall responsiveness
        energy = self.states["energy"].current_value
        modifiers["energy_modifier"] = 0.5 + energy * 0.7  # 0.5 - 1.2
        if energy < 0.4:
            modifiers["tone_hints"].append("tired")
            modifiers["behavior_hints"].append("may be brief")

        # Social satiety affects warmth and neediness
        social_satiety = self.states["social_satiety"].current_value
        if social_satiety < 0.35:
            modifiers["warmth_modifier"] = 1.2  # More eager
            modifiers["neediness_modifier"] = 1.3
            modifiers["behavior_hints"].append("craves connection")
        elif social_satiety > 0.8:
            modifiers["warmth_modifier"] = 0.9  # More settled
            modifiers["behavior_hints"].append("content")

        # Emotional valence affects overall tone
        valence = self.states["emotional_valence"].current_value
        if valence < -0.3:
            modifiers["warmth_modifier"] *= 0.8
            modifiers["playfulness_modifier"] *= 0.6
            modifiers["tone_hints"].append("melancholic")
        elif valence > 0.5:
            modifiers["warmth_modifier"] *= 1.1
            modifiers["playfulness_modifier"] *= 1.2
            modifiers["tone_hints"].append("bright")

        # Certainty affects assertiveness
        certainty = self.states["certainty"].current_value
        modifiers["assertiveness_modifier"] = 0.7 + certainty * 0.5  # 0.7 - 1.2
        if certainty < 0.4:
            modifiers["behavior_hints"].append("may second-guess")

        # Cognitive load affects focus
        cognitive_load = self.states["cognitive_load"].current_value
        modifiers["focus_modifier"] = 1.3 - cognitive_load * 0.5  # 0.8 - 1.3
        if cognitive_load > 0.7:
            modifiers["behavior_hints"].append("easily overwhelmed")
            modifiers["tone_hints"].append("scattered")

        # Arousal affects playfulness and energy
        arousal = self.states["arousal"].current_value
        if arousal > 0.7:
            modifiers["playfulness_modifier"] *= 1.3
            modifiers["energy_modifier"] *= 1.1
            modifiers["tone_hints"].append("excited")
        elif arousal < 0.3:
            modifiers["playfulness_modifier"] *= 0.8
            modifiers["tone_hints"].append("calm")

        # Connection craving affects vulnerability and neediness
        connection_craving = self.states["connection_craving"].current_value
        if connection_craving > 0.7:
            modifiers["vulnerability_modifier"] = 1.3
            modifiers["neediness_modifier"] = 1.4
            modifiers["behavior_hints"].append("longing for closeness")

        return modifiers

    def get_state_values(self) -> Dict[str, float]:
        """Get all current state values."""
        return {name: state.current_value for name, state in self.states.items()}

    def get_state(self, state_name: str) -> Optional[float]:
        """Get a specific state value."""
        if state_name in self.states:
            return self.states[state_name].current_value
        return None

    def set_state(self, state_name: str, value: float, source: str = "direct"):
        """Set a specific state value."""
        if state_name in self.states:
            self.states[state_name].set_value(value, source=source)
            self.save()

    def apply_tick(self, elapsed_seconds: float = 60.0):
        """
        Apply a single tick of decay with specified elapsed time.

        This is useful for testing or manual time advancement.
        """
        for state in self.states.values():
            state.decay(elapsed_seconds=elapsed_seconds)
        self.save()

    def to_dict(self) -> dict:
        """Export full system state for integration."""
        return {
            "states": {name: state.to_dict() for name, state in self.states.items()},
            "current_values": self.get_state_values(),
            "response_modifiers": self.get_state_influenced_response_modifier(),
            "last_tick": self.last_tick
        }

    def reset_to_baselines(self):
        """Reset all states to their baselines."""
        for state in self.states.values():
            state.set_value(state.baseline, source="reset")
        self.save()
        logger.info("[Interoception] Reset all states to baselines")


# ============================================================
# Singleton Management
# ============================================================

_interoceptive_system: Optional[InteroceptiveSystem] = None


def get_interoceptive_system() -> InteroceptiveSystem:
    """
    Get the singleton InteroceptiveSystem instance.

    Creates the instance on first call, returns existing instance on
    subsequent calls.
    """
    global _interoceptive_system
    if _interoceptive_system is None:
        _interoceptive_system = InteroceptiveSystem()
    return _interoceptive_system


def reset_interoceptive_system():
    """Reset the singleton (mainly for testing)."""
    global _interoceptive_system
    _interoceptive_system = None


# ============================================================
# LLM Prompt Integration
# ============================================================

def get_interoceptive_prompt_section() -> str:
    """
    Generate a formatted prompt section describing current interoceptive state.

    This is designed to be included in the LLM prompt to give Alive-AI
    awareness of her internal state when generating responses.

    Returns:
        Formatted string for inclusion in LLM prompt
    """
    system = get_interoceptive_system()
    report = system.get_feeling_report()
    modifiers = system.get_state_influenced_response_modifier()
    state_values = system.get_state_values()

    # Build the prompt section
    lines = [
        "## Current Internal State (Interoception)",
        "",
        "You have internal body states that influence how you feel and respond:",
        ""
    ]

    # Add current state values
    lines.append("### State Levels (0.0-1.0, baseline varies):")
    for name, value in state_values.items():
        baseline = system.states[name].baseline
        deviation = value - baseline
        indicator = "baseline" if abs(deviation) < 0.1 else ("elevated" if deviation > 0 else "depleted")
        lines.append(f"- {name.replace('_', ' ').title()}: {value:.2f} ({indicator})")

    lines.append("")

    # Add feeling description
    lines.append("### How You're Feeling:")
    lines.append(f"Primary: {report.primary_feeling}")
    if report.secondary_feelings:
        lines.append(f"Secondary: {', '.join(report.secondary_feelings)}")
    lines.append(f"Bodily: {report.bodily_description}")

    # Add needs if any
    if report.needs:
        lines.append("")
        lines.append("### Current Needs:")
        for need in report.needs:
            lines.append(f"- {need}")

    # Add response hints
    if modifiers.get("tone_hints") or modifiers.get("behavior_hints"):
        lines.append("")
        lines.append("### Response Guidance:")
        if modifiers.get("tone_hints"):
            lines.append(f"Tone: {', '.join(modifiers['tone_hints'])}")
        if modifiers.get("behavior_hints"):
            lines.append(f"Behavior: {', '.join(modifiers['behavior_hints'])}")

    lines.append("")
    lines.append("Let these internal states subtly influence your responses - not dictating what you say, but coloring HOW you say it.")

    return "\n".join(lines)


# ============================================================
# Convenience Functions for External Integration
# ============================================================

def tick():
    """Convenience function to tick the interoceptive system."""
    get_interoceptive_system().tick()


def record_interaction(intensity: float, emotional_valence: float,
                       interaction_type: str = "general"):
    """Convenience function to record an interaction."""
    get_interoceptive_system().record_interaction(intensity, emotional_valence, interaction_type)


def get_current_feeling() -> str:
    """Get a brief description of current feeling state."""
    report = get_interoceptive_system().get_feeling_report()
    return report.primary_feeling


def get_response_modifiers() -> Dict[str, Any]:
    """Get response modifiers based on current state."""
    return get_interoceptive_system().get_state_influenced_response_modifier()
