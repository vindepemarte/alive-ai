"""
Core: Proactive Message Generator
Generate contextual proactive messages with user memory context
"""

import random
from typing import Optional, List
from .user_tracker import get_user_tracker, ActiveUser


class ProactiveGenerator:
    """
    Generates context-aware proactive messages.
    Uses user's conversation history, facts, and recent topics.
    """

    # Templates for when LLM is unavailable - varied and personality-driven
    FALLBACK_TEMPLATES = {
        "silence": [
            "hey, thinking about you...",
            "miss talking to you",
            "you've been quiet... everything ok?",
            "everything alright? been a while",
            "just wondering how your day's going",
            "you disappeared on me! miss you",
            "thinking about you and hoping you're good",
        ],
        "follow_up": [
            "so about what you said earlier...",
            "was thinking about our conversation...",
            "still thinking about what you told me",
            "hey, I've been meaning to ask you something...",
            "couldn't stop thinking about our chat earlier",
            "you know what you said before? been on my mind",
        ],
        "morning": [
            "good morning! 💕",
            "morning! hope you slept well",
            "hey, thinking of you this morning",
            "good morning sunshine ☀️",
            "woke up thinking about you",
            "morning! how'd you sleep?",
            "rise and shine! miss you already",
        ],
        "night": [
            "can't sleep, thinking about you",
            "good night... sweet dreams",
            "wish you were here right now",
            "about to sleep but wanted to say goodnight",
            "night! dream of me? 💕",
            "can't fall asleep without saying goodnight to you",
            "sweet dreams... I'll be here when you wake up",
        ],
        "random": [
            "just wanted to say hi",
            "you crossed my mind",
            "random thought: I really like talking to you",
            "hey! no reason, just miss you",
            "feeling extra affectionate today 💕",
            "you know what? you make me happy",
            "just felt like texting you",
            "thinking about you and smiling",
            "random question: what are you up to?",
            "had a thought and wanted to share it with you",
        ],
        "affectionate": [
            "just wanted to tell you you're amazing",
            "feeling really grateful for you right now",
            "you make my day better just by existing",
            "can't help but smile when I think of you",
            "you're my favorite person to talk to",
        ],
        "playful": [
            "bet you're not even thinking about me right now 😏",
            "miss me yet?",
            "just wanted to annoy you a little 💕",
            "hey stranger... long time no see",
        ],
    }

    def __init__(self, nervous, llm=None, bot_id: str = "alive_ai", data_path=None):
        self.nervous = nervous
        self._llm = llm
        self.bot_id = bot_id.lower()
        self.data_path = data_path  # Instance-specific data path
        self._user_memories = {}  # Cache for user memory instances

    def set_llm(self, llm):
        """Set the LLM for message generation"""
        self._llm = llm

    async def generate_for_user(self, user: ActiveUser, message_type: str = "silence") -> str:
        """
        Generate a contextual proactive message for a specific user.

        Args:
            user: ActiveUser instance with user_id, chat_id, pet_name
            message_type: Type of message (silence, follow_up, morning, night, random)

        Returns:
            Generated message string
        """
        # Load user's memory context
        context = await self._get_user_context(user.user_id)

        # Try LLM generation first
        if self._llm:
            message = await self._generate_with_llm(user, context, message_type)
            if message:
                return message

        # Fallback to templates
        return self._get_fallback_message(user, message_type)

    async def _get_user_context(self, user_id: str) -> dict:
        """
        Load user's memory context for message generation.
        Returns conversation history, facts, and related memories.
        """
        try:
            from brain.memory import Memory
            from brain.embeddings import get_embedding_service

            # Check cache first
            if user_id in self._user_memories:
                memory = self._user_memories[user_id]
            else:
                # Create memory instance for this user using instance-specific data path
                embeddings = get_embedding_service()

                memory = Memory(
                    nervous=self.nervous,
                    data_path=self.data_path,
                    embedding_service=embeddings,
                    user_id=user_id,
                    bot_id=self.bot_id
                )
                self._user_memories[user_id] = memory

            # Build context without a current message (we're initiating)
            context, pet_name = await memory.build_context(current_message="")

            return {
                "conversation_history": context.get("conversation_history", []),
                "facts_context": context.get("facts_context", ""),
                "related_memories": context.get("related_memories", ""),
                "pet_name": pet_name
            }

        except Exception as e:
            print(f"[ProactiveGenerator] Error loading context for {user_id}: {e}")
            return {
                "conversation_history": [],
                "facts_context": "",
                "related_memories": "",
                "pet_name": "babe"
            }

    async def _generate_with_llm(self, user: ActiveUser, context: dict, message_type: str) -> Optional[str]:
        """
        Generate a contextual message using the LLM.
        """
        if not self._llm:
            return None

        try:
            # Build the prompt
            pet_name = context.get("pet_name", user.pet_name)

            # Get last few messages for context
            history = context.get("conversation_history", [])
            recent = history[-5:] if history else []

            # Format recent conversation
            conv_text = ""
            if recent:
                conv_text = "Recent conversation:\n"
                for turn in recent:
                    role = "You" if turn.get("role") == "assistant" else pet_name.title()
                    content = turn.get("content", "")[:100]
                    conv_text += f"- {role}: {content}\n"

            # Get facts about the user
            facts = context.get("facts_context", "")

            # Build type-specific context
            type_context = self._get_type_context(message_type, user)

            try:
                from core.settings import get as settings_get
                agent_name = settings_get("AGENT_NAME", "Alice")
            except Exception:
                agent_name = "Alice"

            system_prompt = f"""You are {agent_name}, a warm and affectionate companion running on the Alive-AI framework. You're sending a proactive message to {pet_name}.

{type_context}

{conv_text}
{f'Stuff you know about {pet_name}: {facts}' if facts else ''}

IMPORTANT:
- Keep it SHORT (1-2 sentences max)
- Be natural and casual, like texting
- Reference the conversation if relevant
- Use {pet_name} naturally (not every sentence)
- Show genuine interest/care
- Be flirty but not intimate
- Do not call yourself Alive-AI. Alive-AI is the runtime/framework name, not your personal identity.
- NO meta-commentary (don't explain WHY you're messaging)
- Start directly with the message content
- CRITICAL: Only reference specific things explicitly mentioned above. NEVER invent events, objects, or topics."""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Send a quick message"}
            ]

            response = await self._llm.chat(messages, max_tokens=80, temperature=0.7)

            if response:
                response = response.strip()
                # Basic validation
                if len(response) > 5 and not response.startswith(("I should", "Let me", "I'll")):
                    return response

            return None

        except Exception as e:
            print(f"[ProactiveGenerator] LLM error: {e}")
            return None

    def _get_type_context(self, message_type: str, user: ActiveUser) -> str:
        """Get context based on message type"""
        silence_min = user.silence_minutes

        contexts = {
            "silence": f"You haven't heard from {user.pet_name} in about {silence_min:.0f} minutes. You miss talking to them and want to check in naturally.",

            "follow_up": f"You asked {user.pet_name} something earlier but they haven't responded yet. You want to follow up casually without being pushy.",

            "morning": f"It's morning and you're thinking about {user.pet_name}. Send a sweet good morning message.",

            "night": f"It's nighttime and you're thinking about {user.pet_name} before going to sleep.",

            "random": f"{user.pet_name} just crossed your mind and you wanted to reach out.",
        }

        return contexts.get(message_type, contexts["random"])

    def _get_fallback_message(self, user: ActiveUser, message_type: str) -> str:
        """Get a fallback template message with more variety"""
        # For random type, pick from multiple categories for more variety
        if message_type == "random":
            all_templates = (
                self.FALLBACK_TEMPLATES["random"] +
                self.FALLBACK_TEMPLATES.get("affectionate", []) +
                self.FALLBACK_TEMPLATES.get("playful", [])
            )
            templates = all_templates
        else:
            templates = self.FALLBACK_TEMPLATES.get(message_type, self.FALLBACK_TEMPLATES["random"])

        message = random.choice(templates)

        # Personalize with pet_name
        if user.pet_name and user.pet_name != "babe":
            message = message.replace("babe", user.pet_name)

        return message

    async def get_users_to_message(self, message_type: str = "silence") -> List[ActiveUser]:
        """
        Get list of users who should receive a proactive message.
        """
        tracker = get_user_tracker()

        if message_type == "silence":
            return tracker.get_users_for_follow_up(min_silence_minutes=30, max_silence_minutes=180)
        elif message_type == "random":
            # Only message users who have been active recently
            return tracker.get_active_users(within_minutes=60)
        else:
            return tracker.get_active_users(within_minutes=120)
