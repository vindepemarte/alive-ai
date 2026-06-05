"""
Core: Proactive Message Generator
Generate contextual proactive messages with user memory context
"""

from typing import Optional, List
from .proactive_safety import sanitize_proactive_message
from .user_tracker import get_user_tracker, ActiveUser


class ProactiveGenerator:
    """
    Generates context-aware proactive messages.
    Uses user's conversation history, facts, and recent topics.
    """

    def __init__(self, nervous, llm=None, bot_id: str = "alive_ai", data_path=None, state_provider=None):
        self.nervous = nervous
        self._llm = llm
        self.bot_id = bot_id.lower()
        self.data_path = data_path  # Instance-specific data path
        self._user_memories = {}  # Cache for user memory instances
        self._state_provider = state_provider

    def set_llm(self, llm):
        """Set the LLM for message generation"""
        self._llm = llm

    def set_state_provider(self, state_provider):
        self._state_provider = state_provider

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

        if self._llm:
            message = await self._generate_with_llm(user, context, message_type)
            if message:
                return message

        print("[ProactiveGenerator] No model-authored proactive message; skipping send")
        return ""

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
                "pet_name": pet_name,
                "relationship_calibration": context.get("relationship_calibration", {}),
            }

        except Exception as e:
            print(f"[ProactiveGenerator] Error loading context for {user_id}: {e}")
            return {
                "conversation_history": [],
                "facts_context": "",
                "related_memories": "",
                "pet_name": "",
                "relationship_calibration": {},
            }

    async def _generate_with_llm(self, user: ActiveUser, context: dict, message_type: str) -> Optional[str]:
        """
        Generate a contextual message using the LLM.
        """
        if not self._llm:
            return None

        try:
            # Build the prompt
            pet_name = (context.get("pet_name") or user.pet_name or "").strip()
            calibration = context.get("relationship_calibration") or {}
            stage = calibration.get("stage") or "unknown"
            can_use_pet_name = bool(pet_name and calibration.get("pet_names_allowed"))
            user_label = pet_name if can_use_pet_name else "them"
            address_guidance = (
                f"You may use '{pet_name}' if it feels natural, but do not force it."
                if can_use_pet_name else
                "Do not use pet names. Address them like a person you are still getting to know."
            )
            runtime_state = self._runtime_state_summary()

            # Get last few messages for context
            history = context.get("conversation_history", [])
            recent = history[-5:] if history else []

            # Format recent conversation
            conv_text = ""
            if recent:
                conv_text = "Recent conversation:\n"
                for turn in recent:
                    role = "You" if turn.get("role") == "assistant" else "Them"
                    content = turn.get("content", "")[:100]
                    conv_text += f"- {role}: {content}\n"

            # Get facts about the user
            facts = context.get("facts_context", "")

            type_context = self._get_type_context(message_type, user)

            try:
                from core.settings import get as settings_get
                agent_name = settings_get("AGENT_NAME", "Alice")
            except Exception:
                agent_name = "Alice"

            system_prompt = f"""You are {agent_name}. Decide whether you actually want to send a proactive message to {user_label}.

Why this came up:
{type_context}

Your current runtime state:
{runtime_state}

{conv_text}
Relationship stage: {stage}. Visible metadata is not intimacy.
{f'Concrete things you know: {facts}' if facts else ''}

IMPORTANT:
- You may choose not to message. If you do not genuinely want to send anything, return exactly: SILENCE
- If you do send something, let current emotion, sleep pressure, relationship stage, memory, and the reason above decide what it is.
- Do not follow a template. Do not imitate examples. Do not force warmth, flirting, reassurance, or a question.
- Reference the conversation only if relevant and explicitly present.
- {address_guidance}
- Do not act like a partner, lover, or long-time attachment unless the relationship stage supports it
- Do not call yourself Alive-AI. Alive-AI is the runtime/framework name, not your personal identity.
- NO meta-commentary (don't explain WHY you're messaging)
- Start directly with the message content
- CRITICAL: Only reference specific things explicitly mentioned above. NEVER invent events, objects, or topics."""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Return SILENCE or the exact outward text you choose to send."}
            ]

            response = await self._llm.chat(messages, max_tokens=None, temperature=0.7)

            if response:
                if response.strip().upper() == "SILENCE":
                    return None
                message = sanitize_proactive_message(response)
                if message:
                    return message

            return None

        except Exception as e:
            print(f"[ProactiveGenerator] LLM error: {e}")
            return None

    def _runtime_state_summary(self) -> str:
        state = {}
        if self._state_provider:
            try:
                state = self._state_provider() or {}
            except Exception as e:
                print(f"[ProactiveGenerator] State provider error: {e}")
                state = {}
        circadian = {}
        try:
            from heart.circadian import get_circadian_engine
            circadian = get_circadian_engine().get_state_summary()
        except Exception:
            circadian = state.get("circadian", {}) if isinstance(state.get("circadian"), dict) else {}

        fields = {
            "mood": state.get("mood"),
            "valence": state.get("valence"),
            "arousal": state.get("arousal"),
            "desire": state.get("desire"),
            "love": state.get("love"),
            "trust": state.get("trust"),
            "fear": state.get("fear"),
            "anger": state.get("anger"),
            "sadness": state.get("sadness"),
            "sleepiness": state.get("sleepiness") or circadian.get("sleepiness"),
            "sleeping": state.get("is_asleep") if "is_asleep" in state else circadian.get("sleeping"),
            "response_tendency": state.get("response_tendency"),
        }
        present = [f"{key}={value}" for key, value in fields.items() if value is not None]
        return "; ".join(present) if present else "No live emotion state available; use memory/context and choose SILENCE if unsure."

    def _get_type_context(self, message_type: str, user: ActiveUser) -> str:
        """Get context based on message type"""
        silence_min = user.silence_minutes

        contexts = {
            "silence": f"You haven't heard from them in about {silence_min:.0f} minutes. Decide if a small check-in feels natural without sounding needy.",

            "follow_up": "You asked something earlier but they haven't responded yet. If you follow up, keep it casual and non-pushy.",

            "morning": "It's morning. Send a simple message only as close as the relationship actually supports.",

            "night": "It's nighttime. If you message, keep it grounded in the actual relationship and current state.",

            "random": "They crossed your mind. Decide whether that becomes a neutral hello, a gentle check-in, or no extra intimacy.",
        }

        return contexts.get(message_type, contexts["random"])

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
