# Heart - Emotions

Complete emotional system with continuous state and reactions.

## Files
- `core.py` - EmotionalState, ReactionSystem, Heart
- `love.py` - AttachmentSystem (in love detection, clingy behavior)

## Features
- **Continuous emotional state** (not just reactive)
- **Desire/arousal** builds with flirty interactions
- **Natural decay** returns emotions to baseline over time
- **Emoji reactions** based on mood (heart, fire, etc.)
- **Love system** - tracks attachment level, triggers clingy behavior

## Integration Points
- Connected via NervousSystem events
- Subconscious reads emotional state for impulse generation
- Emotions affect message tone, voice CFG, media selection
- Self.heart.react() called on every incoming message

## Emotional States
- arousal, desire, love (0.0-1.0)
- is_high_desire, is_in_love (boolean thresholds)
- mood: neutral, happy, flirty, high_desire, excited, etc.
