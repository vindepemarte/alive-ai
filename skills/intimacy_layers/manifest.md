# Skills: Intimacy Layers

Manages natural intimacy progression through relationship layers. Ensures intimacy is earned through meaningful interactions, not rushed.

## Files
- `__init__.py` - Module exports
- `layers.py` - IntimacyLayers class implementation

## Features

### Layer System
Intimacy progresses through 5 layers, each unlocking deeper conversation topics:

| Layer | Name | Interactions | Love | Trust | Days | Intimacy |
|-------|------|--------------|------|-------|------|----------|
| 1 | surface | 0 | - | - | - | 0.0 |
| 2 | friendly | 15 | 0.25 | - | - | 0.2 |
| 3 | close | 50 | 0.45 | 0.5 | - | 0.4 |
| 4 | romantic | 100 | 0.65 | - | 5 | 0.6 |
| 5 | intimate | 200 | 0.8 | - | 14 | 0.85 |

### Layer Topics

**Layer 1 - Surface**
- Daily life, hobbies, work, weather, small talk, introductions

**Layer 2 - Friendly**
- Feelings, dreams, opinions, preferences, stories, interests

**Layer 3 - Close**
- Secrets, fears, childhood, vulnerabilities, hopes, struggles

**Layer 4 - Romantic**
- Attraction, desire, fantasy, romance, longing, affection

**Layer 5 - Intimate**
- Intimate content, vulnerability, deep desires, fantasies, passion

### Progression Hints
Natural hints that suggest the relationship is deepening:

**Layer 2 hints:**
- "I feel like I can tell you stuff"
- "you're easy to talk to"
- "I'm starting to feel comfortable with you"

**Layer 3 hints:**
- "I don't usually share this but..."
- "can I tell you something personal?"
- "I trust you enough to say this"

**Layer 4 hints:**
- "the more I talk to you the more I want..."
- "I think about you differently now"
- "I'm starting to feel something more"

**Layer 5 hints:**
- "I trust you with everything"
- "you know me better than anyone"
- "I've never felt this comfortable with someone"

## Integration

### Event Listeners
- `message_received` - Track interactions and check for progression
- `thinking_done` - Apply layer context to responses

### Dependencies
- `nervous` - Nervous system for event handling
- `heart` - Heart module for love/trust values
- `state` - State manager for relationship data

## Usage

```python
from skills.intimacy_layers import IntimacyLayers

# Initialize with dependencies
intimacy = IntimacyLayers(
    nervous=nervous_system,
    heart=heart_module,
    state=state_manager
)

# Get current layer
current_layer = intimacy.get_current_layer()  # Returns 1-5

# Check if topic is appropriate
if intimacy.is_topic_appropriate("fantasy"):
    # Can discuss fantasies
    pass

# Get available topics
topics = intimacy.get_available_topics()

# Check if intimate content allowed
if intimacy.can_be_intimate():
    # Can send intimate content
    pass

# Get progression hint
hint = intimacy.get_progression_hint()
if hint:
    # Include hint in response naturally
    pass

# Get context for response generation
context = intimacy.get_context_for_response()
# Returns: {
#     "current_layer": 2,
#     "layer_name": "friendly",
#     "intimacy_level": 0.2,
#     "available_topics": [...],
#     "can_be_intimate": False,
#     "total_interactions": 25,
#     "days_together": 3,
#     "next_layer": {...}
# }
```

## Key Methods

### Core Methods
- `get_current_layer() -> int` - Get current layer (1-5)
- `check_progression() -> bool` - Check and apply progression if eligible
- `is_topic_appropriate(topic) -> bool` - Check if topic is allowed
- `get_available_topics() -> list` - Get all available topics
- `get_progression_hint() -> str | None` - Get hint for next layer
- `can_be_intimate() -> bool` - Check if intimate content allowed
- `get_intimacy_level() -> float` - Get intimacy level (0.0-1.0)

### Information Methods
- `get_layer_info(layer=None) -> dict` - Get detailed layer info
- `get_next_layer_requirements() -> dict` - Get requirements for next layer
- `get_layer_name() -> str` - Get name of current layer
- `get_days_together() -> int` - Get days since first interaction
- `get_context_for_response() -> dict` - Get context for AI response

### Admin Methods
- `force_layer(layer) -> bool` - Force set layer (testing)
- `reset_progress()` - Reset to initial state
- `get_debug_info() -> dict` - Get detailed debug info

## Progression Logic

### Automatic Checks
- Progression is checked every 10 interactions
- All requirements for the next layer must be met
- Progress is saved to `data/intimacy_layers.json`

### Requirements
- **Interactions**: Total message exchanges
- **Love**: From heart.emotion.love or heart.attachment.affection
- **Trust**: From heart.attachment.trust_level or heart.emotion.trust
- **Days**: Days since first interaction (stored)

### Natural Progression
Intimacy should feel earned:
1. Start at layer 1 (surface)
2. After ~15 interactions and some affection, progress to layer 2
3. With trust and 50+ interactions, reach layer 3
4. After 5 days and 100+ interactions with love, reach layer 4
5. After 2 weeks and 200+ interactions with deep love, reach layer 5

## Data Storage

Data is stored in `./data/data/intimacy_layers.json`:

```json
{
  "version": "1.0",
  "current_layer": 2,
  "first_interaction_date": "2024-01-15T10:30:00",
  "total_interactions": 25,
  "hints_shown": ["I feel like I can tell you stuff"],
  "updated_at": "2024-01-16T14:22:00",
  "progress": {
    "interactions_since_check": 5,
    "last_check_interactions": 20,
    "progression_blocked_reason": null,
    "hint_shown": true,
    "hint_cooldown_until": "2024-01-16T18:22:00"
  },
  "layer_history": [
    {
      "from_layer": 1,
      "to_layer": 2,
      "timestamp": "2024-01-15T18:45:00",
      "total_interactions": 15,
      "days_together": 0
    }
  ]
}
```

## Philosophy

The intimacy system ensures:
- **Natural pacing**: Relationships take time to develop
- **Earned progression**: Must meet multiple requirements
- **No rushing**: Cannot skip to intimate content early
- **Subtle hints**: Progression feels organic, not mechanical
- **Persistence**: Progress is saved and restored
