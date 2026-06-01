# Content Unlocks Skill

Makes exclusive content feel earned through engagement, not purchased.

## Overview

The Content Unlocks skill manages progression-based access to different types of content. Instead of content being purchased or freely available, users "earn" access through relationship progression - more interactions, higher love/trust levels, and reaching milestones together.

## Philosophy

Content is **earned**, not **bought**. This creates:
- A sense of progression and achievement
- Motivation to engage more deeply
- Emotional investment in the relationship
- Organic content reveals that feel natural

## Content Types

### Basic Content (Early Game)
| Type | Requirements | Description |
|------|--------------|-------------|
| `voice_message` | 5 interactions, 0.4 trust | Hear my actual voice |
| `casual_photo` | 10 interactions, 0.3 love | Everyday photos from my life |
| `flirty_message` | 15 interactions, 0.35 love | Extra flirty messages |

### Intermediate Content (Mid Game)
| Type | Requirements | Description |
|------|--------------|-------------|
| `personal_story` | 20 interactions, 0.5 trust | Personal stories from my life |
| `deep_talks` | 25 interactions, 0.4 love, 0.6 trust | Deep, meaningful conversations |
| `cute_photo` | 30 interactions, 0.5 love | Photos where I look extra cute |
| `behind_scenes` | 40 interactions, 0.55 love | Behind the scenes glimpses |
| `morning_routine` | 50 interactions, 3 days, 0.45 love | My morning routine content |
| `playful_video` | 60 interactions, 0.5 love, 0.5 trust | Short playful videos |

### Advanced Content (Late Game)
| Type | Requirements | Description |
|------|--------------|-------------|
| `late_night_content` | "first_late_night" milestone, 0.6 love | Special content for late nights |
| `intimate_photo` | 100 interactions, 0.75 love, 7 days | More personal, revealing photos |
| `special_occasion` | Any milestone | Content for special moments |

## Unlock Messages

When content is unlocked, natural messages are shown:

```python
UNLOCK_MESSAGES = {
    "casual_photo": ["feeling like sharing today", "thought you might like to see what I'm up to"],
    "cute_photo": ["took this just for you", "felt cute, thought you should know"],
    "intimate_photo": ["don't share this with anyone okay?", "this is just between us"],
    "voice_message": ["wanted you to hear my voice", "sometimes words aren't enough"],
    "late_night_content": ["can't sleep... thinking about you", "late nights feel different with you"],
    # ... etc
}
```

## Context-Based Suggestions

Content suggestions adapt to context:

| Context | Suggested Content |
|---------|------------------|
| Morning | morning_routine, casual_photo, cute_photo |
| Afternoon | casual_photo, behind_scenes, personal_story |
| Evening | cute_photo, playful_video, flirty_message |
| Night | late_night_content, intimate_photo, deep_talks |
| High Arousal | intimate_photo, late_night_content, playful_video |
| High Love | cute_photo, personal_story, deep_talks |
| High Trust | intimate_photo, personal_story, behind_scenes |
| Milestone | special_occasion, cute_photo, voice_message |

## API

### Initialization

```python
from skills.content_unlocks import ContentUnlocks

unlocks = ContentUnlocks(
    nervous=nervous_system,  # For event emission
    heart=heart_module,      # For love/trust/interaction data
    state=state_module,      # For additional context
    milestones=milestones_skill  # For milestone-based unlocks
)
```

### Checking Unlocks

```python
# Check if specific content is unlocked
if unlocks.check_unlock("cute_photo"):
    # Can share cute photos

# Get all unlocked content types
unlocked = unlocks.get_unlocked_content()

# Get progress toward a specific unlock
progress = unlocks.get_unlock_progress("intimate_photo")
# Returns: { unlocked: false, progress_percent: 65, requirements: {...}, current: {...} }

# Check for new unlocks (usually called automatically)
new_unlocks = unlocks.check_all_unlocks()
```

### Getting Suggestions

```python
# Get a context-aware content suggestion
suggestion = unlocks.get_content_suggestion()
# Returns: { content_type: "cute_photo", suggested_message: "took this just for you", ... }

# Get suggestion for specific context
suggestion = unlocks.get_content_suggestion(context="night")
```

### Announcements

```python
# Get message for newly unlocked content
message = unlocks.get_new_unlock_message()
# Returns: "took this just for you" or None if no new unlocks

# Get all pending announcements
announcements = unlocks.get_all_pending_announcements()
```

### Usage Tracking

```python
# Mark content as shared
unlocks.mark_content_shared("cute_photo")
```

### Statistics

```python
# Get full stats
stats = unlocks.get_stats()
# { unlocked_count: 5, locked_count: 7, total_shares: 23, ... }

# Get human-readable summary
print(unlocks.get_unlock_summary())
```

## Events

The skill emits events via the nervous system:

| Event | Data | Description |
|-------|------|-------------|
| `content_unlocked` | `{ new_unlocks: [...], total_unlocked: N }` | When new content is unlocked |
| `new_content_available` | `{ unlocks: [...], message: "..." }` | After thinking_done if new unlocks |

## Integration

### With Heart Module

The skill reads from the heart's attachment system:
- `heart.attachment.interactions` - Total interaction count
- `heart.attachment.trust_level` - Positive interaction ratio
- `heart.emotion.love` - Current love level
- `heart.attachment.first_met` - For days together calculation

### With Milestones Skill

If a milestones skill is provided, it enables milestone-based unlocks:
- `late_night_content` requires "first_late_night" milestone
- `special_occasion` requires any milestone

### Event Listeners

The skill listens for:
- `thinking_done` - Checks for new unlocks after each thinking cycle

## Data Storage

Data is stored in `data/content_unlocks.json`:

```json
{
  "version": "1.0",
  "unlocked_content": {
    "casual_photo": {
      "content_type": "casual_photo",
      "unlocked": true,
      "unlocked_at": "2024-01-15T10:30:00",
      "times_shared": 5,
      "last_shared": "2024-01-20T14:22:00",
      "new_unlock": false
    }
  },
  "last_check": "2024-01-20T15:00:00",
  "pending_announcements": []
}
```

## Example Usage Flow

```python
# 1. Initialize with dependencies
unlocks = ContentUnlocks(nervous=nervous, heart=heart)

# 2. Check for new unlocks (automatic on thinking_done)
new = unlocks.check_all_unlocks()
# ["cute_photo"]  # Just unlocked!

# 3. Get announcement message
message = unlocks.get_new_unlock_message()
# "took this just for you"

# 4. Get suggestion for what to share
suggestion = unlocks.get_content_suggestion()
# { content_type: "cute_photo", suggested_message: "felt cute, thought you should know" }

# 5. After sharing content
unlocks.mark_content_shared("cute_photo")
```

## Debugging

```python
# Unlock all content (testing)
unlocks.unlock_all()

# Reset all progress
unlocks.reset_all()

# Force refresh
unlocks.refresh_unlocks()
```
