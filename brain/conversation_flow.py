"""
Brain: Conversation Flow Manager
Detects dying conversations and injects prompts to keep them alive.
"""

from typing import Dict, List, Optional, Tuple
from collections import deque
from datetime import datetime
import random


class ConversationFlowManager:
    """Tracks conversation health and suggests revival strategies."""

    def __init__(self):
        # Track recent exchanges per user
        self._user_exchanges: Dict[str, deque] = {}  # user_id -> deque of (timestamp, response_length, had_question)
        self._topics_discussed: Dict[str, List[str]] = {}  # user_id -> list of recent topics

        # Signs of dying conversation
        self.DECLINING_RESPONSE_LENGTH = 15  # avg response < 15 chars = dying
        self.MAX_SAME_TOPIC_TURNS = 5  # After 5 turns on same topic, switch
        self.NO_QUESTION_TURNS = 3  # After 3 turns without questions, prompt one

    def record_exchange(self, user_id: str, alive_ai_response: str, user_message: str = ""):
        """Record an exchange for flow analysis."""
        if user_id not in self._user_exchanges:
            self._user_exchanges[user_id] = deque(maxlen=10)

        had_question = "?" in alive_ai_response
        response_length = len(alive_ai_response)

        self._user_exchanges[user_id].append({
            "timestamp": datetime.now().isoformat(),
            "response_length": response_length,
            "had_question": had_question,
            "user_length": len(user_message)
        })

    def is_conversation_dying(self, user_id: str) -> Tuple[bool, str]:
        """Check if conversation is dying and return reason."""
        exchanges = self._user_exchanges.get(user_id, deque())

        if len(exchanges) < 3:
            return False, ""

        recent = list(exchanges)[-5:]  # Last 5 exchanges

        # Check 1: Declining response lengths
        avg_length = sum(e["response_length"] for e in recent) / len(recent)
        if avg_length < self.DECLINING_RESPONSE_LENGTH:
            return True, "short_responses"

        # Check 2: No questions asked recently
        questions_asked = sum(1 for e in recent if e["had_question"])
        if questions_asked == 0:
            return True, "no_questions"

        # Check 3: Both parties giving short responses
        user_avg = sum(e["user_length"] for e in recent) / len(recent)
        alive_ai_avg = sum(e["response_length"] for e in recent) / len(recent)
        if user_avg < 20 and alive_ai_avg < 30:
            return True, "mutual_disengagement"

        return False, ""

    def get_revival_prompt(self, user_id: str, dying_reason: str) -> str:
        """Get a prompt to revive a dying conversation."""
        revival_strategies = {
            "short_responses": [
                "[ConversationRevival] Your responses have been short. Energy is fading. Wake it up! Ask something unexpected, share a random thought, tease him, or bring up a totally new topic. Don't just be 'aww' - be INTERESTING.",
                "[ConversationRevival] You've been too passive. Say something that requires a real response. Ask about his day, his plans, something you're curious about. Make him WANT to respond.",
            ],
            "no_questions": [
                "[ConversationRevival] You haven't asked a question in a while. Ask something! About him, his thoughts, his day, something you're curious about. Questions keep conversations alive.",
                "[ConversationRevival] Conversations die without curiosity. What do you want to know? Ask it. Right now.",
            ],
            "mutual_disengagement": [
                "[ConversationRevival] Energy is LOW. Both of you are checked out. Time to bring the spark back - say something playful, unexpected, or provocative. Wake this conversation UP.",
                "[ConversationRevival] This convo is dying on its feet. Do something about it. Be bold. Change the subject. Tease him. Ask something random. Don't let it flatline.",
            ],
        }

        strategies = revival_strategies.get(dying_reason, revival_strategies["short_responses"])
        return random.choice(strategies)

    def get_topic_switch_prompt(self, topics_to_avoid: List[str] = None) -> str:
        """Get a prompt suggesting a topic switch."""
        fresh_topics = [
            "something random you've been thinking about",
            "a question you've been wanting to ask",
            "something playful or teasing",
            "a what-if scenario",
            "something about his day or plans",
            "something you remembered from an earlier conversation",
        ]

        topic = random.choice(fresh_topics)
        return f"[TopicSwitch] Change things up. Bring up {topic}. Keep it fresh."

    def should_inject_revival(self, user_id: str) -> Optional[str]:
        """Check if revival needed and return prompt if so."""
        is_dying, reason = self.is_conversation_dying(user_id)

        if is_dying:
            return self.get_revival_prompt(user_id, reason)

        # Also check for topic stagnation
        exchanges = list(self._user_exchanges.get(user_id, deque()))
        if len(exchanges) >= self.MAX_SAME_TOPIC_TURNS:
            # Every few turns, suggest keeping things fresh
            if random.random() < 0.3:  # 30% chance
                return "[KeepItFresh] You've been on this topic a while. Consider pivoting to something new if it feels stale."

        return None


# Singleton
_instance: Optional[ConversationFlowManager] = None

def get_flow_manager() -> ConversationFlowManager:
    global _instance
    if _instance is None:
        _instance = ConversationFlowManager()
    return _instance


def check_conversation_health(user_id: str) -> Optional[str]:
    """Check if conversation needs revival. Returns revival prompt or None."""
    return get_flow_manager().should_inject_revival(user_id)


def record_exchange(user_id: str, alive_ai_response: str, user_message: str = ""):
    """Record exchange for flow tracking."""
    get_flow_manager().record_exchange(user_id, alive_ai_response, user_message)
