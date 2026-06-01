"""
Brain: Working Memory
Short-term RAM-like memory for recent conversation turns
"""

from datetime import datetime


class WorkingMemory:
    """Working memory - stores structured conversation turns"""

    def __init__(self, max_items: int = 14):
        self.items = []
        self.max_items = max_items

    def add(self, role: str, content: str):
        """Add a structured turn to working memory"""
        self.items.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        if len(self.items) > self.max_items:
            self.items.pop(0)

    def get_history(self) -> list:
        """Get conversation history as list of {role, content} dicts"""
        return [{"role": item["role"], "content": item["content"]} for item in self.items]

    def get_context(self) -> str:
        """Get all items as context string (legacy fallback)"""
        parts = []
        for item in self.items:
            prefix = "User" if item["role"] == "user" else "You"
            parts.append(f"{prefix}: {item['content']}")
        return "\n".join(parts)

    def clear(self):
        """Clear working memory"""
        self.items = []

    def __len__(self):
        return len(self.items)
