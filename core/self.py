"""
Core: Self
The AI's Self - coordinates everything via nervous system
"""

import asyncio
from pathlib import Path
from .events import NervousSystem
from .config import Config
from .state import State
from .initialization import load_modules
from .subconscious_bridge import handle_subconscious_impulse
from .message_handler import handle_message
from .settings import ACTIVE_SETTINGS_PATH


class Self:
    """The Self - central consciousness"""

    def __init__(self, base_path: Path):
        self.base = base_path
        self.nervous = NervousSystem()
        self.config = Config(base_path / "config")
        self.state = State()

        # Modules (lazy loaded)
        self._memory = None
        self._heart = None
        self._input = None
        self._output = None
        self._llm = None
        self._fast_llm = None
        self._voice = None
        self._timer_task = None
        self._subconscious = None
        self._system_prompt = ""
        self._default_chat_id = None
        self._stt = None
        self._embeddings = None
        self._photos = None
        self._videos = None
        self._hot_reload = None

        # User Experience Skills
        self._memory_callbacks = None
        self._anticipation_engine = None
        self._relationship_milestones = None
        self._content_unlocks = None
        self._intimacy_layers = None
        self._exclusive_moments = None

        # Default Mode Network (background idle processing)
        self._default_mode = None

    async def start(self):
        """Start the AI system"""
        # Set the active settings path for this async context
        settings_path = self.base / "config" / "settings.json"
        ACTIVE_SETTINGS_PATH.set(settings_path)

        # Set the self.json path for instance-specific identity
        from skills.self_authorship.author import set_self_path
        self_path = self.base / "config" / "self.json"
        set_self_path(self_path)

        # Set the directives.json path for instance-specific rules
        from core.directives import set_directives_path
        directives_path = self.base / "config" / "directives.json"
        set_directives_path(directives_path)

        name = self.config.identity.get("name", "AI")

        # Load modules via initialization module
        await load_modules(self)

        # Init Subconscious
        from brain.subconscious import SubconsciousLoop
        self._subconscious = SubconsciousLoop(
            nervous=self.nervous,
            heart=self._heart,
            llm=self._llm,
            fast_llm=self._fast_llm,
            on_impulse=lambda impulse: handle_subconscious_impulse(self, impulse),
            bot_id=name
        )

        # Initialize proactive generator for contextual messages
        self._subconscious.init_proactive_generator(llm=self._fast_llm, data_path=self.base / "data")

        await self._subconscious.start()
        print(f"[{name}] Subconscious activated - {name} is now ALIVE!")

        # Init Default Mode Network (background idle processing)
        try:
            from brain.default_mode import get_default_mode_processor
            self._default_mode = get_default_mode_processor(
                nervous=self.nervous,
                data_path=self.base / "data",
                llm=self._fast_llm,
                bot_id=name
            )
            await self._default_mode.start_background_processing()
            print(f"[{name}] Default Mode Network activated - background thoughts enabled")
        except Exception as e:
            print(f"[{name}] Default Mode Network unavailable: {e}")

        # Init command handler
        self._input.init_commands(
            heart=self._heart, subconscious=self._subconscious, llm=self._llm,
            voice=self._voice, photos=self._photos, videos=self._videos,
            ai=self  # Pass self reference for owner commands
        )

        # Register handlers - use asyncio.ensure_future for async handler
        from core.message_handler import handle_message, handle_group_message
        self.nervous.on("message_received", lambda data: asyncio.ensure_future(handle_message(self, data)))
        self.nervous.on("group_message_received", lambda data: asyncio.ensure_future(handle_group_message(self, data)))

        # Start emotion decay timer
        self._timer_task = asyncio.create_task(self._decay_timer())

        # Start hot reloader
        try:
            from .hot_reload import HotReloader
            self._hot_reload = HotReloader(self.nervous)
            self._hot_reload.start()
        except Exception as e:
            print(f"[{name}] Hot reload unavailable: {e}")

        print(f"[{name}] Ready!")

        # Start listening
        await self._input.start()

    async def _decay_timer(self):
        """Natural emotion decay every minute + memory check"""
        from .memory_monitor import get_memory_monitor

        # Get memory limit from env or default to 5GB
        import os
        max_mem = float(os.environ.get("ALIVE_AI_MAX_MEMORY_GB", "5.0"))
        monitor = get_memory_monitor(max_memory_gb=max_mem)

        while True:
            await asyncio.sleep(60)
            await self.nervous.emit("timer_tick", {})

            # Check memory every minute
            try:
                result = monitor.check()
                if result["status"] != "ok":
                    print(f"[Self] Memory status: {result['status']}, actions: {result['actions']}")
            except Exception as e:
                print(f"[Self] Memory check error: {e}")

    def get_subconscious_status(self) -> dict:
        """Get status of the subconscious system"""
        if self._subconscious:
            return self._subconscious.get_status()
        return {"running": False, "error": "Subconscious not initialized"}

    def get_soul_status(self) -> dict:
        """Get status of the Soul Architecture system"""
        if self._heart and hasattr(self._heart, 'soul'):
            return self._heart.soul.get_state_summary()
        return {"error": "Soul Architecture not initialized"}

    def get_soul_experience(self) -> dict:
        """Get current soul emotional experience"""
        if self._heart and hasattr(self._heart, 'soul'):
            experience = self._heart.soul.process_moment()
            return {
                "valence": experience.overall_valence,
                "arousal": experience.overall_arousal,
                "vulnerability": experience.overall_vulnerability,
                "response_tendency": experience.response_tendency,
                "description": experience.experience_description,
                "somatic": experience.somatic_sensation,
                "integrity": self._heart.soul.integrity.overall,
                "conflicts": len(experience.active_conflicts)
            }
        return {"error": "Soul Architecture not available"}

    def get_default_mode_status(self) -> dict:
        """Get status of the Default Mode Network"""
        if self._default_mode:
            return self._default_mode.get_status()
        return {"running": False, "error": "Default Mode Network not initialized"}
