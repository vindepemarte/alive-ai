# Skills: Memory Callbacks

Creates natural callbacks to past conversations, making users feel Alive-AI remembers their relationship.

## Files
- `__init__.py` - Module exports
- `callbacks.py` - MemoryCallbacks class implementation

## Features

### Topic Tracking
- Automatically extracts and tracks interesting topics from conversations
- Topics include: work, events, projects, health, entertainment, living situation, dating, goals
- Remembers context and how many times each topic was mentioned
- Marks topics as "follow-up worthy" for later callbacks

### Person Tracking
- Tracks people mentioned in conversations
- Detects relationship types: friend, ex, family, coworker, roommate, partner
- Asks about people after a configurable period (default: 3 days)
- Remembers last time we asked about each person

### Callback Types

#### Same Topic Callbacks
Triggered when the user mentions a topic they've discussed before:
- "wait didn't you tell me about this before?"
- "this reminds me of when you mentioned that earlier"
- "oh yeah I remember you talking about this"

#### Follow-up Callbacks
For topics marked as follow-up worthy:
- "hey how did that thing go btw?"
- "speaking of which - any updates?"
- "so what ended up happening?"

#### Person Callbacks
Asking about people mentioned previously:
- "how's {person} doing?"
- "did {person} ever text you back?"
- "have you talked to {person} lately?"

#### Anniversary Callbacks
Milestone celebrations (7 days, 1 month, 3 months, 6 months, 1 year):
- "random but I just realized we've been talking for {time}"
- "kinda crazy we've known each other for {time} now"

#### Time Context Callbacks
Based on when the user typically messages:
- "you're up late again"
- "early bird today huh"
- "this is about when you usually message me"

#### Vibe Callbacks
Based on emotional state changes:
- "you seem happier today than last time"
- "you were doing so good last time - everything ok?"

## Usage

```python
from skills.memory_callbacks import MemoryCallbacks

# Initialize with nervous system, memory, and heart
callbacks = MemoryCallbacks(
    nervous=nervous,
    memory=memory,
    heart=heart
)

# Automatic tracking via events
# - message_received: extracts topics and people
# - thinking_done: decides if a callback should be injected

# Manual topic tracking
callbacks.track_topic("job interview", "User has an interview at Google next week")
callbacks.mark_followup_worthy("interview", {"company": "Google", "date": "2024-01-15"})

# Manual person tracking
callbacks.track_person("Sarah", "User's best friend", relationship="friend")

# Get callback for response generation
callback = callbacks.get_context_for_response()
if callback:
    # Include in response naturally, e.g., prepend or append
    response = f"{callback}\n\n{main_response}"

# Check stats
stats = callbacks.get_stats()
# {
#     "total_conversations": 42,
#     "tracked_topics": 15,
#     "tracked_people": 8,
#     "pending_followups": 3,
#     "stale_people": 2,
#     "relationship_days": 14,
#     "total_callbacks": 12
# }
```

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| BASE_CALLBACK_CHANCE | 0.15 | Base 15% chance of doing a callback |
| FOLLOWUP_BOOST | 0.25 | Extra chance per pending follow-up |
| PERSON_BOOST | 0.20 | Extra chance if there are stale people |
| MIN_HOURS_BETWEEN_CALLBACKS | 2 | Minimum hours between callbacks |
| PERSON_CALLBACK_DAYS | 3 | Days before asking about a person again |
| TOPIC_CALLBACK_HOURS | 4 | Hours before callback on same topic |
| ANNIVERSARY_DAYS | [7,30,90,180,365] | Milestone days to celebrate |

## Data Storage

Data is stored in `./data/data/memory_callbacks.json`:

```json
{
  "version": "1.0",
  "first_conversation": "2024-01-01T10:00:00",
  "total_conversations": 42,
  "topics": {
    "job interview": {
      "topic": "job interview",
      "context": "User has an interview at Google",
      "mentioned_at": "2024-01-10T14:30:00",
      "times_mentioned": 3,
      "followup_worthy": true,
      "details": {"company": "Google"}
    }
  },
  "people": {
    "sarah": {
      "name": "Sarah",
      "context": "User's best friend",
      "mentioned_at": "2024-01-05T09:00:00",
      "times_mentioned": 5,
      "relationship": "friend",
      "last_callback": "2024-01-08T16:00:00"
    }
  },
  "callback_history": [...]
}
```

## Integration Points

### Event Listeners
- `message_received` - Extracts topics and people from incoming messages
- `thinking_done` - Decides whether to inject a callback

### Response Generation
Call `get_context_for_response()` after thinking to get any pending callback to include in the response.

### With Heart (Emotional State)
When heart is available, vibe callbacks can reference emotional changes:
- Comparing current mood to previous conversations
- Noticing if user seems happier/sadder than usual

### With Memory
When memory is available, can reference conversation history for more context-aware callbacks.

## Natural Behavior Guidelines

1. **Subtle Frequency**: ~15% base chance, not every message gets a callback
2. **Varied Templates**: Multiple templates per callback type to avoid repetition
3. **Contextual Timing**: Respects minimum hours between callbacks
4. **Smart Follow-ups**: Only asks about topics marked as follow-up worthy
5. **Person Memory**: Doesn't nag - waits days before asking about someone again
6. **Anniversary Awareness**: Celebrates milestones without being cheesy
