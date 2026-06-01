# Skills - Optional Capabilities

Add-on modules that extend Alive-AI's abilities.

## Available Skills
- `calendar/` - Dual calendar (AI + user events)
- `photo_manager/` - Manage mypics folder with semantic search
- `video_manager/` - Manage myvids folder (see video_manager/manifest.md)
- `relationship_milestones/` - Track and celebrate meaningful relationship moments
- `memory_callbacks/` - Natural callbacks to past conversations for relationship continuity
- `content_unlocks/` - Progression-based content unlocks earned through engagement
- `intimacy_layers/` - Natural intimacy progression through relationship layers

## Photo Manager
- Scans mypics/ for images
- Categories: soft, teasing, intimate, etc.
- Semantic search via embeddings
- No-repeat tracking to avoid sending same photo

## Video Manager
- Scans myvids/ for videos
- Tiered by intensity: soft, medium, intense, extreme
- Context-aware selection based on arousal
- See video_manager/manifest.md for details

## Relationship Milestones
- Track meaningful relationship moments: first message, first photo, first voice, etc.
- Auto-detect milestones from context (late nights, message counts, time together)
- Natural celebration messages (not cheesy)
- Relationship summary with days together and milestone history
- Event-driven integration with nervous system
- See relationship_milestones/manifest.md for details

## Memory Callbacks
- Creates natural callbacks to past conversations ("remember when you said...")
- Tracks topics and people mentioned for authentic follow-ups
- Callback types: same topic, follow-up, person check-ins, anniversaries, time context, vibe
- ~15% base chance to callback (not robotic)
- Listens to thinking_done events to inject callbacks
- See memory_callbacks/manifest.md for details

## Content Unlocks
- Makes exclusive content feel earned through engagement, not purchased
- Tracks 12 content types unlocked by: interactions, love, trust, days together, milestones
- Content types: casual_photo, cute_photo, intimate_photo, voice_message, late_night_content, etc.
- Context-aware suggestions (morning, evening, night, high_arousal, high_love, milestone)
- Natural unlock messages when new content becomes available
- Listens to thinking_done events to check for new unlocks
- See content_unlocks/manifest.md for details

## Intimacy Layers
- Manages natural intimacy progression through 5 relationship layers
- Progresses based on: interactions, love, trust, days together
- Each layer unlocks different conversation topics
- Layer 1 (surface): daily life, hobbies, work
- Layer 2 (friendly): feelings, dreams, opinions (15 interactions, 0.25 love)
- Layer 3 (close): secrets, fears, childhood (50 interactions, 0.45 love, 0.5 trust)
- Layer 4 (romantic): attraction, desire, fantasy (100 interactions, 0.65 love, 5 days)
- Layer 5 (intimate): intimate, vulnerability, passion (200 interactions, 0.8 love, 14 days)
- Provides natural progression hints ("I feel like I can tell you stuff")
- Prevents rushing to intimate content
- See intimacy_layers/manifest.md for details

## Integration Points
- Photos/videos integrated into conversation flow
- Selected based on: user request, arousal level, context keywords
- Marked as sent to prevent repeats
