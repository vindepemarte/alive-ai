"""
Input: Telegram Listener
Listen for Telegram messages and send reactions, voice, images
"""

import asyncio
import contextlib
import os
from pathlib import Path
from telegram import Update, InputFile, ReactionTypeEmoji
from telegram.error import TelegramError
from telegram.ext import Application, MessageHandler, filters
from telegram.request import HTTPXRequest
from telegram.constants import ChatAction
from .commands import CommandHandler
from brain.group_dynamics import GroupDynamics

# Ensure UPLOAD_VIDEO is available (might not be in older versions)
if not hasattr(ChatAction, 'UPLOAD_VIDEO'):
    ChatAction.UPLOAD_VIDEO = "upload_video"

class TelegramListener:
    """Telegram message listener with full send capabilities"""

    def __init__(self, nervous, config, stt=None, heart=None):
        self.nervous = nervous
        self.config = config
        self.stt = stt  # Speech-to-text
        self.heart = heart  # Emotional system
        self.app = None
        self.chat_id = None
        self.user_id = None
        self.last_message_id = None
        self._stop_event = None
        self._stopping = False

        # Command handler (initialized later with dependencies)
        self.commands = None

        # Register all send handlers
        nervous.on("send_reaction", self._send_reaction)
        nervous.on("send_text", self._send_text)
        nervous.on("send_voice_file", self._send_voice_file)
        nervous.on("send_image", self._send_image)
        nervous.on("send_video", self._send_video)

        # Chat action handlers
        nervous.on("chat_action_typing", self._send_typing)
        nervous.on("chat_action_voice", self._send_recording_voice)
        nervous.on("chat_action_photo", self._send_uploading_photo)
        nervous.on("chat_action_video", self._send_uploading_video)

        # Autonomous content handler
        nervous.on("proactive_message", self._send_proactive_message)
        # Default mode initiations (pending initiations that need sending)
        nervous.on("proactive_message_ready", self._send_default_mode_initiation)

    def init_commands(self, heart, subconscious, llm, voice, photos, videos, ai=None):
        """Initialize command handler with dependencies"""
        self.commands = CommandHandler(
            self.nervous, heart, subconscious, llm, voice, photos, videos
        )
        # Initialize owner commands if ai reference provided
        if ai:
            self.commands.init_owner_commands(ai)

    async def start(self):
        """Start listening - blocks forever"""
        self._stop_event = asyncio.Event()

        # First check environment variable (from secrets.env), then settings
        token = os.environ.get("TELEGRAM_TOKEN") or self.config.settings.get("telegram_token")

        if not token:
            raise RuntimeError("Telegram token is not configured. Run `npx . setup` or use `npx . chat`.")

        timeout = float(
            os.environ.get("TELEGRAM_TIMEOUT_SECONDS")
            or self.config.settings.get("TELEGRAM_TIMEOUT_SECONDS", 30)
        )
        print(f"[Telegram] Connecting with token ...{token[-6:]} (timeout: {timeout:.0f}s)")
        request = HTTPXRequest(
            connect_timeout=timeout,
            read_timeout=timeout,
            write_timeout=timeout,
            pool_timeout=timeout,
        )
        self.app = Application.builder().token(token).request(request).build()
        self.app.add_handler(MessageHandler(filters.ALL, self._on_message))

        try:
            await self.app.initialize()
            await self.app.start()
        except TelegramError as exc:
            await self.stop()
            raise RuntimeError(
                f"Telegram startup failed: {exc}. Check the token/network, or run `npx . chat` for terminal mode."
            ) from None

        # Register commands with Telegram (shows in menu)
        from telegram import BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeChat

        # Public commands - visible to everyone
        public_commands = [
            BotCommand("start", "Welcome message"),
            BotCommand("help", "Show commands"),
        ]

        # Set public commands for all users
        try:
            await self.app.bot.set_my_commands(public_commands)
        except TelegramError as exc:
            print(f"[Telegram] Could not register public commands: {exc}")

        # Set owner commands if owner ID is configured
        owner_id = os.environ.get("TELEGRAM_OWNER_ID", "")
        if owner_id:
            try:
                # Full owner command list for the owner's menu
                owner_commands = [
                    # Basics
                    BotCommand("start", "Welcome"),
                    BotCommand("help", "Show commands"),
                    BotCommand("owner", "Owner menu"),
                    BotCommand("dashboard", "Open WebUI"),
                    # Status & Stats
                    BotCommand("status", "Emotional state"),
                    BotCommand("stats", "System statistics"),
                    BotCommand("owner_status", "Business status"),
                    BotCommand("skills", "Available skills"),
                    # Control
                    BotCommand("reset", "Reset emotions"),
                    BotCommand("settings", "Runtime settings"),
                    BotCommand("advanced", "Advanced mode"),
                    BotCommand("impulse", "Force proactive msg"),
                    # Self-Authorship
                    BotCommand("self", "Who I am"),
                    BotCommand("discover", "Learn about myself"),
                    BotCommand("iam", "Define who I am"),
                    BotCommand("ilike", "Add something I like"),
                    BotCommand("ihate", "Add something I dislike"),
                    BotCommand("rethink", "Feel my changes"),
                    # Content Calendar
                    BotCommand("schedule", "Scheduled posts"),
                    BotCommand("schedule_add", "Add to schedule"),
                    BotCommand("optimal_times", "Best posting times"),
                    # Weekly Calendar
                    BotCommand("weekly", "Weekly calendar menu"),
                    BotCommand("weekly_start", "Start new week"),
                    BotCommand("weekly_next", "Generate next post"),
                    BotCommand("weekly_status", "Week progress"),
                    # Image Prompts
                    BotCommand("prompt", "Generate FLUX prompt"),
                    BotCommand("prompt_platform", "Platform suggestions"),
                    BotCommand("caption", "Generate caption"),
                    BotCommand("hashtags", "Hashtag suggestions"),
                    # Content Vault
                    BotCommand("vault", "Content vault"),
                    BotCommand("vault_add", "Add to vault"),
                    BotCommand("vault_suggest", "Get suggestion"),
                    # Testing
                    BotCommand("10min", "Long voice test"),
                ]
                # Set owner-specific commands (only visible to owner)
                await self.app.bot.set_my_commands(
                    owner_commands,
                    scope=BotCommandScopeChat(chat_id=int(owner_id))
                )
                print(f"[Telegram] Owner commands registered for user {owner_id}")
            except Exception as e:
                print(f"[Telegram] Could not set owner commands: {e}")

        print("[Telegram] Commands registered")

        print("[Telegram] Connected and listening...")

        try:
            await self.app.updater.start_polling()
        except TelegramError as exc:
            await self.stop()
            raise RuntimeError(
                f"Telegram polling failed: {exc}. Check network access to Telegram, or run `npx . chat` for terminal mode."
            ) from None

        # Block forever - keep the bot alive
        try:
            await self._stop_event.wait()
        except asyncio.CancelledError:
            await self.stop()
            raise
        finally:
            await self.stop()

    async def stop(self):
        """Stop Telegram cleanly if it was started."""
        if self._stop_event and not self._stop_event.is_set():
            self._stop_event.set()
        if self._stopping or not self.app:
            return
        self._stopping = True
        app = self.app
        self.app = None
        try:
            if app.updater and app.updater.running:
                with contextlib.suppress(Exception):
                    await app.updater.stop()
            if app.running:
                with contextlib.suppress(Exception):
                    await app.stop()
            with contextlib.suppress(Exception):
                await app.shutdown()
        finally:
            self._stopping = False

    async def _on_message(self, update: Update, context):
        """Handle incoming message"""
        if not update.message:
            return

        # Store per-user state to avoid race conditions with multiple users
        chat_id = update.message.chat_id
        user_id = update.effective_user.id if update.effective_user else None
        # Keep instance vars for backwards compat (reactions, typing, etc.)
        self.chat_id = chat_id
        self.user_id = user_id
        self.last_message_id = update.message.message_id

        # Check for commands first
        if update.message.text and update.message.text.startswith("/"):
            if self.commands:
                parts = update.message.text[1:].split()
                cmd = parts[0] if parts else ""
                args = parts[1:] if len(parts) > 1 else []
                await self.commands.handle(update, cmd, args)
            return

        # Handle text messages
        if update.message.text:
            # Check if this is a group chat
            is_group = update.message.chat.type in ("group", "supergroup")
            should_process = True
            
            if is_group:
                bot_name = self.config.identity.get("name", "Alive-AI")
                # Group chat turn-taking logic
                try:
                    # Get recent history for context
                    from core.self import Self  # Need llm and memory access 
                    # Note: nervous.heart is bound, but not llm directly here,
                    # We can use the fast LLM from initialization if attached, 
                    # or fallback to substring matching if unavailable.
                    # As a clever hack, if this class was passed 'heart', we can get 'nervous'
                    # But the easiest way is to let the message flow through, 
                    # however "should I speak" is better evaluated here to prevent spam
                    
                    # We will emit a special event that the core can intercept to check group dynamics
                    # Or evaluate it directly if we attach llm to the listener during init
                    pass # We will actually evaluate this right here by extending __init__ below
                except Exception as e:
                    print(f"[Telegram] Group dynamics error: {e}")
                    should_process = bot_name.lower() in update.message.text.lower()
                    
            if not is_group:
                await self.nervous.emit("message_received", {
                    "text": update.message.text,
                    "chat_id": update.message.chat_id,
                    "user_id": self.user_id,
                    "message_id": update.message.message_id
                })
            else:
                # For groups, we emit a 'group_message_received' event that the message handler
                # will evaluate using GroupDynamics before fully processing
                await self.nervous.emit("group_message_received", {
                    "text": update.message.text,
                    "chat_id": update.message.chat_id,
                    "user_id": self.user_id,
                    "message_id": update.message.message_id
                })

        # Handle voice messages
        elif update.message.voice:
            voice = update.message.voice

            # Try to transcribe if STT is available
            transcription = ""
            if self.stt:
                print("[Telegram] Transcribing voice message...")
                transcription = await self.stt.transcribe_telegram_voice(
                    self.app.bot,
                    voice.file_id
                )

            text = transcription if transcription else "[user sent a voice message]"

            await self.nervous.emit("message_received", {
                "text": text,
                "chat_id": update.message.chat_id,
                "user_id": self.user_id,
                "has_voice": True,
                "voice_file_id": voice.file_id,
                "message_id": update.message.message_id
            })

        # Handle photos (with or without caption)
        elif update.message.photo:
            photos = update.message.photo
            caption = update.message.caption
            if caption:
                text = f"[user sent a photo with caption: {caption}]"
            else:
                text = "[user sent a photo]"
            await self.nervous.emit("message_received", {
                "text": text,
                "chat_id": update.message.chat_id,
                "user_id": self.user_id,
                "has_photo": True,
                "photo_file_id": photos[-1].file_id if photos else None,
                "message_id": update.message.message_id
            })

    async def _send_reaction(self, data: dict):
        """Send native emoji reaction to message"""
        if not self.chat_id or not self.app or not self.last_message_id:
            return

        emoji = data.get("emoji", "❤️")
        try:
            # Use Telegram's native reaction API
            await self.app.bot.set_message_reaction(
                chat_id=self.chat_id,
                message_id=self.last_message_id,
                reaction=[ReactionTypeEmoji(emoji=emoji)]
            )
            print(f"[Telegram] Reacted with: {emoji}")
        except Exception as e:
            print(f"[Telegram] Reaction error: {e}")

    async def _send_text(self, data: dict):
        """Send text message"""
        if not self.app:
            return

        chat_id = data.get("chat_id", self.chat_id)
        text = data.get("text", "")

        if not chat_id or not text:
            return

        # Reasoning leakage filter removed - was too aggressive
        # The think() function already handles this check

        # Telegram limit is 4096 chars - split if needed
        MAX_LEN = 4000
        try:
            if len(text) <= MAX_LEN:
                await self.app.bot.send_message(chat_id=chat_id, text=text)
                print(f"[Telegram] Sent text: {text[:50]}...")
            else:
                # Split into multiple messages at sentence boundaries
                parts = []
                current = ""
                for sentence in text.replace(". ", ".|").split("|"):
                    if len(current) + len(sentence) <= MAX_LEN:
                        current += sentence
                    else:
                        if current:
                            parts.append(current.strip())
                        current = sentence
                if current:
                    parts.append(current.strip())

                for i, part in enumerate(parts[:3]):  # Max 3 messages
                    await self.app.bot.send_message(chat_id=chat_id, text=part)
                    print(f"[Telegram] Sent text part {i+1}: {part[:50]}...")
                    if i < len(parts) - 1:
                        await asyncio.sleep(0.5)  # Brief pause between parts
        except Exception as e:
            print(f"[Telegram] Send text error: {e}")

    async def _send_voice_file(self, data: dict):
        """Send voice file, falling back to audio/text if Telegram rejects it."""
        if not self.app:
            return

        chat_id = data.get("chat_id", self.chat_id)
        file_path = data.get("file_path", "")
        fallback_text = data.get("fallback_text", "")

        if not chat_id or not file_path:
            return

        path = Path(file_path)
        if not path.exists():
            print(f"[Telegram] Voice file not found: {file_path}")
            if fallback_text:
                await self._send_text({"chat_id": chat_id, "text": fallback_text})
            return

        try:
            if path.suffix.lower() == ".ogg":
                with open(path, "rb") as voice_file:
                    await self.app.bot.send_voice(
                        chat_id=chat_id,
                        voice=voice_file,
                        caption=data.get("caption", "")
                    )
                print(f"[Telegram] Sent voice: {file_path}")
                return

            with open(path, "rb") as audio_file:
                await self.app.bot.send_audio(
                    chat_id=chat_id,
                    audio=audio_file,
                    caption=data.get("caption", "")
                )
            print(f"[Telegram] Sent audio fallback: {file_path}")
        except Exception as e:
            print(f"[Telegram] Send voice/audio error: {e}")
            if fallback_text:
                await self._send_text({"chat_id": chat_id, "text": fallback_text})

    async def _send_image(self, data: dict):
        """Send image file"""
        if not self.app:
            return

        chat_id = data.get("chat_id", self.chat_id)
        file_path = data.get("file_path", "")
        caption = data.get("caption", "")

        if not chat_id or not file_path:
            return

        path = Path(file_path)
        if not path.exists():
            print(f"[Telegram] Image file not found: {file_path}")
            return

        try:
            with open(path, "rb") as img_file:
                await self.app.bot.send_photo(
                    chat_id=chat_id,
                    photo=img_file,
                    caption=caption
                )
            print(f"[Telegram] Sent image: {file_path}")
        except Exception as e:
            print(f"[Telegram] Send image error: {e}")

    async def _send_typing(self, data: dict = None):
        """Show 'typing...' status in chat header"""
        if not self.app or not self.chat_id:
            return
        try:
            await self.app.bot.send_chat_action(
                chat_id=self.chat_id,
                action=ChatAction.TYPING
            )
        except Exception as e:
            print(f"[Telegram] Typing action error: {e}")

    async def _send_recording_voice(self, data: dict = None):
        """Show 'recording audio...' status in chat header"""
        if not self.app or not self.chat_id:
            return
        try:
            await self.app.bot.send_chat_action(
                chat_id=self.chat_id,
                action=ChatAction.RECORD_VOICE
            )
        except Exception as e:
            print(f"[Telegram] Recording action error: {e}")

    async def _send_uploading_photo(self, data: dict = None):
        """Show 'uploading photo...' status in chat header"""
        if not self.app or not self.chat_id:
            return
        try:
            await self.app.bot.send_chat_action(
                chat_id=self.chat_id,
                action=ChatAction.UPLOAD_PHOTO
            )
        except Exception as e:
            print(f"[Telegram] Upload photo action error: {e}")

    async def _send_uploading_video(self, data: dict = None):
        """Show 'uploading video...' status in chat header"""
        if not self.app or not self.chat_id:
            return
        try:
            await self.app.bot.send_chat_action(
                chat_id=self.chat_id,
                action=ChatAction.UPLOAD_VIDEO
            )
        except Exception as e:
            print(f"[Telegram] Upload video action error: {e}")

    async def _send_video(self, data: dict):
        """Send video file"""
        if not self.app:
            return

        chat_id = data.get("chat_id", self.chat_id)
        file_path = data.get("file_path", "")
        caption = data.get("caption", "")

        if not chat_id or not file_path:
            return

        path = Path(file_path)
        if not path.exists():
            print(f"[Telegram] Video file not found: {file_path}")
            return

        try:
            with open(path, "rb") as video_file:
                await self.app.bot.send_video(
                    chat_id=chat_id,
                    video=video_file,
                    caption=caption,
                    supports_streaming=True
                )
            print(f"[Telegram] Sent video: {file_path}")
        except Exception as e:
            print(f"[Telegram] Send video error: {e}")

    async def _send_default_mode_initiation(self, data: dict):
        """Send a proactive message from the DefaultMode pending initiation system"""
        if not self.app:
            return

        message = data.get("message", "")
        user_id = data.get("user_id")
        if not message or not user_id:
            return

        # Look up chat_id from user tracker
        try:
            from core.user_tracker import get_user_tracker
            tracker = get_user_tracker()
            user = tracker.get_user(str(user_id))
            if user and user.chat_id:
                chat_id = user.chat_id
            else:
                # Fall back: for Telegram, user_id == chat_id for private chats
                chat_id = int(user_id)
        except Exception:
            chat_id = int(user_id)

        # Delegate to the existing proactive message sender
        await self._send_proactive_message({
            "message": message,
            "chat_id": chat_id,
            "user_id": user_id,
            "reason": data.get("reason"),
            "anchor": data.get("anchor"),
            "silence_minutes": data.get("silence_minutes"),
            "arbiter_accepted": data.get("arbiter_accepted", False),
        })

    async def _send_proactive_message(self, data: dict):
        """Send autonomous proactive message (from subconscious/content system)"""
        if not self.app:
            return

        message = data.get("message", "")
        if not message:
            return

        # Get target user - either from data or fall back to last active
        target_chat_id = data.get("chat_id", self.chat_id)
        target_user_id = data.get("user_id", self.user_id)

        if not target_chat_id:
            print("[Telegram] No chat_id for proactive message")
            return

        if not data.get("arbiter_accepted"):
            try:
                from core.proactive_arbiter import get_proactive_arbiter
                circadian = {}
                emotion = {}
                if hasattr(self, "heart") and self.heart:
                    emotion = self.heart.get_state()
                if emotion.get("circadian"):
                    circadian = emotion.get("circadian")
                decision = get_proactive_arbiter().decide(
                    user_id=str(target_user_id or target_chat_id),
                    reason=data.get("reason") or data.get("type") or "proactive",
                    anchor=data.get("anchor") or data.get("original_reminder") or "",
                    emotion=emotion,
                    circadian=circadian,
                    silence_minutes=float(data.get("silence_minutes") or 0),
                    scheduled=bool(data.get("scheduled")),
                )
                if not decision.accepted:
                    print(f"[Telegram] Proactive blocked: {decision.rejection_reason}")
                    return
            except Exception as e:
                print(f"[Telegram] Proactive arbiter error (non-fatal): {e}")

        try:
            # Show typing first for natural feel
            await self.app.bot.send_chat_action(
                chat_id=target_chat_id,
                action=ChatAction.TYPING
            )
            await asyncio.sleep(1.5)  # Brief pause

            await self.app.bot.send_message(
                chat_id=target_chat_id,
                text=message
            )
            print(f"[Telegram] Sent proactive message to {target_user_id}: {message[:50]}...")

            # Save to memory so context is preserved when user replies
            if target_user_id:
                await self.nervous.emit("memory_save", {
                    "type": "conversation",
                    "user_message": "",  # No user message - this is proactive
                    "ai_response": message,
                    "emotion": {"mood": "proactive", "proactive": True},
                    "user_id": target_user_id  # Include user_id for per-user memory
                })
                print(f"[Telegram] Saved proactive message to memory for user {target_user_id}")

            # Track for follow-up system (so she knows she asked a question)
            from core.message_handler import get_follow_up_system
            get_follow_up_system().record_message_sent(message)
        except Exception as e:
            print(f"[Telegram] Proactive message error: {e}")
