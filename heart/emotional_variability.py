"""
Heart: Emotional Variability
Add organic randomness, inertia, and reaction cooldowns
"""

import random
import time
from dataclasses import dataclass, field


@dataclass
class ReactionCooldown:
    """Track when reactions were last used"""
    emoji: str = ""
    last_used: float = 0.0
    count_recent: int = 0


class EmotionalVariability:
    """Adds organic feel to emotional responses"""

    # Minimum seconds between same emoji reactions
    COOLDOWN_SECONDS = 60

    # How many recent uses trigger "cooling off"
    SPAM_THRESHOLD = 3

    def __init__(self):
        self.reaction_history: dict[str, ReactionCooldown] = {}
        self.momentum: dict[str, float] = {}  # Emotional inertia
        self.last_tick_randomness = 0.0

    def can_react(self, emoji: str) -> bool:
        """Check if this emoji is off cooldown"""
        now = time.time()

        if emoji not in self.reaction_history:
            self.reaction_history[emoji] = ReactionCooldown(emoji=emoji)
            return True

        history = self.reaction_history[emoji]

        # Check cooldown
        if now - history.last_used < self.COOLDOWN_SECONDS:
            return False

        # Reduce spam count over time
        if now - history.last_used > self.COOLDOWN_SECONDS * 2:
            history.count_recent = max(0, history.count_recent - 1)

        return True

    def record_reaction(self, emoji: str):
        """Record that a reaction was used"""
        now = time.time()

        if emoji not in self.reaction_history:
            self.reaction_history[emoji] = ReactionCooldown(emoji=emoji)

        history = self.reaction_history[emoji]
        history.last_used = now
        history.count_recent += 1

    def get_reaction_probability(self, emoji: str) -> float:
        """Get probability modifier based on recent usage"""
        if emoji not in self.reaction_history:
            return 1.0

        history = self.reaction_history[emoji]

        # Reduce probability if spammed recently
        if history.count_recent >= self.SPAM_THRESHOLD:
            return 0.2  # 20% chance if spammed

        if history.count_recent >= 2:
            return 0.5  # 50% chance if used a few times

        return 1.0

    def add_momentum(self, emotion: str, change: float):
        """Track emotional momentum/inertia"""
        current = self.momentum.get(emotion, 0.0)
        # Weighted average with recent changes
        self.momentum[emotion] = current * 0.6 + change * 0.4

    def get_inertia_modifier(self, emotion: str, current_value: float) -> float:
        """Get modifier for emotional changes based on momentum"""
        momentum = self.momentum.get(emotion, 0.0)

        # High momentum in same direction = amplification
        # High momentum in opposite direction = resistance
        if abs(momentum) > 0.1:
            # Amplify changes in momentum direction
            return 1.0 + momentum * 0.3

        return 1.0

    def randomize_decay(self, base_rate: float) -> float:
        """Add organic randomness to decay rates"""
        # Randomize between 0.7x and 1.3x base rate
        multiplier = random.uniform(0.7, 1.3)
        return base_rate * multiplier

    def get_organic_tick(self) -> float:
        """Get a random organic fluctuation for tick updates"""
        # Small random emotional noise (-0.02 to +0.02)
        self.last_tick_randomness = random.gauss(0, 0.01)
        return self.last_tick_randomness

    def should_skip_decay(self, emotion: str, value: float) -> bool:
        """Sometimes emotions just don't decay (organic feel)"""
        # 10% chance to skip decay entirely
        if random.random() < 0.1:
            return True

        # High-intensity emotions resist decay more
        if value > 0.8 and random.random() < 0.2:
            return True

        return False

    def get_available_emojis(self, preferred: list[str]) -> list[str]:
        """Filter emoji list to only available ones (off cooldown)"""
        return [e for e in preferred if self.can_react(e)]

    def choose_organic_reaction(self, candidates: list[str]) -> str | None:
        """Choose a reaction with organic variability"""
        available = self.get_available_emojis(candidates)

        if not available:
            return None

        # Weight by inverse of recent usage
        weights = []
        for emoji in available:
            prob = self.get_reaction_probability(emoji)
            weights.append(prob)

        if sum(weights) == 0:
            return None

        chosen = random.choices(available, weights=weights, k=1)[0]
        self.record_reaction(chosen)
        return chosen

    def clear_old_history(self, max_age_seconds: float = 3600):
        """Clean up old reaction history"""
        now = time.time()
        to_remove = []

        for emoji, history in self.reaction_history.items():
            if now - history.last_used > max_age_seconds:
                to_remove.append(emoji)

        for emoji in to_remove:
            del self.reaction_history[emoji]
