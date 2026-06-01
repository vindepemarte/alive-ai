"""
Core: User Tracker
Track active users for proactive messaging and multi-user support
"""

import time
from typing import Dict, Optional, List
from dataclasses import dataclass, field


@dataclass
class ActiveUser:
    """Represents an active user conversation"""
    user_id: str
    chat_id: int
    last_interaction: float = field(default_factory=time.time)
    message_count: int = 0
    pet_name: str = "babe"

    def touch(self):
        """Update last interaction time"""
        self.last_interaction = time.time()
        self.message_count += 1

    @property
    def silence_minutes(self) -> float:
        """How long since last interaction"""
        return (time.time() - self.last_interaction) / 60


class UserTracker:
    """
    Tracks active users for proactive messaging.
    Stores user_id, chat_id, and conversation metadata.
    """

    # Users inactive for this long are considered "gone"
    INACTIVE_AFTER_MINUTES = 120

    # Users inactive for this long are removed from tracking
    FORGET_AFTER_HOURS = 48

    def __init__(self):
        self._users: Dict[str, ActiveUser] = {}
        self._chat_to_user: Dict[int, str] = {}  # chat_id -> user_id mapping

    def register_message(self, user_id: str, chat_id: int, pet_name: str = "babe"):
        """Register that a message was received from this user"""
        if not user_id:
            return

        user_id = str(user_id)

        if user_id in self._users:
            self._users[user_id].touch()
            self._users[user_id].chat_id = chat_id
            self._users[user_id].pet_name = pet_name
        else:
            self._users[user_id] = ActiveUser(
                user_id=user_id,
                chat_id=chat_id,
                pet_name=pet_name
            )
            print(f"[UserTracker] New user registered: {user_id}")

        # Update chat_id mapping
        self._chat_to_user[chat_id] = user_id

    def get_user(self, user_id: str) -> Optional[ActiveUser]:
        """Get user by user_id"""
        return self._users.get(str(user_id))

    def get_user_by_chat(self, chat_id: int) -> Optional[ActiveUser]:
        """Get user by chat_id"""
        user_id = self._chat_to_user.get(chat_id)
        if user_id:
            return self._users.get(user_id)
        return None

    def get_active_users(self, within_minutes: float = None) -> List[ActiveUser]:
        """
        Get list of users who are still considered active.
        within_minutes: only users who messaged within this time (default: INACTIVE_AFTER_MINUTES)
        """
        threshold = (within_minutes or self.INACTIVE_AFTER_MINUTES) * 60
        now = time.time()
        return [u for u in self._users.values() if (now - u.last_interaction) < threshold]

    def get_users_for_follow_up(self, min_silence_minutes: float = 30, max_silence_minutes: float = 180) -> List[ActiveUser]:
        """
        Get users who might need a follow-up message.
        - Have been silent for at least min_silence_minutes
        - Haven't been silent for more than max_silence_minutes (they're probably gone)
        """
        result = []
        for user in self._users.values():
            silence = user.silence_minutes
            if min_silence_minutes <= silence <= max_silence_minutes:
                result.append(user)
        return result

    def cleanup_stale(self):
        """Remove users who have been inactive too long"""
        threshold = self.FORGET_AFTER_HOURS * 3600
        now = time.time()
        stale = [uid for uid, u in self._users.items() if (now - u.last_interaction) > threshold]
        for uid in stale:
            chat_id = self._users[uid].chat_id
            del self._users[uid]
            if chat_id in self._chat_to_user:
                del self._chat_to_user[chat_id]
            print(f"[UserTracker] Removed stale user: {uid}")

    @property
    def total_users(self) -> int:
        return len(self._users)

    def get_status(self) -> dict:
        """Get status summary for debugging"""
        return {
            "total_users": self.total_users,
            "active_users": len(self.get_active_users()),
            "users_needing_follow_up": len(self.get_users_for_follow_up()),
            "users": [
                {
                    "user_id": u.user_id,
                    "silence_minutes": round(u.silence_minutes, 1),
                    "message_count": u.message_count
                }
                for u in self._users.values()
            ]
        }


# Global instance
_tracker: Optional[UserTracker] = None


def get_user_tracker() -> UserTracker:
    """Get the global user tracker instance"""
    global _tracker
    if _tracker is None:
        _tracker = UserTracker()
    return _tracker
