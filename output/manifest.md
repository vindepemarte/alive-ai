# Output - Actions

How the AI responds to users.

## Modules
- `text/` - Text message sender
- `voice/` - Voice synthesis via VibeTTS
  - `vibe_tts.py` - TTS client with auto-splitting (5000 char limit)
  - `sender.py` - Voice file sender
- `images/` - Image generation via Fal.ai
  - `fal_gen.py` - Fal.ai API client

## Voice (VibeTTS)
- Connects to VibeVoice server (VIBE_TTS_URL)
- Mood-based CFG scaling (high_desire=1.9, neutral=1.5)
- Auto-splits long texts at paragraph boundaries
- Output: OGG format for Telegram

## Image Generation
- Fal.ai API for AI image generation
- Prompt enhancement based on mood/context

## Integration Points
- Receives events: `send_text`, `send_voice_file`, `send_image`, `send_video`
- Voice triggered by: user request, high desire, is_high_desire state
- Images/videos selected based on arousal level and context
