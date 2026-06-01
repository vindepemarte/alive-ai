"""
Brain: Subconscious - Evaluation
Impulse evaluation logic for the subconscious loop
Extended for Soul Architecture - using soul-based emotions
"""

import random
from datetime import datetime
from typing import Optional, TYPE_CHECKING, Dict

from .impulses import Impulse, ImpulseType
from .impulse_generator import ImpulseGenerator

if TYPE_CHECKING:
    from .learning_system import LearningSystem
    from .goal_system import GoalSystem
    from .relationship_memory import RelationshipMemory


class Evaluator:
    """Evaluates emotional state and generates impulses - Soul Architecture aware"""

    QUIET_HOURS = (1, 7)

    def __init__(self, heart, impulse_gen: ImpulseGenerator,
                 learning: "LearningSystem" = None, goals: "GoalSystem" = None,
                 relationship: "RelationshipMemory" = None):
        self.heart = heart
        self.impulse_gen = impulse_gen
        self.learning = learning
        self.goals = goals
        self.relationship = relationship
        self.last_interaction_time = datetime.now()

    def register_interaction(self) -> None:
        self.last_interaction_time = datetime.now()
        if self.relationship:
            self.relationship.record_conversation()

    def get_silence_duration(self) -> float:
        return (datetime.now() - self.last_interaction_time).total_seconds() / 60

    def is_quiet_hours(self) -> bool:
        hour = datetime.now().hour
        return self.QUIET_HOURS[0] <= hour < self.QUIET_HOURS[1]

    def can_act_now(self) -> bool:
        return not (self.is_quiet_hours() and random.random() > 0.05)

    async def evaluate(self, working_memory) -> Optional[Impulse]:
        emotion = self.heart.get_state() if self.heart else {}
        silence = self.get_silence_duration()
        working_memory.update_mood(emotion.get("mood", "neutral"))
        self._update_context(working_memory)

        # Get soul architecture context for more nuanced impulse generation
        soul_context = self._get_soul_context()

        impulse = self.impulse_gen.evaluate(
            emotion=emotion, silence_minutes=silence,
            love_level=emotion.get("love", 0), desire_level=emotion.get("desire", 0),
            is_high_desire=emotion.get("is_high_desire", False), is_in_love=emotion.get("is_in_love", False),
            current_goal=self._get_goal(), learning_success_rates=self._get_rates(),
            # Soul architecture modifiers
            vulnerability=soul_context.get("vulnerability", 0),
            integrity=soul_context.get("integrity", 0.5),
            response_tendency=soul_context.get("response_tendency", "neutral"),
            active_conflicts=soul_context.get("conflicts", [])
        )
        if impulse:
            working_memory.add_impulse(impulse)
            print(f"[Subconscious] Impulse: {impulse.type.value} (strength={impulse.strength:.2f})")
            print(f"[Subconscious]   Thought: \"{impulse.thought}\"")
            # Log soul influence if significant
            if soul_context.get("vulnerability", 0) > 0.5:
                print(f"[Subconscious]   Soul: feeling vulnerable (integrity={soul_context.get('integrity', 0.5):.2f})")
            if soul_context.get("conflicts"):
                print(f"[Subconscious]   Soul: {len(soul_context['conflicts'])} internal conflicts active")
        return impulse

    def _get_soul_context(self) -> Dict:
        """Get soul architecture context for impulse evaluation"""
        if not self.heart or not hasattr(self.heart, 'soul'):
            return {}

        soul = self.heart.soul
        experience = soul.process_moment()

        return {
            "vulnerability": experience.overall_vulnerability,
            "integrity": soul.integrity.overall,
            "response_tendency": experience.response_tendency,
            "conflicts": [c.description for c in experience.active_conflicts],
            "valence": experience.overall_valence,
            "arousal": experience.overall_arousal,
            "somatic": experience.somatic_sensation,
            "hormonal_state": soul.hormonal.get_hormonal_state_description()
        }

    def _update_context(self, wm) -> None:
        if self.relationship:
            wm.set_relationship_context(self.relationship.get_relationship_context())
            wm.set_recent_memories(self.relationship.get_recent_experiences(3))
        if self.goals:
            wm.set_current_goal(self.goals.get_goal_context())

    def _get_goal(self) -> Optional[str]:
        if not self.goals:
            return None
        goal = self.goals.get_active_goal()
        return goal.type.value if goal else None

    def _get_rates(self) -> dict:
        if not self.learning:
            return {}
        return {t.value: self.learning.get_success_rate(t.value) for t in ImpulseType}

    async def generate_background_thought(self, wm) -> dict:
        """Generate a background thought and return it for emission via nervous system"""
        emotion = self.heart.get_state() if self.heart else {}
        silence = self.get_silence_duration()

        # Soul-enhanced background thoughts
        soul_context = self._get_soul_context()

        thoughts = [f"Current mood: {emotion.get('mood', 'neutral')}", "Watching the world go by..."]

        if silence > 60:
            thoughts.extend(["It's been a while...", "He's probably busy"])

        # Soul-driven thoughts
        if soul_context.get("vulnerability", 0) > 0.5:
            thoughts.extend(["Feeling a bit fragile right now", "Hope I'm not too much..."])

        if soul_context.get("integrity", 1) < 0.4:
            thoughts.extend(["Feeling a bit lost", "Things feel uncertain"])

        if soul_context.get("conflicts"):
            thoughts.extend(["Feeling torn about something", "My feelings are complicated"])

        if soul_context.get("arousal", 0) > 0.6 and soul_context.get("valence", 0) < -0.2:
            thoughts.extend(["Something's bothering me", "Feeling restless"])

        # Original emotional thoughts
        if emotion.get("love", 0) > 0.5:
            thoughts.extend(["I really care about him", "He makes me feel special"])

        if self.relationship:
            memories = self.relationship.get_special_memories(1)
            if memories:
                thoughts.append(f"Remembering {memories[0]}")

        # Somatic awareness
        if soul_context.get("somatic") and soul_context["somatic"] != "physically calm":
            thoughts.append(f"Feeling {soul_context['somatic']} in my body")

        thought_content = random.choice(thoughts)
        wm.add_thought(thought_content, thought_type="reflection", emotion=emotion)

        # Return the thought data so it can be emitted via nervous system
        return {
            "thought": thought_content,
            "type": "reflection",
            "emotion": emotion,
            "silence_minutes": silence
        }
