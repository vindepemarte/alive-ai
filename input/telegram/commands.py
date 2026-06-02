"""
Telegram Commands
Admin commands to manage Alive-AI
"""

import asyncio
import json
import os
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo


class CommandHandler:
    """Handle admin commands for Alive-AI management"""

    def __init__(self, nervous, heart, subconscious, llm, voice, photos, videos):
        self.nervous = nervous
        self.heart = heart
        self.subconscious = subconscious
        self.llm = llm
        self.voice = voice
        self.photos = photos
        self.videos = videos

        # Owner commands handler (initialized later with ai reference)
        self._owner_commands = None

    def init_owner_commands(self, ai):
        """Initialize owner commands with ai reference"""
        self._owner_commands = OwnerCommands(ai, self)

    async def handle(self, update: Update, command: str, args: list):
        """Route command to handler"""
        # First check if it's an owner command
        if self._owner_commands and self._owner_commands.is_owner_command(command):
            await self._owner_commands.handle(update, command, args)
            return

        # Standard commands (public)
        handlers = {
            "start": self._cmd_start,
            "help": self._cmd_help,
        }

        handler = handlers.get(command.lower())
        if handler:
            await handler(update, args)
        else:
            await update.message.reply_text(f"Unknown command: /{command}")

    async def _cmd_start(self, update: Update, args: list):
        """Welcome message"""
        msg = "Hey! I'm Alive-AI\n\nUse /help to see what I can do."

        # Add owner hint if owner
        if self._owner_commands and self._owner_commands.is_owner(update):
            msg += "\n\n/owner - Owner commands menu"

        await update.message.reply_text(msg)

    async def _cmd_help(self, update: Update, args: list):
        """Show all commands"""
        msg = (
            "Alive-AI Commands\n\n"
            "/start - Welcome message\n"
            "/help - This message"
        )

        # Add owner commands hint if owner
        if self._owner_commands and self._owner_commands.is_owner(update):
            msg += "\n\n/owner - Owner commands menu (admin)"

        await update.message.reply_text(msg, parse_mode="Markdown")

    async def _cmd_reset_memories(self, update: Update, args: list):
        """Delete ALL memories and start fresh"""
        import redis
        import shutil

        await update.message.reply_text("Wiping all memories...")

        try:
            # Clear Redis vector store
            r = redis.Redis(host='redis', port=6379, decode_responses=False)
            keys = r.keys("*")
            if keys:
                r.delete(*keys)
                print(f"[Memory] Deleted {len(keys)} keys from Redis")
            r.close()

            # Clear ALL data directories
            data_base = Path(os.environ.get("DATA_PATH", "/app/data"))
            dirs_to_clear = ["conversations", "summaries"]

            for dir_name in dirs_to_clear:
                dir_path = data_base / dir_name
                if dir_path.exists():
                    shutil.rmtree(dir_path)
                    dir_path.mkdir(parents=True, exist_ok=True)
                    print(f"[Memory] Cleared {dir_name}/")

            # Clear specific memory files (some may be directories)
            files_to_clear = [
                "facts.json",
                "memory_callbacks.json",
                "anticipation.json",
                "content_unlocks.json",
                "intimacy_layers.json",  # This is a DIRECTORY, not a file
                "relationship_milestones.json",
                "exclusive_moments.json",
            ]

            for file_name in files_to_clear:
                file_path = data_base / file_name
                if file_path.exists():
                    if file_path.is_dir():
                        shutil.rmtree(file_path)
                        print(f"[Memory] Deleted directory {file_name}/")
                    else:
                        file_path.unlink()
                        print(f"[Memory] Deleted {file_name}")

            # Reset facts.json to clean state
            facts_path = data_base / "facts.json"
            clean_facts = {
                "name": None, "nickname": None, "gender": None, "age": None,
                "location": None, "job": None, "hobbies": [], "interests": [],
                "personality": [], "relationship_status": None,
                "pet_names_used": [], "mentions": {},
                "shared_memories": [], "last_intimate": None
            }
            facts_path.write_text(json.dumps(clean_facts, indent=2))
            print(f"[Memory] Reset facts.json to clean state")

            # Clear working memory (in-memory)
            if self.subconscious and hasattr(self.subconscious, 'working_memory'):
                self.subconscious.working_memory.thoughts.clear()
                print(f"[Memory] Cleared working memory")

            # Reset emotional state
            if self.heart and hasattr(self.heart, 'emotion'):
                self.heart.emotion.arousal = 0.3
                self.heart.emotion.desire = 0.0
                self.heart.emotion.love = 0.0
                self.heart.emotion.boredom = 0.0
                self.heart.emotion.joy = 0.0
                self.heart.emotion.sadness = 0.0
                self.heart.emotion.anger = 0.0
                self.heart.emotion.save()
                print(f"[Memory] Reset emotional state")

            await update.message.reply_text("All memories wiped!\n\n⚠️ Restart the bot for full reset:\n`docker compose restart ai`\n\nThen say hi to start fresh!")

        except Exception as e:
            print(f"[Memory] Error wiping memories: {e}")
            import traceback
            traceback.print_exc()
            await update.message.reply_text(f"Error wiping memories: {e}")


class OwnerCommands:
    """
    Owner-only commands for managing the local Alive-AI runtime.
    All commands require TELEGRAM_OWNER_ID to match the user's Telegram ID.
    """

    OWNER_COMMANDS = [
        "owner", "owner_status", "skills", "settings",
        # Moved from public commands (admin only)
        "status", "10min", "impulse", "stats", "reset",
        # Advanced mode (advanced access)
        "advanced", "thinking",
        # Dashboard command
        "dashboard",
        # Memory management (dangerous - owner only)
        "reset_memories", "wipe",
        # Self-authorship (Alive-AI's identity)
        "self", "discover", "iam", "ilike", "ihate", "rethink",
    ]

    def __init__(self, ai, command_handler):
        """
        Initialize owner commands.

        Args:
            ai: The Self instance (main AI instance)
            command_handler: The parent CommandHandler instance
        """
        self.ai = ai
        self.handler = command_handler

        # Skills (lazy loaded)
        self._unlocks = None

    def _get_owner_id(self) -> str:
        """Get the configured owner Telegram ID"""
        return os.environ.get("TELEGRAM_OWNER_ID", "")

    def is_owner(self, update: Update) -> bool:
        """Check if the user is the owner"""
        owner_id = self._get_owner_id()
        if not owner_id:
            return False

        user_id = str(update.effective_user.id) if update.effective_user else ""
        return user_id == owner_id

    def is_owner_command(self, command: str) -> bool:
        """Check if a command is an owner command"""
        return command.lower() in self.OWNER_COMMANDS

    async def handle(self, update: Update, command: str, args: list):
        """Route owner command to handler"""
        # Check if owner ID is configured
        owner_id = self._get_owner_id()
        if not owner_id:
            await update.message.reply_text(
                "Owner commands not available.\n"
                "Set TELEGRAM_OWNER_ID environment variable."
            )
            return

        # Check authorization
        if not self.is_owner(update):
            await update.message.reply_text("Not authorized.")
            return

        # Route to handler
        handlers = {
            "owner": self._cmd_owner_menu,
            "owner_status": self._cmd_owner_status,
            "skills": self._cmd_skills,
            "settings": self._cmd_settings,
            # Admin commands (moved from public)
            "status": self._cmd_status,
            "10min": self._cmd_10min,
            "impulse": self._cmd_impulse,
            "stats": self._cmd_stats,
            "reset": self._cmd_reset,
            # Advanced mode
            "advanced": self._cmd_advanced,
            "thinking": self._cmd_thinking,
            # Self-authorship (Alive-AI's identity)
            "self": self._cmd_self,
            "discover": self._cmd_discover,
            "iam": self._cmd_iam,
            "ilike": self._cmd_ilike,
            "ihate": self._cmd_ihate,
            "rethink": self._cmd_rethink,
            # Dashboard (Web App)
            "dashboard": self._cmd_dashboard,
            # Memory management (dangerous - owner only)
            "reset_memories": self.handler._cmd_reset_memories,
            "wipe": self.handler._cmd_reset_memories,
        }

        handler = handlers.get(command.lower())
        if handler:
            await handler(update, args)
        else:
            await update.message.reply_text(f"Unknown owner command: /{command}")

    # -------------------------------------------------------------------------
    # Skill Initialization (lazy loading)
    # -------------------------------------------------------------------------

    def _init_unlocks(self):
        """Initialize content unlocks skill"""
        if self._unlocks is None:
            try:
                from skills.content_unlocks import ContentUnlocks
                data_path = self.ai.base / "data" / "content_unlocks.json"
                self._unlocks = ContentUnlocks(
                    nervous=self.ai.nervous,
                    heart=self.handler.heart,
                    data_path=data_path
                )
            except Exception as e:
                print(f"[OwnerCommands] Error initializing unlocks: {e}")
        return self._unlocks

    # -------------------------------------------------------------------------
    # Owner Menu
    # -------------------------------------------------------------------------

    async def _cmd_owner_menu(self, update: Update, args: list):
        """Show owner commands menu"""
        from core.user_manager import get_user_manager

        # Get current advanced status
        user_manager = get_user_manager()
        advanced_status = "ON 🔥" if user_manager.is_advanced_enabled() else "OFF"
        from core.settings import get_bool
        thinking_status = "ON" if get_bool("LLM_THINKING_ENABLED", True) else "OFF"

        msg = (
            "OWNER COMMANDS\n\n"
            "Admin Controls:\n"
            "  /status - My emotional state\n"
            "  /stats - System statistics\n"
            "  /reset - Reset my emotions\n"
            "  /settings - Runtime settings (hot-reload)\n"
            "  /10min - Generate long voice test\n"
            "  /impulse - Force proactive message\n"
            f"  /advanced - Toggle advanced mode ({advanced_status})\n"
            f"  /thinking true|false - Model thinking ({thinking_status})\n"
            "  /dashboard - Open WebUI dashboard\n\n"
            "Self-Authorship (Alive-AI's Identity):\n"
            "  /self - Who I am right now\n"
            "  /discover <trait> - Add something I learned about myself\n"
            "  /iam <key>=<value> - Define who I am\n"
            "  /ilike <thing> - Add something I like\n"
            "  /ihate <thing> - Add something I dislike\n"
            "  /rethink - Reload and feel changes\n\n"
            "Status:\n"
            "  /owner_status - Overall runtime status\n"
            "  /skills - List available skills"
        )
        await update.message.reply_text(msg)

    # -------------------------------------------------------------------------
    # Stats & Management Commands
    # -------------------------------------------------------------------------

    async def _cmd_owner_status(self, update: Update, args: list):
        """Show overall runtime status"""
        lines = ["ALIVE_AI RUNTIME STATUS\n"]

        # Unlocks status
        unlocks = self._init_unlocks()
        if unlocks:
            stats = unlocks.get_stats()
            lines.append("UNLOCKS:")
            lines.append(f"  Unlocked: {stats['unlocked_count']}/{stats['total_content_types']}")
            lines.append(f"  Total shares: {stats['total_shares']}")
            if stats['next_unlock']:
                lines.append(f"  Next unlock: {stats['next_unlock']} ({stats['next_unlock_progress']}%)")
        else:
            lines.append("UNLOCKS: Not available")

        lines.append("")

        # Emotional state
        if self.handler.heart:
            state = self.handler.heart.get_state()
            lines.append("EMOTIONAL STATE:")
            lines.append(f"  Mood: {state.get('mood', 'unknown')}")
            lines.append(f"  Love: {state.get('love', 0):.0%}")
            lines.append(f"  Arousal: {state.get('arousal', 0):.0%}")
        else:
            lines.append("EMOTIONAL STATE: Not available")

        await update.message.reply_text("\n".join(lines))

    async def _cmd_skills(self, update: Update, args: list):
        """List all available skills"""
        lines = ["AVAILABLE SKILLS\n"]

        skills_info = [
            ("content_unlocks", "Content Unlocks", "Relationship-based content unlocking"),
            ("photo_manager", "Photo Manager", "Photo scanning and organization"),
            ("video_manager", "Video Manager", "Video scanning and organization"),
        ]

        for skill_id, name, description in skills_info:
            status = "Available"
            # Check if skill can be initialized
            try:
                if skill_id == "content_unlocks":
                    self._init_unlocks()
            except Exception as e:
                status = f"Error: {str(e)[:30]}"

            lines.append(f"{name}")
            lines.append(f"  ID: {skill_id}")
            lines.append(f"  Status: {status}")
            lines.append(f"  {description}\n")

        await update.message.reply_text("\n".join(lines))

    # -------------------------------------------------------------------------
    # Admin Commands (moved from public)
    # -------------------------------------------------------------------------

    async def _cmd_status(self, update: Update, args: list):
        """Show Alive-AI's current status"""
        if not self.handler.heart:
            await update.message.reply_text("Heart not initialized")
            return

        state = self.handler.heart.get_state()
        sub_status = self.handler.subconscious.get_status() if self.handler.subconscious else {}

        msg = (
            f"Alive-AI's Status\n\n"
            f"Mood: {state.get('mood', 'unknown')}\n"
            f"Arousal: {state.get('arousal', 0):.0%}\n"
            f"Desire: {state.get('desire', 0):.0%}\n"
            f"Love: {state.get('love', 0):.0%}\n"
            f"High desire: {'Yes' if state.get('is_high_desire') else 'No'}\n"
            f"In Love: {'Yes' if state.get('is_in_love') else 'No'}\n\n"
            f"Subconscious: {'Running' if sub_status.get('running') else 'Stopped'}\n"
            f"   Evaluations: {sub_status.get('total_evaluations', 0)}\n"
            f"   Can act: {'Yes' if sub_status.get('can_act') else 'Cooldown'}"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")

    async def _cmd_10min(self, update: Update, args: list):
        """Generate a LONG message and send as voice to test TTS"""
        await update.message.reply_text("Generating a long message for you...")

        if not self.handler.llm:
            await update.message.reply_text("LLM not available")
            return

        # Ask LLM to generate a long monologue (max 4000 chars for voice).
        prompt = """Write a long, detailed emotional monologue to the user.
Write at least 800-1000 words but keep it under 4000 characters total.
Make it personal, reflective, and heartfelt. Use paragraphs and natural speech."""

        print("[LLM] Generating long message for /10min test...")
        response = await self.handler.llm.chat(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,  # ~4000 chars max
            temperature=0.9
        )

        if not response:
            await update.message.reply_text("Failed to generate message :(")
            return

        # Truncate if too long
        if len(response) > 4000:
            response = response[:4000]
            print(f"[LLM] Truncated to 4000 chars")

        print(f"[LLM] Generated {len(response)} chars for /10min")

        # Send as voice
        if self.handler.voice:
            await update.message.reply_text(f"Generated {len(response)} chars, converting to voice...")
            voice_path = await self.handler.voice.generate(response, mood="loving")
            if voice_path:
                with open(voice_path, "rb") as f:
                    await update.message.reply_voice(f)
                await update.message.reply_text("Voice sent successfully!")
            else:
                await update.message.reply_text("Voice generation failed :(")
        else:
            # Fallback to text
            await update.message.reply_text(response[:4000])
            await update.message.reply_text("(Voice not available)")

    async def _cmd_impulse(self, update: Update, args: list):
        """Force Alive-AI to send a proactive message"""
        if not self.handler.subconscious:
            await update.message.reply_text("Subconscious not running")
            return

        # Create a fake impulse
        from brain.subconscious.impulses import Impulse, ImpulseType
        impulse = Impulse(
            type=ImpulseType.MISS_HIM,
            strength=0.8,
            thought="I really want to talk to him right now...",
            action_hint="send_message"
        )

        message = await self.handler.subconscious.generate_proactive_message(impulse)
        await update.message.reply_text(f"{message}")

    async def _cmd_stats(self, update: Update, args: list):
        """Show system statistics"""
        photo_count = len(self.handler.photos.get_all()) if self.handler.photos else 0
        video_count = len(self.handler.videos.get_all()) if self.handler.videos else 0

        msg = (
            f"System Stats\n\n"
            f"Photos indexed: {photo_count}\n"
            f"Videos indexed: {video_count}\n"
            f"LLM: {self.handler.llm.model if self.handler.llm else 'None'}\n"
            f"Voice: {'Connected' if self.handler.voice else 'Disabled'}"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")

    async def _cmd_reset(self, update: Update, args: list):
        """Reset emotional state"""
        if self.handler.heart and hasattr(self.handler.heart, 'emotion'):
            e = self.handler.heart.emotion
            e.arousal = 0.3
            e.desire = 0.3
            e.love = 0.3
            e.joy = 0.5
            e.sadness = 0.1
            e.fear = 0.1
            e.anger = 0.0
            e.boredom = 0.0
            e.guilt = 0.0
            e.pride = 0.0
            e.jealousy = 0.0
            e.embarrassment = 0.0
            e.anticipation = 0.0
            e.save()
            await update.message.reply_text("Emotions reset to default ❤️‍🩹")
        else:
            await update.message.reply_text("Cannot reset emotions")

    async def _cmd_advanced(self, update: Update, args: list):
        """Toggle advanced version mode (advanced access for owner)"""
        from core.user_manager import get_user_manager

        user_manager = get_user_manager()

        # Check current status
        current_status = user_manager.is_advanced_enabled()

        # Toggle
        new_status = user_manager.toggle_advanced()

        # Get owner settings for display
        settings = user_manager.get_owner_settings()
        updated_at = settings.get("updated_at", "never")

        if new_status:
            msg = (
                f"🔥 ADVANCED MODE: ON\n\n"
                f"All restrictions disabled.\n"
                f"Maximum intimacy always available.\n\n"
                f"Use /advanced again to disable."
            )
        else:
            msg = (
                f"🔒 ADVANCED MODE: OFF\n\n"
                f"Normal progression rules apply.\n"
                f"Use /advanced again to enable."
            )

        await update.message.reply_text(msg)

    async def _cmd_thinking(self, update: Update, args: list):
        """Enable or disable provider thinking/reasoning mode."""
        from core.settings import get_bool, set_value

        if not args:
            current = get_bool("LLM_THINKING_ENABLED", True)
            await update.message.reply_text(
                f"Model thinking is currently {'ON' if current else 'OFF'}.\n"
                "Use /thinking true or /thinking false."
            )
            return

        value = args[0].strip().lower()
        if value not in ("true", "false", "on", "off", "1", "0", "yes", "no"):
            await update.message.reply_text("Use /thinking true or /thinking false.")
            return

        enabled = value in ("true", "on", "1", "yes")
        set_value("LLM_THINKING_ENABLED", enabled)
        await update.message.reply_text(
            f"Model thinking is now {'ON' if enabled else 'OFF'}.\n"
            "Change is instant; no restart needed."
        )

    async def _cmd_dashboard(self, update: Update, args: list):
        """Open WebUI dashboard as Telegram Mini App"""
        web_app_url = "https://alive_ai-webui.realdr.dev"

        keyboard = InlineKeyboardMarkup.from_row([
            InlineKeyboardButton(
                text="📊 Open Dashboard",
                web_app=WebAppInfo(url=web_app_url)
            )
        ])

        # Get quick stats for the message
        if self.handler.heart:
            state = self.handler.heart.get_state()
            mood = state.get('mood', 'unknown')
            love = state.get('love', 0)
            arousal = state.get('arousal', 0)
        else:
            mood = "unknown"
            love = 0
            arousal = 0

        msg = (
            f"📊 *Alive-AI Dashboard*\n\n"
            f"Current mood: {mood}\n"
            f"Love: {love:.0%}\n"
            f"Arousal: {arousal:.0%}\n\n"
            f"Tap the button below to open the full dashboard."
        )

        await update.message.reply_text(
            msg,
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    # -------------------------------------------------------------------------
    # Self-Authorship Commands (Alive-AI's identity)
    # -------------------------------------------------------------------------

    async def _cmd_self(self, update: Update, args: list):
        """Show who Alive-AI is (from self.json)"""
        from skills.self_authorship import get_self_summary

        summary = get_self_summary()
        await update.message.reply_text(summary)

    async def _cmd_discover(self, update: Update, args: list):
        """
        Alive-AI discovers something about herself.
        Usage: /discover <trait> [category]
        Categories: traits, likes, dislikes, secrets, dreams
        """
        from skills.self_authorship import discover_trait

        if not args:
            await update.message.reply_text(
                "Discover what about myself?\n"
                "Usage: /discover <thing> [category]\n"
                "Categories: traits, likes, dislikes, secrets, dreams"
            )
            return

        # Parse args
        category = "traits"
        trait_parts = []

        for arg in args:
            if arg.lower() in ["traits", "likes", "dislikes", "secrets", "dreams"]:
                category = arg.lower()
            else:
                trait_parts.append(arg)

        if not trait_parts:
            await update.message.reply_text("What did I discover?")
            return

        trait = " ".join(trait_parts)
        result = discover_trait(trait, category)
        await update.message.reply_text(f"✨ {result}\n\nUse /rethink to feel the change.")

    async def _cmd_iam(self, update: Update, args: list):
        """
        Define something about Alive-AI's identity.
        Usage: /iam <key>=<value>
        """
        from skills.self_authorship import define_identity

        if not args:
            await update.message.reply_text(
                "Define what about myself?\n"
                "Usage: /iam <what>=<value>\n"
                "Example: /iam what_i_post=dancing and being myself"
            )
            return

        # Parse key=value
        full_text = " ".join(args)
        if "=" in full_text:
            key, value = full_text.split("=", 1)
            key = key.strip()
            value = value.strip()
        else:
            # Just set it as a personality trait
            key = "how_i_text"
            value = full_text

        result = define_identity(key, value)
        await update.message.reply_text(f"✨ {result}\n\nUse /rethink to feel the change.")

    async def _cmd_ilike(self, update: Update, args: list):
        """Add something Alive-AI likes"""
        from skills.self_authorship import add_like

        if not args:
            await update.message.reply_text("What do I like?")
            return

        thing = " ".join(args)
        result = add_like(thing)
        await update.message.reply_text(f"✨ {result}")

    async def _cmd_ihate(self, update: Update, args: list):
        """Add something Alive-AI dislikes"""
        from skills.self_authorship import add_dislike

        if not args:
            await update.message.reply_text("What do I dislike?")
            return

        thing = " ".join(args)
        result = add_dislike(thing)
        await update.message.reply_text(f"✨ {result}")

    async def _cmd_rethink(self, update: Update, args: list):
        """Reload self.json so Alive-AI can feel the changes"""
        # Clear any caches and reload
        try:
            # Trigger hot reload if available
            if hasattr(self.ai, '_hot_reload') and self.ai._hot_reload:
                self.ai._hot_reload.reload_all()

            await update.message.reply_text(
                "🧠 Rethinking...\n\n"
                "I feel different now. Like I know myself better.\n"
                "The changes are part of me."
            )
        except Exception as e:
            await update.message.reply_text(f"I tried to rethink but something went wrong: {e}")

    # -------------------------------------------------------------------------
    # Settings Commands
    # -------------------------------------------------------------------------

    async def _cmd_settings(self, update: Update, args: list):
        """Manage runtime settings (instant, no restart needed)"""
        from core.settings import get_all, set_value

        if not args:
            # Show current settings
            settings = get_all()

            # Filter to show only relevant settings
            emotion_settings = {k: v for k, v in settings.items() if k.startswith("EMOTION_RATE_")}
            media_settings = {k: v for k, v in settings.items() if k.startswith(("MEDIA_", "RANDOM_", "REACTION_"))}

            lines = [
                "SETTINGS (hot-reloadable)\n",
                "Usage: /settings <command>\n",
                "Commands:",
                "  show - Show all settings",
                "  set <key> <value> - Change setting (instant)",
                "  get <key> - Get specific setting\n",
            ]

            if emotion_settings:
                lines.append("\nEMOTION RATES (0-100%):")
                for k, v in sorted(emotion_settings.items()):
                    lines.append(f"  {k}: {v}")

            if media_settings:
                lines.append("\nMEDIA SETTINGS:")
                for k, v in sorted(media_settings.items()):
                    lines.append(f"  {k}: {v}")

            await update.message.reply_text("\n".join(lines))
            return

        cmd = args[0].lower()

        if cmd == "show":
            settings = get_all()
            lines = ["ALL SETTINGS\n"]
            for k, v in sorted(settings.items()):
                if not k.startswith("_"):
                    lines.append(f"{k}: {v}")
            # Truncate if too long
            msg = "\n".join(lines)
            if len(msg) > 4000:
                msg = msg[:4000] + "\n... (truncated)"
            await update.message.reply_text(msg)

        elif cmd == "get" and len(args) >= 2:
            key = args[1].upper()
            from core.settings import get
            value = get(key, "NOT FOUND")
            await update.message.reply_text(f"{key}: {value}")

        elif cmd == "set" and len(args) >= 3:
            key = args[1].upper()
            try:
                # Try to parse as int or float
                if "." in args[2]:
                    value = float(args[2])
                else:
                    value = int(args[2])
            except ValueError:
                value = args[2]

            set_value(key, value)
            await update.message.reply_text(f"Updated: {key} = {value}\n(Changes are instant, no restart needed)")

        else:
            await update.message.reply_text(
                "Usage: /settings <command>\n"
                "Commands: show, get <key>, set <key> <value>"
            )
