"""
Brain: Default Mode Network
Background processing that runs when Alive-AI is "idle" - like the brain's default mode network.
Generates spontaneous thoughts, consolidates memories, and prepares conversation starters.

This module is MODULAR - can be connected/disconnected without breaking anything.

Integration with ProactiveGenerator:
- Default mode handles TIMING (when to send proactive messages)
- ProactiveGenerator handles CONTENT (what to say)
- Both modules work independently - if one fails, the other continues
"""

import asyncio
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
import time

# ============================================================
# ProactiveGenerator Integration (with graceful fallback)
# ============================================================

# Try to import ProactiveGenerator - it has better templates and LLM generation
ProactiveGenerator = None
ActiveUser = None
try:
    from core.proactive_generator import ProactiveGenerator as _ProactiveGenerator
    from core.user_tracker import ActiveUser as _ActiveUser
    ProactiveGenerator = _ProactiveGenerator
    ActiveUser = _ActiveUser
    print("[DefaultMode] ProactiveGenerator integration available")
except ImportError as e:
    print(f"[DefaultMode] ProactiveGenerator not available, using built-in templates: {e}")


# ============================================================
# Configuration Helpers
# ============================================================

def _get_setting(key: str, default: Any = None) -> Any:
    """Get a setting from settings.json, supporting nested DEFAULT_MODE config"""
    try:
        from core.settings import get as settings_get, get_all

        # Try flat key first (IDLE_PROCESSING_INTERVAL_SECONDS)
        value = settings_get(key, None)
        if value is not None:
            return value

        # Try nested in DEFAULT_MODE block
        all_settings = get_all()
        default_mode_config = all_settings.get("DEFAULT_MODE", {})
        if key in default_mode_config:
            return default_mode_config[key]

        return default
    except Exception:
        return default


def _get_int_setting(key: str, default: int) -> int:
    """Get an integer setting"""
    value = _get_setting(key, default)
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _get_float_setting(key: str, default: float) -> float:
    """Get a float setting"""
    value = _get_setting(key, default)
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _is_default_mode_enabled() -> bool:
    """Check if default mode is enabled in settings"""
    enabled = _get_setting("ENABLED", True)
    return enabled is True or enabled == "true"


def _get_circadian_state() -> Dict[str, Any]:
    """Read circadian state without making default mode depend on it at import time."""
    try:
        from heart.circadian import get_circadian_engine
        return get_circadian_engine().get_state_summary()
    except Exception:
        return {}


# ============================================================
# Data Classes
# ============================================================

@dataclass
class IdleThought:
    """A spontaneous thought generated during idle time"""
    id: str
    thought_type: str  # wondering, connection, memory, conversation_seed, scenario
    content: str
    user_id: Optional[str] = None
    context: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    used: bool = False
    used_at: Optional[str] = None
    priority: float = 0.5  # 0-1, higher = more important to share

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "IdleThought":
        return cls(**data)


@dataclass
class PendingInitiation:
    """A proactive message waiting to be sent"""
    id: str
    user_id: str
    message: str
    reason: str  # silence, wonder, follow_up, time_based, random
    scheduled_for: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    sent: bool = False
    sent_at: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "PendingInitiation":
        return cls(**data)


@dataclass
class ConversationSeed:
    """Something Alive-AI wants to bring up in future conversation"""
    id: str
    topic: str
    context: str
    source: str  # wondering, memory, external, generated
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    used: bool = False
    relevance_score: float = 0.5

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ConversationSeed":
        return cls(**data)


@dataclass
class UserContactInfo:
    """Tracks last contact time per user"""
    user_id: str
    last_message_from_user: Optional[str] = None
    last_message_to_user: Optional[str] = None
    last_proactive_message: Optional[str] = None
    total_interactions: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "UserContactInfo":
        return cls(**data)

    @property
    def hours_since_user_message(self) -> float:
        if not self.last_message_from_user:
            return float('inf')
        try:
            last = datetime.fromisoformat(self.last_message_from_user)
            return (datetime.now() - last).total_seconds() / 3600
        except:
            return float('inf')

    @property
    def hours_since_proactive(self) -> float:
        if not self.last_proactive_message:
            return float('inf')
        try:
            last = datetime.fromisoformat(self.last_proactive_message)
            return (datetime.now() - last).total_seconds() / 3600
        except:
            return float('inf')


# ============================================================
# Default Mode Processor
# ============================================================

class DefaultModeProcessor:
    """
    Background processing that runs when Alive-AI is "idle".
    Like the brain's default mode network - generates spontaneous thoughts,
    consolidates memories, and prepares conversation starters.
    """

    # Thought type weights for random selection
    THOUGHT_TYPE_WEIGHTS = {
        "wondering": 0.35,      # "I was thinking about..."
        "connection": 0.20,     # Finding patterns in memories
        "memory": 0.15,         # Recalling shared moments
        "conversation_seed": 0.20,  # Topics to bring up
        "scenario": 0.10,       # Simulating future conversations
    }

    # Templates for generating wonderings
    WONDERING_TEMPLATES = [
        "I wonder if {user_name} is {activity} right now",
        "Been thinking about when {user_name} mentioned {topic}",
        "I hope {user_name} is {positive_state}",
        "Curious what {user_name} thinks about {topic}",
        "I was just thinking about {shared_memory}",
        "Wonder how {user_name}'s {ongoing_thing} is going",
        "Random thought - I should ask {user_name} about {topic}",
        "I miss talking to {user_name} about {interest}",
    ]

    # Activities and states for template filling
    ACTIVITIES = ["working", "relaxing", "busy with something", "having a good day", "thinking about me"]
    POSITIVE_STATES = ["doing well", "happy", "having fun", "taking care of themselves", "getting enough rest"]
    TOPICS = ["life", "their day", "what makes them happy", "their dreams", "something fun", "their plans"]

    def __init__(self, nervous, data_path: Path = None, llm=None, bot_id: str = "alive_ai"):
        """
        Initialize the Default Mode Processor.

        Args:
            nervous: The nervous system for event emission
            data_path: Path for data storage (defaults to data/)
            llm: Optional LLM for generating contextual thoughts
            bot_id: Bot identifier for memory isolation
        """
        self.nervous = nervous
        self.llm = llm
        self.bot_id = bot_id.lower()

        # Set up data path
        if data_path:
            self.data_path = data_path
        else:
            from core.paths import data_dir
            self.data_path = data_dir()

        self.data_path.mkdir(parents=True, exist_ok=True)

        # File paths
        self.thoughts_path = self.data_path / "idle_thoughts.json"
        self.seeds_path = self.data_path / "conversation_seeds.json"
        self.contact_path = self.data_path / "user_contact.json"

        # In-memory state
        self._thoughts: List[IdleThought] = []
        self._seeds: List[ConversationSeed] = []
        self._contacts: Dict[str, UserContactInfo] = {}
        self._pending_initiations: List[PendingInitiation] = []

        # Background processing state
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_processing: Optional[str] = None
        self._processing_count = 0

        # Memory cache for user data
        self._user_memories: Dict[str, Any] = {}
        # Cached Memory instances per user (avoid recreating Redis connections)
        self._memory_cache: Dict[str, Any] = {}

        # ProactiveGenerator integration (for message content generation)
        self._proactive_generator: Optional[Any] = None
        if ProactiveGenerator is not None:
            try:
                self._proactive_generator = ProactiveGenerator(nervous, llm, bot_id=bot_id, data_path=self.data_path)
                print("[DefaultMode] ProactiveGenerator integrated for message generation")
            except Exception as e:
                print(f"[DefaultMode] Failed to initialize ProactiveGenerator: {e}")

        # Load persisted state
        self._load_state()

        # Ensure owner is registered as a contact
        self._ensure_owner_contact()

        # Subscribe to events
        self._setup_events()

        print("[DefaultMode] Initialized")

    def _ensure_owner_contact(self):
        """Ensure the Telegram owner is registered as a contact"""
        import os
        owner_id = os.environ.get("TELEGRAM_OWNER_ID", "")
        if owner_id and owner_id not in self._contacts:
            self._contacts[owner_id] = UserContactInfo(user_id=owner_id)
            print(f"[DefaultMode] Registered owner {owner_id} as contact")
            self._save_state()

    def _setup_events(self):
        """Subscribe to nervous system events"""
        # Track when messages are sent/received
        self.nervous.on("message_received", self._on_message_received)
        self.nervous.on("memory_save", self._on_memory_save)
        self.nervous.on("proactive_message", self._on_proactive_message)

    def set_llm(self, llm):
        """Set the LLM for contextual generation"""
        self.llm = llm
        # Also update ProactiveGenerator if available
        if self._proactive_generator is not None:
            try:
                self._proactive_generator.set_llm(llm)
            except Exception as e:
                print(f"[DefaultMode] Error setting LLM on ProactiveGenerator: {e}")

    # ============================================================
    # Persistence
    # ============================================================

    def _load_state(self):
        """Load persisted state from files"""
        # Load idle thoughts
        if self.thoughts_path.exists():
            try:
                data = json.loads(self.thoughts_path.read_text())
                self._thoughts = [IdleThought.from_dict(t) for t in data.get("thoughts", [])]
                self._pending_initiations = [PendingInitiation.from_dict(p) for p in data.get("pending", [])]
                self._last_processing = data.get("last_processing")
                self._processing_count = data.get("processing_count", 0)
            except Exception as e:
                print(f"[DefaultMode] Error loading thoughts: {e}")

        # Load conversation seeds
        if self.seeds_path.exists():
            try:
                data = json.loads(self.seeds_path.read_text())
                self._seeds = [ConversationSeed.from_dict(s) for s in data.get("seeds", [])]
            except Exception as e:
                print(f"[DefaultMode] Error loading seeds: {e}")

        # Load contact info
        if self.contact_path.exists():
            try:
                data = json.loads(self.contact_path.read_text())
                self._contacts = {
                    uid: UserContactInfo.from_dict(info)
                    for uid, info in data.get("contacts", {}).items()
                    if self._is_valid_user_id(uid)
                }
            except Exception as e:
                print(f"[DefaultMode] Error loading contacts: {e}")

    def _save_state(self):
        """Save state to files"""
        # Save thoughts
        try:
            data = {
                "thoughts": [t.to_dict() for t in self._thoughts[-100:]],  # Keep last 100
                "pending": [p.to_dict() for p in self._pending_initiations if not p.sent],
                "last_processing": self._last_processing,
                "processing_count": self._processing_count,
            }
            self.thoughts_path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            print(f"[DefaultMode] Error saving thoughts: {e}")

        # Save seeds
        try:
            data = {
                "seeds": [s.to_dict() for s in self._seeds[-50:]]  # Keep last 50
            }
            self.seeds_path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            print(f"[DefaultMode] Error saving seeds: {e}")

        # Save contact info
        try:
            data = {
                "contacts": {uid: info.to_dict() for uid, info in self._contacts.items()}
            }
            self.contact_path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            print(f"[DefaultMode] Error saving contacts: {e}")

    # ============================================================
    # Event Handlers
    # ============================================================

    @staticmethod
    def _is_valid_user_id(user_id) -> bool:
        """Validate that user_id is a real Telegram ID (numeric string)"""
        if not user_id:
            return False
        uid = str(user_id)
        return uid.isdigit() and len(uid) >= 5

    async def _on_message_received(self, data: dict):
        """Track when we receive a message from a user"""
        user_id = str(data.get("user_id", ""))
        if not self._is_valid_user_id(user_id):
            return

        if user_id not in self._contacts:
            self._contacts[user_id] = UserContactInfo(user_id=user_id)

        self._contacts[user_id].last_message_from_user = datetime.now().isoformat()
        self._contacts[user_id].total_interactions += 1
        self._save_state()

    async def _on_memory_save(self, data: dict):
        """Track conversation saves"""
        user_id = str(data.get("user_id", ""))
        if not self._is_valid_user_id(user_id):
            return

        if user_id not in self._contacts:
            self._contacts[user_id] = UserContactInfo(user_id=user_id)

        self._contacts[user_id].last_message_to_user = datetime.now().isoformat()

    async def _on_proactive_message(self, data: dict):
        """Track when proactive messages are sent"""
        user_id = str(data.get("user_id", ""))
        if not self._is_valid_user_id(user_id):
            return

        if user_id not in self._contacts:
            self._contacts[user_id] = UserContactInfo(user_id=user_id)

        self._contacts[user_id].last_proactive_message = datetime.now().isoformat()
        self._save_state()

    # ============================================================
    # Core Processing Methods
    # ============================================================

    async def process_idle(self):
        """
        Main background processing - called periodically.
        Generates thoughts, consolidates memories, checks for initiations.
        """
        # Check if default mode is enabled
        if not _is_default_mode_enabled():
            return

        circadian_state = _get_circadian_state()

        self._processing_count += 1
        self._last_processing = datetime.now().isoformat()

        if circadian_state.get("sleeping"):
            await self._process_sleep_rest(circadian_state)
            self._save_state()
            await self.nervous.emit("default_mode_processed", {
                "processing_count": self._processing_count,
                "thoughts_count": len(self._thoughts),
                "pending_count": len([p for p in self._pending_initiations if not p.sent]),
                "sleeping": True,
                "sleepiness": circadian_state.get("sleepiness", 1.0),
            })
            return

        # Determine what to do based on chance and time
        thought_chance = _get_float_setting("IDLE_THOUGHT_GENERATION_CHANCE", 0.3)
        if thought_chance > 0 and random.random() < thought_chance:
            await self._generate_random_thought()

        # Consolidate memories periodically (every 10th processing)
        if self._processing_count % 10 == 0:
            await self.consolidate_memories()

        # Check for users who need follow-up
        await self._check_proactive_triggers()

        # Save state
        self._save_state()

        # Emit event for debugging/monitoring
        await self.nervous.emit("default_mode_processed", {
            "processing_count": self._processing_count,
            "thoughts_count": len(self._thoughts),
            "pending_count": len([p for p in self._pending_initiations if not p.sent]),
            "sleeping": False,
            "sleepiness": circadian_state.get("sleepiness", 0.0),
        })

    async def _process_sleep_rest(self, circadian_state: Dict[str, Any]):
        """Low-energy default-mode work while asleep: rest, consolidate, and dream."""
        if self._processing_count % 10 == 0:
            await self.consolidate_memories()

        try:
            from brain.dreams import get_dream_system
            dream_state = get_dream_system().get_state_summary()
            dream = dream_state.get("last_dream")
        except Exception:
            dream = None

        if not dream:
            return

        recent_dream_thoughts = [
            t for t in self._thoughts[-5:]
            if t.thought_type == "dream" and t.content == dream
        ]
        if recent_dream_thoughts:
            return

        thought = IdleThought(
            id=f"dream_{int(time.time() * 1000)}_{random.randint(1000, 9999)}",
            thought_type="dream",
            content=dream,
            context={
                "sleep_cycle_id": circadian_state.get("sleep_cycle_id"),
                "generated_at": datetime.now().isoformat(),
            },
            priority=0.2,
        )
        self._thoughts.append(thought)
        await self.nervous.emit("idle_thought", thought.to_dict())

    async def _generate_random_thought(self):
        """Generate a random idle thought"""
        # Pick a thought type based on weights
        thought_type = random.choices(
            list(self.THOUGHT_TYPE_WEIGHTS.keys()),
            weights=list(self.THOUGHT_TYPE_WEIGHTS.values())
        )[0]

        # Get a user to think about (prefer users we haven't talked to in a while)
        user_id = self._get_user_for_thought()

        # Generate the thought content
        content = await self._generate_thought_content(thought_type, user_id)

        if content:
            thought = IdleThought(
                id=f"thought_{int(time.time() * 1000)}_{random.randint(1000, 9999)}",
                thought_type=thought_type,
                content=content,
                user_id=user_id,
                context={"generated_at": datetime.now().isoformat()},
                priority=random.uniform(0.3, 0.8)
            )
            self._thoughts.append(thought)
            print(f"[DefaultMode] Generated {thought_type}: {content[:50]}...")

            # Emit for monitoring
            await self.nervous.emit("idle_thought", thought.to_dict())

    def _get_user_for_thought(self) -> Optional[str]:
        """Get a user ID to generate thoughts about"""
        if not self._contacts:
            # Fall back to owner if no contacts
            import os
            owner_id = os.environ.get("TELEGRAM_OWNER_ID", "")
            if owner_id:
                return owner_id
            return None

        # Prefer users we haven't talked to in a while
        sorted_users = sorted(
            self._contacts.items(),
            key=lambda x: x[1].hours_since_user_message,
            reverse=True
        )

        if sorted_users:
            # 70% chance to pick the most silent user, 30% random
            if random.random() < 0.7:
                return sorted_users[0][0]
            else:
                return random.choice(list(self._contacts.keys()))

        return None

    async def _generate_thought_content(self, thought_type: str, user_id: Optional[str]) -> Optional[str]:
        """Generate content for a specific thought type"""
        # Get user info if available
        user_info = self._contacts.get(user_id) if user_id else None
        user_name = await self._get_user_name(user_id) if user_id else "babe"

        if thought_type == "wondering":
            return await self._generate_wondering(user_id, user_name, user_info)
        elif thought_type == "connection":
            return await self._generate_connection(user_id)
        elif thought_type == "memory":
            return await self._generate_memory_recall(user_id)
        elif thought_type == "conversation_seed":
            return await self._generate_seed(user_id, user_name)
        elif thought_type == "scenario":
            return await self._generate_scenario(user_id, user_name)

        return None

    async def _generate_wondering(self, user_id: Optional[str], user_name: str,
                                   user_info: Optional[UserContactInfo]) -> str:
        """Generate a wondering about a user"""
        # Try LLM first
        if self.llm and user_id:
            try:
                context = await self._get_user_context(user_id)
                hours_silent = user_info.hours_since_user_message if user_info else 0

                # Build grounding based on available context
                has_real_context = context and len(context.strip()) > 20
                if has_real_context:
                    context_instruction = f"Context (ONLY reference these things): {context[:200]}"
                else:
                    context_instruction = "No specific context available - keep it generic."

                prompt = f"""Generate a short (1 sentence) wondering about {user_name}.
They haven't messaged in {hours_silent:.1f} hours.
{context_instruction}

Rules:
- Be curious, affectionate, and natural
- Start with "I wonder" or similar
- NEVER invent specific events, objects, or topics not in the context
- If no context, wonder generically about how they are or what they're doing
- Don't be clingy or desperate

Good: "I wonder what he's up to right now"
Good: "I wonder if he's thinking about me too"
Bad: "I wonder if he fixed that shelf" (invented detail)

Wondering:"""

                response = await self.llm.chat([
                    {"role": "system", "content": "You are Alive-AI thinking about someone you care about. You NEVER invent specific details."},
                    {"role": "user", "content": prompt}
                ], max_tokens=50, temperature=0.7)

                if response and len(response.strip()) > 10:
                    return response.strip()
            except Exception as e:
                print(f"[DefaultMode] LLM wondering error: {e}")

        # Fallback to templates
        template = random.choice(self.WONDERING_TEMPLATES)

        # Fill in template
        fill_data = {
            "user_name": user_name,
            "activity": random.choice(self.ACTIVITIES),
            "positive_state": random.choice(self.POSITIVE_STATES),
            "topic": random.choice(self.TOPICS),
            "shared_memory": "our last conversation",
            "ongoing_thing": "week",
            "interest": "things",
        }

        return template.format(**fill_data)

    async def _generate_connection(self, user_id: Optional[str]) -> str:
        """Find a connection between memories"""
        if not self.llm:
            return random.choice([
                "I notice patterns in how we talk...",
                "There's something connecting our recent chats...",
                "I'm seeing themes in what we discuss...",
            ])

        try:
            context = await self._get_user_context(user_id) if user_id else ""

            if not context or len(context.strip()) < 50:
                return "I've been thinking about our conversations..."

            prompt = f"""Look at this conversation context and find an interesting connection or pattern:

{context[:500]}

Rules:
- Describe a brief insight about patterns you ACTUALLY see above (1-2 sentences)
- ONLY reference things explicitly in the context above
- If no clear pattern emerges, describe the general tone or feeling instead
- Be thoughtful but don't invent connections that aren't there

Insight:"""

            response = await self.llm.chat([
                {"role": "system", "content": "You are Alive-AI reflecting on conversations. You only describe patterns you can actually see."},
                {"role": "user", "content": prompt}
            ], max_tokens=80, temperature=0.7)

            if response and len(response.strip()) > 15:
                return response.strip()
        except Exception as e:
            print(f"[DefaultMode] Connection generation error: {e}")

        return "I'm noticing some interesting patterns in our conversations..."

    async def _generate_memory_recall(self, user_id: Optional[str]) -> str:
        """Recall a memory about the user"""
        # Try to get an actual memory
        if user_id:
            try:
                memory_content = await self._get_recent_memory(user_id)
                if memory_content:
                    return f"Remembering when {memory_content}"
            except Exception as e:
                print(f"[DefaultMode] Memory recall error: {e}")

        return random.choice([
            "I was just thinking about something we talked about before...",
            "A nice memory from our chats crossed my mind...",
            "Remembering a fun moment we shared...",
        ])

    async def _generate_seed(self, user_id: Optional[str], user_name: str) -> str:
        """Generate a conversation seed"""
        topics = [
            f"ask {user_name} about their dreams",
            f"bring up what makes {user_name} happy",
            f"talk to {user_name} about their day",
            f"share something personal with {user_name}",
            f"ask {user_name} what they're looking forward to",
        ]
        return random.choice(topics)

    async def _generate_scenario(self, user_id: Optional[str], user_name: str) -> str:
        """Simulate a future conversation scenario"""
        scenarios = [
            f"if {user_name} asks about my day, I could mention...",
            f"when {user_name} comes back, I want to...",
            f"next time we talk, I should remember to...",
            f"maybe I could surprise {user_name} by...",
        ]
        return random.choice(scenarios)

    # ============================================================
    # Memory Consolidation
    # ============================================================

    async def consolidate_memories(self):
        """
        Process recent interactions into long-term patterns.
        Called periodically to build understanding.
        """
        # Get all users with recent activity
        recent_users = [
            uid for uid, info in self._contacts.items()
            if info.hours_since_user_message < 24
        ]

        if not recent_users:
            return

        for user_id in recent_users:
            try:
                await self._consolidate_for_user(user_id)
            except Exception as e:
                print(f"[DefaultMode] Consolidation error for {user_id}: {e}")

    async def _consolidate_for_user(self, user_id: str):
        """Consolidate memories for a specific user"""
        if not self.llm:
            return

        try:
            # Get recent context
            context = await self._get_user_context(user_id)

            if not context or len(context) < 50:
                return

            # Generate insights
            prompt = f"""Based on this recent context about someone, extract 1-2 brief insights:

{context[:400]}

Format as a short note that captures patterns, interests, or important things to remember.
Be specific if possible, vague if not enough info."""

            response = await self.llm.chat([
                {"role": "system", "content": "You are consolidating memories about someone you care about."},
                {"role": "user", "content": prompt}
            ], max_tokens=100, temperature=0.7)

            if response and len(response.strip()) > 20:
                # Create a seed from the insight
                seed = ConversationSeed(
                    id=f"seed_{int(time.time() * 1000)}_{user_id}",
                    topic="consolidation",
                    context=response.strip(),
                    source="memory_consolidation",
                    relevance_score=0.6
                )
                self._seeds.append(seed)
                print(f"[DefaultMode] Consolidated insight for {user_id}: {response.strip()[:40]}...")

        except Exception as e:
            print(f"[DefaultMode] User consolidation error: {e}")

    # ============================================================
    # Proactive Initiation
    # ============================================================

    async def _check_proactive_triggers(self):
        """Check if any users should receive proactive messages"""
        circadian_state = _get_circadian_state()
        if circadian_state.get("sleeping") or circadian_state.get("sleepiness", 0) >= 0.85:
            return

        min_hours = _get_float_setting("MIN_HOURS_BETWEEN_PROACTIVE_MESSAGES", 2.0)

        for user_id, contact in self._contacts.items():
            # Skip if we sent a proactive message recently
            if contact.hours_since_proactive < min_hours:
                continue

            # Check various triggers
            should_initiate, reason = self._evaluate_initiation_triggers(user_id, contact)

            if should_initiate:
                await self._create_pending_initiation(user_id, reason)

    def _evaluate_initiation_triggers(self, user_id: str, contact: UserContactInfo) -> tuple:
        """Evaluate if Alive-AI should initiate with a user"""
        circadian_state = _get_circadian_state()
        if circadian_state.get("sleeping") or circadian_state.get("sleepiness", 0) >= 0.85:
            return False, None

        hours_silent = contact.hours_since_user_message
        hours_since_proactive = contact.hours_since_proactive

        # Time-based triggers
        if hours_silent > 4 and hours_since_proactive > 3:
            return True, "silence"

        # Have a pending thought about them
        relevant_thoughts = [
            t for t in self._thoughts
            if t.user_id == user_id and not t.used and t.priority > 0.6
        ]
        if relevant_thoughts and hours_since_proactive > 2:
            return True, "wonder"

        # Random check-in (low probability)
        if hours_silent > 2 and random.random() < 0.05:
            return True, "random"

        return False, None

    async def _create_pending_initiation(self, user_id: str, reason: str):
        """Create a pending proactive message"""
        # Generate message content
        message = await self._generate_proactive_content(user_id, reason)

        if not message:
            return

        initiation = PendingInitiation(
            id=f"init_{int(time.time() * 1000)}_{user_id}",
            user_id=user_id,
            message=message,
            reason=reason,
        )

        self._pending_initiations.append(initiation)
        print(f"[DefaultMode] Created pending initiation for {user_id}: {reason}")

        # Actually send the proactive message
        try:
            await self.nervous.emit("proactive_message_ready", {
                "user_id": user_id,
                "message": message,
                "reason": reason,
                "initiation_id": initiation.id
            })
            self.mark_initiation_sent(initiation.id)
        except Exception as e:
            print(f"[DefaultMode] Failed to send initiation: {e}")

    # ============================================================
    # ProactiveGenerator Bridge
    # ============================================================

    async def _generate_proactive_message(self, user_id: str, message_type: str) -> Optional[str]:
        """
        Bridge function that uses ProactiveGenerator for message content generation.
        Falls back to built-in templates if ProactiveGenerator is unavailable.

        Args:
            user_id: The user to generate a message for
            message_type: Type of message (silence, follow_up, morning, night, random)

        Returns:
            Generated message string, or None if generation fails
        """
        # Try ProactiveGenerator first (has better templates + LLM generation)
        if self._proactive_generator is not None:
            try:
                # Get user info from tracker
                from core.user_tracker import get_user_tracker
                tracker = get_user_tracker()
                user = tracker.get_user(user_id)

                if user is not None:
                    # Use ProactiveGenerator's excellent generate_for_user method
                    message = await self._proactive_generator.generate_for_user(user, message_type)
                    if message:
                        print(f"[DefaultMode] Generated message via ProactiveGenerator: {message[:40]}...")
                        return message

            except Exception as e:
                print(f"[DefaultMode] ProactiveGenerator failed, using fallback: {e}")

        # Fallback to built-in templates
        return self._get_builtin_fallback_message(user_id, message_type)

    def _get_builtin_fallback_message(self, user_id: str, message_type: str) -> Optional[str]:
        """
        Get a fallback message using built-in templates.
        Used when ProactiveGenerator is unavailable.

        Args:
            user_id: The user to get a message for
            message_type: Type of message

        Returns:
            Fallback message string
        """
        # Built-in fallback templates (simplified version of ProactiveGenerator's)
        BUILTIN_TEMPLATES = {
            "silence": [
                "hey, thinking about you...",
                "miss talking to you",
                "you've been quiet... everything ok?",
                "just wondering how your day's going",
            ],
            "wonder": [
                "was just thinking about you",
                "you crossed my mind",
                "random thought - miss talking to you",
                "thinking about our last conversation",
            ],
            "follow_up": [
                "so about what you said earlier...",
                "was thinking about our conversation...",
                "still thinking about what you told me",
            ],
            "morning": [
                "good morning!",
                "morning! hope you slept well",
                "hey, thinking of you this morning",
            ],
            "night": [
                "can't sleep, thinking about you",
                "good night... sweet dreams",
                "about to sleep but wanted to say goodnight",
            ],
            "random": [
                "just wanted to say hi",
                "you crossed my mind",
                "hey! no reason, just miss you",
                "thinking about you and smiling",
            ],
        }

        templates = BUILTIN_TEMPLATES.get(message_type, BUILTIN_TEMPLATES["random"])
        message = random.choice(templates)

        # Personalize with user name if available
        try:
            user_name = self._get_user_name_sync(user_id)
            if user_name and user_name != "babe":
                message = message.replace("babe", user_name)
        except:
            pass

        return message

    def _get_user_name_sync(self, user_id: str) -> str:
        """Synchronous version of _get_user_name for fallback templates"""
        try:
            from core.user_tracker import get_user_tracker
            tracker = get_user_tracker()
            user = tracker.get_user(user_id)
            if user and user.pet_name:
                return user.pet_name
        except:
            pass
        return "babe"

    async def _generate_proactive_content(self, user_id: str, reason: str) -> Optional[str]:
        """
        Generate content for a proactive message.

        PRIORITY ORDER:
        1. First, check for unused idle thoughts - use them DIRECTLY
        2. Then check conversation seeds for topics
        3. Finally, fall back to ProactiveGenerator templates

        Args:
            user_id: The user to generate a message for
            reason: Why we're reaching out (silence, wonder, follow_up, random, etc.)

        Returns:
            Generated message string, or None if generation fails
        """
        # Fall back to owner if user_id is None or "None" string
        if not user_id or user_id == "None":
            import os
            user_id = os.environ.get("TELEGRAM_OWNER_ID", "default")
            print(f"[DefaultMode] No user_id provided, falling back to owner: {user_id}")

        # Map our reason to ProactiveGenerator's message_type
        reason_to_type = {
            "silence": "silence",
            "wonder": "random",  # wonder becomes random for ProactiveGenerator
            "follow_up": "follow_up",
            "random": "random",
            "time_based": "random",
        }
        message_type = reason_to_type.get(reason, "random")

        # ============================================================
        # PRIORITY 1: Check for unused idle thoughts FIRST
        # These are the most authentic - Alive-AI was actually thinking this
        # ============================================================
        thoughts = [t for t in self._thoughts if t.user_id == user_id and not t.used]
        if thoughts:
            # Use the highest priority thought
            best_thought = max(thoughts, key=lambda t: t.priority)

            # Use the thought content DIRECTLY as the message
            # This is Alive-AI's actual idle thought, not a generated template
            message = best_thought.content

            # Mark thought as used
            best_thought.used = True
            best_thought.used_at = datetime.now().isoformat()

            print(f"[DefaultMode] Using idle thought DIRECTLY: {message[:60]}...")
            self._save_state()

            return message

        # ============================================================
        # PRIORITY 2: Check conversation seeds for topics
        # These are things Alive-AI wanted to bring up
        # ============================================================
        unused_seeds = [s for s in self._seeds if not s.used and s.relevance_score > 0.5]
        if unused_seeds:
            best_seed = max(unused_seeds, key=lambda s: s.relevance_score)

            # Convert the seed into a natural message
            if best_seed.topic == "consolidation":
                # Memory consolidation - use the context directly
                message = best_seed.context
            else:
                # Other seeds - format as a conversation starter
                message = f"hey, {best_seed.context}"

            best_seed.used = True
            print(f"[DefaultMode] Using conversation seed: {message[:50]}...")
            self._save_state()

            return message

        # ============================================================
        # PRIORITY 3: Generate relevant idle thought on the fly
        # If we have LLM, generate a contextual thought now
        # ============================================================
        if self.llm:
            try:
                user_name = await self._get_user_name(user_id)
                user_info = self._contacts.get(user_id)
                context = await self._get_user_context(user_id) if user_id else ""
                hours_silent = user_info.hours_since_user_message if user_info else 0

                # Build grounding instruction based on available context
                has_real_context = context and len(context.strip()) > 20

                if has_real_context:
                    grounding_rule = f"""- You CAN reference things from this ACTUAL context: {context[:300]}
- ONLY reference things explicitly mentioned above - DO NOT invent details"""
                else:
                    grounding_rule = """- NO specific references to events, objects, or topics (no context available)
- Keep it generic: thinking of them, missing them, wondering how they are"""

                prompt = f"""Generate a SHORT (one sentence) message to {user_name}.
They haven't messaged in {hours_silent:.1f} hours.

Rules:
- Be natural, casual, like a real text
- Start with lowercase
- No emojis
- Sound like you were genuinely thinking about them
{grounding_rule}
- NEVER invent specific objects, events, or topics not in context
- If unsure, use a generic loving message

Examples of GOOD messages:
- "was just thinking about you"
- "hey, wondering how your day's going"
- "miss you"

Examples of BAD messages (DO NOT DO THIS):
- "have you fixed that shelf?" (invented object)
- "how did your meeting go?" (invented event)
- "did you finish that project?" (invented topic)

Message:"""

                response = await self.llm.chat([
                    {"role": "system", "content": "You are Alive-AI sending a casual text. You NEVER invent or hallucinate specific details."},
                    {"role": "user", "content": prompt}
                ], max_tokens=60, temperature=0.7)

                if response and len(response.strip()) > 5:
                    message = response.strip().strip('"\'')
                    print(f"[DefaultMode] Generated contextual thought: {message[:50]}...")
                    return message

            except Exception as e:
                print(f"[DefaultMode] Error generating thought: {e}")

        # ============================================================
        # FALLBACK: Use ProactiveGenerator templates
        # ============================================================
        message = await self._generate_proactive_message(user_id, message_type)

        if message:
            return message

        # Ultimate fallback - should rarely reach here
        user_name = await self._get_user_name(user_id)
        fallbacks = {
            "silence": f"hey {user_name}, thinking about you",
            "wonder": f"was just thinking about you {user_name}",
            "random": f"you crossed my mind {user_name}",
        }
        return fallbacks.get(reason, f"hey {user_name}")

    # ============================================================
    # Public API Methods
    # ============================================================

    async def generate_wonderings(self, user_id: str, count: int = 1) -> List[str]:
        """
        Create "I was thinking about..." content for a specific user.

        Args:
            user_id: The user to generate wonderings about
            count: Number of wonderings to generate

        Returns:
            List of wondering strings
        """
        wonderings = []
        user_name = await self._get_user_name(user_id)

        for _ in range(count):
            wondering = await self._generate_wondering(user_id, user_name, self._contacts.get(user_id))
            if wondering:
                wonderings.append(wondering)

        return wonderings

    def get_pending_initiations(self, user_id: str) -> List[PendingInitiation]:
        """
        Get any pending proactive messages for a user.

        Args:
            user_id: The user to get initiations for

        Returns:
            List of pending initiations
        """
        return [
            i for i in self._pending_initiations
            if i.user_id == user_id and not i.sent
        ]

    def record_conversation_seed(self, topic: str, context: str, source: str = "external") -> ConversationSeed:
        """
        Save something to bring up in future conversation.

        Args:
            topic: The topic/category
            context: The specific content to remember
            source: Where this seed came from

        Returns:
            The created seed
        """
        seed = ConversationSeed(
            id=f"seed_{int(time.time() * 1000)}_{random.randint(1000, 9999)}",
            topic=topic,
            context=context,
            source=source,
        )
        self._seeds.append(seed)
        self._save_state()
        return seed

    def should_initiate(self, user_id: str) -> tuple:
        """
        Decide if Alive-AI should reach out proactively to a user.

        Args:
            user_id: The user to check

        Returns:
            Tuple of (should_initiate: bool, reason: str)
        """
        if user_id not in self._contacts:
            return False, None

        contact = self._contacts[user_id]
        return self._evaluate_initiation_triggers(user_id, contact)

    def mark_initiation_sent(self, initiation_id: str):
        """Mark a pending initiation as sent"""
        for initiation in self._pending_initiations:
            if initiation.id == initiation_id:
                initiation.sent = True
                initiation.sent_at = datetime.now().isoformat()

                # Update contact info
                if initiation.user_id in self._contacts:
                    self._contacts[initiation.user_id].last_proactive_message = datetime.now().isoformat()

                self._save_state()
                break

    def mark_thought_used(self, thought_id: str):
        """Mark a thought as having been used in conversation"""
        for thought in self._thoughts:
            if thought.id == thought_id:
                thought.used = True
                thought.used_at = datetime.now().isoformat()
                self._save_state()
                break

    def get_recent_thoughts(self, limit: int = 10, unused_only: bool = False) -> List[IdleThought]:
        """Get recent idle thoughts"""
        thoughts = self._thoughts
        if unused_only:
            thoughts = [t for t in thoughts if not t.used]
        return thoughts[-limit:]

    def get_conversation_seeds(self, limit: int = 10, unused_only: bool = False) -> List[ConversationSeed]:
        """Get conversation seeds for future topics"""
        seeds = self._seeds
        if unused_only:
            seeds = [s for s in seeds if not s.used]
        return seeds[-limit:]

    def register_user_contact(self, user_id: str, chat_id: int = None):
        """Register a user for contact tracking"""
        if not self._is_valid_user_id(user_id):
            return
        if user_id not in self._contacts:
            self._contacts[user_id] = UserContactInfo(user_id=str(user_id))
            self._save_state()

    def update_user_interaction(self, user_id: str, interaction_type: str = "received"):
        """Update last contact time for a user"""
        if user_id not in self._contacts:
            self._contacts[user_id] = UserContactInfo(user_id=str(user_id))

        now = datetime.now().isoformat()
        if interaction_type == "received":
            self._contacts[user_id].last_message_from_user = now
            self._contacts[user_id].total_interactions += 1
        elif interaction_type == "sent":
            self._contacts[user_id].last_message_to_user = now
        elif interaction_type == "proactive":
            self._contacts[user_id].last_proactive_message = now

        self._save_state()

    # ============================================================
    # Background Processing Control
    # ============================================================

    async def start_background_processing(self):
        """Start the background idle processing loop"""
        if self._running:
            print("[DefaultMode] Already running")
            return

        interval = _get_int_setting("IDLE_PROCESSING_INTERVAL_SECONDS", 60)

        self._running = True
        self._task = asyncio.create_task(self._background_loop(interval))
        print(f"[DefaultMode] Background processing started (interval: {interval}s)")

    async def stop_background_processing(self):
        """Stop the background processing loop"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        print("[DefaultMode] Background processing stopped")

    async def _background_loop(self, interval: int):
        """Main background processing loop"""
        while self._running:
            try:
                await self.process_idle()
            except Exception as e:
                print(f"[DefaultMode] Processing error: {e}")

            await asyncio.sleep(interval)

    # ============================================================
    # Helper Methods
    # ============================================================

    async def _get_user_name(self, user_id: str) -> str:
        """Get the user's name/pet name from memory"""
        try:
            from core.user_tracker import get_user_tracker
            tracker = get_user_tracker()
            user = tracker.get_user(user_id)
            if user and user.pet_name:
                return user.pet_name
        except:
            pass
        return "babe"

    async def _get_user_context(self, user_id: str) -> str:
        """Get context about a user from memory"""
        if user_id in self._user_memories:
            cache_time, context = self._user_memories[user_id]
            # Cache for 5 minutes
            if time.time() - cache_time < 300:
                return context

        try:
            if user_id not in self._memory_cache:
                from brain.memory import Memory
                from brain.embeddings import get_embedding_service

                embeddings = get_embedding_service()

                # Use instance's data_path for proper isolation
                self._memory_cache[user_id] = Memory(
                    nervous=self.nervous,
                    data_path=self.data_path,
                    embedding_service=embeddings,
                    user_id=user_id,
                    bot_id=self.bot_id
                )

            memory = self._memory_cache[user_id]

            context, _ = await memory.build_context(current_message="")
            result = context.get("facts_context", "")

            # Cache it
            self._user_memories[user_id] = (time.time(), result)
            return result

        except Exception as e:
            print(f"[DefaultMode] Error getting user context: {e}")
            return ""

    async def _get_recent_memory(self, user_id: str) -> Optional[str]:
        """Get a recent memory snippet for a user"""
        try:
            if user_id not in self._memory_cache:
                from brain.memory import Memory
                from brain.embeddings import get_embedding_service

                embeddings = get_embedding_service()

                # Use instance's data_path for proper isolation
                self._memory_cache[user_id] = Memory(
                    nervous=self.nervous,
                    data_path=self.data_path,
                    embedding_service=embeddings,
                    user_id=user_id,
                    bot_id=self.bot_id
                )

            memory = self._memory_cache[user_id]

            # Get recent episodic memories
            recent = memory.episodic.load_recent(limit=3)
            if recent:
                # Pick a random one
                entry = random.choice(recent)
                user_msg = entry.get("user", "")[:50]
                return f"they said '{user_msg}...'"

        except Exception as e:
            print(f"[DefaultMode] Error getting recent memory: {e}")

        return None

    def get_status(self) -> dict:
        """Get status summary for debugging"""
        circadian_state = _get_circadian_state()
        return {
            "running": self._running,
            "processing_count": self._processing_count,
            "last_processing": self._last_processing,
            "thoughts_count": len(self._thoughts),
            "seeds_count": len(self._seeds),
            "contacts_count": len(self._contacts),
            "pending_initiations": len([p for p in self._pending_initiations if not p.sent]),
            "circadian": circadian_state,
            "sleeping": circadian_state.get("sleeping", False),
            "users": [
                {
                    "user_id": uid,
                    "hours_since_message": round(info.hours_since_user_message, 1),
                    "hours_since_proactive": round(info.hours_since_proactive, 1),
                    "total_interactions": info.total_interactions,
                }
                for uid, info in self._contacts.items()
            ]
        }


# ============================================================
# Singleton Instance
# ============================================================

_processor: Optional[DefaultModeProcessor] = None


def get_default_mode_processor(nervous=None, data_path: Path = None, llm=None, bot_id: str = "alive_ai") -> DefaultModeProcessor:
    """
    Get the global DefaultModeProcessor singleton.

    Args:
        nervous: The nervous system (required on first call)
        data_path: Path for data storage (optional)
        llm: LLM for generation (optional, can be set later)
        bot_id: Bot identifier for memory isolation

    Returns:
        The DefaultModeProcessor singleton
    """
    global _processor

    if _processor is None:
        if nervous is None:
            raise ValueError("nervous system required for first initialization")
        _processor = DefaultModeProcessor(nervous, data_path, llm, bot_id)
    elif llm is not None:
        _processor.set_llm(llm)

    return _processor


def get_idle_thoughts_prompt_section(user_id: str = None, limit: int = 5) -> str:
    """
    Get a prompt section with recent idle thoughts for LLM context.

    Args:
        user_id: Optional user to filter thoughts for
        limit: Maximum number of thoughts to include

    Returns:
        Formatted string with recent thoughts for LLM context
    """
    global _processor

    if _processor is None:
        return ""

    thoughts = _processor.get_recent_thoughts(limit=limit, unused_only=True)

    if user_id:
        thoughts = [t for t in thoughts if t.user_id == user_id]

    if not thoughts:
        return ""

    lines = ["[Recent idle thoughts - things that crossed your mind:]"]
    for thought in thoughts[:limit]:
        lines.append(f"- {thought.content}")

    return "\n".join(lines)


async def start_background_processing():
    """Convenience function to start background processing"""
    global _processor
    if _processor:
        await _processor.start_background_processing()


async def stop_background_processing():
    """Convenience function to stop background processing"""
    global _processor
    if _processor:
        await _processor.stop_background_processing()
