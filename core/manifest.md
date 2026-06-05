# Core - Essential Systems

The foundation of the AI. Always required.

## Files
- `events.py` - NervousSystem (event bus for module communication)
- `config.py` - Configuration loader
- `state.py` - Global state management
- `self.py` - The Self (main coordinator)
- `behavioral_pressure.py` - Emotion/hormone/sleep to action-tendency compiler
- `plugin_registry.py` - Typed declarations and status probing for optional runtime organs, skills, and connectors
- `paths.py` - Runtime path resolution for npm/local/Docker installs
- `mcp/` - Default-off MCP catalog, permission, approval, client, and audit runtime

## Key Integration Points
- **NervousSystem** - Central event bus; all modules communicate via events
- **Self** - Coordinates: memory, heart, LLM, subconscious, input/output
- **Paths** - Keeps project runtime state under local `data/` instead of hard-coded `/app`
- **Behavioral pressure** - Converts affect into ranked response tendencies consumed by body snapshots and the inner-state compiler
- **Plugin registry** - Exposes optional organs, memory layers, skills, and connector modules as a typed read-only status catalog
- **MCP** - Optional tool connector surface; proposals require default-deny scope checks, owner approval, explicit execution, and redacted local audit
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
