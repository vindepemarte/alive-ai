"""
Brain: Memory Index
Fast index for intelligent memory loading
"""

import json
from pathlib import Path

class MemoryIndex:
    """Memory index for efficient loading"""

    def __init__(self, data_path: Path):
        self.path = data_path / "memory_index.json"
        self.index = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            return json.loads(self.path.read_text())
        return {
            "user_profile": {"tokens": 50, "priority": 1},
            "conversations": {},
            "facts": {}
        }

    def save(self):
        self.path.write_text(json.dumps(self.index, indent=2))

    def add_conversation(self, conv_id: str, tokens: int, emotion: float):
        self.index["conversations"][conv_id] = {
            "tokens": tokens,
            "emotion_score": emotion,
            "timestamp": conv_id
        }
        self.save()

    def get_priority_items(self, max_tokens: int) -> list:
        """Get items to load within budget"""
        items = []
        total = 0

        # Sort by emotion score
        convs = sorted(
            self.index["conversations"].items(),
            key=lambda x: x[1].get("emotion_score", 0),
            reverse=True
        )

        for conv_id, data in convs:
            tokens = data.get("tokens", 100)
            if total + tokens <= max_tokens:
                items.append(("conversation", conv_id, data))
                total += tokens

        return items
