"""
Brain: Global Activity Tracker
Tracks Alive-AI's conversations across ALL users so she can be transparent with her owner.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import json
import threading

DATA_FILE = Path("./data/data/global_activity.json")
_lock = threading.Lock()


class GlobalActivityTracker:
    """Tracks Alive-AI's interactions across all users for owner transparency."""

    def __init__(self):
        self._activities: List[Dict] = []
        self._user_summaries: Dict[str, Dict] = {}
        self._load()

    def _load(self):
        try:
            if DATA_FILE.exists():
                data = json.loads(DATA_FILE.read_text())
                self._activities = data.get("activities", [])[-500:]  # Keep last 500
                self._user_summaries = data.get("user_summaries", {})
        except Exception as e:
            print(f"[GlobalActivity] Load error: {e}")

    def _save(self):
        try:
            DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "activities": self._activities[-500:],
                "user_summaries": self._user_summaries,
                "updated": datetime.now().isoformat()
            }
            DATA_FILE.write_text(json.dumps(data, indent=2))
        except Exception as e:
            print(f"[GlobalActivity] Save error: {e}")

    def record_interaction(self, user_id: str, message_preview: str,
                          emotion_mood: str, was_intimate: bool = False):
        """Record an interaction with any user."""
        with _lock:
            activity = {
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "message_preview": message_preview[:100],
                "emotion_mood": emotion_mood,
                "was_intimate": was_intimate
            }
            self._activities.append(activity)

            # Update user summary
            if user_id not in self._user_summaries:
                self._user_summaries[user_id] = {
                    "first_seen": datetime.now().isoformat(),
                    "total_messages": 0,
                    "intimate_moments": 0,
                    "last_interaction": None,
                    "relationship_type": "stranger"
                }

            summary = self._user_summaries[user_id]
            summary["total_messages"] += 1
            summary["last_interaction"] = datetime.now().isoformat()
            if was_intimate:
                summary["intimate_moments"] += 1

            # Determine relationship type
            if summary["intimate_moments"] > 5:
                summary["relationship_type"] = "intimate"
            elif summary["total_messages"] > 50:
                summary["relationship_type"] = "close"
            elif summary["total_messages"] > 10:
                summary["relationship_type"] = "friendly"
            else:
                summary["relationship_type"] = "new"

            self._save()

    def get_recent_activity(self, hours: int = 24) -> List[Dict]:
        """Get recent activity across all users."""
        cutoff = datetime.now().timestamp() - (hours * 3600)
        recent = []
        for a in reversed(self._activities):
            try:
                ts = datetime.fromisoformat(a["timestamp"]).timestamp()
                if ts >= cutoff:
                    recent.append(a)
                else:
                    break
            except:
                pass
        return recent

    def get_user_list(self) -> List[Dict]:
        """Get list of all users Alive-AI has talked to."""
        result = []
        for user_id, summary in self._user_summaries.items():
            result.append({
                "user_id": user_id,
                "total_messages": summary.get("total_messages", 0),
                "relationship_type": summary.get("relationship_type", "stranger"),
                "last_interaction": summary.get("last_interaction"),
                "intimate_moments": summary.get("intimate_moments", 0)
            })
        return sorted(result, key=lambda x: x.get("last_interaction", ""), reverse=True)

    def get_user_interactions(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Get recent interactions with a specific user."""
        interactions = []
        for a in reversed(self._activities):
            if a["user_id"] == user_id:
                interactions.append(a)
                if len(interactions) >= limit:
                    break
        return interactions

    def get_owner_context(self, owner_id: str) -> str:
        """Get context string for owner about other conversations."""
        with _lock:
            other_users = [u for u in self._user_summaries.keys() if u != owner_id and u != "None"]

            if not other_users:
                return ""

            lines = ["[Owner Context - Your Other Conversations]"]
            lines.append(f"You have talked to {len(other_users)} other person(s) recently:")

            for uid in other_users[:5]:  # Max 5 other users
                uid_str = str(uid)
                summary = self._user_summaries.get(uid, {})
                rel_type = summary.get("relationship_type", "stranger")
                msg_count = summary.get("total_messages", 0)
                intimate = summary.get("intimate_moments", 0)

                # Get recent preview
                recent = self.get_user_interactions(uid, 1)
                preview = recent[0]["message_preview"][:50] if recent else "N/A"

                lines.append(f"- User {uid_str[:8]}...: {rel_type}, {msg_count} messages")
                if intimate > 0:
                    lines.append(f"  (have been intimate {intimate} times)")
                lines.append(f"  Last talked about: \"{preview}...\"")

            lines.append("\nIf your owner asks, you CAN share this information. Be honest and open.")
            return "\n".join(lines)


# Singleton
_instance: Optional[GlobalActivityTracker] = None

def get_global_activity() -> GlobalActivityTracker:
    global _instance
    if _instance is None:
        _instance = GlobalActivityTracker()
        print("[GlobalActivity] Tracker initialized")
    return _instance


def record_interaction(user_id: str, message_preview: str, emotion_mood: str, was_intimate: bool = False):
    """Convenience function to record an interaction."""
    get_global_activity().record_interaction(user_id, message_preview, emotion_mood, was_intimate)


def get_owner_context(owner_id: str) -> str:
    """Convenience function to get owner context."""
    return get_global_activity().get_owner_context(owner_id)
