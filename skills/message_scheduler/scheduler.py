"""
Skills: Message Scheduler

Schedule Telegram messages to be sent at specific times.
Allows Alive-AI to remember to message users when they ask her to.
"""

import json
import uuid
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class ScheduledMessage:
    """A message scheduled for future delivery"""
    id: str
    user_id: str
    message: str
    scheduled_for: str  # ISO format datetime
    context: str = ""  # Why this was scheduled
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    sent: bool = False
    sent_at: Optional[str] = None
    cancelled: bool = False
    cancelled_at: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ScheduledMessage":
        return cls(**data)

    @property
    def scheduled_datetime(self) -> datetime:
        return datetime.fromisoformat(self.scheduled_for)

    def is_due(self) -> bool:
        """Check if this message should be sent now"""
        if self.sent or self.cancelled:
            return False
        return datetime.now() >= self.scheduled_datetime


class MessageScheduler:
    """
    Manages scheduled messages for Alive-AI.

    Allows scheduling messages for specific times and checking
    when they're due to be sent.
    """

    # Regex patterns for natural time parsing
    TIME_PATTERNS = {
        # "at 15:00" or "at 3pm" or "at 3:30pm"
        "specific_time": re.compile(
            r'(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?',
            re.IGNORECASE
        ),
        # "in 30 minutes" or "in an hour"
        "relative": re.compile(
            r'in\s+(?:about\s+)?(\d+)\s*(minute|min|hour|hr)s?',
            re.IGNORECASE
        ),
        # "in an hour" (special case)
        "relative_an": re.compile(
            r'in\s+an?\s+(minute|hour)',
            re.IGNORECASE
        ),
    }

    def __init__(self, nervous=None, data_path: Path = None):
        """
        Initialize the Message Scheduler.

        Args:
            nervous: The nervous system for event emission
            data_path: Path for data storage (defaults to data/scheduled_messages)
        """
        self.nervous = nervous

        # Set up data path
        if data_path:
            self.data_path = Path(data_path)
        else:
            self.data_path = Path(__file__).parent.parent.parent / "data" / "scheduled_messages"

        self.data_path.mkdir(parents=True, exist_ok=True)

        # File paths
        self.queue_path = self.data_path / "queue.json"
        self.history_path = self.data_path / "history.json"

        # In-memory state
        self._queue: List[ScheduledMessage] = []
        self._history: List[ScheduledMessage] = []

        # Load persisted state
        self._load_state()

        print(f"[MessageScheduler] Initialized with {len(self._queue)} pending messages")

    def _load_state(self):
        """Load persisted state from files"""
        # Load queue
        if self.queue_path.exists():
            try:
                data = json.loads(self.queue_path.read_text())
                self._queue = [
                    ScheduledMessage.from_dict(m)
                    for m in data.get("messages", [])
                    if not m.get("sent") and not m.get("cancelled")
                ]
            except Exception as e:
                print(f"[MessageScheduler] Error loading queue: {e}")

        # Load history
        if self.history_path.exists():
            try:
                data = json.loads(self.history_path.read_text())
                self._history = [
                    ScheduledMessage.from_dict(m)
                    for m in data.get("messages", [])
                ]
            except Exception as e:
                print(f"[MessageScheduler] Error loading history: {e}")

    def _save_state(self):
        """Save state to files"""
        # Save queue
        try:
            data = {
                "messages": [m.to_dict() for m in self._queue if not m.sent and not m.cancelled],
                "updated_at": datetime.now().isoformat()
            }
            self.queue_path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            print(f"[MessageScheduler] Error saving queue: {e}")

        # Save history (keep last 100)
        try:
            data = {
                "messages": [m.to_dict() for m in self._history[-100:]],
                "updated_at": datetime.now().isoformat()
            }
            self.history_path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            print(f"[MessageScheduler] Error saving history: {e}")

    def schedule_message(
        self,
        user_id: str,
        message: str,
        scheduled_time: datetime,
        context: str = ""
    ) -> ScheduledMessage:
        """
        Schedule a message for a specific time.

        Args:
            user_id: Telegram user ID to send to
            message: The message content
            scheduled_time: When to send the message
            context: Why this message was scheduled (for Alive-AI's reference)

        Returns:
            The created ScheduledMessage
        """
        msg = ScheduledMessage(
            id=str(uuid.uuid4())[:8],
            user_id=str(user_id),
            message=message,
            scheduled_for=scheduled_time.isoformat(),
            context=context
        )

        self._queue.append(msg)
        self._save_state()

        print(f"[MessageScheduler] Scheduled message for {scheduled_time}: {message[:40]}...")

        return msg

    def schedule_in(
        self,
        user_id: str,
        message: str,
        minutes: int = 0,
        hours: int = 0,
        context: str = ""
    ) -> ScheduledMessage:
        """
        Schedule a message relative to now.

        Args:
            user_id: Telegram user ID
            message: The message content
            minutes: Minutes from now
            hours: Hours from now
            context: Why this message was scheduled

        Returns:
            The created ScheduledMessage
        """
        delta = timedelta(hours=hours, minutes=minutes)
        scheduled_time = datetime.now() + delta

        return self.schedule_message(user_id, message, scheduled_time, context)

    def parse_time_string(self, time_str: str, now: datetime = None) -> Optional[datetime]:
        """
        Parse a natural language time string into a datetime.

        Supports:
        - "at 15:00" / "at 3pm"
        - "in 30 minutes" / "in an hour"
        - "tonight at 8"

        Args:
            time_str: Natural language time description
            now: Base time (defaults to current time)

        Returns:
            Parsed datetime or None if parsing fails
        """
        if now is None:
            now = datetime.now()

        time_str = time_str.lower().strip()

        # Try relative time first: "in X minutes/hours"
        match = self.TIME_PATTERNS["relative"].search(time_str)
        if match:
            amount = int(match.group(1))
            unit = match.group(2).lower()

            if unit in ("minute", "min"):
                return now + timedelta(minutes=amount)
            elif unit in ("hour", "hr"):
                return now + timedelta(hours=amount)

        # Try "in an hour" / "in a minute"
        match = self.TIME_PATTERNS["relative_an"].search(time_str)
        if match:
            unit = match.group(1).lower()
            if unit == "hour":
                return now + timedelta(hours=1)
            elif unit == "minute":
                return now + timedelta(minutes=1)

        # Try specific time: "at 15:00" / "at 3pm"
        match = self.TIME_PATTERNS["specific_time"].search(time_str)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2)) if match.group(2) else 0
            am_pm = match.group(3)

            # Handle 12-hour format
            if am_pm:
                am_pm = am_pm.lower()
                if am_pm == "pm" and hour < 12:
                    hour += 12
                elif am_pm == "am" and hour == 12:
                    hour = 0

            # Create datetime for today
            try:
                scheduled = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

                # If time has passed today, assume tomorrow
                if scheduled <= now:
                    scheduled += timedelta(days=1)

                return scheduled
            except ValueError:
                return None

        # Check for "tonight"
        if "tonight" in time_str:
            match = self.TIME_PATTERNS["specific_time"].search(time_str)
            if match:
                hour = int(match.group(1))
                minute = int(match.group(2)) if match.group(2) else 0
                am_pm = match.group(3)

                # Force PM for "tonight"
                if am_pm and am_pm.lower() == "am":
                    hour = hour  # Keep as is if explicitly AM
                elif hour < 12:
                    hour += 12  # Convert to PM

                try:
                    return now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                except ValueError:
                    return None
            else:
                # "tonight" without time = 8pm
                return now.replace(hour=20, minute=0, second=0, microsecond=0)

        # Check for "tomorrow morning"
        if "tomorrow" in time_str:
            tomorrow = now + timedelta(days=1)

            if "morning" in time_str:
                return tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
            elif "afternoon" in time_str:
                return tomorrow.replace(hour=14, minute=0, second=0, microsecond=0)
            elif "evening" in time_str or "night" in time_str:
                return tomorrow.replace(hour=19, minute=0, second=0, microsecond=0)
            else:
                # Just "tomorrow" = same time tomorrow
                return tomorrow

        return None

    def get_due_messages(self) -> List[ScheduledMessage]:
        """
        Get all messages that are due to be sent.

        Returns:
            List of ScheduledMessage objects ready to send
        """
        due = [msg for msg in self._queue if msg.is_due()]
        return due

    def get_pending(self, user_id: str = None) -> List[ScheduledMessage]:
        """
        Get all pending scheduled messages.

        Args:
            user_id: Optional user ID to filter by

        Returns:
            List of pending ScheduledMessage objects
        """
        pending = [msg for msg in self._queue if not msg.sent and not msg.cancelled]

        if user_id:
            pending = [msg for msg in pending if msg.user_id == str(user_id)]

        # Sort by scheduled time
        pending.sort(key=lambda m: m.scheduled_datetime)
        return pending

    def get_next_for_user(self, user_id: str) -> Optional[ScheduledMessage]:
        """
        Get the next scheduled message for a user.

        Args:
            user_id: The user to check

        Returns:
            The next ScheduledMessage or None
        """
        pending = self.get_pending(user_id)
        return pending[0] if pending else None

    def mark_sent(self, message_id: str) -> bool:
        """
        Mark a message as sent.

        Args:
            message_id: The message ID to mark

        Returns:
            True if found and marked, False otherwise
        """
        for msg in self._queue:
            if msg.id == message_id:
                msg.sent = True
                msg.sent_at = datetime.now().isoformat()

                # Move to history
                self._history.append(msg)
                self._queue.remove(msg)

                self._save_state()
                print(f"[MessageScheduler] Marked message {message_id} as sent")
                return True

        return False

    def cancel_message(self, message_id: str) -> bool:
        """
        Cancel a scheduled message.

        Args:
            message_id: The message ID to cancel

        Returns:
            True if found and cancelled, False otherwise
        """
        for msg in self._queue:
            if msg.id == message_id and not msg.sent:
                msg.cancelled = True
                msg.cancelled_at = datetime.now().isoformat()

                # Move to history
                self._history.append(msg)
                self._queue.remove(msg)

                self._save_state()
                print(f"[MessageScheduler] Cancelled message {message_id}")
                return True

        return False

    def cancel_all_for_user(self, user_id: str) -> int:
        """
        Cancel all pending messages for a user.

        Args:
            user_id: The user whose messages to cancel

        Returns:
            Number of messages cancelled
        """
        count = 0
        for msg in list(self._queue):
            if msg.user_id == str(user_id) and not msg.sent:
                msg.cancelled = True
                msg.cancelled_at = datetime.now().isoformat()
                self._history.append(msg)
                self._queue.remove(msg)
                count += 1

        if count > 0:
            self._save_state()
            print(f"[MessageScheduler] Cancelled {count} messages for user {user_id}")

        return count

    def get_status(self) -> Dict[str, Any]:
        """
        Get scheduler status for debugging.

        Returns:
            Dict with status information
        """
        return {
            "pending_count": len([m for m in self._queue if not m.sent and not m.cancelled]),
            "history_count": len(self._history),
            "due_count": len(self.get_due_messages()),
            "pending_messages": [
                {
                    "id": m.id,
                    "user_id": m.user_id,
                    "scheduled_for": m.scheduled_for,
                    "message_preview": m.message[:50] + "..." if len(m.message) > 50 else m.message,
                    "context": m.context
                }
                for m in self.get_pending()
            ]
        }


# ============================================================
# Singleton Instance
# ============================================================

_scheduler: Optional[MessageScheduler] = None


def get_message_scheduler(nervous=None, data_path: Path = None) -> MessageScheduler:
    """
    Get the global MessageScheduler singleton.

    Args:
        nervous: The nervous system (required on first call)
        data_path: Path for data storage (optional)

    Returns:
        The MessageScheduler singleton
    """
    global _scheduler

    if _scheduler is None:
        _scheduler = MessageScheduler(nervous, data_path)
    elif nervous is not None and _scheduler.nervous is None:
        _scheduler.nervous = nervous

    return _scheduler


def get_scheduler_prompt_section() -> str:
    """
    Get a prompt section describing scheduled messages for LLM context.

    Returns:
        Formatted string with scheduled message info
    """
    global _scheduler

    if _scheduler is None:
        return ""

    pending = _scheduler.get_pending()
    if not pending:
        return ""

    lines = ["[Your Scheduled Messages:]"]
    for msg in pending[:5]:  # Show next 5
        time_str = msg.scheduled_datetime.strftime("%H:%M")
        lines.append(f"- At {time_str}: '{msg.message[:40]}...' (to user {msg.user_id})")

    return "\n".join(lines)
