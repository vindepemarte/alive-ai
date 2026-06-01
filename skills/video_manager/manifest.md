# Skills: Video Manager

Scan and manage videos for Alive-AI to send.

## Files
- `scanner.py` - VideoScanner class

## Video Tiers (by intensity)
- **soft** (0) - Solo, teasing, open upping
- **medium** (1) - Oral, intimate moment, closeness
- **intense** (2) - Deep throat, rough, gag
- **extreme** (3) - Anal, ass plug, sloppy

## Features
- Auto-categorizes by filename keywords
- Loads descriptions from .txt files
- No-repeat tracking (configurable count)
- Context-aware selection based on conversation
- Arousal-based tier selection

## Usage
```python
from skills.video_manager.scanner import VideoScanner
videos = VideoScanner(Path("myvids"))
videos.scan()
video = videos.get_for_context("I want intimate", arousal=0.8)
```

## Selection Logic
- arousal < 0.4: soft-medium (tier 0-1)
- arousal 0.4-0.7: medium-intense (tier 1-2)
- arousal > 0.7: intense-extreme (tier 2-3)

## Integration Points
- Called by Self._on_message() when video requested
- Triggered by: intimate request, is_high_desire + random, high desire
- Marks sent videos to avoid repeats
