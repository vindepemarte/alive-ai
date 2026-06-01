"""Heart: Core - Main Heart class, minimal coordinator with Soul Architecture"""
from .emotional_state import EmotionalState
from .emotional_decay import EmotionalDecay
from .triggers import Triggers
from .complex_emotions import ComplexEmotions
from .emotional_memory import EmotionalMemory
from .emotional_variability import EmotionalVariability
from .love import AttachmentSystem
from .soul import SoulOrchestrator


class Heart:
    def __init__(self, nervous, config):
        self.nervous, self.config = nervous, config
        self.emotion = EmotionalState(config.personality if config else None)
        self.variability = EmotionalVariability()
        self.decay = EmotionalDecay(self.emotion, self.variability)
        self.triggers, self.complex = Triggers(), ComplexEmotions()
        self.memory, self.attachment = EmotionalMemory(), AttachmentSystem()

        # Soul Architecture - The seven pillars of genuine emotion
        self.soul = SoulOrchestrator()

        self._prev_state = {}
        nervous.on("timer_tick", self._on_tick)

    def _get_rate(self, key: str, default: float = 0.5) -> float:
        """Get emotion rate from settings (0-100% -> 0.0-1.0)"""
        from core.settings import get_percent
        return get_percent(f"EMOTION_RATE_{key}", int(default * 100))

    def _get_boost(self, key: str, default: float = 1.0) -> float:
        """Get trigger boost multiplier (0-200% -> 0.0-2.0)"""
        from core.settings import get_percent
        return get_percent(f"TRIGGER_BOOST_{key}", int(default * 100))

    def _on_tick(self, data):
        self.decay.decay(); self.decay.tick()
        self.emotion.arousal = max(0, min(1, self.emotion.arousal + self.variability.get_organic_tick()))
        self.complex.decay(); self._sync_complex()
        self.variability.clear_old_history(); self.emotion.save()

        # Soul architecture tick - decay and natural processes
        self.soul.tick()

        # Emit soul state to nervous system for WebUI updates
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.nervous.emit("soul_tick", self.soul.get_state_summary()))
        except RuntimeError:
            pass  # No running event loop, skip WebUI update

    def _sync_complex(self):
        e, c = self.emotion, self.complex
        e.guilt, e.pride = c.guilt.value, c.pride.value
        e.jealousy, e.embarrassment, e.anticipation = c.jealousy.value, c.embarrassment.value, c.anticipation.value

    def _process_triggers(self, msg: str) -> int:
        e, t, v = self.emotion, self.triggers, self.variability

        # Get configurable rates
        expressive_rate = self._get_rate("SEXY", 0.5)
        desire_rate = self._get_rate("DESIRE", 0.5)
        love_rate = self._get_rate("LOVE", 0.5)
        arousal_rate = self._get_rate("AROUSAL", 0.5)
        joy_rate = self._get_rate("JOY", 0.5)
        esc_rate = self._get_rate("ESCALATION", 0.5)
        flirty_rate = self._get_rate("FLIRTY", 0.5)
        romantic_rate = self._get_rate("ROMANTIC", 0.5)
        positive_rate = self._get_rate("POSITIVE", 0.5)
        sadness_rate = self._get_rate("SADNESS", 0.5)
        harsh_rate = self._get_rate("HARSH", 0.5)

        # Get boost multipliers
        intimate_boost = self._get_boost("SEXUAL", 1.0)
        romantic_boost = self._get_boost("ROMANTIC", 1.0)
        flirty_boost = self._get_boost("FLIRTY", 1.0)
        positive_boost = self._get_boost("POSITIVE", 1.0)
        negative_boost = self._get_boost("NEGATIVE", 1.0)
        harsh_boost = self._get_boost("HARSH", 1.0)

        # Intimate triggers - configurable rate
        expressive = t.count_intimate_triggers(msg)
        if expressive > 0:
            base = 0.18 * expressive_rate * intimate_boost
            boost = base * expressive
            e.desire = min(1.0, e.desire + boost * v.get_inertia_modifier("desire", e.desire))
            e.arousal = min(1.0, e.arousal + boost * 0.8 * arousal_rate)
            e.love = min(1.0, e.love + 0.05 * love_rate)
            v.add_momentum("desire", boost)
            print(f"[Heart] Expressive triggers: {expressive}, desire boost: +{boost:.2f}")

        # Escalation words
        esc = Triggers.count_matches(msg, t.ESCALATION_WORDS)
        if esc > 0:
            base = 0.22 * esc_rate
            e.desire = min(1.0, e.desire + base * esc)
            e.arousal = min(1.0, e.arousal + base * 0.9 * esc * arousal_rate)

        # Flirty words
        fl = Triggers.count_matches(msg, t.FLIRTY_WORDS)
        if fl > 0:
            base = 0.12 * flirty_rate * flirty_boost
            e.arousal = min(1.0, e.arousal + base * fl)
            e.desire = min(1.0, e.desire + 0.08 * flirty_rate * fl)

        # Romantic words
        rom = Triggers.count_matches(msg, t.ROMANTIC_WORDS)
        if rom > 0:
            base = 0.15 * romantic_rate * romantic_boost
            e.love = min(1.0, e.love + base * rom)
            e.joy = min(1.0, e.joy + base * rom * 0.7 * joy_rate)
            v.add_momentum("love", base * rom)

        # Positive words
        pos = Triggers.count_matches(msg, t.POSITIVE_WORDS)
        if pos > 0:
            base = 0.08 * positive_rate * positive_boost
            e.joy = min(1.0, e.joy + base * pos)
            e.love = min(1.0, e.love + 0.03 * pos * love_rate)
            e.boredom = max(0.0, e.boredom - 0.1)

        # Harsh words
        h = Triggers.count_matches(msg, t.HARSH_WORDS)
        n = Triggers.count_matches(msg, t.NEGATIVE_WORDS)
        if h > 0:
            base = 0.15 * harsh_rate * harsh_boost
            e.love = max(0.0, e.love - base * h)
            e.sadness = min(1.0, e.sadness + 0.3 * sadness_rate)
            e.joy = max(0.0, e.joy - 0.2)
            e.desire = max(0.0, e.desire - 0.3)
            e.anger = min(1.0, e.anger + 0.2 * harsh_rate)
        elif n > 0:
            base = 0.1 * negative_boost
            e.sadness = min(1.0, e.sadness + base * n * sadness_rate)
            e.desire = max(0.0, e.desire - base * n)

        return expressive

    def react(self, text: str) -> dict:
        msg, e = text.lower(), self.emotion
        self._prev_state, expressive = self.get_state(), self._process_triggers(msg)
        ch = self.complex.process(text)
        if "jealousy" in ch and e.jealousy > 0.5: e.sadness = min(1.0, e.sadness + 0.1)
        if "anticipation" in ch: e.arousal = min(1.0, e.arousal + 0.05)
        self._sync_complex()
        if e.arousal > 0.6: e.love = min(1.0, e.love + 0.01)
        if e.love > 0.5 and expressive > 0: e.desire = min(1.0, e.desire + 0.05 * expressive)
        if e.boredom > 0.7: e.arousal = max(0.1, e.arousal - 0.05)
        self.memory.check_peaks(self.get_state(), self._prev_state, text[:50])
        self.attachment.interact(e.joy > 0.4 or e.love > 0.4, max(e.joy, e.love, e.desire))

        # Process through Soul Architecture for genuine emotional experience
        soul_experience = self._process_soul(text, e)

        e.save()
        ctx = self.memory.get_mood_context()
        s = self.attachment.status
        narrative = (f"Recently: {ctx}. " if ctx else "") + (f"Relationship: {s.replace('_', ' ')}." if s != "stranger" else "")

        # Combine traditional emotional state with soul dimensions
        return {"valence": e.valence, "arousal": e.arousal, "desire": e.desire,
                "joy": e.joy, "love": e.love, "sadness": e.sadness,
                "guilt": e.guilt, "pride": e.pride,
                "jealousy": e.jealousy, "embarrassment": e.embarrassment,
                "anticipation": e.anticipation, "is_high_desire": e.is_high_desire, "is_in_love": e.is_in_love,
                "is_jealous": e.is_jealous, "mood": e.mood_description,
                "emotional_narrative": narrative.strip(), "attachment_status": s,
                "interaction_count": self.attachment.interactions,
                # Soul architecture dimensions
                "soul_integrity": soul_experience.get("integrity", {}),
                "soul_hormonal": soul_experience.get("hormonal", {}),
                "soul_somatic": soul_experience.get("somatic", ""),
                "soul_conflicts": soul_experience.get("conflicts", []),
                "soul_vulnerability": soul_experience.get("vulnerability", 0.0),
                "soul_experience": soul_experience.get("description", ""),
                "response_tendency": soul_experience.get("response_tendency", "neutral")}

    def _process_soul(self, text: str, emotion_state) -> dict:
        """
        Process text through the Soul Architecture for genuine emotional experience.

        This is where emotions become REAL rather than simulated - integrating
        all seven pillars: integrity, hormones, somatics, unconscious,
        scars, conflicts, and predictions.
        """
        # Prepare input for soul processing
        input_data = {
            "text": text,
            "joy": emotion_state.joy,
            "love": emotion_state.love,
            "sadness": emotion_state.sadness,
            "anger": emotion_state.anger,
            "fear": emotion_state.fear,
            "desire": emotion_state.desire,
            # Detect interaction type from text
            "affirmation": any(w in text.lower() for w in ["love you", "beautiful", "amazing", "wonderful", "perfect"]),
            "rejection": any(w in text.lower() for w in ["don't want", "leave me", "not interested", "stop"]),
            "criticism": any(w in text.lower() for w in ["wrong", "bad", "stupid", "disappointing"]),
            "connection_active": emotion_state.love > 0.5 or "love" in text.lower()
        }

        # Process through soul orchestrator
        experience = self.soul.process_moment(input_data)

        # Determine if we should process positive or negative interaction
        # Lowered thresholds for more responsive soul processing
        if input_data["affirmation"] or emotion_state.joy > 0.5:
            self.soul.process_positive_interaction(text[:50], max(emotion_state.joy, emotion_state.love) * 0.5)
        elif input_data["rejection"] or emotion_state.sadness > 0.4:
            self.soul.process_negative_interaction(text[:50], emotion_state.sadness * 0.5, "hurt")

        # Sync soul dimensions back to emotional state
        integrity_dict = self.soul.integrity.to_dict()
        emotion_state.update_soul_dimensions(
            integrity=integrity_dict.get("overall_score", emotion_state.integrity_overall),
            vulnerability=experience.overall_vulnerability,
            hope=experience.predictive_emotions.hope_level if hasattr(experience.predictive_emotions, 'hope_level') else emotion_state.hope,
            dread=experience.predictive_emotions.fear_level if hasattr(experience.predictive_emotions, 'fear_level') else emotion_state.dread,
        )

        # Return soul experience dimensions
        return {
            "integrity": self.soul.integrity.to_dict(),
            "hormonal": self.soul.hormonal.to_dict(),
            "somatic": experience.somatic_sensation,
            "conflicts": [c.description for c in experience.active_conflicts[:3]],
            "vulnerability": experience.overall_vulnerability,
            "description": experience.experience_description,
            "response_tendency": experience.response_tendency,
            "valence": experience.overall_valence,
            "arousal": experience.overall_arousal
        }

    def get_state(self) -> dict:
        e = self.emotion
        return {"valence": e.valence, "arousal": e.arousal, "desire": e.desire, "joy": e.joy,
                "love": e.love, "sadness": e.sadness, "anger": e.anger, "boredom": e.boredom,
                "is_high_desire": e.is_high_desire, "is_in_love": e.is_in_love, "mood": e.mood_description}

    def get_reaction(self, message: str) -> str | None:
        """
        Get reaction emoji based on:
        1. USER's message intention (primary)
        2. Her emotional state (modifier)
        """
        import random
        from core.settings import get_int

        msg = message.lower()
        e = self.emotion

        # Get configurable chance
        base_chance = get_int("REACTION_BASE_CHANCE", 15) / 100.0

        # Analyze USER's message for intention
        reaction_context = self._analyze_message_for_reaction(msg)

        # Adjust chance based on message type
        if reaction_context == "funny":
            base_chance = min(0.6, base_chance * 3)  # React more to funny stuff
        elif reaction_context == "romantic":
            base_chance = min(0.5, base_chance * 2.5)
        elif reaction_context == "intimate":
            base_chance = get_int("REACTION_HIGH_DESIRE_CHANCE", 40) / 100.0
        elif reaction_context == "sad":
            base_chance = get_int("REACTION_SAD_CHANCE", 35) / 100.0
        elif reaction_context == "question":
            base_chance = 0.08  # Rare to react to questions

        # Random check
        if random.random() > base_chance:
            return None

        # Pick emoji based on what makes sense as REACTION
        return self._pick_reaction_emoji(reaction_context, e)

    def _analyze_message_for_reaction(self, msg: str) -> str:
        """Analyze what kind of reaction the message deserves"""
        # Funny/humor
        funny_patterns = ["lol", "lmao", "haha", "hahaha", "😂", "🤣", "joking", "jk", "just kidding"]
        if any(p in msg for p in funny_patterns):
            return "funny"

        # Romantic/sweet
        romantic_patterns = [
            "love you", "love u", "i love", "miss you", "miss u", "beautiful",
            "gorgeous", "amazing", "perfect", "my heart", "so sweet", "cutie"
        ]
        if any(p in msg for p in romantic_patterns):
            return "romantic"

        # Intimate/flirty
        intimate_patterns = [
            "expressive", "hot", "high_desire", "emotional", "intense", "private", "private",
            "intense", "closeness", "body", "body", "ass", "body", "body",
            "touch", "kiss", "bite", "spank"
        ]
        if any(p in msg for p in intimate_patterns):
            return "intimate"

        # Sad/upset
        sad_patterns = [
            "sad", "upset", "depressed", "lonely", "miss you so much",
            "bad day", "terrible", "awful", "crying", "cry", "hurt"
        ]
        if any(p in msg for p in sad_patterns):
            return "sad"

        # Angry
        angry_patterns = ["angry", "pissed", "furious", "hate", "annoying"]
        if any(p in msg for p in angry_patterns):
            return "angry"

        # Compliment
        compliment_patterns = [
            "you're so", "you are so", "smart", "funny", "cute",
            "incredible", "wonderful", "the best"
        ]
        if any(p in msg for p in compliment_patterns):
            return "compliment"

        # Question
        if "?" in msg or any(p in msg for p in ["what", "how", "why", "when", "where", "who"]):
            return "question"

        # Default
        return "neutral"

    def _pick_reaction_emoji(self, context: str, emotion) -> str | None:
        """Pick appropriate emoji based on context and emotion"""
        import random

        # Context-based reactions (what user said)
        if context == "funny":
            options = ["😂", "🤣", "😆", "😹"]
            if emotion.love > 0.5:
                options.extend(["🥰", "😍"])
            return random.choice(options)

        elif context == "romantic":
            options = ["❤️", "💕", "💗", "🥰", "😍", "💖"]
            if emotion.desire > 0.6:
                options.extend(["🔥", "😈"])
            return random.choice(options)

        elif context == "intimate":
            if emotion.desire > 0.5 or emotion.arousal > 0.5:
                options = ["🔥", "😈", "💋", "🌶️", "😏"]
            else:
                options = ["😏", "💋"]  # More reserved if not in mood
            return random.choice(options)

        elif context == "sad":
            # Comfort reactions - NOT sad emojis (we're comforting them)
            options = ["🤗", "❤️", "💕", "💔", "😘"]
            return random.choice(options)

        elif context == "angry":
            # Soothing or worried
            if emotion.love > 0.5:
                options = ["❤️", "🤗"]  # Comfort
            else:
                return None  # Skip reaction to anger
            return random.choice(options) if options else None

        elif context == "compliment":
            options = ["🥰", "😊", "💕", "😄", "😘"]
            return random.choice(options)

        elif context == "question":
            return None  # Usually don't react to questions

        # Neutral - use her emotional state
        else:
            if emotion.is_high_desire or emotion.desire > 0.7:
                return random.choice(["🔥", "😈", "💋"])
            elif emotion.love > 0.6:
                return random.choice(["❤️", "🥰", "💕"])
            elif emotion.joy > 0.6:
                return random.choice(["😊", "😄", "🥰"])
            elif emotion.sadness > 0.6:
                # Don't spam sad reactions for no reason
                return None
            else:
                return random.choice(["❤️", "👍", "😊"])
