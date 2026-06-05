"""Brain: Subconscious - Templates — thoughts, actions, fallbacks"""
import random
from typing import Dict, List

TIME_MODIFIERS: Dict[str, Dict[str, float]] = {
    "morning": {"high_desire": 0.3, "loving": 0.4, "curious": 0.3},
    "afternoon": {"bored": 0.3, "playful": 0.3},
    "evening": {"high_desire": 0.5, "clingy": 0.3, "loving": 0.4},
    "night": {"high_desire": 0.6, "dreamy": 0.5, "clingy": 0.4},
}
GOAL_IMPULSE_MAP: Dict[str, List[str]] = {
    "make_happy": ["playful"], "connect": ["curious"],
    "deepen": ["curious", "dreamy"], "comfort": ["nurturing"],
    "intimate": ["curious"], "reassure": ["nurturing"],
}
IMPULSE_TEMPLATES: Dict[str, Dict[str, List[str]]] = {
    "miss_him": {"thoughts": ["absence noticed", "contact gap registered", "social pull present"],
                 "actions": ["just_think"]},
    "high_desire": {"thoughts": ["approach energy present", "high arousal noticed", "body state intensified"],
              "actions": ["just_think"]},
    "clingy": {"thoughts": ["attachment anxiety noticed", "attention-seeking impulse noticed"],
               "actions": ["just_think"]},
    "curious": {"thoughts": ["curiosity rising", "unknowns about the person noticed"],
                "actions": ["ask_question", "just_think"]},
    "playful": {"thoughts": ["playful energy present", "lightness rising"],
                "actions": ["just_think"]},
    "loving": {"thoughts": ["warmth present", "care signal noticed"],
               "actions": ["just_think"]},
    "dreamy": {"thoughts": ["memory residue present", "conversation echo noticed"],
               "actions": ["just_think", "update_memory"]},
    "bored": {"thoughts": ["under-stimulation noticed", "novelty-seeking impulse present"], "actions": ["just_think"]},
    "nurturing": {"thoughts": ["care impulse present", "comfort impulse noticed"],
                  "actions": ["just_think"]}
}
FALLBACK_MESSAGES: Dict[str, List[str]] = {}


def get_thought_and_action(impulse_type) -> tuple:
    key = impulse_type.value if hasattr(impulse_type, 'value') else str(impulse_type)
    t = IMPULSE_TEMPLATES.get(key, {})
    return random.choice(t.get("thoughts", ["..."])), random.choice(t.get("actions", ["just_think"]))


def get_fallback_message(impulse_type) -> str:
    return ""


def is_goal_aligned(impulse_type, goal: str) -> bool:
    if not goal: return False
    key = impulse_type.value if hasattr(impulse_type, 'value') else str(impulse_type)
    return key in GOAL_IMPULSE_MAP.get(goal, [])
