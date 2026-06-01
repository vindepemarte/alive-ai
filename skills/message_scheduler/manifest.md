# Skills: Message Scheduler

Schedule Telegram messages to be sent at specific times. Alive-AI can use this to remember to message users at requested times.

## Files
- `scheduler.py` - MessageScheduler class
- `__init__.py` - Module exports

## Purpose

Allows Alive-AI to schedule messages for specific times when users ask her to remind them or message them later.

## Usage Examples

When users say:
- "Message me at 15:00"
- "Text me in an hour"
- "Remind me at 3pm"
- "Send me something tonight"

Alive-AI can schedule these messages using this skill.

## Integration

### Initialization
```python
from skills.message_scheduler import MessageScheduler

scheduler = MessageScheduler(
    nervous=nervous_system,
    data_path=Path("data/scheduled_messages")
)
```

### Scheduling a Message
```python
# Schedule for specific time
scheduler.schedule_message(
    user_id="123456789",
    message="Hey! This is your scheduled message",
    scheduled_time=datetime(2024, 1, 15, 15, 0),  # 15:00
    context="User asked me to message at 15:00"
)

# Schedule relative time
scheduler.schedule_in(
    user_id="123456789",
    message="An hour has passed!",
    minutes=60
)
```

### Checking Due Messages
```python
# Get messages that should be sent now
due_messages = scheduler.get_due_messages()
for msg in due_messages:
    await send_telegram(msg.user_id, msg.message)
    scheduler.mark_sent(msg.id)
```

## Data Storage

Files stored in `data/scheduled_messages/`:
- `queue.json` - Pending scheduled messages
- `history.json` - Sent message history

## Methods

| Method | Description |
|--------|-------------|
| `schedule_message()` | Schedule message for specific datetime |
| `schedule_in()` | Schedule message relative to now |
| `get_due_messages()` | Get messages ready to send |
| `get_pending()` | Get all pending scheduled messages |
| `cancel_message()` | Cancel a scheduled message |
| `mark_sent()` | Mark message as sent |
| `get_next_for_user()` | Get next scheduled message for user |

## Events Emitted

### `scheduled_message_due`
Emitted when a scheduled message's time arrives:
```python
{
    "message_id": "uuid",
    "user_id": "123456789",
    "message": "Hey! Scheduled message here",
    "scheduled_for": "2024-01-15T15:00:00",
    "context": "User asked me to message at 15:00"
}
```

## Natural Time Parsing

The scheduler can parse natural language times:
- "at 15:00" / "at 3pm"
- "in an hour" / "in 30 minutes"
- "tonight at 8"
- "tomorrow morning"

## Important Notes

- Messages persist across restarts
- Messages can be cancelled before sending
- History kept for debugging (last 100 sent)
- Timezone-aware (uses system timezone)
