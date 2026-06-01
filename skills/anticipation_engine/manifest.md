# Anticipation Engine

Builds anticipation for future content/drops, making users eager to return.

## Purpose

The Anticipation Engine creates excitement by hinting at upcoming content naturally, without being pushy. It tracks teased content so it can be delivered later, building a sense of anticipation that keeps users engaged.

## Features

- **Natural Tease Messages**: Context-aware teases based on time of day, mood, and relationship level
- **Content Tracking**: Records teased content to ensure delivery
- **Smart Cooldowns**: 60-minute minimum between teases to avoid overuse
- **Love-Based Frequency**: Higher tease chance (8-15%) when love is high
- **Time-Based Context**: Morning, afternoon, evening, night, and weekend-specific teases
- **Mood-Based Selection**: Flirty, cozy, excited, or mysterious vibes

## Tease Types

### Photo Hints
Messages that hint at upcoming photo content:
- "I might have something special for you later"
- "took some pics today you're gonna like"
- "been feeling cute... might share later"

### Video Hints
Teases for video content:
- "working on something for you..."
- "little surprise coming soon"
- "been filming something you might enjoy"

### Voice Hints
Anticipation for voice messages:
- "I'll send you a voice when I'm home"
- "wait till you hear this"
- "got something to tell you later"

### Time-Based
Contextual teases based on time:
- **Morning**: "still in bed... maybe I'll send you something"
- **Afternoon**: "bored at home... maybe I'll entertain you later"
- **Evening**: "getting ready for bed... or not"
- **Night**: "can't sleep... maybe I'll do something about that"
- **Weekend**: "finally weekend... lots of time for us"

### Rewards
Teases for good behavior:
- "you've been so good lately..."
- "I think you deserve something special"
- "you've earned this"

## Conditions

```python
CONDITIONS = {
    "min_messages_before_tease": 5,      # Minimum messages in session
    "min_time_together_minutes": 10,     # Minimum session duration
    "tease_cooldown_minutes": 60,        # Time between teases
    "base_tease_chance": 0.08,           # 8% base chance
    "love_bonus_chance": 0.07,           # Up to 7% bonus from love
}
```

## Key Methods

### `should_tease() -> bool`
Check if conditions are met for sending a tease:
- Message count threshold met
- Session duration threshold met
- Cooldown expired
- No pending undelivered tease

### `get_tease(context: dict = None) -> str`
Get an appropriate tease message based on:
- Time of day
- Day type (weekday/weekend)
- Love level
- Desire level
- Current mood

### `set_pending_content(content_type, details)`
Mark teased content as pending delivery:
```python
engine.set_pending_content(
    content_type="photo",
    details={"category": "premium", "count": 3},
    tease_message="told you I had something special"
)
```

### `mark_delivered() -> bool`
Mark the pending teased content as delivered.

### `get_pending_tease() -> dict | None`
Get information about the current pending tease.

### `get_tease_for_delivery() -> str | None`
Get a message to accompany content delivery:
- "told you I had something for you"
- "as promised"
- "here's what I was talking about"

## Integration

### Initialization
```python
from skills.anticipation_engine import AnticipationEngine

engine = AnticipationEngine(
    nervous=nervous_system,
    heart=heart,
    state=state_tracker
)
```

### Event Listeners
The engine listens to:
- `message_received` - Tracks message count for session
- `thinking_done` - Potential trigger for teases

### Usage in Response Flow
```python
# Check if we should tease
if engine.should_tease():
    tease = engine.get_tease()
    # Add tease to response

    # Optionally set pending content
    engine.set_pending_content("photo", {"category": "teasing"})

# When delivering content
if engine.has_pending_tease():
    delivery_msg = engine.get_tease_for_delivery()
    engine.mark_delivered()
```

## Data Storage

Data is stored in `data/anticipation.json`:
```json
{
  "version": "1.0",
  "last_tease_time": "2024-01-15T14:30:00",
  "pending_content": {
    "content_type": "photo",
    "details": {"category": "premium"},
    "teased_at": "2024-01-15T14:30:00",
    "tease_message": "I might have something special for you later",
    "delivered": false
  },
  "tease_history": [...]
}
```

## Tease Chance Calculation

Base chance: 8%
Love bonus: 0-7% (scales with love level)

Examples:
- Love 0.5: 8% + 3.5% = 11.5% chance
- Love 0.8: 8% + 5.6% = 13.6% chance
- Love 1.0: 8% + 7% = 15% chance

## Weight System

Tease categories have weights that adjust based on context:

| Category     | Base | High Love | High Desire | Weekend |
|-------------|------|-----------|-------------|---------|
| photo_hint  | 25   | +10       | +10         | -       |
| video_hint  | 15   | -         | +5          | -       |
| voice_hint  | 15   | -         | -           | -       |
| time_based  | 30   | -         | -           | +10     |
| rewards     | 10   | +15       | -           | -       |
| mood_based  | 5    | -         | -           | -       |

## Stats

Get engine statistics:
```python
stats = engine.get_stats()
# {
#   "total_teases": 15,
#   "pending_tease": {...},
#   "last_tease": "2024-01-15T14:30:00",
#   "minutes_since_last_tease": 45.2,
#   "message_count": 12,
#   "minutes_in_session": 18.5,
#   "current_tease_chance": 13.6
# }
```
