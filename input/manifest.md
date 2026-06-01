# Input - Senses

How the AI perceives and processes incoming messages.

## Modules
- `telegram/` - Telegram bot integration
  - `listener.py` - Message handler, routes to nervous system
  - `voice.py` - Voice message processing via STT
  - `commands.py` - Admin command handler
- `terminal/` - Local terminal chat integration
  - `listener.py` - CLI chat loop, slash commands, TUI events, and output handlers

## Commands
- `/start` - Welcome message
- `/help` - Show all commands
- `/status` - Current emotional/subconscious state
- `/10min` - Generate long voice message (TTS test)
- `/impulse` - Force proactive message generation
- `/stats` - System statistics (photos, videos, LLM)
- `/reset` - Reset emotional state to defaults
- `/dashboard` - Show local WebUI URL
- `/self`, `/iam`, `/ilike`, `/ihate`, `/discover`, `/rethink` - Self-authorship commands
- `/exit` - Stop terminal chat

## Integration Points
- Receives Telegram updates
- Receives split-pane terminal input through `npx . chat`, or raw shell input through `npx . chat --plain`
- Uses STT for voice transcription
- Emits `message_received` event to nervous system
- Commands access: heart, subconscious, LLM, voice, photos, videos
