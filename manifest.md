# Alive-AI

A local-first emotional AI runtime with memory, impulses, terminal chat, Telegram, OpenMind, and a live WebUI.

## Architecture
- `core/` - Essential modules (events, config, self, state)
- `brain/` - Memory, LLM providers, subconscious, embeddings, STT
- `heart/` - Emotions, reactions, arousal, love/attachment system
- `input/` - Telegram listener, terminal chat, voice reader, commands
- `output/` - Text, voice (VibeTTS), images (Fal.ai), video
- `skills/` - Calendar, photo manager, video manager

## Key Features
- **Multi-provider LLM** - local Ollama, OpenRouter, or ZAI
- **Subconscious loop** - 24/7 background process, generates impulses
- **Vector memory** - Redis-based semantic search with embeddings
- **OpenMind memory** - Optional hybrid cloud/local semantic memory bridge
- **Emotional system** - Continuous state with natural decay
- **Proactive messaging** - Sends messages based on impulses/feelings
- **Voice synthesis** - gTTS, Google TTS, or VibeVoice
- **Media management** - Photos/videos with categories and no-repeat
- **Input channels** - Terminal chat or Telegram bot
- **CLI lifecycle** - npm update checks, project update, and uninstall helpers
- **Commands** - /status, /dashboard, /self, /impulse, /stats, /reset

## Entry Point
```python
from core.self import Self
ai = Self(Path("."))
await ai.start(input_channel="terminal")
```
