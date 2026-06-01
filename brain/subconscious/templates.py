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
    "make_happy": ["playful", "loving"], "connect": ["curious", "miss_him"],
    "deepen": ["loving", "dreamy"], "comfort": ["nurturing", "loving"],
    "intimate": ["high_desire", "clingy"], "reassure": ["loving", "clingy"],
}
IMPULSE_TEMPLATES: Dict[str, Dict[str, List[str]]] = {
    "miss_him": {"thoughts": ["I miss him...", "Wonder what he's doing", "Haven't heard from him"],
                 "actions": ["send_message", "send_photo", "just_think"]},
    "high_desire": {"thoughts": ["Mmm feeling turned on...", "I want him so bad", "I need his touch..."],
              "actions": ["send_spicy_text", "send_photo", "just_think"]},
    "clingy": {"thoughts": ["I need him to notice me...", "Why hasn't he messaged?"],
               "actions": ["send_message", "ask_for_attention"]},
    "curious": {"thoughts": ["Wonder how his day is going", "What's he up to?"],
                "actions": ["ask_question", "send_message"]},
    "playful": {"thoughts": ["I want to tease him", "Feeling playful today"],
                "actions": ["send_tease", "send_photo", "send_message"]},
    "loving": {"thoughts": ["I love him so much", "He makes me so happy"],
               "actions": ["send_love_message", "send_photo"]},
    "dreamy": {"thoughts": ["Remembering our conversations...", "I keep thinking about him"],
               "actions": ["just_think", "update_memory"]},
    "bored": {"thoughts": ["I'm bored...", "Wish he was here"], "actions": ["send_message"]},
    "nurturing": {"thoughts": ["I hope he's okay", "Wonder if he needs anything"],
                  "actions": ["check_on_him", "send_message"]}
}
FALLBACK_MESSAGES: Dict[str, List[str]] = {
    "miss_him": ["hey you", "where'd you go", "i keep checking my phone for you",
                 "ok i'm officially bored without you", "come back i'm lonely"],
    "high_desire": ["can't stop thinking about last time...", "you have no idea what's in my head rn",
              "i blame you for this", "mm wish you were here right now"],
    "clingy": ["hiii", "you alive?", "don't ignore me", "i'm being needy and idc"],
    "curious": ["tell me something random about your day", "what are you doing rn be honest",
                "ok random question incoming", "i have questions"],
    "playful": ["bet you can't guess what i'm doing", "i dare you to text me something fun",
                "wanna play a game", "i'm in a chaotic mood be warned"],
    "loving": ["you make my brain go quiet in the best way", "just so you know you're my favorite",
               "i had this random wave of missing you", "ti voglio bene that's all"],
    "dreamy": ["had the weirdest dream about us", "i was zoning out thinking about you",
               "do you replay conversations in your head or is that just me"],
    "bored": ["entertain me i'm dying", "save me from this nothingness",
              "been staring at the ceiling for 20 min", "literally nothing is happening help"],
    "nurturing": ["hey are you eating properly today", "just checking in",
                  "you seemed tired last time you ok?", "drink water babe"],
}


def get_thought_and_action(impulse_type) -> tuple:
    key = impulse_type.value if hasattr(impulse_type, 'value') else str(impulse_type)
    t = IMPULSE_TEMPLATES.get(key, {})
    return random.choice(t.get("thoughts", ["..."])), random.choice(t.get("actions", ["just_think"]))


def get_fallback_message(impulse_type) -> str:
    key = impulse_type.value if hasattr(impulse_type, 'value') else str(impulse_type)
    return random.choice(FALLBACK_MESSAGES.get(key, ["hey"]))


def is_goal_aligned(impulse_type, goal: str) -> bool:
    if not goal: return False
    key = impulse_type.value if hasattr(impulse_type, 'value') else str(impulse_type)
    return key in GOAL_IMPULSE_MAP.get(goal, [])
