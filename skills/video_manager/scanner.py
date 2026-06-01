"""
Skills: Video Manager
Scan and manage videos for Alive-AI to send
"""

import os
import random
import hashlib
from pathlib import Path
from typing import List, Tuple, Optional
from collections import deque


class VideoScanner:
    """Scan and manage videos with descriptions, categories, and no-repeat tracking"""

    # Video categories by intensity/tier
    TIERS = {
        "soft": 0,      # Solo, teasing
        "medium": 1,    # Oral, intimate
        "intense": 2,      # Rough, intense
        "extreme": 3    # Very intimate
    }

    # Keywords to categorize videos automatically
    CATEGORY_KEYWORDS = {
        "soft": ["solo", "playing", "teasing", "open upping"],
        "medium": ["intimate", "intimate moment", "sucking", "licking", "closeness"],
        "intense": ["deep_throat", "face_intense", "throat", "rough", "gag"],
        "extreme": ["anal", "ass_plug", "butt", "sloppy", "dormitory"]
    }

    def __init__(self, videos_path: Path, no_repeat_count: int = 10):
        self.path = Path(videos_path)
        self.videos = {}  # filename -> {description, tier, hash}
        self._hash_file = self.path / ".video_hashes.json"

        # Track recently sent to avoid repeats
        self.recently_sent = deque(maxlen=no_repeat_count)
        self.no_repeat_count = no_repeat_count

    def scan(self) -> int:
        """Scan all videos and load descriptions"""
        if not self.path.exists():
            self.path.mkdir(parents=True, exist_ok=True)
            return 0

        self.videos = {}
        count = 0

        for file in self.path.iterdir():
            if file.suffix.lower() in [".mp4", ".mov", ".avi", ".mkv", ".webm"]:
                filename = file.stem
                description = self._load_description(file)

                # Auto-categorize based on filename
                tier = self._categorize(filename, description)

                self.videos[file.name] = {
                    "path": str(file),
                    "description": description,
                    "tier": tier,
                    "filename": filename
                }
                count += 1

        return count

    def _load_description(self, video_path: Path) -> str:
        """Load description from .txt file or generate from filename"""
        desc_path = video_path.with_suffix(".txt")

        if desc_path.exists():
            return desc_path.read_text().strip()

        # Generate from filename
        filename = video_path.stem
        # Replace underscores with spaces, clean up
        desc = filename.replace("_", " ").replace("alive_ai ", "I am ")
        return desc

    def _categorize(self, filename: str, description: str) -> int:
        """Auto-categorize video based on filename and description"""
        text = (filename + " " + description).lower()

        # Check for extreme keywords first
        for keyword in self.CATEGORY_KEYWORDS["extreme"]:
            if keyword in text:
                return 3

        # Then intense
        for keyword in self.CATEGORY_KEYWORDS["intense"]:
            if keyword in text:
                return 2

        # Then medium
        for keyword in self.CATEGORY_KEYWORDS["medium"]:
            if keyword in text:
                return 1

        # Default to soft
        return 0

    def mark_sent(self, video_name: str):
        """Mark a video as recently sent"""
        self.recently_sent.append(video_name)

    def was_recently_sent(self, video_name: str) -> bool:
        """Check if video was recently sent"""
        return video_name in self.recently_sent

    def get_all(self) -> List[dict]:
        """Get all videos"""
        return list(self.videos.values())

    def get_by_tier(self, tier: int) -> List[dict]:
        """Get videos by tier"""
        return [v for v in self.videos.values() if v["tier"] == tier]

    def get_random(self, min_tier: int = 0, max_tier: int = 3) -> Optional[Tuple[str, str, int]]:
        """Get random video within tier range, avoiding recently sent"""
        matching = [
            v for name, v in self.videos.items()
            if min_tier <= v["tier"] <= max_tier
            and name not in self.recently_sent  # Avoid repeats
        ]

        # If all have been sent, allow repeats
        if not matching:
            matching = [
                v for v in self.videos.values()
                if min_tier <= v["tier"] <= max_tier
            ]

        if not matching:
            return None

        video = random.choice(matching)
        return (
            video["path"],
            video["description"],
            video["tier"]
        )

    def get_for_context(self, context: str, arousal: float = 0.5) -> Optional[Tuple[str, str]]:
        """Get video that matches context and arousal level, avoiding repeats"""
        context_lower = context.lower()

        # Determine appropriate tier based on arousal
        if arousal < 0.4:
            min_tier, max_tier = 0, 1  # Soft to medium
        elif arousal < 0.7:
            min_tier, max_tier = 1, 2  # Medium to intense
        else:
            min_tier, max_tier = 2, 3  # Hard to extreme

        print(f"[VideoScanner] Searching for context: '{context[:50]}...' arousal={arousal:.2f} tier={min_tier}-{max_tier}")

        # Important keywords to match (expand these)
        important_keywords = {
            "doggy": ["doggy", "doggi", "behind", "back"],
            "anal": ["anal", "ass", "butt", "butthole", "asshole"],
            "riding": ["riding", "ride", "on top", "cowgirl"],
            "intense": ["intense", "overwhelmed", "sex", "deep-intimacy"],
            "solo": ["solo", "alone", "playing", "fingering"],
            "intimate moment": ["intimate moment", "suck", "intimate", "mouth", "deepthroat"],
        }

        # Find matching videos, excluding recently sent
        matching = []
        for name, v in self.videos.items():
            if min_tier <= v["tier"] <= max_tier:
                if name in self.recently_sent:
                    continue  # Skip recently sent
                # Score by description match
                desc_lower = v["description"].lower()
                filename_lower = v.get("filename", "").lower()

                # Check both description and filename
                combined = desc_lower + " " + filename_lower

                # Score based on matches
                score = 0

                # Direct word matches
                for word in context_lower.split():
                    if len(word) > 2 and word in combined:
                        score += 1

                # Check important keyword groups
                for key, keywords in important_keywords.items():
                    if any(kw in context_lower for kw in keywords):
                        if any(kw in combined for kw in keywords):
                            score += 3  # Bonus for matching important keywords

                if score > 0:
                    matching.append((v, score, name))

        if matching:
            # Sort by score and pick from top
            matching.sort(key=lambda x: x[1], reverse=True)
            video = matching[0][0]
            print(f"[VideoScanner] Found match: {video['path']} (score={matching[0][1]})")
            return video["path"], video["description"]

        # Fallback to random (also respects no-repeat)
        print(f"[VideoScanner] No keyword match, falling back to random")
        result = self.get_random(min_tier, max_tier)
        if result:
            return result[0], result[1]

        print(f"[VideoScanner] No videos available in tier {min_tier}-{max_tier}")
        return None

    def stats(self) -> dict:
        """Get video statistics"""
        tiers = {}
        for v in self.videos.values():
            tier = v["tier"]
            tiers[tier] = tiers.get(tier, 0) + 1

        tier_names = {0: "soft", 1: "medium", 2: "intense", 3: "extreme"}
        tier_stats = {tier_names.get(k, k): v for k, v in tiers.items()}

        return {
            "total": len(self.videos),
            "categories": tier_stats,
            "recently_sent": len(self.recently_sent)
        }
