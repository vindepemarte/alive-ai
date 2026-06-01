# Brain: Subconscious Module

The living background process that makes Alive-AI feel alive 24/7.

## Files
- `loop.py` - SubconsciousLoop (main background process)
- `impulses.py` - ImpulseGenerator, Impulse, ImpulseType enum
- `working_memory.py` - WorkingMemory (short-term thought stream)

## Impulse Types
- `MISS_HIM` - Want to say hi, thinking of him
- `HIGH_DESIRE` - Intimate desire, want attention
- `CLINGY` - Need reassurance, attachment
- `CURIOUS` - Wonder about him, ask questions
- `PLAYFUL` - Want to tease, be flirty
- `LOVING` - Want to express love
- `DREAMY` - Reflect, process feelings
- `BORED` - Want entertainment
- `NURTURING` - Want to care for him

## How It Works
1. Runs every 30 seconds (EVAL_INTERVAL)
2. Evaluates emotional state + silence duration
3. Generates impulses based on mood/love/desire
4. Strong impulses (>=0.5) can trigger proactive messages
5. Quiet hours (1am-7am) reduce activity

## Integration Points
- Reads from: Heart (emotions), WorkingMemory
- Uses: fast_llm for message generation
- Emits: `subconscious_impulse` event
- Callback: `on_impulse` for proactive actions
