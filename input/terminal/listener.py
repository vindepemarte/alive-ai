"""
Input: Terminal Listener
Local terminal chat channel that emits the same events as Telegram.
"""

import asyncio
import os


class TerminalListener:
    """Terminal input/output adapter for Alive-AI."""

    def __init__(self, nervous, config, stt=None, heart=None):
        self.nervous = nervous
        self.config = config
        self.stt = stt
        self.heart = heart
        self.subconscious = None
        self.llm = None
        self.voice = None
        self.photos = None
        self.videos = None
        self.ai = None
        self.user_id = os.environ.get("ALIVE_AI_TERMINAL_USER_ID", "terminal_owner")
        self.chat_id = "terminal"

        nervous.on("send_text", self._send_text)
        nervous.on("send_voice_file", self._send_file)
        nervous.on("send_image", self._send_file)
        nervous.on("send_video", self._send_file)
        nervous.on("proactive_message", self._send_proactive)
        nervous.on("proactive_message_ready", self._send_proactive)

    def init_commands(self, heart, subconscious, llm, voice, photos, videos, ai=None):
        self.heart = heart
        self.subconscious = subconscious
        self.llm = llm
        self.voice = voice
        self.photos = photos
        self.videos = videos
        self.ai = ai

    async def start(self):
        """Start terminal chat. Blocks until /exit, EOF, or Ctrl+C."""
        name = self.config.identity.get("name", "Alive-AI")
        port = self.config.settings.get("WEBUI_PORT", 8080)
        print("")
        print(f"[Terminal] Chatting with {name}. Type /help for commands, /exit to stop.")
        print(f"[Terminal] Dashboard: http://127.0.0.1:{port}")
        print("")

        loop = asyncio.get_running_loop()
        while True:
            try:
                line = await loop.run_in_executor(None, input, "> ")
            except (EOFError, KeyboardInterrupt):
                print("")
                return

            text = line.strip()
            if not text:
                continue
            if text.startswith("/"):
                should_continue = await self._handle_command(text)
                if not should_continue:
                    return
                continue

            await self.nervous.emit("message_received", {
                "text": text,
                "chat_id": self.chat_id,
                "user_id": self.user_id,
                "message_id": "terminal"
            })

    async def _send_text(self, data: dict):
        text = data.get("text", "")
        if text:
            print("")
            print(text)
            print("")

    async def _send_file(self, data: dict):
        file_path = data.get("file_path") or data.get("path") or ""
        caption = data.get("caption") or ""
        if file_path:
            print("")
            print(f"[file] {file_path}")
            if caption:
                print(caption)
            print("")

    async def _send_proactive(self, data: dict):
        text = data.get("message") or data.get("text") or data.get("thought") or ""
        if text:
            print("")
            print(f"[proactive] {text}")
            print("")

    async def _handle_command(self, raw: str) -> bool:
        parts = raw[1:].split()
        command = parts[0].lower() if parts else ""
        args = parts[1:]

        handlers = {
            "help": self._cmd_help,
            "owner": self._cmd_help,
            "dashboard": self._cmd_dashboard,
            "status": self._cmd_status,
            "stats": self._cmd_stats,
            "self": self._cmd_self,
            "discover": self._cmd_discover,
            "iam": self._cmd_iam,
            "ilike": self._cmd_ilike,
            "ihate": self._cmd_ihate,
            "rethink": self._cmd_rethink,
            "reset": self._cmd_reset,
            "settings": self._cmd_settings,
            "impulse": self._cmd_impulse,
        }

        if command in ("exit", "quit", "stop"):
            print("[Terminal] Stopping Alive-AI.")
            return False

        handler = handlers.get(command)
        if not handler:
            print(f"Unknown command: /{command}. Type /help.")
            return True

        await handler(args)
        return True

    async def _cmd_help(self, args):
        print(
            "Terminal commands:\n"
            "  /help                 Show this menu\n"
            "  /dashboard            Show local dashboard URL\n"
            "  /status               Current emotional state\n"
            "  /stats                Runtime stats\n"
            "  /self                 Show identity summary\n"
            "  /discover <trait>     Add a discovered trait\n"
            "  /iam <key>=<value>    Define identity field\n"
            "  /ilike <thing>        Add a like\n"
            "  /ihate <thing>        Add a dislike\n"
            "  /rethink              Reload self-authorship changes\n"
            "  /settings show|get|set Runtime settings\n"
            "  /reset                Reset emotional state\n"
            "  /impulse              Force a proactive message\n"
            "  /exit                 Stop the runtime"
        )

    async def _cmd_dashboard(self, args):
        port = self.config.settings.get("WEBUI_PORT", 8080)
        print(f"Dashboard: http://127.0.0.1:{port}")

    async def _cmd_status(self, args):
        if not self.heart:
            print("Heart not initialized.")
            return
        state = self.heart.get_state()
        sub_status = self.subconscious.get_status() if self.subconscious else {}
        print(
            "Alive-AI status\n\n"
            f"Mood: {state.get('mood', 'unknown')}\n"
            f"Arousal: {state.get('arousal', 0):.0%}\n"
            f"Desire: {state.get('desire', 0):.0%}\n"
            f"Love: {state.get('love', 0):.0%}\n"
            f"Trust: {state.get('trust', 0):.0%}\n"
            f"Subconscious: {'running' if sub_status.get('running') else 'stopped'}\n"
            f"Evaluations: {sub_status.get('total_evaluations', 0)}"
        )

    async def _cmd_stats(self, args):
        photo_count = len(self.photos.get_all()) if self.photos else 0
        video_count = len(self.videos.get_all()) if self.videos else 0
        llm_name = getattr(self.llm, "model", None) or "none"
        print(
            "Runtime stats\n\n"
            f"Photos indexed: {photo_count}\n"
            f"Videos indexed: {video_count}\n"
            f"LLM: {llm_name}\n"
            f"Voice: {'connected' if self.voice else 'disabled'}"
        )

    async def _cmd_self(self, args):
        from skills.self_authorship import get_self_summary
        print(get_self_summary())

    async def _cmd_discover(self, args):
        from skills.self_authorship import discover_trait
        if not args:
            print("Usage: /discover <thing> [traits|likes|dislikes|secrets|dreams]")
            return
        category = "traits"
        trait_parts = []
        for arg in args:
            if arg.lower() in ("traits", "likes", "dislikes", "secrets", "dreams"):
                category = arg.lower()
            else:
                trait_parts.append(arg)
        if not trait_parts:
            print("What did I discover?")
            return
        print(discover_trait(" ".join(trait_parts), category))
        print("Use /rethink to feel the change.")

    async def _cmd_iam(self, args):
        from skills.self_authorship import define_identity
        if not args:
            print("Usage: /iam <key>=<value>")
            return
        full_text = " ".join(args)
        if "=" in full_text:
            key, value = full_text.split("=", 1)
        else:
            key, value = "how_i_text", full_text
        print(define_identity(key.strip(), value.strip()))
        print("Use /rethink to feel the change.")

    async def _cmd_ilike(self, args):
        from skills.self_authorship import add_like
        if not args:
            print("Usage: /ilike <thing>")
            return
        print(add_like(" ".join(args)))

    async def _cmd_ihate(self, args):
        from skills.self_authorship import add_dislike
        if not args:
            print("Usage: /ihate <thing>")
            return
        print(add_dislike(" ".join(args)))

    async def _cmd_rethink(self, args):
        if self.ai and getattr(self.ai, "_hot_reload", None):
            self.ai._hot_reload.reload_all()
        print("Rethinking complete. The updated self file is active.")

    async def _cmd_reset(self, args):
        if not self.heart or not hasattr(self.heart, "emotion"):
            print("Cannot reset emotions.")
            return
        emotion = self.heart.emotion
        emotion.arousal = 0.3
        emotion.desire = 0.3
        emotion.love = 0.3
        emotion.joy = 0.5
        emotion.sadness = 0.1
        emotion.fear = 0.1
        emotion.anger = 0.0
        emotion.boredom = 0.0
        emotion.guilt = 0.0
        emotion.pride = 0.0
        emotion.jealousy = 0.0
        emotion.embarrassment = 0.0
        emotion.anticipation = 0.0
        emotion.save()
        print("Emotions reset to defaults.")

    async def _cmd_settings(self, args):
        from core.settings import get, get_all, set_value
        if not args or args[0].lower() == "show":
            settings = get_all()
            for key, value in sorted(settings.items()):
                if not key.startswith("_"):
                    print(f"{key}: {value}")
            return
        if args[0].lower() == "get" and len(args) >= 2:
            key = args[1].upper()
            print(f"{key}: {get(key, 'NOT FOUND')}")
            return
        if args[0].lower() == "set" and len(args) >= 3:
            key = args[1].upper()
            raw_value = " ".join(args[2:])
            value = self._parse_setting_value(raw_value)
            set_value(key, value)
            print(f"Updated {key} = {value}")
            return
        print("Usage: /settings show|get <key>|set <key> <value>")

    async def _cmd_impulse(self, args):
        if not self.subconscious:
            print("Subconscious not running.")
            return
        from brain.subconscious.impulses import Impulse, ImpulseType
        impulse = Impulse(
            type=ImpulseType.MISS_HIM,
            strength=0.8,
            thought="I want to talk right now.",
            action_hint="send_message"
        )
        message = await self.subconscious.generate_proactive_message(impulse)
        print(message)

    def _parse_setting_value(self, raw_value: str):
        lowered = raw_value.lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
        try:
            if "." in raw_value:
                return float(raw_value)
            return int(raw_value)
        except ValueError:
            return raw_value
