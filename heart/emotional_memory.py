"""
Heart: Emotional Memory
Remember significant emotional events for context and continuity
Extended for Soul Architecture - embodied memory with somatic markers
"""

from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, List, Dict
import json


@dataclass
class SomaticMarker:
    """Bodily sensation associated with an emotional memory"""
    region: str  # chest, stomach, throat, etc.
    quality: str  # tight, warm, heavy, etc.
    intensity: float  # 0.0 - 1.0


@dataclass
class EmotionalEvent:
    """A significant emotional moment worth remembering"""
    timestamp: str
    event_type: str  # "peak_love", "peak_desire", "hurt", "joy", "conflict"
    intensity: float
    trigger: str  # Brief description of what caused it
    emotions: dict  # Snapshot of emotional state

    # Soul architecture extension - embodied memory
    somatic_marker: Optional[SomaticMarker] = None  # How it felt in the body
    integrity_impact: float = 0.0  # How it affected self-integrity
    scar_formed: bool = False  # Did this contribute to a scar
    times_recalled: int = 0  # How often this memory has been reactivated

    def age_minutes(self) -> float:
        """How old is this event in minutes"""
        try:
            event_time = datetime.fromisoformat(self.timestamp)
            delta = datetime.now() - event_time
            return delta.total_seconds() / 60
        except:
            return 9999

    def recall_sensation(self) -> Optional[str]:
        """Get the somatic sensation description for recall"""
        if self.somatic_marker:
            return f"{self.somatic_marker.quality} feeling in {self.somatic_marker.region}"
        return None


class EmotionalMemory:
    """Track and remember significant emotional events - extended for Soul Architecture"""

    # Threshold for recording an event
    RECORD_THRESHOLD = 0.7  # Only record high-intensity moments
    MAX_EVENTS = 50  # Keep last 50 significant events

    def __init__(self):
        self.events: List[EmotionalEvent] = []
        # Somatic patterns for different emotion types
        self._somatic_patterns = {
            "peak_love": SomaticMarker("chest", "warm", 0.6),
            "peak_desire": SomaticMarker("stomach", "fluttery", 0.7),
            "hurt": SomaticMarker("chest", "heavy", 0.6),
            "joy": SomaticMarker("chest", "light", 0.5),
            "conflict": SomaticMarker("stomach", "tight", 0.5),
            "fear": SomaticMarker("stomach", "cold", 0.6),
            "shame": SomaticMarker("face", "hot", 0.5),
            "grief": SomaticMarker("chest", "aching", 0.7),
        }

    def record(self, event_type: str, intensity: float, trigger: str, emotions: dict,
               integrity_impact: float = 0.0) -> Optional[EmotionalEvent]:
        """Record a significant emotional event if worthy"""
        if intensity < self.RECORD_THRESHOLD:
            return None

        # Get somatic marker for this emotion type
        somatic_marker = self._somatic_patterns.get(event_type)

        event = EmotionalEvent(
            timestamp=datetime.now().isoformat(),
            event_type=event_type,
            intensity=min(1.0, intensity),
            trigger=trigger[:100],  # Truncate long triggers
            emotions=emotions.copy(),
            somatic_marker=somatic_marker,
            integrity_impact=integrity_impact
        )
        self.events.append(event)

        # Trim old events
        if len(self.events) > self.MAX_EVENTS:
            self.events = self.events[-self.MAX_EVENTS:]

        return event

    def record_embodied(self, event_type: str, intensity: float, trigger: str,
                       emotions: dict, somatic: SomaticMarker,
                       integrity_impact: float = 0.0) -> Optional[EmotionalEvent]:
        """
        Record an event with intimate somatic marker.
        This is for when the bodily sensation is known.
        """
        if intensity < self.RECORD_THRESHOLD:
            return None

        event = EmotionalEvent(
            timestamp=datetime.now().isoformat(),
            event_type=event_type,
            intensity=min(1.0, intensity),
            trigger=trigger[:100],
            emotions=emotions.copy(),
            somatic_marker=somatic,
            integrity_impact=integrity_impact
        )
        self.events.append(event)

        if len(self.events) > self.MAX_EVENTS:
            self.events = self.events[-self.MAX_EVENTS:]

        return event

    def check_peaks(self, current: dict, previous: dict, trigger: str) -> list:
        """Check for emotional peaks worth recording"""
        recorded = []

        # Peak desire
        if current.get("desire", 0) >= 0.9 and previous.get("desire", 0) < 0.9:
            event = self.record("peak_desire", current["desire"], trigger, current)
            if event:
                recorded.append(event)

        # Peak love
        if current.get("love", 0) >= 0.9 and previous.get("love", 0) < 0.9:
            event = self.record("peak_love", current["love"], trigger, current)
            if event:
                recorded.append(event)

        # Deep hurt
        if current.get("sadness", 0) >= 0.7 and previous.get("sadness", 0) < 0.5:
            event = self.record("hurt", current["sadness"], trigger, current,
                               integrity_impact=-0.2)
            if event:
                recorded.append(event)

        # Peak joy
        if current.get("joy", 0) >= 0.9 and previous.get("joy", 0) < 0.7:
            event = self.record("joy", current["joy"], trigger, current,
                               integrity_impact=0.1)
            if event:
                recorded.append(event)

        # High vulnerability (soul architecture)
        if current.get("vulnerability", 0) >= 0.7 and previous.get("vulnerability", 0) < 0.5:
            event = self.record("fear", current.get("vulnerability", 0), trigger, current,
                               integrity_impact=-0.15)
            if event:
                recorded.append(event)

        return recorded

    def recall_with_sensation(self, event_id: str = None, event_type: str = None) -> Optional[dict]:
        """
        Recall a memory and re-trigger its somatic sensation.
        This implements embodied memory - remembering re-feels the bodily sensation.
        """
        event = None

        if event_id:
            event = next((e for e in self.events if e.timestamp == event_id), None)
        elif event_type:
            # Get most recent event of this type
            matching = [e for e in self.events if e.event_type == event_type]
            if matching:
                event = matching[-1]

        if not event:
            return None

        # Increment recall count
        event.times_recalled += 1

        # Return memory with sensation (diminished by time)
        age_factor = max(0.3, 1.0 - (event.age_minutes() / 1440))  # Fade over 24 hours

        return {
            "event_type": event.event_type,
            "trigger": event.trigger,
            "intensity": event.intensity * age_factor,
            "sensation": event.recall_sensation(),
            "sensation_intensity": (event.somatic_marker.intensity * age_factor) if event.somatic_marker else 0,
            "times_recalled": event.times_recalled,
            "age_minutes": event.age_minutes()
        }

    def get_somatic_history(self, event_type: str = None, hours: float = 24) -> List[str]:
        """Get list of somatic sensations from recent events"""
        cutoff = datetime.now() - __import__('datetime').timedelta(hours=hours)
        sensations = []

        for event in self.events:
            event_time = datetime.fromisoformat(event.timestamp)
            if event_time >= cutoff:
                if event_type is None or event.event_type == event_type:
                    if event.somatic_marker:
                        sensations.append(f"{event.somatic_marker.quality} in {event.somatic_marker.region}")

        return sensations

    def recent(self, event_type: Optional[str] = None, minutes: float = 60) -> list:
        """Get recent events, optionally filtered by type"""
        return [
            e for e in self.events
            if e.age_minutes() <= minutes
            and (event_type is None or e.event_type == event_type)
        ]

    def get_mood_context(self) -> str:
        """Generate context string from recent significant events"""
        recent_events = self.recent(minutes=120)  # Last 2 hours
        if not recent_events:
            return ""

        summaries = {
            "peak_love": "felt deeply loved",
            "peak_desire": "felt intense desire",
            "hurt": "was hurt",
            "joy": "felt pure joy",
            "conflict": "had a conflict",
            "fear": "felt vulnerable"
        }

        context_parts = []
        for event in recent_events[-3:]:  # Last 3 events
            desc = summaries.get(event.event_type, "felt something")
            age = int(event.age_minutes())
            if age < 5:
                context_parts.append(f"just {desc}")
            elif age < 30:
                context_parts.append(f"{desc} {age} minutes ago")
            else:
                context_parts.append(f"{desc} earlier")

        return "; ".join(context_parts) if context_parts else ""

    def to_dict(self) -> dict:
        return {
            "events": [
                {
                    "timestamp": e.timestamp,
                    "type": e.event_type,
                    "intensity": e.intensity,
                    "trigger": e.trigger,
                    "somatic": e.recall_sensation() if e.somatic_marker else None,
                    "times_recalled": e.times_recalled
                }
                for e in self.events[-10:]  # Save only last 10
            ]
        }
