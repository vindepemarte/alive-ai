# Input - Senses

How the AI perceives and processes incoming messages.

## Modules
- `telegram/` - Telegram bot integration
  - `listener.py` - Message handler, routes to nervous system
  - `voice.py` - Voice message processing via STT
  - `commands.py` - Admin command handler

## Commands (Admin Only)
- `/start` - Welcome message
- `/help` - Show all commands
- `/status` - Current emotional/subconscious state
- `/10min` - Generate long voice message (TTS test)
- `/impulse` - Force proactive message generation
- `/stats` - System statistics (photos, videos, LLM)
- `/reset` - Reset emotional state to defaults

## Integration Points
- Receives Telegram updates
- Uses STT for voice transcription
- Emits `message_received` event to nervous system
- Commands access: heart, subconscious, LLM, voice, photos, videos
