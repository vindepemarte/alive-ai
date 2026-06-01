"""
EmotionalDecay: Decay logic and baseline management
"""


class EmotionalDecay:
    """Handles emotional decay and natural changes"""

    def __init__(self, emotion_state, variability=None):
        self.e = emotion_state
        self.variability = variability

    def set_variability(self, variability):
        """Set variability module for organic randomness"""
        self.variability = variability

    def decay(self):
        """Natural return to baseline - LOVE IS STICKY AT HIGH LEVELS"""
        for emo, base in self.e.baseline.items():
            curr = getattr(self.e, emo)

            # LOVE: Very slow decay at high levels (sticky love)
            if emo == "love":
                if curr >= 0.9:
                    rate = 0.001  # Almost no decay at max
                elif curr >= 0.7:
                    rate = 0.005  # Very slow at high
                elif curr >= 0.5:
                    rate = 0.01   # Slow at moderate
                else:
                    rate = 0.03   # Normal at low
            elif emo == "desire":
                rate = 0.02  # Faster decay
            else:
                rate = 0.05  # Standard decay

            # Add organic randomness if variability provided
            if self.variability:
                if self.variability.should_skip_decay(emo, curr):
                    continue
                rate = self.variability.randomize_decay(rate)

            new = curr + (base - curr) * rate
            setattr(self.e, emo, max(0, min(1, new)))

    def tick(self):
        """Minute tick for natural changes"""
        # Desire slowly fades
        self.e.desire = max(0.0, self.e.desire - 0.002)

        # Boredom increases if low arousal
        if self.e.arousal < 0.3:
            self.e.boredom = min(1.0, self.e.boredom + 0.01)
        else:
            self.e.boredom = max(0.0, self.e.boredom - 0.005)

        # Love slowly creeps up if in good relationship
        if self.e.joy > 0.6 and self.e.love > 0.3:
            self.e.love = min(1.0, self.e.love + 0.001)
