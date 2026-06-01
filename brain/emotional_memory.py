"""
Brain: Emotional Memory System
Memories weighted by emotional significance

Based on neuroscience:
- Amygdala tags emotional significance
- Hippocampus binds context (emotion + content + relationship state)
- High-emotion memories stored with higher fidelity and retrieved more easily
- "Tag and capture": emotional moments strengthen surrounding memories

This module is MODULAR - can be connected/disconnected without breaking anything.
"""

import json
import uuid
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field, asdict
import threading

# Import settings for configuration
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.settings import get_int, get_float


# ============================================================
# Data Classes
# ============================================================

@dataclass
class EmotionalMemory:
    """
    A single memory with emotional weighting.

    Memory Structure:
    - id: unique identifier
    - content: what happened
    - emotional_weight: 0-1, how significant (amygdala tag strength)
    - emotional_valence: -1 to 1, positive/negative
    - emotions_felt: list of emotion names
    - context: surrounding information (hippocampus binding)
    - timestamp: when it occurred
    - access_count: how many times retrieved
    - last_accessed: when last retrieved
    - consolidated: processed into long-term patterns
    """
    id: str
    content: str
    emotional_weight: float  # 0-1
    emotional_valence: float  # -1 to 1
    emotions_felt: List[str]
    context: Dict[str, Any]
    timestamp: str
    access_count: int = 0
    last_accessed: Optional[str] = None
    consolidated: bool = False

    # Additional metadata
    user_id: str = "default"
    importance_boost: float = 0.0  # Additional boost from consolidation

    def __post_init__(self):
        """Ensure values are within bounds"""
        self.emotional_weight = max(0.0, min(1.0, self.emotional_weight))
        self.emotional_valence = max(-1.0, min(1.0, self.emotional_valence))

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "EmotionalMemory":
        """Create from dictionary"""
        return cls(**data)

    def age_hours(self) -> float:
        """How old is this memory in hours"""
        try:
            event_time = datetime.fromisoformat(self.timestamp)
            delta = datetime.now() - event_time
            return delta.total_seconds() / 3600
        except:
            return 9999

    def age_days(self) -> float:
        """How old is this memory in days"""
        return self.age_hours() / 24

    def get_retrieval_score(self,
                            current_emotion: dict = None,
                            recency_weight: float = 0.3,
                            emotional_similarity_weight: float = 0.4,
                            access_weight: float = 0.2,
                            base_weight: float = 0.1) -> float:
        """
        Calculate retrieval score based on multiple factors.
        Higher score = more likely to be retrieved.
        """
        # Base score from emotional weight
        score = self.emotional_weight * base_weight

        # Recency factor (exponential decay)
        decay_days = get_int("EMOTIONAL_MEMORY_DECAY_DAYS", 30)
        recency_factor = math.exp(-self.age_days() / decay_days)
        score += recency_factor * recency_weight

        # Access count factor (memories accessed more are easier to retrieve)
        access_factor = min(1.0, self.access_count / 10)
        score += access_factor * access_weight

        # Emotional similarity factor
        if current_emotion and self.emotions_felt:
            similarity = self._calculate_emotional_similarity(current_emotion)
            score += similarity * emotional_similarity_weight

        # Importance boost from consolidation
        score += self.importance_boost * 0.1

        return min(1.0, score)

    def _calculate_emotional_similarity(self, current_emotion: dict) -> float:
        """Calculate how similar current emotional state is to this memory"""
        if not self.emotions_felt:
            return 0.0

        # Map emotion names to valence/arousal for comparison
        emotion_mapping = {
            "happy": (0.8, 0.5),
            "joy": (0.9, 0.6),
            "excited": (0.7, 0.8),
            "love": (0.9, 0.4),
            "desire": (0.6, 0.7),
            "arousal": (0.5, 0.9),
            "sad": (-0.6, 0.3),
            "angry": (-0.7, 0.7),
            "fear": (-0.5, 0.8),
            "anxious": (-0.3, 0.6),
            "calm": (0.3, 0.2),
            "content": (0.5, 0.2),
            "nostalgic": (0.3, 0.3),
            "romantic": (0.7, 0.5),
            "flirty": (0.6, 0.6),
            "vulnerable": (-0.2, 0.5),
            "grateful": (0.8, 0.3),
        }

        # Get average valence/arousal for memory's emotions
        memory_va = [emotion_mapping.get(e, (0, 0)) for e in self.emotions_felt]
        if not memory_va:
            return 0.0

        memory_valence = sum(v for v, _ in memory_va) / len(memory_va)
        memory_arousal = sum(a for _, a in memory_va) / len(memory_va)

        # Calculate current state valence/arousal
        current_valence = current_emotion.get("valence", 0)
        current_arousal = current_emotion.get("arousal", 0.5)

        # Infer from named emotions if present
        if "emotions" in current_emotion:
            for emotion_name, value in current_emotion["emotions"].items():
                if emotion_name in emotion_mapping and value > 0.3:
                    ev, ea = emotion_mapping[emotion_name]
                    current_valence = current_valence * 0.5 + ev * 0.5
                    current_arousal = current_arousal * 0.5 + ea * 0.5

        # Calculate Euclidean similarity
        distance = math.sqrt((memory_valence - current_valence)**2 +
                           (memory_arousal - current_arousal)**2)
        similarity = 1.0 - min(1.0, distance / 2.0)  # Normalize to 0-1

        return similarity


# ============================================================
# Main System Class
# ============================================================

class EmotionalMemorySystem:
    """
    Core emotional memory system implementing amygdala-hippocampus-like
    memory processing with emotional weighting.

    Features:
    - Emotional tagging of interactions
    - Weighted memory storage and retrieval
    - Contextual binding (emotion + content + relationship state)
    - Memory consolidation over time
    """

    def __init__(self, data_path: Path = None, user_id: str = "default"):
        """
        Initialize the emotional memory system.

        Args:
            data_path: Path to data directory (defaults to project data/)
            user_id: User identifier for per-user memory isolation
        """
        self.user_id = user_id
        self._lock = threading.RLock()

        # Set up data path
        if data_path is None:
            data_path = Path(__file__).parent.parent / "data"
        self.data_path = Path(data_path)
        self.storage_path = self.data_path / "emotional_memories"
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # User-specific storage
        self.user_storage_file = self.storage_path / f"{user_id}_memories.json"

        # In-memory cache
        self._memories: Dict[str, EmotionalMemory] = {}
        self._recent_memories: List[str] = []  # IDs of recent memories
        self._consolidation_queue: List[str] = []  # IDs pending consolidation

        # Configuration from settings
        self.max_stored = get_int("EMOTIONAL_MEMORY_MAX_STORED", 500)
        self.high_emotion_threshold = get_float("HIGH_EMOTION_THRESHOLD", 0.7)
        self.decay_days = get_int("EMOTIONAL_MEMORY_DECAY_DAYS", 30)

        # Load existing memories
        self._load()

        print(f"[EmotionalMemory] Initialized for user {user_id} with {len(self._memories)} memories")

    # ============================================================
    # Core API Methods
    # ============================================================

    def encode_memory(self,
                      content: str,
                      emotional_weight: float,
                      context: dict = None,
                      emotional_valence: float = 0.0,
                      emotions_felt: List[str] = None) -> EmotionalMemory:
        """
        Store a memory with emotional weighting.

        Args:
            content: What happened (the memory content)
            emotional_weight: 0-1, how emotionally significant (amygdala tag)
            context: Additional context (relationship state, time, topic, etc.)
            emotional_valence: -1 to 1, positive vs negative
            emotions_felt: List of emotion names experienced

        Returns:
            The created EmotionalMemory object
        """
        with self._lock:
            memory_id = str(uuid.uuid4())

            # Enrich context with defaults
            if context is None:
                context = {}

            # Add automatic context
            context.setdefault("time_of_day", self._get_time_of_day())
            context.setdefault("day_of_week", datetime.now().strftime("%A"))
            if "relationship_state" not in context:
                context["relationship_state"] = "unknown"

            # Create memory object
            memory = EmotionalMemory(
                id=memory_id,
                content=content,
                emotional_weight=emotional_weight,
                emotional_valence=emotional_valence,
                emotions_felt=emotions_felt or [],
                context=context,
                timestamp=datetime.now().isoformat(),
                user_id=self.user_id
            )

            # Store in cache
            self._memories[memory_id] = memory
            self._recent_memories.append(memory_id)

            # Queue for consolidation if high emotion
            if emotional_weight >= self.high_emotion_threshold:
                self._consolidation_queue.append(memory_id)
                print(f"[EmotionalMemory] High-emotion memory queued for consolidation: {content[:50]}...")

            # Enforce storage limits
            self._enforce_limits()

            # Save to disk
            self._save()

            print(f"[EmotionalMemory] Encoded memory (weight={emotional_weight:.2f}): {content[:50]}...")

            return memory

    def retrieve_relevant(self,
                          query: str = None,
                          current_emotion: dict = None,
                          limit: int = 5,
                          min_weight: float = 0.0,
                          include_consolidated: bool = True) -> List[EmotionalMemory]:
        """
        Retrieve memories with emotional resonance scoring.

        Args:
            query: Optional search query for content matching
            current_emotion: Current emotional state for resonance matching
            limit: Maximum number of memories to return
            min_weight: Minimum emotional weight threshold
            include_consolidated: Whether to include consolidated memories

        Returns:
            List of EmotionalMemory objects sorted by relevance
        """
        with self._lock:
            candidates = []

            for memory in self._memories.values():
                # Apply filters
                if memory.emotional_weight < min_weight:
                    continue

                if not include_consolidated and memory.consolidated:
                    continue

                # Calculate retrieval score
                score = memory.get_retrieval_score(current_emotion)

                # Boost score for query matching
                if query and query.lower() in memory.content.lower():
                    score += 0.3

                candidates.append((memory, score))

            # Sort by score descending
            candidates.sort(key=lambda x: x[1], reverse=True)

            # Get top memories
            results = []
            for memory, score in candidates[:limit]:
                # Update access tracking
                memory.access_count += 1
                memory.last_accessed = datetime.now().isoformat()
                results.append(memory)

            # Save updated access counts
            if results:
                self._save()

            return results

    def get_emotionally_similar_memories(self,
                                         emotion_state: dict,
                                         limit: int = 5,
                                         valence_tolerance: float = 0.3) -> List[EmotionalMemory]:
        """
        Find memories matching current mood/emotional state.

        This implements "state-dependent memory" - memories are easier
        to retrieve when in a similar emotional state.

        Args:
            emotion_state: Current emotional state (valence, arousal, emotion names)
            limit: Maximum memories to return
            valence_tolerance: How close valence must match

        Returns:
            List of emotionally similar memories
        """
        with self._lock:
            # Extract current valence
            current_valence = emotion_state.get("valence", 0)
            current_arousal = emotion_state.get("arousal", 0.5)

            # Get named emotions
            active_emotions = set()
            if "emotions" in emotion_state:
                active_emotions = {e for e, v in emotion_state["emotions"].items() if v > 0.3}

            candidates = []

            for memory in self._memories.values():
                # Check valence similarity
                valence_diff = abs(memory.emotional_valence - current_valence)
                if valence_diff > valence_tolerance:
                    continue

                # Calculate similarity score
                similarity = memory._calculate_emotional_similarity(emotion_state)

                # Boost for matching emotion names
                if active_emotions and memory.emotions_felt:
                    overlap = len(active_emotions & set(memory.emotions_felt))
                    similarity += overlap * 0.1

                # Apply emotional weight as multiplier
                final_score = similarity * (0.5 + memory.emotional_weight * 0.5)

                candidates.append((memory, final_score))

            # Sort by score
            candidates.sort(key=lambda x: x[1], reverse=True)

            return [m for m, _ in candidates[:limit]]

    def consolidate_recent_memories(self,
                                    max_age_hours: float = 24,
                                    min_weight: float = 0.5) -> int:
        """
        Process recent memories into long-term patterns.

        This implements "memory consolidation" - important recent memories
        are strengthened and linked together.

        Args:
            max_age_hours: Only consolidate memories newer than this
            min_weight: Minimum weight to consider for consolidation

        Returns:
            Number of memories consolidated
        """
        with self._lock:
            consolidated_count = 0

            # Find recent, significant, unconsolidated memories
            candidates = []
            for memory_id, memory in self._memories.items():
                if memory.consolidated:
                    continue
                if memory.age_hours() > max_age_hours:
                    continue
                if memory.emotional_weight < min_weight:
                    continue
                candidates.append(memory)

            # Process consolidation queue first (high-emotion memories)
            queue_ids = set(self._consolidation_queue)
            high_priority = [m for m in candidates if m.id in queue_ids]
            normal_priority = [m for m in candidates if m.id not in queue_ids]

            # Consolidate high priority first
            for memory in high_priority + normal_priority:
                # Mark as consolidated
                memory.consolidated = True

                # Calculate importance boost based on:
                # - Emotional weight
                # - Access count
                # - Age (slightly older = more stable)
                importance = (
                    memory.emotional_weight * 0.5 +
                    min(0.3, memory.access_count * 0.03) +
                    min(0.2, memory.age_hours() / 168)  # Up to 0.2 after a week
                )
                memory.importance_boost = min(1.0, importance)

                consolidated_count += 1
                print(f"[EmotionalMemory] Consolidated: {memory.content[:50]}... (boost={memory.importance_boost:.2f})")

            # Clear consolidation queue
            self._consolidation_queue = []

            # Save changes
            if consolidated_count > 0:
                self._save()

            return consolidated_count

    def get_memory_prompt_section(self,
                                  user_id: str = None,
                                  current_emotion: dict = None,
                                  max_memories: int = 5,
                                  max_tokens: int = 500) -> str:
        """
        Format relevant memories for LLM context.

        This provides emotionally-weighted memory context to the LLM,
        prioritizing high-emotion and mood-matching memories.

        Args:
            user_id: Optional user filter (uses instance user_id if not provided)
            current_emotion: Current emotional state for matching
            max_memories: Maximum memories to include
            max_tokens: Approximate token limit for output

        Returns:
            Formatted string for LLM prompt
        """
        with self._lock:
            # Get emotionally relevant memories
            memories = self.retrieve_relevant(
                query=None,
                current_emotion=current_emotion,
                limit=max_memories * 2,  # Get more for filtering
                min_weight=0.3
            )

            if not memories:
                return ""

            # Build prompt section
            sections = []
            sections.append("EMOTIONAL MEMORIES (significant moments):")

            char_estimate = 0
            included_count = 0

            for memory in memories:
                # Format single memory
                valence_indicator = "+" if memory.emotional_valence > 0.3 else ("-" if memory.emotional_valence < -0.3 else "~")

                # Time context
                age = memory.age_hours()
                if age < 1:
                    time_str = "very recently"
                elif age < 24:
                    time_str = f"{int(age)} hours ago"
                elif age < 168:
                    time_str = f"{int(age/24)} days ago"
                else:
                    time_str = f"{int(age/168)} weeks ago"

                # Emotions felt
                emotions_str = ""
                if memory.emotions_felt:
                    emotions_str = f" [felt: {', '.join(memory.emotions_felt[:3])}]"

                # Context
                context_str = ""
                if memory.context.get("conversation_topic"):
                    context_str = f" (about: {memory.context['conversation_topic']})"

                line = f"  {valence_indicator} [{time_str}] {memory.content[:100]}{emotions_str}{context_str}"

                # Check token limit (rough estimate: 1 token ~ 4 chars)
                if char_estimate + len(line) > max_tokens * 4:
                    break

                sections.append(line)
                char_estimate += len(line)
                included_count += 1

                if included_count >= max_memories:
                    break

            if included_count == 0:
                return ""

            return "\n".join(sections)

    def tag_emotional_moment(self,
                            content: str,
                            intensity: float,
                            emotion_type: str = None,
                            context: dict = None) -> EmotionalMemory:
        """
        Mark a significant emotional moment for strong encoding.

        This is the "tag and capture" mechanism - highly emotional
        moments get stronger memory encoding.

        Args:
            content: What happened
            intensity: 0-1 intensity of the emotion
            emotion_type: Type of emotion (love, desire, joy, hurt, etc.)
            context: Additional context

        Returns:
            The created high-emotion memory
        """
        # Map emotion types to valence
        valence_map = {
            "love": 0.9,
            "joy": 0.8,
            "excited": 0.7,
            "happy": 0.7,
            "desire": 0.6,
            "arousal": 0.5,
            "romantic": 0.7,
            "flirty": 0.6,
            "calm": 0.3,
            "content": 0.5,
            "sad": -0.6,
            "hurt": -0.7,
            "angry": -0.8,
            "fear": -0.6,
            "anxious": -0.4,
            "vulnerable": -0.2,
        }

        # Determine valence
        valence = valence_map.get(emotion_type, 0.0) if emotion_type else 0.0

        # High-intensity moments get boosted weight
        weight = min(1.0, intensity * 1.2)

        # Create emotions list
        emotions_felt = [emotion_type] if emotion_type else []

        # Add intensity to context
        if context is None:
            context = {}
        context["moment_type"] = "emotional_peak"
        context["intensity"] = intensity

        return self.encode_memory(
            content=content,
            emotional_weight=weight,
            emotional_valence=valence,
            emotions_felt=emotions_felt,
            context=context
        )

    # ============================================================
    # Additional Utility Methods
    # ============================================================

    def get_memory_by_id(self, memory_id: str) -> Optional[EmotionalMemory]:
        """Retrieve a specific memory by ID"""
        return self._memories.get(memory_id)

    def get_recent_high_emotion(self,
                                hours: float = 24,
                                limit: int = 5) -> List[EmotionalMemory]:
        """Get recent high-emotion memories"""
        with self._lock:
            candidates = [
                m for m in self._memories.values()
                if m.age_hours() <= hours and m.emotional_weight >= self.high_emotion_threshold
            ]
            candidates.sort(key=lambda m: m.timestamp, reverse=True)
            return candidates[:limit]

    def get_emotional_summary(self, hours: float = 24) -> dict:
        """
        Get a summary of recent emotional memory patterns.
        Useful for understanding overall emotional state.
        """
        with self._lock:
            recent = [m for m in self._memories.values() if m.age_hours() <= hours]

            if not recent:
                return {"count": 0, "average_weight": 0, "dominant_valence": "neutral"}

            avg_weight = sum(m.emotional_weight for m in recent) / len(recent)
            avg_valence = sum(m.emotional_valence for m in recent) / len(recent)

            # Find dominant emotions
            emotion_counts = {}
            for m in recent:
                for e in m.emotions_felt:
                    emotion_counts[e] = emotion_counts.get(e, 0) + 1

            dominant_emotions = sorted(emotion_counts.items(), key=lambda x: x[1], reverse=True)[:3]

            return {
                "count": len(recent),
                "average_weight": round(avg_weight, 2),
                "average_valence": round(avg_valence, 2),
                "dominant_valence": "positive" if avg_valence > 0.2 else ("negative" if avg_valence < -0.2 else "neutral"),
                "dominant_emotions": [e for e, _ in dominant_emotions],
                "high_emotion_count": len([m for m in recent if m.emotional_weight >= self.high_emotion_threshold])
            }

    def strengthen_memory(self, memory_id: str, boost: float = 0.1) -> bool:
        """
        Strengthen a memory (like remembering/rehearsing it).
        Implements memory strengthening through recall.
        """
        with self._lock:
            if memory_id not in self._memories:
                return False

            memory = self._memories[memory_id]
            memory.emotional_weight = min(1.0, memory.emotional_weight + boost)
            memory.access_count += 1
            memory.last_accessed = datetime.now().isoformat()

            self._save()
            return True

    def link_memories(self, memory_id1: str, memory_id2: str, link_type: str = "related") -> bool:
        """
        Create an associative link between two memories.
        This implements memory association/priming.
        """
        with self._lock:
            if memory_id1 not in self._memories or memory_id2 not in self._memories:
                return False

            # Add link to context
            mem1 = self._memories[memory_id1]
            mem2 = self._memories[memory_id2]

            if "linked_memories" not in mem1.context:
                mem1.context["linked_memories"] = []
            if "linked_memories" not in mem2.context:
                mem2.context["linked_memories"] = []

            mem1.context["linked_memories"].append({"id": memory_id2, "type": link_type})
            mem2.context["linked_memories"].append({"id": memory_id1, "type": link_type})

            self._save()
            return True

    def clear_old_memories(self, max_age_days: float = 90, keep_weight_above: float = 0.8) -> int:
        """
        Clean up old, less significant memories.
        High-weight memories are preserved.
        """
        with self._lock:
            to_remove = []

            for memory_id, memory in self._memories.items():
                # Always keep high-weight memories
                if memory.emotional_weight >= keep_weight_above:
                    continue

                # Remove old, low-weight memories
                if memory.age_days() > max_age_days:
                    to_remove.append(memory_id)

            for memory_id in to_remove:
                del self._memories[memory_id]

            if to_remove:
                self._save()
                print(f"[EmotionalMemory] Cleared {len(to_remove)} old memories")

            return len(to_remove)

    def get_stats(self) -> dict:
        """Get system statistics"""
        with self._lock:
            if not self._memories:
                return {
                    "total_memories": 0,
                    "user_id": self.user_id,
                    "storage_path": str(self.user_storage_file)
                }

            weights = [m.emotional_weight for m in self._memories.values()]
            valences = [m.emotional_valence for m in self._memories.values()]

            return {
                "total_memories": len(self._memories),
                "user_id": self.user_id,
                "storage_path": str(self.user_storage_file),
                "average_weight": round(sum(weights) / len(weights), 2),
                "average_valence": round(sum(valences) / len(valences), 2),
                "high_emotion_count": len([w for w in weights if w >= self.high_emotion_threshold]),
                "consolidated_count": len([m for m in self._memories.values() if m.consolidated]),
                "pending_consolidation": len(self._consolidation_queue),
                "oldest_memory_days": round(max(m.age_days() for m in self._memories.values()), 1),
                "config": {
                    "max_stored": self.max_stored,
                    "high_emotion_threshold": self.high_emotion_threshold,
                    "decay_days": self.decay_days
                }
            }

    # ============================================================
    # Private Methods
    # ============================================================

    def _get_time_of_day(self) -> str:
        """Get current time of day category"""
        hour = datetime.now().hour
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 21:
            return "evening"
        else:
            return "night"

    def _enforce_limits(self):
        """Enforce maximum storage limits by removing lowest-weight memories"""
        if len(self._memories) <= self.max_stored:
            return

        # Sort by emotional weight + recency
        def sort_key(m):
            recency = math.exp(-m.age_days() / self.decay_days)
            return m.emotional_weight * 0.7 + recency * 0.3

        sorted_memories = sorted(self._memories.values(), key=sort_key)

        # Remove lowest scoring memories
        to_remove = len(self._memories) - self.max_stored
        for memory in sorted_memories[:to_remove]:
            del self._memories[memory.id]

        print(f"[EmotionalMemory] Removed {to_remove} low-priority memories to enforce limit")

    def _load(self):
        """Load memories from disk"""
        if not self.user_storage_file.exists():
            return

        try:
            with open(self.user_storage_file, 'r') as f:
                data = json.load(f)

            for memory_data in data.get("memories", []):
                try:
                    memory = EmotionalMemory.from_dict(memory_data)
                    self._memories[memory.id] = memory
                except Exception as e:
                    print(f"[EmotionalMemory] Error loading memory: {e}")

            # Load consolidation queue
            self._consolidation_queue = data.get("consolidation_queue", [])

            print(f"[EmotionalMemory] Loaded {len(self._memories)} memories from disk")

        except Exception as e:
            print(f"[EmotionalMemory] Error loading memories: {e}")

    def _save(self):
        """Save memories to disk"""
        try:
            data = {
                "user_id": self.user_id,
                "last_updated": datetime.now().isoformat(),
                "memories": [m.to_dict() for m in self._memories.values()],
                "consolidation_queue": self._consolidation_queue
            }

            with open(self.user_storage_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            print(f"[EmotionalMemory] Error saving memories: {e}")


# ============================================================
# Singleton Management
# ============================================================

_instances: Dict[str, EmotionalMemorySystem] = {}
_instances_lock = threading.Lock()


def get_emotional_memory_system(user_id: str = "default",
                                 data_path: Path = None) -> EmotionalMemorySystem:
    """
    Get or create an EmotionalMemorySystem instance for a user.

    This implements a per-user singleton pattern.

    Args:
        user_id: User identifier
        data_path: Optional custom data path

    Returns:
        EmotionalMemorySystem instance for the user
    """
    with _instances_lock:
        if user_id not in _instances:
            _instances[user_id] = EmotionalMemorySystem(
                data_path=data_path,
                user_id=user_id
            )
        return _instances[user_id]


def reset_emotional_memory_system(user_id: str = None):
    """
    Reset the singleton instances (mainly for testing).

    Args:
        user_id: Specific user to reset, or None for all
    """
    with _instances_lock:
        if user_id:
            _instances.pop(user_id, None)
        else:
            _instances.clear()


# ============================================================
# Integration Helper Functions
# ============================================================

def create_from_conversation(content: str,
                             emotion_data: dict,
                             context: dict = None,
                             user_id: str = "default") -> Optional[EmotionalMemory]:
    """
    Convenience function to create emotional memory from conversation data.

    Args:
        content: Conversation content
        emotion_data: Emotion data from emotional state system
        context: Additional context
        user_id: User identifier

    Returns:
        Created memory or None
    """
    system = get_emotional_memory_system(user_id)

    # Extract emotional weight from emotion data
    weight = 0.5
    valence = 0.0
    emotions = []

    if emotion_data:
        # Get highest emotion intensity as weight
        emotion_values = {k: v for k, v in emotion_data.items()
                        if isinstance(v, (int, float)) and k not in ["valence", "arousal"]}
        if emotion_values:
            weight = max(emotion_values.values())
            emotions = [k for k, v in emotion_values.items() if v >= 0.3]

        valence = emotion_data.get("valence", 0.0)

    return system.encode_memory(
        content=content,
        emotional_weight=weight,
        emotional_valence=valence,
        emotions_felt=emotions,
        context=context
    )


def get_memory_context_for_llm(user_id: str = "default",
                                current_emotion: dict = None,
                                max_memories: int = 5) -> str:
    """
    Convenience function to get memory context for LLM prompts.

    Args:
        user_id: User identifier
        current_emotion: Current emotional state
        max_memories: Maximum memories to include

    Returns:
        Formatted memory context string
    """
    system = get_emotional_memory_system(user_id)
    return system.get_memory_prompt_section(
        user_id=user_id,
        current_emotion=current_emotion,
        max_memories=max_memories
    )
