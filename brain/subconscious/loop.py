"""Brain: Subconscious Loop — continuous background process"""
import asyncio, json, random
from datetime import datetime
from typing import Callable, Optional
from core.paths import state_file
from .impulses import Impulse, ImpulseType
from .impulse_generator import ImpulseGenerator
from .working_memory import WorkingMemory
from .evaluation import Evaluator
from .actions import ActionHandler
from .learning_system import LearningSystem
from .goal_system import GoalSystem
from .relationship_memory import RelationshipMemory
from .relationship import MilestoneType


def _subconscious_state_path(bot_id: str):
    safe_bot_id = "".join(ch if ch.isalnum() or ch in ("_", "-") else "_" for ch in bot_id.lower())
    return state_file(f"subconscious_state_{safe_bot_id or 'alive_ai'}.json")


class SubconsciousLoop:
    EVAL_INTERVAL = 30
    MIN_ACTION_INTERVAL = 7200  # 2 hours minimum between proactive messages (was 30 min)

    def __init__(self, nervous, heart, llm=None, fast_llm=None, on_impulse: Callable = None, bot_id: str = "alive_ai"):
        self.nervous, self.heart = nervous, heart
        self.llm = llm  # Store LLM reference for scheduled message generation
        self.bot_id = bot_id.lower()
        self.impulse_gen = ImpulseGenerator()
        self.working_memory = WorkingMemory()
        self.learning = LearningSystem()
        self.goals = GoalSystem()
        self.relationship = RelationshipMemory()
        self.evaluator = Evaluator(heart, self.impulse_gen, self.learning, self.goals, self.relationship)
        self.action_handler = ActionHandler(nervous, llm, fast_llm, on_impulse)
        self.running, self._task, self.total_evaluations = False, None, 0

        # Proactive message generator (lazy loaded with LLM)
        self._proactive_generator = None

        # Message scheduler (for scheduled messages at specific times)
        self._message_scheduler = None
        self._state_path = _subconscious_state_path(self.bot_id)
        self._load_state_from_disk()

    async def start(self):
        if self.running: return
        self.running = True
        self._task = asyncio.create_task(self._loop())

    async def stop(self):
        self.running = False
        if self._task:
            self._task.cancel()
            try: await self._task
            except asyncio.CancelledError: pass
        self.save_state()

    def register_interaction(self):
        self.evaluator.register_interaction()
        self.relationship.record_message_received()
        self.save_state()

    def init_proactive_generator(self, llm=None, data_path=None):
        """Initialize proactive generator with LLM for contextual messages"""
        try:
            from core.proactive_generator import ProactiveGenerator
            self._proactive_generator = ProactiveGenerator(self.nervous, llm=llm, bot_id=self.bot_id, data_path=data_path)
            print("[Subconscious] Proactive generator initialized")
        except Exception as e:
            print(f"[Subconscious] Failed to init proactive generator: {e}")

    def init_message_scheduler(self):
        """Initialize message scheduler for scheduled messages"""
        try:
            from skills.message_scheduler import get_message_scheduler
            self._message_scheduler = get_message_scheduler(nervous=self.nervous)
            pending = len(self._message_scheduler.get_pending())
            print(f"[Subconscious] Message scheduler initialized ({pending} pending)")
        except Exception as e:
            print(f"[Subconscious] Failed to init message scheduler: {e}")

    def record_outcome(self, message, message_type, response_sentiment=0.0, response_type="neutral"):
        self.learning.record_interaction(message=message, message_type=message_type,
            response_sentiment=response_sentiment, response_type=response_type)
        self.relationship.record_message_sent()
        active = self.goals.get_active_goal()
        if active and response_sentiment > 0.3:
            self.goals.record_progress(active.type)
        self.save_state()

    def record_milestone(self, mtype: str, desc: str):
        try:
            self.relationship.record_milestone(MilestoneType(mtype), desc)
            self.save_state()
        except ValueError: pass

    def record_experience(self, summary, sentiment=0.5, tags=None):
        self.relationship.record_experience(summary, sentiment, tags)
        self.save_state()

    def _get_circadian_state(self) -> dict:
        try:
            from heart.circadian import get_circadian_engine
            return get_circadian_engine().get_state_summary()
        except Exception:
            return {}

    async def _loop(self):
        print("[Subconscious] Loop started - running every 30s")
        while self.running:
            try:
                await self._evaluate()
                self.total_evaluations += 1
                self.save_state()
                if self.total_evaluations % 5 == 0:
                    print(f"[Subconscious] Evaluation #{self.total_evaluations} | Silence: {self.evaluator.get_silence_duration():.0f}min")
            except Exception as e:
                print(f"[Subconscious] Error: {e}")
            await asyncio.sleep(self.EVAL_INTERVAL)

    async def _evaluate(self):
        try:
            circadian_state = self._get_circadian_state()
            if circadian_state.get("sleeping"):
                await self._rest_while_asleep(circadian_state)
                return

            impulse = await self.evaluator.evaluate(self.working_memory)

            # Check for scheduled messages FIRST (highest priority)
            scheduled = self._check_scheduled_messages()

            # Check for follow-up (unanswered questions / silence)
            follow_up = self._check_follow_up()

            # Handle scheduled messages with highest priority
            if scheduled:
                await self._handle_scheduled_messages(scheduled)
                return  # Don't process other impulses after sending scheduled message

            if impulse:
                print(f"[Subconscious] Impulse: {impulse.type.value} | strength: {impulse.strength:.2f} | can_act: {self._can_act()}")
            if follow_up:
                print(f"[Subconscious] Follow-up needed: {follow_up['type']} | silence: {follow_up['silence_minutes']:.0f}min")

            # Prioritize follow-ups over regular impulses.
            if follow_up and self._can_act():
                await self._handle_follow_up(follow_up)
            elif impulse and impulse.should_act and self._can_act():
                print(f"[Subconscious] ACTING on impulse: {impulse.action_hint}")
                await self.action_handler.act_on_impulse(impulse, self.working_memory)
            elif random.random() < 0.1:
                thought_data = await self.evaluator.generate_background_thought(self.working_memory)
                if thought_data:
                    # Emit thought to nervous system so WebUI can see it
                    await self.nervous.emit("subconscious_thought", thought_data)
        finally:
            self.save_state()

    async def _rest_while_asleep(self, circadian_state: dict):
        """Keep the subconscious alive during sleep without acting outward."""
        try:
            from brain.dreams import get_dream_system
            dream = get_dream_system().get_recent_dream(max_age_hours=12)
        except Exception:
            dream = None

        content = f"Dreaming: {dream}" if dream else "Resting during sleep"
        recent = self.working_memory.get_recent_thoughts(3)
        if not recent or recent[-1].content != content:
            self.working_memory.add_thought(
                content,
                thought_type="dream" if dream else "sleep",
                emotion={"mood": "asleep", "sleepiness": circadian_state.get("sleepiness", 1.0)}
            )

        await self.nervous.emit("subconscious_rest", {
            "sleeping": True,
            "sleepiness": circadian_state.get("sleepiness", 1.0),
            "dreaming": bool(dream),
            "sleep_cycle_id": circadian_state.get("sleep_cycle_id"),
        })

    def _check_follow_up(self):
        """Check if we need to follow up on unanswered question or silence"""
        try:
            from core.message_handler import get_follow_up_system
            from core.directives import is_owner as check_is_owner
            import os

            follow_up_sys = get_follow_up_system()
            owner_id = os.environ.get("TELEGRAM_OWNER_ID", "")
            is_owner = bool(owner_id)  # If owner is configured, assume we're talking to them

            return follow_up_sys.should_follow_up(is_owner=is_owner)
        except Exception as e:
            print(f"[Subconscious] Follow-up check error: {e}")
            return None

    def _check_scheduled_messages(self):
        """Check for scheduled messages that are due to be sent"""
        try:
            # Lazy init scheduler
            if self._message_scheduler is None:
                self.init_message_scheduler()

            if self._message_scheduler is None:
                return None

            due_messages = self._message_scheduler.get_due_messages()

            if due_messages:
                print(f"[Subconscious] Found {len(due_messages)} scheduled message(s) due")
                return due_messages

            return None
        except Exception as e:
            print(f"[Subconscious] Scheduled message check error: {e}")
            return None

    async def _handle_scheduled_messages(self, messages: list):
        """Send scheduled messages that are due - generates fresh contextual message"""
        try:
            for msg in messages:
                # Add to working memory
                self.working_memory.add_thought(
                    f"Time to send scheduled message to {msg.user_id}: {msg.message[:30]}...",
                    thought_type="scheduled",
                    emotion={"mood": "remembering"}
                )

                print(f"[Subconscious] Scheduled message due for {msg.user_id}: {msg.message[:50]}...")

                # Generate a fresh contextual message inspired by the scheduled one
                final_message = await self._generate_contextual_scheduled_message(msg)

                print(f"[Subconscious] Generated fresh message: {final_message[:50]}...")

                # Emit as proactive message
                await self.nervous.emit("proactive_message", {
                    "message": final_message,
                    "user_id": msg.user_id,
                    "chat_id": msg.user_id,  # Use user_id as chat_id
                    "scheduled": True,
                    "original_reminder": msg.message,
                    "context": msg.context
                })

                # Mark as sent
                self._message_scheduler.mark_sent(msg.id)

        except Exception as e:
            print(f"[Subconscious] Error sending scheduled messages: {e}")

    async def _generate_contextual_scheduled_message(self, scheduled_msg) -> str:
        """
        Generate a fresh, contextual message inspired by the scheduled reminder.
        The scheduled message serves as a topic/reminder, but the actual message
        is generated fresh based on current context.
        """
        from datetime import datetime

        original_reminder = scheduled_msg.message
        user_id = scheduled_msg.user_id
        context_info = scheduled_msg.context

        # Try to get user context
        user_name = "babe"
        try:
            from core.user_tracker import get_user_tracker
            tracker = get_user_tracker()
            user = tracker.get_user(user_id)
            if user and user.pet_name:
                user_name = user.pet_name
        except:
            pass

        # Try to use proactive generator for contextual message
        if self._proactive_generator:
            try:
                from core.user_tracker import get_user_tracker
                tracker = get_user_tracker()
                user = tracker.get_user(user_id)

                if user:
                    # Generate contextual message
                    base_message = await self._proactive_generator.generate_for_user(user, "scheduled")

                    # Enhance with the reminder context
                    if base_message and self.llm:
                        prompt = f"""You scheduled a reminder to message {user_name}. The reminder was: "{original_reminder}"

Now it's time to send the message. Generate a fresh, natural message that:
- Captures the spirit of what you wanted to say
- Feels spontaneous and in-the-moment
- Is short (1-2 sentences max)
- Doesn't mention "scheduling" or "reminders" - just be natural
- Only reference what's in the reminder above - don't invent new details

Your fresh message:"""

                        response = await self.llm.chat([
                            {"role": "system", "content": "You are Alive-AI sending a text message."},
                            {"role": "user", "content": prompt}
                        ], max_tokens=60, temperature=0.7)

                        if response and response.strip():
                            return response.strip().strip('"\'')

                    elif base_message:
                        return base_message
            except Exception as e:
                print(f"[Subconscious] Proactive generator error: {e}")

        # Fallback: Use LLM directly
        if self.llm:
            try:
                prompt = f"""You wanted to message {user_name}. Your reminder was: "{original_reminder}"

Generate a fresh, natural text message (1-2 sentences) that captures what you wanted to say but feels spontaneous.
- Don't mention reminders or scheduling
- Only reference what's in the reminder above - don't invent new details

Your message:"""

                response = await self.llm.chat([
                    {"role": "system", "content": "You are Alive-AI sending a text message."},
                    {"role": "user", "content": prompt}
                ], max_tokens=60, temperature=0.7)

                if response and response.strip():
                    return response.strip().strip('"\'')
            except Exception as e:
                print(f"[Subconscious] LLM fallback error: {e}")

        # Ultimate fallback: use original message
        return original_reminder

    async def _handle_follow_up(self, follow_up_data: dict):
        """Send a contextual follow-up message"""
        try:
            from core.user_tracker import get_user_tracker

            follow_up_type = follow_up_data.get("type", "silence")

            # Get users who might need a follow-up
            tracker = get_user_tracker()
            users_to_message = tracker.get_users_for_follow_up(min_silence_minutes=30, max_silence_minutes=180)

            if not users_to_message:
                print("[Subconscious] No users to follow up with")
                return

            # For now, pick the user who's been silent the longest
            user = max(users_to_message, key=lambda u: u.silence_minutes)

            # Generate contextual message
            message = await self._generate_contextual_message(user, follow_up_type)

            if follow_up_type == "return_from_away":
                # She's coming back from coffee/shower/etc
                reason = follow_up_data.get("reason", "away")
                away_min = follow_up_data.get("away_minutes", 0)
                self.working_memory.add_thought(
                    f"Returning from {reason} after {away_min:.0f}min",
                    thought_type="return",
                    emotion={"mood": "refreshed"}
                )
            else:
                # Regular silence/question follow-up
                silence_min = user.silence_minutes
                self.working_memory.add_thought(
                    f"Following up with {user.user_id} after {silence_min:.0f}min silence",
                    thought_type="follow_up",
                    emotion={"mood": "curious"}
                )

            print(f"[Subconscious] Sending follow-up to {user.user_id}: {message[:50]}...")

            # Emit with user context
            await self.nervous.emit("proactive_message", {
                "message": message,
                "user_id": user.user_id,
                "chat_id": user.chat_id
            })
        except Exception as e:
            print(f"[Subconscious] Follow-up error: {e}")

    async def _generate_contextual_message(self, user, message_type: str = "silence") -> str:
        """Generate a contextual message for a specific user"""
        # Try proactive generator first (has LLM + context)
        if self._proactive_generator:
            try:
                message = await self._proactive_generator.generate_for_user(user, message_type)
                return message
            except Exception as e:
                print(f"[Subconscious] Proactive generator error: {e}")

        # Fallback to generic messages
        fallbacks = {
            "silence": ["hey... you there?", "thinking about you", "miss talking to you"],
            "follow_up": ["so about earlier...", "was wondering about something"],
            "return_from_away": ["I'm back! 💕", "back now, missed you"],
        }
        templates = fallbacks.get(message_type, fallbacks["silence"])
        return random.choice(templates)

    def _can_act(self):
        """Check if we can send a proactive message.

        Requires:
        1. Not quiet hours
        2. Minimum interval since last action (2 hours)
        3. At least 1 hour since last user message (post-conversation buffer)
        """
        circadian_state = self._get_circadian_state()
        if circadian_state.get("sleeping") or circadian_state.get("sleepiness", 0) >= 0.85:
            return False

        # Check quiet hours
        if not self.evaluator.can_act_now():
            return False

        # Check minimum interval since last proactive action
        if not self.action_handler.can_act_now(self.working_memory, self.MIN_ACTION_INTERVAL / 60):
            return False

        # NEW: Post-conversation buffer - don't send proactive for 60 min after user's last message
        silence_minutes = self.evaluator.get_silence_duration()
        if silence_minutes < 60:  # 1 hour buffer after conversation ends
            return False

        return True

    async def generate_proactive_message(self, impulse: Impulse) -> str:
        return await self.action_handler.generate_proactive_message(impulse, self.working_memory)

    def get_status(self):
        circadian_state = self._get_circadian_state()
        return {"running": self.running, "evaluations": self.total_evaluations,
                "silence": self.evaluator.get_silence_duration(), "can_act": self._can_act(),
                "memory": self.working_memory.get_state_summary(),
                "learning_rate": self.learning.get_recent_success_rate(),
                "goal": self.goals.daily_focus.value if self.goals.daily_focus else None,
                "circadian": circadian_state,
                "sleeping": circadian_state.get("sleeping", False)}

    def get_state_for_save(self):
        return {
            "saved_at": datetime.now().isoformat(),
            "total_evaluations": self.total_evaluations,
            "evaluator_last_interaction_time": self.evaluator.last_interaction_time.isoformat(),
            "learning": self.learning.to_dict(),
            "goals": self.goals.to_dict(),
            "relationship": self.relationship.to_dict(),
            "working_memory": self.working_memory.to_dict(),
        }

    def load_state(self, data):
        if "learning" in data:
            self.learning = LearningSystem.from_dict(data["learning"]); self.evaluator.learning = self.learning
        if "goals" in data:
            self.goals = GoalSystem.from_dict(data["goals"]); self.evaluator.goals = self.goals
        if "relationship" in data:
            self.relationship = RelationshipMemory.from_dict(data["relationship"]); self.evaluator.relationship = self.relationship
        if "working_memory" in data:
            self.working_memory = WorkingMemory.from_dict(data["working_memory"])
        if data.get("evaluator_last_interaction_time"):
            self.evaluator.last_interaction_time = datetime.fromisoformat(data["evaluator_last_interaction_time"])
        self.total_evaluations = int(data.get("total_evaluations", self.total_evaluations))

    def save_state(self):
        try:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            self._state_path.write_text(json.dumps(self.get_state_for_save(), indent=2))
        except Exception as e:
            print(f"[Subconscious] Error saving state: {e}")

    def _load_state_from_disk(self):
        try:
            if self._state_path.exists():
                self.load_state(json.loads(self._state_path.read_text()))
                print(f"[Subconscious] Loaded state from {self._state_path}")
        except Exception as e:
            print(f"[Subconscious] Error loading state: {e}")
