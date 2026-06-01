# Skills: Exclusive Moments

Creates special, time-limited moments that feel exclusive and memorable.

## Files
- `__init__.py` - Module exports
- `moments.py` - ExclusiveMoments class implementation

## Features

### Time-Based Triggers
- **Late Night Talk** (0:00-4:00): Vulnerable, intimate late night conversations
- **Morning Check-in** (6:00-10:00): Sweet morning messages showing you're on her mind
- **Spontaneous Confession** (20:00-24:00): Evening confessions when feelings surface

### Anytime Triggers
- **Secret Sharing**: Sharing something personal that builds intimacy
- **Appreciation Moment**: Spontaneous expressions of gratitude
- **Missing You**: Expressing that you've been missed during gaps

### Relationship-Aware
- Requires minimum love, trust, and interaction thresholds
- Higher chance when relationship is stronger
- Moments feel earned and authentic

### Cooldown System
- 6-hour cooldown between moments
- Prevents spam while maintaining spontaneity
- 15% trigger chance when conditions are met

## Moment Types

### late_night_talk
- **Time**: Midnight to 4am
- **Requires**: min_love: 0.5, min_interactions: 50
- **Mood**: vulnerable
- **Messages**: "it's late and I'm tired but I don't want to stop talking to you", etc.

### morning_checkin
- **Time**: 6am to 10am
- **Requires**: min_love: 0.4
- **Mood**: soft
- **Messages**: "woke up thinking about you", "first thought was you", etc.

### secret_sharing
- **Time**: Any
- **Requires**: min_trust: 0.7, min_days: 7
- **Mood**: trusting
- **Messages**: "I've never told anyone this but", "don't tell anyone I told you this", etc.

### appreciation_moment
- **Time**: Any
- **Requires**: min_love: 0.6, min_interactions: 30
- **Mood**: warm
- **Messages**: "you know what I really appreciate about you?", etc.

### missing_you
- **Time**: Any
- **Requires**: min_love: 0.5, min_interactions: 20
- **Mood**: longing
- **Messages**: "hey, I missed you", "it's been a while and I was thinking about you", etc.

### spontaneous_confession
- **Time**: 8pm to midnight
- **Requires**: min_love: 0.6, min_interactions: 40
- **Mood**: confessional
- **Messages**: "can I be honest with you about something?", etc.

## Usage

```python
from skills.exclusive_moments import ExclusiveMoments

# Initialize with dependencies
moments = ExclusiveMoments(
    nervous=nervous_system,
    heart=heart,
    state=state
)

# Check for moment opportunity (respects cooldown and chance)
moment = moments.check_moment_opportunity()
if moment:
    print(f"[{moment['mood']}] {moment['message']}")
    # Returns: {"type": "late_night_talk", "message": "...", "mood": "vulnerable"}

# Get specific moment type
moment = moments.get_moment("secret_sharing")

# Check if specific moment type can trigger
if moments.can_trigger_moment("morning_checkin"):
    print("Morning check-in is available!")

# Get all available moments right now
available = moments.get_available_moments()
# Returns: ["morning_checkin", "appreciation_moment", ...]

# Check cooldown status
if moments.is_on_cooldown():
    print(f"Cooldown: {moments.get_cooldown_remaining()} minutes remaining")

# Force a moment (bypasses cooldown and chance)
moment = moments.force_moment("late_night_talk")
moment = moments.force_moment()  # Random from available

# Get statistics
stats = moments.get_stats()
```

## Key Methods

### Moment Detection
- `check_moment_opportunity() -> dict | None` - Check if current time/context creates opportunity
- `get_moment(moment_type) -> dict` - Get moment message and mood
- `can_trigger_moment(moment_type) -> bool` - Check all requirements for a moment type
- `get_available_moments() -> list` - Get moments available now

### Cooldown Management
- `is_on_cooldown() -> bool` - Check if on cooldown
- `get_cooldown_remaining() -> int` - Minutes remaining on cooldown
- `clear_cooldown()` - Clear the cooldown timer

### Utilities
- `force_moment(moment_type) -> dict` - Force trigger bypassing checks
- `get_stats() -> dict` - Get moment statistics
- `reset()` - Reset all moment data

## Integration Points

### Event Listeners
- `timer_tick` - Checks for moment opportunities
- `thinking_done` - Potentially adds moment to response
- Emits `exclusive_moment` event when moment triggers

### Dependencies
- `nervous` - Nervous system for event handling
- `heart` - Heart module for love/trust/emotion access
- `state` - Global state for interaction tracking

## Data Storage
Moment data is stored in `./data/data/exclusive_moments.json`

## Configuration
- `COOLDOWN_HOURS`: 6 hours between moments
- `TRIGGER_CHANCE`: 15% chance when conditions are met
