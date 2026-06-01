"""
Core: Initialization
Module loading and startup logic for Self
"""

import os


async def load_modules(self, input_channel: str = "telegram"):
    """Load all modules and initialize the AI system"""
    name = self.config.identity.get("name", "AI")
    print(f"[{name}] Waking up...")

    instructions_path = self.base / "config" / "instructions.md"
    if instructions_path.exists():
        self._system_prompt = instructions_path.read_text()

    # Import modules
    from brain.memory import Memory
    from brain.llm import get_main_llm, get_fast_llm
    from brain.stt import GoogleSTT
    from brain.embeddings import get_embedding_service
    from heart.core import Heart
    from output.text.sender import TextSender
    from skills.photo_manager.scanner import PhotoScanner
    from skills.video_manager.scanner import VideoScanner

    _init_llms(self, name)
    await _init_voice(self, name)

    self._stt = GoogleSTT()
    self._embeddings = get_embedding_service()
    print(f"[{name}] STT and Embeddings ready")

    self._memory = Memory(self.nervous, self.base / "data", embedding_service=self._embeddings, bot_id=name)
    if self._fast_llm:
        self._memory.set_llm(self._fast_llm)
    self._heart = Heart(self.nervous, self.config)

    _init_photos(self, name)
    _init_videos(self, name)

    input_channel = (input_channel or "telegram").lower()
    if input_channel == "terminal":
        from input.terminal.listener import TerminalListener
        self._input = TerminalListener(self.nervous, self.config, stt=self._stt, heart=self._heart)
    else:
        from input.telegram.listener import TelegramListener
        self._input = TelegramListener(self.nervous, self.config, stt=self._stt, heart=self._heart)
    print(f"[{name}] Input channel: {input_channel}")
    self._output = TextSender(self.nervous, self.config)
    self.nervous.heart = self._heart

    # Initialize companion skills (after heart is available)
    _init_companion_tools(self, name)
    _init_experience_skills(self, name)


def _init_llms(self, name: str):
    """Initialize LLM clients with fallback support"""
    from brain.llm import get_main_llm, get_fast_llm, get_unified_llm_client
    from core.settings import get as settings_get

    # Check if fallback mode is enabled
    llm_fallback = settings_get("LLM_FALLBACK", {})
    fallback_enabled = llm_fallback.get("ENABLED", False)

    if fallback_enabled:
        print(f"[{name}] LLM Fallback Mode: ENABLED")
        print(f"[{name}] DEBUG llm_fallback = {llm_fallback}")
        order = llm_fallback.get("ORDER", ["zai", "openrouter"])
        print(f"[{name}] DEBUG order = {order}")
        print(f"[{name}] Fallback Order: {' -> '.join(order)}")

        # Use unified LLM
        self._llm = get_unified_llm_client()
        self._fast_llm = self._llm  # Use same unified client for both

        if self._llm:
            print(f"[{name}] Unified LLM connected with fallback chain")
        else:
            print(f"[{name}] Warning: Unified LLM initialization failed, falling back to single provider")
            self._llm = get_main_llm()
            self._fast_llm = get_fast_llm() or self._llm
    else:
        print(f"[{name}] LLM Provider: {os.environ.get('LLM_PROVIDER', settings_get('LLM_PROVIDER', 'zai'))}")
        self._llm = get_main_llm()
        self._fast_llm = get_fast_llm()

    if self._llm:
        print(f"[{name}] Main LLM connected")
    else:
        print(f"[{name}] Warning: No LLM available!")

    if self._fast_llm:
        print(f"[{name}] Fast LLM connected")
    else:
        self._fast_llm = self._llm


async def _init_voice(self, name: str):
    """Initialize voice TTS - supports multiple providers"""
    from output.voice import create_tts
    from core.settings import get

    # Get TTS provider from settings (default to vibe)
    tts_provider = get("TTS_PROVIDER", "vibe").lower()
    if tts_provider in ("none", "skip", "disabled", "off"):
        print(f"[{name}] Voice disabled")
        self._voice = None
        return

    # Provider-specific configuration
    if tts_provider == "google":
        api_key = get("GOOGLE_TTS_API_KEY", "") or os.environ.get("GOOGLE_TTS_API_KEY", "")
        self._voice = await create_tts("google", api_key=api_key)
    elif tts_provider == "gtts":
        # gTTS is free, no config needed
        self._voice = await create_tts("gtts")
    else:
        # Default: VibeVoice
        tts_url = get("vibe_tts_url", "") or os.environ.get("VIBE_TTS_URL", "")
        if not tts_url:
            print(f"[{name}] Warning: No vibe_tts_url configured")
            return
        self._voice = await create_tts("vibe", url=tts_url)

    if self._voice:
        print(f"[{name}] Voice connected (provider: {tts_provider})")
    else:
        self._voice = None


def _init_photos(self, name: str):
    """Initialize photo scanner"""
    from skills.photo_manager.scanner import PhotoScanner

    self._photos = PhotoScanner(
        self.base / "mypics", embedding_service=self._embeddings,
        vector_store=self._memory.vector_store
    )
    new = self._photos.scan_new()
    print(f"[{name}] Photos: {self._photos.stats()['total']} (+{len(new)} new)")


def _init_videos(self, name: str):
    """Initialize video scanner"""
    from skills.video_manager.scanner import VideoScanner

    self._videos = VideoScanner(self.base / "myvids")
    self._videos.scan()
    print(f"[{name}] Videos: {self._videos.stats()['total']}")


# ============================================================
# Companion Tools
# ============================================================

def _init_companion_tools(self, name: str):
    """Initialize local companion tools that are part of the public runtime."""
    _init_message_scheduler(self, name)


def _init_message_scheduler(self, name: str):
    """Initialize Message Scheduler skill for scheduled messages"""
    from skills.message_scheduler import get_message_scheduler

    self._message_scheduler = get_message_scheduler(
        nervous=self.nervous,
        data_path=self.base / "data" / "scheduled_messages"
    )
    print(f"[{name}] Message Scheduler initialized")


# ============================================================
# User Experience Skills
# ============================================================

def _init_experience_skills(self, name: str):
    """Initialize user experience skills (relationship building tools)"""
    _init_memory_callbacks(self, name)
    _init_anticipation_engine(self, name)
    _init_relationship_milestones(self, name)
    _init_content_unlocks(self, name)
    _init_intimacy_layers(self, name)
    _init_exclusive_moments(self, name)


def _init_memory_callbacks(self, name: str):
    """Initialize Memory Callbacks skill for conversation memory"""
    from skills.memory_callbacks import MemoryCallbacks

    self._memory_callbacks = MemoryCallbacks(
        nervous=self.nervous,
        memory=self._memory,
        heart=self._heart,
        data_path=self.base / "data" / "memory_callbacks.json"
    )
    print(f"[{name}] Memory Callbacks initialized")


def _init_anticipation_engine(self, name: str):
    """Initialize Anticipation Engine skill for content teases"""
    from skills.anticipation_engine import AnticipationEngine

    self._anticipation_engine = AnticipationEngine(
        nervous=self.nervous,
        heart=self._heart,
        state=self.state,
        data_path=self.base / "data" / "anticipation.json"
    )
    print(f"[{name}] Anticipation Engine initialized")


def _init_relationship_milestones(self, name: str):
    """Initialize Relationship Milestones skill"""
    from skills.relationship_milestones import RelationshipMilestones

    self._relationship_milestones = RelationshipMilestones(
        nervous=self.nervous,
        state=self.state,
        data_path=self.base / "data"  # Expects directory, appends milestones.json
    )
    print(f"[{name}] Relationship Milestones initialized")


def _init_content_unlocks(self, name: str):
    """Initialize Content Unlocks skill for progressive content access"""
    from skills.content_unlocks import ContentUnlocks

    self._content_unlocks = ContentUnlocks(
        nervous=self.nervous,
        heart=self._heart,
        state=self.state,
        milestones=self._relationship_milestones,
        data_path=self.base / "data" / "content_unlocks.json"
    )
    print(f"[{name}] Content Unlocks initialized")


def _init_intimacy_layers(self, name: str):
    """Initialize Intimacy Layers skill for natural progression"""
    from skills.intimacy_layers import IntimacyLayers

    self._intimacy_layers = IntimacyLayers(
        nervous=self.nervous,
        heart=self._heart,
        state=self.state,
        data_path=self.base / "data"
    )
    print(f"[{name}] Intimacy Layers initialized")


def _init_exclusive_moments(self, name: str):
    """Initialize Exclusive Moments skill for special time-limited moments"""
    from skills.exclusive_moments import ExclusiveMoments

    self._exclusive_moments = ExclusiveMoments(
        nervous=self.nervous,
        heart=self._heart,
        state=self.state
    )
    print(f"[{name}] Exclusive Moments initialized")
