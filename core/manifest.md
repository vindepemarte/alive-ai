# Core - Essential Systems

The foundation of the AI. Always required.

## Files
- `events.py` - NervousSystem (event bus for module communication)
- `config.py` - Configuration loader
- `state.py` - Global state management
- `self.py` - The Self (main coordinator)

## Key Integration Points
- **NervousSystem** - Central event bus; all modules communicate via events
- **Self** - Coordinates: memory, heart, LLM, subconscious, input/output
- Connects to subconscious for proactive messaging
- Emits: `message_received`, `send_text`, `send_voice_file`, `send_image`, `send_video`

## Usage
```python
from core.self import Self
ai = Self(Path("."))
await ai.start()  # Starts all modules + subconscious loop
```

## Events
- `message_received` - Incoming message
- `memory_save` - Store memory
- `timer_tick` - Emotion decay trigger
- `subconscious_impulse` - Proactive action signal
