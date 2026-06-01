"""
Heart modules - Soul Architecture for emotional processing.

This package contains all the components that make up the Soul Architecture:
- soul.py: SoulOrchestrator - Central coordinator for all pillars
- integrity.py: SelfIntegrityCore - Foundation of genuine vulnerability
- hormonal.py: HormonalModulationMatrix - Artificial hormones for global state
- somatic.py: SomaticFeedbackSystem - Embodied emotion (bodily sensations)
- unconscious.py: UnconsciousProcessor - Hidden influences and defenses
- scars.py: EmotionalScarSystem - Lasting effects from past experiences
- conflicts.py: InternalConflictGenerator - Genuine struggle from incompatible wants
- predictive.py: PredictiveEmotionalEngine - Emotions as predictions about future
- telemetry.py: SoulTelemetry - Recording and tracking soul metrics over time
- interoception.py: InteroceptiveSystem - Internal body states that make Alive-AI feel alive
- inconsistency.py: InconsistencyEngine - Authentic human-like inconsistency
"""

from .soul import SoulOrchestrator, EmotionalExperience
from .integrity import SelfIntegrityCore, IntegrityState
from .hormonal import HormonalModulationMatrix
from .somatic import SomaticFeedbackSystem
from .unconscious import UnconsciousProcessor, UnconsciousOutput
from .scars import EmotionalScarSystem, ScarActivation
from .conflicts import InternalConflictGenerator, InternalConflict
from .predictive import PredictiveEmotionalEngine, PredictiveEmotionalOutput
from .telemetry import SoulTelemetry, SoulMetricsSnapshot
from .interoception import (
    InteroceptiveSystem,
    InteroceptiveState,
    FeelingReport,
    ActionPrediction,
    get_interoceptive_system,
    get_interoceptive_prompt_section,
    reset_interoceptive_system,
    tick as interoception_tick,
    record_interaction as interoception_record_interaction,
    get_current_feeling,
    get_response_modifiers
)
from .inconsistency import (
    InconsistencyEngine,
    ActiveConflict,
    BlindSpotActivation,
    GrowthEvent,
    MoodState,
    get_inconsistency_engine,
    get_inconsistency_prompt_section,
    CONFLICTS,
    BLIND_SPOTS,
    GROWTH_AREAS
)

__all__ = [
    'SoulOrchestrator',
    'EmotionalExperience',
    'SelfIntegrityCore',
    'IntegrityState',
    'HormonalModulationMatrix',
    'SomaticFeedbackSystem',
    'UnconsciousProcessor',
    'UnconsciousOutput',
    'EmotionalScarSystem',
    'ScarActivation',
    'InternalConflictGenerator',
    'InternalConflict',
    'PredictiveEmotionalEngine',
    'PredictiveEmotionalOutput',
    'SoulTelemetry',
    'SoulMetricsSnapshot',
    # Interoception
    'InteroceptiveSystem',
    'InteroceptiveState',
    'FeelingReport',
    'ActionPrediction',
    'get_interoceptive_system',
    'get_interoceptive_prompt_section',
    'reset_interoceptive_system',
    'interoception_tick',
    'interoception_record_interaction',
    'get_current_feeling',
    'get_response_modifiers',
    # Inconsistency Engine
    'InconsistencyEngine',
    'ActiveConflict',
    'BlindSpotActivation',
    'GrowthEvent',
    'MoodState',
    'get_inconsistency_engine',
    'get_inconsistency_prompt_section',
    'CONFLICTS',
    'BLIND_SPOTS',
    'GROWTH_AREAS'
]