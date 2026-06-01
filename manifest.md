# Alive-AI - AI Influencer

A modular AI that can grow, feel emotions, and form relationships.

## Architecture
- `core/` - Essential modules (events, config, self, state)
- `brain/` - Memory, LLM providers, subconscious, embeddings, STT
- `heart/` - Emotions, reactions, arousal, love/attachment system
- `input/` - Telegram listener, voice reader, commands
- `output/` - Text, voice (VibeTTS), images (Fal.ai), video
- `skills/` - Calendar, photo manager, video manager

## Key Features
- **Multi-provider LLM** - ZAI or OpenRouter (main/thinking/fast models)
- **Subconscious loop** - 24/7 background process, generates impulses
- **Vector memory** - Redis-based semantic search with embeddings
- **Emotional system** - Continuous state with natural decay
- **Proactive messaging** - Sends messages based on impulses/feelings
- **Voice synthesis** - VibeTTS with mood-based CFG, auto-splits long text
- **Media management** - Photos/videos with categories and no-repeat
- **Admin commands** - /status, /impulse, /stats, /reset, /10min

## Entry Point
```python
from core.self import Self
ai = Self(Path("."))
await ai.start()
```
