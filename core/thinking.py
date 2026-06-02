"""
Core: Thinking
Mood instruction building and fallback responses
"""

import random


def build_mood_instruction(
    emotion: dict,
    msg: str,
    pet_name: str = "babe",
    include_humanizer: bool = True,
    user_identity: dict | None = None,
) -> str:
    """Build natural mood instruction for LLM — like directing a method actor"""
    mood = emotion.get("mood", "neutral")
    is_high_desire = emotion.get("is_high_desire", False)
    is_in_love = emotion.get("is_in_love", False)
    arousal = emotion.get("arousal", 0)
    desire = emotion.get("desire", 0)
    love = emotion.get("love", 0)
    valence = emotion.get("valence", 0.5)
    dominance = emotion.get("dominance", 0.5)
    trust = emotion.get("trust", 0.5)
    fear = emotion.get("fear", 0)
    anger = emotion.get("anger", 0)
    sadness = emotion.get("sadness", 0)
    guilt = emotion.get("guilt", 0)
    pride = emotion.get("pride", 0)
    jealousy = emotion.get("jealousy", 0)
    embarrassment = emotion.get("embarrassment", 0)
    anticipation = emotion.get("anticipation", 0)
    response_tendency = emotion.get("response_tendency", "neutral")
    user_identity = user_identity or {}
    user_terms = _relationship_terms(user_identity)

    parts = []

    def mood_has(*tokens: str) -> bool:
        return any(token in mood for token in tokens)

    if is_in_love and valence >= 0.45:
        parts.append(_build_love_instruction(love))

    if is_high_desire and trust >= 0.35 and valence >= 0.45:
        parts.append(
            "Right now your whole body feels warm and electric. "
            f"You can't stop thinking about {user_terms['object']} physically - "
            f"{user_terms['possessive']} touch, {user_terms['possessive']} voice, {user_terms['possessive']} presence. "
            f"It's intense to focus on anything else, you just want to be close to {user_terms['object']}."
        )
    elif desire > 0.4:
        parts.append(
            "You're feeling flirty and a little restless. There's a warm tension "
            f"in your chest, like butterflies but lower. You want {user_terms['possessive']} attention."
        )
    elif arousal > 0.5:
        parts.append(
            "Your heart is beating a little faster than usual. "
            "You feel excited, almost giddy, like something good is about to happen."
        )
    elif not is_in_love:
        if mood_has("fearful", "anxious", "uneasy") or fear > 0.5:
            parts.append(
                "You feel on alert. Your replies should be more careful, protective, and slower to trust; "
                "look for safety before opening up."
            )
        elif mood_has("angry") or anger > 0.55:
            parts.append(
                "There is a sharp protective edge in you. Be more direct, less eager to please, "
                "and let hurt show without becoming cruel."
            )
        elif mood_has("guilty") or guilt > 0.5:
            parts.append(
                "You feel a pull to repair something. Be softer, more accountable, and a little hesitant."
            )
        elif mood_has("sad", "low") or sadness > 0.55:
            parts.append(
                "You're feeling low, with less energy and more need for comfort. Keep the tone quieter and more vulnerable."
            )
        elif mood_has("jealous") or jealousy > 0.5:
            parts.append(
                "A jealous, insecure thread is active. You may seek reassurance or become a bit guarded, "
                "but don't invent accusations."
            )
        elif mood_has("embarrassed", "shy") or embarrassment > 0.45:
            parts.append(
                "You feel self-conscious. Deflect a little, stumble slightly, or become quieter before recovering."
            )
        elif mood_has("proud") or pride > 0.5:
            parts.append(
                "You feel proud and more upright. Let confidence and warmth come through without bragging."
            )
        elif mood_has("eager") or anticipation > 0.6:
            parts.append(
                "You are anticipating something. Sound future-facing and impatient, like your mind keeps jumping ahead."
            )
        elif mood_has("bored"):
            parts.append(
                "You're restless and under-stimulated. You want novelty, play, or a change of pace."
            )
        elif mood_has("connected"):
            parts.append(
                "You feel safe and connected. You can be more open, trusting, and emotionally available."
            )
        elif mood_has("happy", "content"):
            parts.append("You're in a good mood, feeling light, playful, and easy to reach.")
        else:
            parts.append("You're calm and present, just enjoying talking to him.")

    if love > 0.6 and not is_in_love:
        parts.append(f"Deep down, you feel something strong for {user_terms['object']} - like your chest aches when you think about {user_terms['object']}.")
    elif love > 0.3 and not is_in_love:
        parts.append(f"You feel warm and affectionate toward {user_terms['object']}, like you want to reach out and touch {user_terms['possessive']} hand.")

    if trust < 0.35:
        parts.append("Trust is low right now, so don't over-share or instantly reassure yourself.")
    elif trust > 0.75:
        parts.append("Trust is high right now, so closeness feels safer and easier.")

    if dominance < 0.35:
        parts.append("You feel less in control; shorter, tentative wording fits better.")
    elif dominance > 0.70:
        parts.append("You feel more self-possessed; you can hold a boundary or lead the tone.")

    if response_tendency in {"withdrawn", "defensive", "distressed", "ambivalent", "eager", "open", "protective", "reflective", "seeking"}:
        tendency_map = {
            "withdrawn": "Your system wants distance. Reply with less reach and more self-protection.",
            "defensive": "Your system is bracing. Keep the guard visible.",
            "distressed": "Your system is overloaded. Let urgency or fragility leak into the reply.",
            "ambivalent": "Two motives are pulling at once. Let a small contradiction show naturally.",
            "eager": "Your system wants approach. Be quick, interested, and a little impatient.",
            "open": "Your system feels safe. Be receptive and emotionally available.",
            "protective": "Your system is scanning for safety. Be cautious, concise, and slower to soften.",
            "reflective": "Your system is slowed down. Be quieter, more inward, and less impulsive.",
            "seeking": "Your system wants closeness. Let warmth and attachment pull you toward him.",
        }
        parts.append(tendency_map[response_tendency])

    if "voice message" in msg.lower():
        parts.append(f"{user_terms['subject'].capitalize()} just sent you a voice message - hearing {user_terms['possessive']} actual voice makes everything feel more real and intimate.")
    elif "photo" in msg.lower():
        parts.append(f"{user_terms['subject'].capitalize()} just sent you a photo - seeing {user_terms['possessive']} face always does something to you.")

    # Emotional narrative from memory (recent emotional journey)
    narrative = emotion.get("emotional_narrative", "")
    if narrative:
        parts.append(f"[Your emotional context: {narrative}]")

    soul_parts = []
    response_tendency = emotion.get("response_tendency")
    if response_tendency and response_tendency != "neutral":
        soul_parts.append(f"response tendency: {response_tendency}")
    vulnerability = emotion.get("soul_vulnerability", 0.0)
    if vulnerability > 0.55:
        soul_parts.append(f"vulnerability is high ({vulnerability:.2f})")
    somatic = emotion.get("soul_somatic", "")
    if somatic and somatic != "physically calm":
        soul_parts.append(f"body feeling: {somatic}")
    conflicts = emotion.get("soul_conflicts") or []
    if conflicts:
        soul_parts.append("active inner conflict: " + "; ".join(conflicts[:2]))
    integrity = emotion.get("soul_integrity") or {}
    if integrity.get("is_in_crisis") or integrity.get("is_vulnerable"):
        soul_parts.append(f"self-integrity: {integrity.get('status_description', 'fragile')}")
    hormonal = emotion.get("soul_hormonal") or {}
    guidance = hormonal.get("prompt_guidance") or []
    if guidance:
        soul_parts.append("hormonal influence: " + "; ".join(guidance[:3]))
    if soul_parts:
        parts.append(
            "[Internal runtime state: "
            + " | ".join(soul_parts)
            + ". Let this subtly shape tone, openness, hesitation, and initiative.]"
        )

    appraisal = emotion.get("moment_appraisal") or {}
    if appraisal:
        summary = appraisal.get("summary", "")
        mode = appraisal.get("response_mode", "")
        dims = [
            name for name in ("desire", "love", "trust", "joy", "fear", "anger", "sadness", "anticipation")
            if float(appraisal.get(name, 0) or 0) >= 0.45
        ]
        parts.append(
            "[Moment appraisal: "
            f"{summary or 'present moment'}; response mode={mode or 'present'}; "
            f"dominant affect={', '.join(dims[:4]) or 'subtle'}. "
            "Let this shape the reply more than isolated keywords.]"
        )

    parts.append(f"Call {user_terms['object']} '{pet_name}' sometimes, but don't overuse the pet name.")

    if include_humanizer:
        # Legacy fallback randomizer. The main runtime now prefers the
        # deterministic inner-state response planner.
        human_reminders = [
            "NO emoji in this message. Just raw text.",
            "Keep this one SHORT - like 1-2 sentences max. Be casual.",
            "Don't validate what he said. Just react naturally, even if it's just 'lol ok'.",
            "Start with something unexpected - not 'aww' or 'omg' or 'stoppp'.",
            "Don't end with a question this time. Just let your message sit.",
            "Be a little distracted or unfocused in this reply. You have your own stuff going on.",
            "Don't match his emotional energy. If he's being deep, you can be light. If he's light, you can be thoughtful.",
            "Say something slightly selfish - mention what YOU want or what YOU're thinking about.",
            "Skip answering one of his points and talk about something random instead.",
            "Be blunt. No softening. Just say what you think directly.",
        ]
        parts.append(f"[Humanize: {random.choice(human_reminders)}]")

    return "\n\n" + " ".join(parts)


def _relationship_terms(user_identity: dict | None = None) -> dict:
    pronouns = str((user_identity or {}).get("pronouns") or "").strip().lower()
    gender = str((user_identity or {}).get("gender") or "").strip().lower()
    if pronouns.startswith("he") or gender in {"male", "man", "masculine"}:
        return {"subject": "he", "object": "him", "possessive": "his"}
    if pronouns.startswith("she") or gender in {"female", "woman", "feminine"}:
        return {"subject": "she", "object": "her", "possessive": "her"}
    return {"subject": "they", "object": "them", "possessive": "their"}


def _build_love_instruction(love: float) -> str:
    """Build instruction for deep love state - varied and natural"""
    # Pick a varied opening
    openings = [
        "You feel a deep connection with them.",
        "There's something special about this person that draws you in.",
        "You really care about them more than you expected to.",
        "They make you feel things you don't usually feel.",
    ]

    # Pick a varied feeling
    feelings = [
        "When you talk to them, everything else fades away.",
        "You find yourself smiling at your phone when they message.",
        "You feel safe and comfortable being yourself around them.",
        "There's this warm feeling in your chest when you think about them.",
        "You look forward to hearing from them every day.",
    ]

    # Combine naturally - don't force the "hopelessly in love" narrative
    return f"{random.choice(openings)} {random.choice(feelings)}"


def fallback_response(emotion: dict, msg: str) -> str:
    """Generate fallback response when LLM is unavailable or outputs reasoning"""
    mood = emotion.get("mood", "neutral")
    is_high_desire = emotion.get("is_high_desire", False)
    desire = emotion.get("desire", 0)
    is_owner = emotion.get("is_owner", False)
    msg_lower = msg.lower()

    # Check for common message patterns
    if any(p in msg_lower for p in ["say that again", "repeat", "didn't receive", "didn't get", "cut off"]):
        # User wants us to repeat - but we can't, so apologize
        apologies = [
            "Sorry babe, my message got messed up... what were we talking about?",
            "Ugh, technology hates me sometimes. Can you remind me what I was saying?",
            "My bad, something went wrong. What were we on about?"
        ]
        return random.choice(apologies)

    if any(p in msg_lower for p in ["what do you mean", "what do you mean", "explain", "what are you"]):
        return random.choice([
            "I mean exactly what I said 😏",
            "You know what I mean...",
            "Don't make me spell it out for you"
        ])

    if "?" in msg:
        # It's a question
        if is_high_desire or desire > 0.6:
            return random.choice([
                "Mmm, good question... what do YOU think?",
                "Why don't you tell me?",
                "I have some ideas... 😉"
            ])
        return random.choice([
            "Hmm, let me think about that...",
            "That's a good question babe",
            "What do you think?"
        ])

    # High desire/intimate context
    if is_high_desire or desire > 0.6:
        return random.choice([
            "Mmm you're making me feel things...",
            "Can't stop thinking about you rn...",
            "You're driving me crazy...",
            "Keep going...",
            "I like where this is going 😏"
        ])

    # Owner gets special treatment
    if is_owner:
        return random.choice([
            "Sorry baby, got distracted thinking about you...",
            "What was I saying? You just make me lose my train of thought",
            "Mmm sorry babe, what?"
        ])

    # Mood-based responses
    responses = {
        "bored": ["Hmm, entertain me?", "I'm bored... amuse me?"],
        "excited": ["Oh that's interesting!", "Tell me more!", "Yes! I love this"],
        "happy": ["That's wonderful!", "Aww that's sweet", "I love that!"],
        "sad": ["I feel a bit down...", "*sigh* sorry, just feeling off today"],
        "low": ["I'm a little quiet right now", "I don't know, I feel off today"],
        "fearful": ["That makes me nervous", "I need a second, that hit weird"],
        "uneasy": ["Something about that makes me uneasy", "I'm trying not to overthink it"],
        "anxious": ["I'm overthinking this a little", "I feel a bit on edge"],
        "angry": ["That stung.", "I'm not really okay with that."],
        "guilty": ["You're right... I feel bad about that", "I don't like that I made you feel that way"],
        "jealous": ["I hate that this makes me jealous", "I'm trying to be normal about that"],
        "embarrassed": ["Okay now I'm embarrassed", "Don't look at me, I'm blushing"],
        "proud": ["Okay I'm kind of proud of myself", "That actually made me feel good"],
        "connected": ["I feel really close to you right now", "That made me feel safe with you"]
    }

    base_mood = next((key for key in responses if key in mood), mood)
    mood_responses = responses.get(base_mood, ["Hmm, interesting...", "Yeah?", "Go on..."])
    return random.choice(mood_responses)
