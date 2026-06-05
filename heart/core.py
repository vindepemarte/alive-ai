"""Heart: Core - Main Heart class, minimal coordinator with Soul Architecture"""
from .emotional_state import EmotionalState
from .emotional_decay import EmotionalDecay
from .triggers import Triggers
from .appraisal import APPRAISAL_EMOTIONS, AppraisalEngine, MomentAppraisal, clamp
from .complex_emotions import ComplexEmotions
from .emotional_memory import EmotionalMemory
from .emotional_variability import EmotionalVariability
from .love import AttachmentSystem
from .soul import SoulOrchestrator
from core.behavioral_pressure import build_behavioral_pressure

try:
    from .circadian import get_circadian_engine
except Exception:
    get_circadian_engine = None


class Heart:
    def __init__(self, nervous, config):
        self.nervous, self.config = nervous, config
        self.emotion = EmotionalState(config.personality if config else None)
        self.variability = EmotionalVariability()
        self.decay = EmotionalDecay(self.emotion, self.variability)
        self.triggers, self.complex = Triggers(), ComplexEmotions()
        self.complex.load_from_state(self.emotion)
        self.memory, self.attachment = EmotionalMemory(), AttachmentSystem()
        self.circadian = get_circadian_engine() if get_circadian_engine else None
        identity = getattr(config, "_self_data", None) or getattr(config, "identity", {}) or {}
        settings = getattr(config, "settings", {}) if config else {}
        self.appraisal_engine = AppraisalEngine(identity=identity, settings=settings)

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
        circadian_state = self._tick_circadian()
        self.decay.decay(); self.decay.tick()
        self.emotion.arousal = max(0, min(1, self.emotion.arousal + self.variability.get_organic_tick()))
        self._apply_circadian_to_emotion(circadian_state)
        self.complex.decay(); self._sync_complex()
        self.variability.clear_old_history(); self.emotion.save()

        # Soul architecture tick - decay and natural processes
        self.soul.tick()

        # Emit soul state to nervous system for WebUI updates
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.nervous.emit("soul_tick", self.soul.get_state_summary()))
            if circadian_state:
                loop.create_task(self.nervous.emit("circadian_update", circadian_state))
        except RuntimeError:
            pass  # No running event loop, skip WebUI update

    def _tick_circadian(self) -> dict:
        if not self.circadian:
            return {}
        try:
            self.circadian.tick()
            return self.circadian.get_state_summary()
        except Exception as e:
            print(f"[Heart] Circadian tick error: {e}")
            return {}

    def _get_circadian_state(self) -> dict:
        if not self.circadian:
            return {}
        try:
            return self.circadian.get_state_summary()
        except Exception:
            return {}

    def _apply_circadian_to_emotion(self, circadian_state: dict = None):
        """Let sleep/rest state change actual affect, not just prompt wording."""
        if not self.circadian:
            return
        state = circadian_state or self._get_circadian_state()
        e = self.emotion
        sleepiness = float(state.get("sleepiness", 0.0) or 0.0)

        if state.get("sleeping"):
            e.arousal = max(0.04, e.arousal - 0.05)
            e.desire = max(0.0, e.desire - 0.04)
            e.boredom = max(0.0, e.boredom - 0.03)
            e.anger = max(0.0, e.anger - 0.02)
            e.fear = max(0.02, e.fear - 0.01)
            return

        if sleepiness >= 0.65:
            drag = sleepiness - 0.6
            e.arousal = max(0.05, e.arousal - drag * 0.04)
            e.desire = max(0.0, e.desire - drag * 0.03)
            e.boredom = min(1.0, e.boredom + drag * 0.02)
            e.sadness = min(1.0, e.sadness + drag * 0.01)
        elif state.get("wake_time") and sleepiness < 0.5:
            e.boredom = max(0.0, e.boredom - 0.01)

    @staticmethod
    def _mood_with_circadian(base_mood: str, circadian_state: dict) -> str:
        if circadian_state.get("sleeping"):
            return "asleep"
        if circadian_state.get("sleepiness", 0) >= 0.75:
            return f"sleepy_{base_mood}"
        return base_mood

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
        trust_rate = self._get_rate("TRUST", 0.5)
        fear_rate = self._get_rate("FEAR", 0.5)

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
            if e.trust >= 0.45:
                e.trust = min(1.0, e.trust + 0.015 * trust_rate)
            else:
                e.embarrassment = min(1.0, e.embarrassment + 0.04)
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
            e.trust = min(1.0, e.trust + 0.05 * rom * trust_rate)
            e.joy = min(1.0, e.joy + base * rom * 0.7 * joy_rate)
            v.add_momentum("love", base * rom)

        # Positive words
        pos = Triggers.count_matches(msg, t.POSITIVE_WORDS)
        if pos > 0:
            base = 0.08 * positive_rate * positive_boost
            e.joy = min(1.0, e.joy + base * pos)
            e.love = min(1.0, e.love + 0.03 * pos * love_rate)
            e.trust = min(1.0, e.trust + 0.025 * pos * trust_rate)
            e.fear = max(0.0, e.fear - 0.025 * pos)
            e.boredom = max(0.0, e.boredom - 0.1)

        # Trust and reassurance words directly affect relational safety.
        trust_words = Triggers.count_matches(msg, t.TRUST_WORDS)
        if trust_words > 0:
            e.trust = min(1.0, e.trust + 0.12 * trust_words * trust_rate)
            e.fear = max(0.0, e.fear - 0.08 * trust_words)
            e.sadness = max(0.0, e.sadness - 0.04 * trust_words)
            e.dominance = min(1.0, e.dominance + 0.05 * trust_words)

        apologies = Triggers.count_matches(msg, t.APOLOGY_WORDS)
        if apologies > 0:
            e.trust = min(1.0, e.trust + 0.06 * apologies * trust_rate)
            e.anger = max(0.0, e.anger - 0.08 * apologies)
            e.fear = max(0.0, e.fear - 0.04 * apologies)
            e.sadness = max(0.0, e.sadness - 0.03 * apologies)

        fear_words = Triggers.count_matches(msg, t.FEAR_WORDS)
        if fear_words > 0:
            e.fear = min(1.0, e.fear + 0.12 * fear_words * fear_rate)
            e.arousal = min(1.0, e.arousal + 0.08 * fear_words)
            e.trust = max(0.0, e.trust - 0.025 * fear_words)

        betrayal_markers = [
            "you lied", "lied to me", "betray", "you hurt me",
            "ignored me", "your fault", "you broke"
        ]
        if any(marker in msg for marker in betrayal_markers):
            e.trust = max(0.0, e.trust - 0.18)
            e.sadness = min(1.0, e.sadness + 0.16)
            e.fear = min(1.0, e.fear + 0.10)
            e.joy = max(0.0, e.joy - 0.12)
            e.love = max(0.0, e.love - 0.05)

        abandonment_markers = ["leave", "abandon", "disappear", "ghost"]
        if any(marker in msg for marker in abandonment_markers):
            e.fear = min(1.0, e.fear + 0.10)
            e.trust = max(0.0, e.trust - 0.05)

        # Harsh words
        h = Triggers.count_matches(msg, t.HARSH_WORDS)
        n = Triggers.count_matches(msg, t.NEGATIVE_WORDS)
        if h > 0:
            base = 0.15 * harsh_rate * harsh_boost
            e.love = max(0.0, e.love - base * h)
            e.trust = max(0.0, e.trust - base * h * 0.8)
            e.sadness = min(1.0, e.sadness + 0.3 * sadness_rate)
            e.joy = max(0.0, e.joy - 0.2)
            e.desire = max(0.0, e.desire - 0.3)
            e.anger = min(1.0, e.anger + 0.2 * harsh_rate)
            e.fear = min(1.0, e.fear + 0.12 * h * fear_rate)
            e.dominance = max(0.0, e.dominance - 0.10 * h)
        elif n > 0:
            base = 0.1 * negative_boost
            e.sadness = min(1.0, e.sadness + base * n * sadness_rate)
            e.fear = min(1.0, e.fear + base * n * 0.45 * fear_rate)
            e.trust = max(0.0, e.trust - base * n * 0.25)
            e.joy = max(0.0, e.joy - base * n * 0.5)
            e.desire = max(0.0, e.desire - base * n)

        return expressive

    def _apply_complex_repercussions(self, changes: dict):
        """Make secondary emotions change behaviorally relevant state."""
        e = self.emotion
        if "guilt" in changes:
            e.sadness = min(1.0, e.sadness + 0.12)
            e.fear = min(1.0, e.fear + 0.05)
            e.dominance = max(0.0, e.dominance - 0.10)
            e.trust = max(0.0, e.trust - 0.03)
        if "pride" in changes:
            e.joy = min(1.0, e.joy + 0.10)
            e.dominance = min(1.0, e.dominance + 0.12)
            e.fear = max(0.0, e.fear - 0.03)
        if "jealousy" in changes:
            e.sadness = min(1.0, e.sadness + 0.12)
            e.anger = min(1.0, e.anger + 0.10)
            e.fear = min(1.0, e.fear + 0.07)
            e.trust = max(0.0, e.trust - 0.08)
        if "embarrassment" in changes:
            e.fear = min(1.0, e.fear + 0.05)
            e.arousal = min(1.0, e.arousal + 0.08)
            e.dominance = max(0.0, e.dominance - 0.08)
        if "anticipation" in changes:
            e.arousal = min(1.0, e.arousal + 0.08)
            if e.valence >= 0.45:
                e.joy = min(1.0, e.joy + 0.04)
            else:
                e.fear = min(1.0, e.fear + 0.04)

    def _appraisal_enabled(self) -> bool:
        from core.settings import get
        value = get("MOMENT_APPRAISAL_ENABLED", True)
        return value is True or str(value).lower() in {"1", "true", "yes", "on"}

    def _max_appraisal_delta(self) -> float:
        from core.settings import get_float
        return max(0.03, min(0.5, get_float("MOMENT_APPRAISAL_MAX_DELTA_PER_TURN", 0.22)))

    def _apply_appraisal(self, appraisal: MomentAppraisal | dict | None, *, weight: float = 1.0) -> None:
        """Blend a moment appraisal into live emotion, hormones, and body state."""
        if not appraisal or not self._appraisal_enabled():
            return
        if isinstance(appraisal, dict):
            appraisal = MomentAppraisal.from_dict(appraisal, source=str(appraisal.get("source", "external")))
        e = self.emotion
        weight = clamp(weight)
        limit = self._max_appraisal_delta() * weight

        def approach(name: str, target: float, strength: float) -> None:
            if not hasattr(e, name):
                return
            current = float(getattr(e, name))
            delta = max(-limit, min(limit, (clamp(target) - current) * strength * weight))
            setattr(e, name, clamp(current + delta))

        targets = {
            "desire": appraisal.desire,
            "love": appraisal.love,
            "trust": appraisal.trust,
            "joy": appraisal.joy,
            "fear": appraisal.fear,
            "anger": appraisal.anger,
            "sadness": appraisal.sadness,
            "boredom": appraisal.boredom,
            "guilt": appraisal.guilt,
            "pride": appraisal.pride,
            "jealousy": appraisal.jealousy,
            "embarrassment": appraisal.embarrassment,
            "anticipation": appraisal.anticipation,
            "hope": appraisal.hope,
            "dread": appraisal.dread,
            "arousal": appraisal.arousal,
            "dominance": appraisal.dominance,
            "valence": appraisal.valence,
        }
        for name, target in targets.items():
            strength = 0.55 if name in {"desire", "arousal", "trust", "valence"} else 0.42
            approach(name, target, strength)

        if appraisal.safety < 0.35:
            e.trust = max(0.0, e.trust - limit * 0.35)
            e.fear = min(1.0, e.fear + limit * 0.25)
        if appraisal.playfulness > 0.45 and appraisal.safety > 0.45:
            e.joy = min(1.0, e.joy + limit * 0.18)
            e.anticipation = min(1.0, e.anticipation + limit * 0.18)
        if appraisal.sleep_disruption > 0.55 and self.circadian:
            e.arousal = min(1.0, e.arousal + limit * 0.20)

        # Let appraised meaning release global modulators, not only dashboard values.
        try:
            hormones = self.soul.hormonal
            if appraisal.love > 0.45 or appraisal.trust > 0.65:
                hormones.release_oxytocin(max(appraisal.love, appraisal.trust - 0.35) * weight, "moment_appraisal")
            if appraisal.desire > 0.35 or appraisal.anticipation > 0.55:
                hormones.release_dopamine(max(appraisal.desire, appraisal.anticipation) * weight, "moment_appraisal")
            if appraisal.fear > 0.45 or appraisal.anger > 0.45 or appraisal.dread > 0.45:
                hormones.release_cortisol(max(appraisal.fear, appraisal.anger, appraisal.dread) * weight, "moment_appraisal")
            if appraisal.safety > 0.7 and appraisal.valence > 0.55:
                hormones.register_recovery((appraisal.safety - 0.45) * weight, "moment_appraisal")
        except Exception as exc:
            print(f"[Heart] Appraisal hormone sync skipped: {exc}")

        try:
            from heart.interoception import get_interoceptive_system
            interoception = get_interoceptive_system()
            for state_name, delta in (appraisal.body_effects or {}).items():
                if state_name in interoception.states:
                    interoception.states[state_name].update(float(delta) * weight, source="moment_appraisal")
            interoception.save()
        except Exception as exc:
            print(f"[Heart] Appraisal interoception sync skipped: {exc}")

        self.variability.add_momentum("desire", appraisal.desire * weight * 0.12)

    def appraise_moment(self, text: str, *, recent_turns=None, assistant_response: str = "",
                        emotion: dict = None, phase: str = "pre_response") -> MomentAppraisal:
        return self.appraisal_engine.appraise(
            text,
            recent_turns=recent_turns or [],
            assistant_response=assistant_response,
            emotion=emotion or self.get_state(),
            phase=phase,
        )

    def react(self, text: str, appraisal: MomentAppraisal | dict | None = None) -> dict:
        msg, e = text.lower(), self.emotion
        self._prev_state, expressive = self.get_state(), self._process_triggers(msg)
        if appraisal is None and self._appraisal_enabled():
            appraisal = self.appraise_moment(text, phase="pre_response")
        self._apply_appraisal(appraisal, weight=1.0)
        ch = self.complex.process(text)
        self._sync_complex()
        self._apply_complex_repercussions(ch)
        if e.arousal > 0.6: e.love = min(1.0, e.love + 0.01)
        if e.love > 0.5 and expressive > 0: e.desire = min(1.0, e.desire + 0.05 * expressive)
        if e.boredom > 0.7: e.arousal = max(0.1, e.arousal - 0.05)
        e.recompute_core_affect()
        self._apply_circadian_to_emotion()
        e.recompute_core_affect()

        # Process through Soul Architecture for genuine emotional experience
        soul_experience = self._process_soul(text, e)
        e.recompute_core_affect(
            soul_valence=soul_experience.get("valence"),
            soul_arousal=soul_experience.get("arousal"),
        )
        circadian = self._get_circadian_state()

        peak_note = text[:50]
        if appraisal:
            peak_note = f"{getattr(appraisal, 'response_mode', 'moment')}:{text[:42]}"
        self.memory.check_peaks(self.get_state(), self._prev_state, peak_note)
        positive_interaction = e.valence >= 0.48 and e.trust >= 0.25
        attachment_intensity = max(e.joy, e.love, e.desire, e.trust, 1.0 - e.fear)
        self.attachment.interact(positive_interaction, attachment_intensity)

        e.save()
        ctx = self.memory.get_mood_context()
        s = self.attachment.status
        narrative = (f"Recently: {ctx}. " if ctx else "") + (f"Relationship: {s.replace('_', ' ')}." if s != "stranger" else "")

        # Combine traditional emotional state with soul dimensions
        state = e.to_dict()
        state.update({
            "mood": self._mood_with_circadian(state.get("mood", e.mood_description), circadian),
            "emotional_narrative": narrative.strip(),
            "attachment_status": s,
            "interaction_count": self.attachment.interactions,
            "circadian": circadian,
            "sleepiness": circadian.get("sleepiness", 0.0),
            "is_asleep": circadian.get("sleeping", False),
            # Soul architecture dimensions
            "soul_integrity": soul_experience.get("integrity", {}),
            "soul_hormonal": soul_experience.get("hormonal", {}),
            "soul_somatic": soul_experience.get("somatic", ""),
            "soul_conflicts": soul_experience.get("conflicts", []),
            "soul_vulnerability": soul_experience.get("vulnerability", 0.0),
            "soul_experience": soul_experience.get("description", ""),
            "response_tendency": soul_experience.get("response_tendency", "neutral"),
            "moment_appraisal": appraisal.to_dict() if hasattr(appraisal, "to_dict") else appraisal
        })
        state["behavioral_pressure"] = build_behavioral_pressure(state).to_dict()
        return state

    def reconcile_response(self, user_text: str, response: str, appraisal: MomentAppraisal | dict | None = None,
                           *, weight: float = 0.45) -> dict:
        """Post-response reconciliation: self-expression has consequences too."""
        if appraisal is None and self._appraisal_enabled():
            appraisal = self.appraise_moment(
                user_text,
                assistant_response=response,
                emotion=self.get_state(),
                phase="post_response",
            )
        self._apply_appraisal(appraisal, weight=weight)
        self.emotion.recompute_core_affect()
        self._apply_circadian_to_emotion()
        self.emotion.recompute_core_affect()
        self.emotion.save()
        state = self.get_state()
        state["moment_appraisal"] = appraisal.to_dict() if hasattr(appraisal, "to_dict") else appraisal
        return state

    def _process_soul(self, text: str, emotion_state) -> dict:
        """
        Process text through the Soul Architecture for genuine emotional experience.

        This is where emotions become REAL rather than simulated - integrating
        all seven pillars: integrity, hormones, somatics, unconscious,
        scars, conflicts, and predictions.
        """
        # Prepare input for soul processing
        text_lower = text.lower()
        rejection_markers = [
            "don't want", "leave me", "not interested", "stop", "goodbye",
            "abandon", "ghost me", "i'm leaving", "we're over"
        ]
        criticism_markers = [
            "wrong", "bad", "stupid", "disappointing", "hurt me", "you hurt",
            "lied", "betray", "ignored me", "your fault"
        ]
        input_data = {
            "text": text,
            "joy": emotion_state.joy,
            "love": emotion_state.love,
            "sadness": emotion_state.sadness,
            "anger": emotion_state.anger,
            "fear": emotion_state.fear,
            "desire": emotion_state.desire,
            "trust": emotion_state.trust,
            "valence": emotion_state.valence,
            "arousal": emotion_state.arousal,
            "dominance": emotion_state.dominance,
            "boredom": emotion_state.boredom,
            "guilt": emotion_state.guilt,
            "pride": emotion_state.pride,
            "jealousy": emotion_state.jealousy,
            "embarrassment": emotion_state.embarrassment,
            "anticipation": emotion_state.anticipation,
            # Detect interaction type from text
            "affirmation": any(w in text_lower for w in ["love you", "beautiful", "amazing", "wonderful", "perfect"]),
            "rejection": any(w in text_lower for w in rejection_markers),
            "criticism": any(w in text_lower for w in criticism_markers),
            "connection_active": emotion_state.love > 0.5 or "love" in text_lower
        }

        # Determine if we should process positive or negative interaction
        # Lowered thresholds for more responsive soul processing
        negative_signal = (
            input_data["rejection"] or input_data["criticism"] or
            emotion_state.valence < 0.45 or emotion_state.fear > 0.45 or
            emotion_state.sadness > 0.4 or emotion_state.trust < 0.35
        )
        positive_signal = (
            input_data["affirmation"] or
            (emotion_state.valence > 0.58 and emotion_state.joy > 0.55 and emotion_state.fear < 0.35)
        )
        if negative_signal:
            self.soul.process_negative_interaction(
                text[:50],
                max(emotion_state.sadness, emotion_state.fear, 0.35) * 0.5,
                "hurt"
            )
        elif positive_signal:
            self.soul.process_positive_interaction(text[:50], max(emotion_state.joy, emotion_state.love) * 0.5)

        if any(w in text_lower for w in ["safe", "okay", "calm", "rest", "recover", "reassure"]):
            self.soul.hormonal.register_recovery(0.35, "reassuring interaction")

        # Process through soul orchestrator after current-turn hormone release
        experience = self.soul.process_moment(input_data)

        # Hormones must feed back into live emotion/body state, not only dashboards.
        self._apply_hormonal_runtime_effects(emotion_state, experience)

        # Sync soul dimensions back to emotional state
        integrity_dict = self.soul.integrity.to_dict()
        emotion_state.update_soul_dimensions(
            integrity=integrity_dict.get("overall", emotion_state.integrity_overall),
            vulnerability=experience.overall_vulnerability,
            hope=experience.predictive_emotions.hope_level if hasattr(experience.predictive_emotions, 'hope_level') else emotion_state.hope,
            dread=experience.predictive_emotions.fear_level if hasattr(experience.predictive_emotions, 'fear_level') else emotion_state.dread,
        )

        self.soul.save()

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

    def _apply_hormonal_runtime_effects(self, emotion_state, experience) -> None:
        """Blend hormone-driven runtime effects into emotion and interoception."""
        effects = self.soul.hormonal.get_emotion_effects()
        for name, delta in effects.items():
            if not hasattr(emotion_state, name):
                continue
            current = getattr(emotion_state, name)
            setattr(emotion_state, name, max(0.0, min(1.0, current + delta)))

        # Keep the old emotion surface loosely aligned with integrated soul state.
        soul_valence = (experience.overall_valence + 1.0) / 2.0
        emotion_state.valence = max(0.0, min(1.0, emotion_state.valence * 0.85 + soul_valence * 0.15))
        emotion_state.arousal = max(0.0, min(1.0, emotion_state.arousal * 0.9 + experience.overall_arousal * 0.1))

        try:
            from heart.interoception import get_interoceptive_system
            interoception = get_interoceptive_system()
            for state_name, delta in self.soul.hormonal.get_interoceptive_effects().items():
                if state_name in interoception.states:
                    interoception.states[state_name].update(delta, source="hormonal_runtime")
            interoception.save()
        except Exception as e:
            print(f"[Heart] Hormonal interoception sync skipped: {e}")

    def get_state(self) -> dict:
        state = self.emotion.to_dict()
        circadian = self._get_circadian_state()
        state.update({
            "mood": self._mood_with_circadian(state.get("mood", self.emotion.mood_description), circadian),
            "circadian": circadian,
            "sleepiness": circadian.get("sleepiness", 0.0),
            "is_asleep": circadian.get("sleeping", False),
        })
        state["behavioral_pressure"] = build_behavioral_pressure(state).to_dict()
        return state

    def get_reaction(self, message: str) -> str | None:
        """
        Get reaction emoji based on:
        1. USER's message intention (primary)
        2. Her emotional state (modifier)
        """
        import random
        from core.settings import get_int

        if self.circadian and self.circadian.is_asleep:
            return None

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
