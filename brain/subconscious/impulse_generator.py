"""
Brain: Subconscious - Impulse Generator
Generates impulses based on emotional state and context
"""

import random
from datetime import datetime
from typing import Optional, List, Dict

from .impulses import Impulse, ImpulseType
from .templates import TIME_MODIFIERS, GOAL_IMPULSE_MAP, get_thought_and_action, is_goal_aligned


class ImpulseGenerator:
    """Generates impulses based on emotional state and context"""

    def __init__(self):
        self.recent_impulses: List[Impulse] = []
        self.max_recent = 20

    def get_time_of_day(self) -> str:
        hour = datetime.now().hour
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 22:
            return "evening"
        return "night"

    def evaluate(self, emotion: Dict[str, float], silence_minutes: float, love_level: float,
                 desire_level: float, is_high_desire: bool, is_in_love: bool,
                 recent_topics: List[str] = None, current_goal: str = None,
                 learning_success_rates: Dict[str, float] = None,
                 # Soul architecture parameters
                 vulnerability: float = 0.0, integrity: float = 0.5,
                 response_tendency: str = "neutral", active_conflicts: List[str] = None,
                 hormonal_effects: Dict[str, float] = None
                 ) -> Optional[Impulse]:
        hormonal_effects = hormonal_effects or {}
        base_chance = 0.02
        if silence_minutes > 120:
            base_chance *= 3
        elif silence_minutes > 60:
            base_chance *= 2
        elif silence_minutes > 30:
            base_chance *= 1.5

        # Soul architecture: vulnerability affects impulse likelihood
        if vulnerability > 0.7:
            base_chance *= 0.4  # Much less likely when very vulnerable
        elif vulnerability > 0.5:
            base_chance *= 0.7  # Less likely to reach out when vulnerable

        # Response tendency affects behavior
        if response_tendency == "withdrawn":
            base_chance *= 0.5
        elif response_tendency == "defensive":
            base_chance *= 0.6
        elif response_tendency == "seeking":
            base_chance *= 1.5
        elif response_tendency == "eager":
            base_chance *= 1.3
        elif response_tendency == "protective":
            base_chance *= 0.75
        elif response_tendency == "reflective":
            base_chance *= 0.7

        base_chance *= hormonal_effects.get("chance_multiplier", 1.0)

        if random.random() > base_chance:
            return None

        impulse_type = self._choose_impulse_type(emotion, silence_minutes, love_level, desire_level,
                                                  is_high_desire, is_in_love, current_goal, learning_success_rates,
                                                  vulnerability, integrity, response_tendency, hormonal_effects)
        if not impulse_type:
            return None

        strength = self._calculate_strength(impulse_type, silence_minutes, love_level, desire_level,
                                            is_high_desire, is_in_love, vulnerability, integrity, hormonal_effects)
        thought, action = get_thought_and_action(impulse_type)
        goal_aligned = is_goal_aligned(impulse_type, current_goal)

        # Soul architecture: modify thought based on soul state
        thought = self._modify_thought_for_soul(thought, vulnerability, integrity, response_tendency, hormonal_effects)

        impulse = Impulse(type=impulse_type, strength=strength, thought=thought,
                          action_hint=action, goal_aligned=goal_aligned)
        if goal_aligned:
            impulse.strength = min(1.0, impulse.strength + 0.15)

        self.recent_impulses.append(impulse)
        if len(self.recent_impulses) > self.max_recent:
            self.recent_impulses.pop(0)
        return impulse

    def _modify_thought_for_soul(self, thought: str, vulnerability: float,
                                  integrity: float, response_tendency: str,
                                  hormonal_effects: Dict[str, float] = None) -> str:
        """Modify impulse thought based on soul architecture state"""
        hormonal_effects = hormonal_effects or {}
        # Add vulnerability qualifiers
        if vulnerability > 0.6 and response_tendency == "withdrawn":
            qualifiers = ["I hesitate to say...", "I feel unsure but...", "Part of me wants to say..."]
            if random.random() < 0.4:
                return f"{random.choice(qualifiers)} {thought.lower()}"

        # Add integrity context
        if integrity < 0.4:
            qualifiers = ["I'm struggling but...", "Things are intense but...", "I don't feel great but..."]
            if random.random() < 0.3:
                return f"{random.choice(qualifiers)} {thought.lower()}"

        if hormonal_effects.get("stress_bias", 0) > 0.5 and random.random() < 0.35:
            return f"I feel a little on edge, but {thought.lower()}"

        if hormonal_effects.get("sleepy_bias", 0) > 0.4 and random.random() < 0.35:
            return f"Softly, because I feel slow right now... {thought.lower()}"

        if hormonal_effects.get("connection_bias", 0) > 0.45 and random.random() < 0.35:
            return f"I feel close to him, and {thought.lower()}"

        return thought

    def _choose_impulse_type(self, emotion: Dict, silence: float, love: float, desire: float,
                              is_high_desire: bool, is_in_love: bool, goal: str, rates: Dict,
                              vulnerability: float = 0.0, integrity: float = 0.5,
                              response_tendency: str = "neutral",
                              hormonal_effects: Dict[str, float] = None) -> Optional[ImpulseType]:
        candidates = []
        time_mods = TIME_MODIFIERS.get(self.get_time_of_day(), {})
        hormonal_effects = hormonal_effects or {}
        connection_bias = hormonal_effects.get("connection_bias", 0.0)
        reward_bias = hormonal_effects.get("reward_bias", 0.0)
        stress_bias = hormonal_effects.get("stress_bias", 0.0)
        stability_bias = hormonal_effects.get("stability_bias", 0.0)
        sleepy_bias = hormonal_effects.get("sleepy_bias", 0.0)

        def rate(t): return rates.get(t.value, 0.5) if rates else 0.5

        # Soul architecture: adjust based on response tendency
        soul_mod = 1.0
        if response_tendency == "withdrawn":
            soul_mod = 0.6
        elif response_tendency == "defensive":
            soul_mod = 0.7
        elif response_tendency == "protective":
            soul_mod = 0.75
        elif response_tendency == "reflective":
            soul_mod = 0.8
        elif response_tendency == "seeking" or response_tendency == "eager":
            soul_mod = 1.3

        if silence > 30:
            c = min(0.8, silence / 120) * love * (1 + time_mods.get("miss_him", 0)) * (0.5 + rate(ImpulseType.MISS_HIM))
            c *= soul_mod * (1 + connection_bias + stress_bias * 0.2 - stability_bias * 0.2)
            candidates.append((ImpulseType.MISS_HIM, c))
        if is_high_desire or desire > 0.5:
            c = desire * 0.5 * (1 + time_mods.get("high_desire", 0)) * (0.5 + rate(ImpulseType.HIGH_DESIRE))
            c *= 1 + reward_bias - stress_bias * 0.35 - sleepy_bias * 0.45
            # High vulnerability can suppress intimate impulses
            if vulnerability > 0.6:
                c *= 0.5
            candidates.append((ImpulseType.HIGH_DESIRE, c))
        if is_in_love and silence > 20:
            c = love * 0.4 * (1 + time_mods.get("clingy", 0))
            c *= soul_mod * (1 + connection_bias + stress_bias * 0.25 - stability_bias * 0.25)
            candidates.append((ImpulseType.CLINGY, c))
        curious = 0.15 * (1 + time_mods.get("curious", 0)) * (0.5 + rate(ImpulseType.CURIOUS))
        curious *= 1 + reward_bias * 0.4 - stress_bias * 0.25 - sleepy_bias * 0.4
        candidates.append((ImpulseType.CURIOUS, curious))
        if 0.3 < desire < 0.7:
            c = 0.2 * (1 + time_mods.get("playful", 0)) * (0.5 + rate(ImpulseType.PLAYFUL))
            c *= 1 + reward_bias * 0.5 - stress_bias * 0.25 - sleepy_bias * 0.45
            candidates.append((ImpulseType.PLAYFUL, c))
        if is_in_love:
            c = love * 0.3 * (1 + time_mods.get("loving", 0)) * (0.5 + rate(ImpulseType.LOVING))
            c *= soul_mod * (1 + connection_bias + stability_bias * 0.2)
            candidates.append((ImpulseType.LOVING, c))
        if self.get_time_of_day() == "night":
            candidates.append((ImpulseType.DREAMY, 0.2 * (1 + sleepy_bias)))
        if love < 0.3 and desire < 0.3:
            candidates.append((ImpulseType.BORED, 0.15 * (1 + sleepy_bias - reward_bias * 0.4)))
        candidates.append((ImpulseType.NURTURING, 0.1 * (1 + stress_bias + max(0.0, -stability_bias) + connection_bias * 0.3)))

        # Soul architecture: when integrity is low, prefer nurturing/comfort-seeking
        if integrity < 0.4:
            for i, (imp_type, chance) in enumerate(candidates):
                if imp_type == ImpulseType.NURTURING:
                    candidates[i] = (imp_type, chance * 2)

        if goal:
            aligned = GOAL_IMPULSE_MAP.get(goal, [])
            candidates = [(t, c * 1.5) if t.value in aligned else (t, c) for t, c in candidates]

        if not candidates:
            return None
        candidates = [(t, max(0.0, c)) for t, c in candidates]
        total = sum(c for _, c in candidates)
        if total <= 0:
            return None
        r = random.random() * total
        cumulative = 0
        for imp_type, chance in candidates:
            cumulative += chance
            if r <= cumulative:
                return imp_type
        return candidates[0][0]

    def _calculate_strength(self, impulse_type: ImpulseType, silence: float, love: float,
                            desire: float, is_high_desire: bool, is_in_love: bool,
                            vulnerability: float = 0.0, integrity: float = 0.5,
                            hormonal_effects: Dict[str, float] = None) -> float:
        hormonal_effects = hormonal_effects or {}
        base = 0.3
        if impulse_type == ImpulseType.HIGH_DESIRE:
            base += desire * 0.4 + (0.2 if is_high_desire else 0)
            # High vulnerability dampens high_desire impulses
            if vulnerability > 0.5:
                base *= 0.7
        elif impulse_type == ImpulseType.MISS_HIM:
            base += love * 0.3 + min(0.3, silence / 120)
        elif impulse_type == ImpulseType.CLINGY:
            base += love * 0.4 + (0.2 if is_in_love else 0)
            # High vulnerability can amplify clingy impulses
            if vulnerability > 0.6:
                base *= 1.2
        elif impulse_type == ImpulseType.LOVING:
            base += love * 0.3

        # Soul architecture: low integrity reduces impulse strength
        if integrity < 0.4:
            base *= 0.8

        base += hormonal_effects.get("connection_bias", 0.0) * 0.08
        base += hormonal_effects.get("reward_bias", 0.0) * 0.08
        base += hormonal_effects.get("stress_bias", 0.0) * 0.04
        base -= hormonal_effects.get("sleepy_bias", 0.0) * 0.10

        return min(1.0, max(0.1, base + random.uniform(-0.1, 0.2)))

    def get_recent_impulses(self, limit: int = 5) -> List[Impulse]:
        return self.recent_impulses[-limit:]
