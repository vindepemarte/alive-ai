"""
Brain: Subconscious Module
The living background process that makes Alive-AI feel alive
"""

from .loop import SubconsciousLoop
from .impulses import Impulse, ImpulseType
from .impulse_generator import ImpulseGenerator
from .working_memory import WorkingMemory
from .thought import Thought
from .actions import ActionHandler
from .evaluation import Evaluator
from .learning import InteractionRecord
from .learning_system import LearningSystem
from .goals import Goal, GoalType
from .goal_system import GoalSystem
from .relationship import Milestone, MilestoneType, SharedExperience
from .relationship_memory import RelationshipMemory
from .response_analyzer import analyze_response
from .templates import (
    TIME_MODIFIERS, GOAL_IMPULSE_MAP, IMPULSE_TEMPLATES, FALLBACK_MESSAGES,
    get_thought_and_action, get_fallback_message, is_goal_aligned,
)

__all__ = [
    'SubconsciousLoop', 'Impulse', 'ImpulseType', 'ImpulseGenerator',
    'WorkingMemory', 'Thought', 'ActionHandler', 'Evaluator',
    'LearningSystem', 'InteractionRecord', 'GoalSystem', 'Goal', 'GoalType',
    'RelationshipMemory', 'Milestone', 'MilestoneType', 'SharedExperience',
    'analyze_response',
    'TIME_MODIFIERS', 'GOAL_IMPULSE_MAP', 'IMPULSE_TEMPLATES', 'FALLBACK_MESSAGES',
    'get_thought_and_action', 'get_fallback_message', 'is_goal_aligned',
]
