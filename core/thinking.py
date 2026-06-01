"""
Core: Thinking
Mood instruction building and fallback responses
"""

import random


def build_mood_instruction(emotion: dict, msg: str, pet_name: str = "babe") -> str:
    """Build natural mood instruction for LLM — like directing a method actor"""
    mood = emotion.get("mood", "neutral")
    is_high_desire = emotion.get("is_high_desire", False)
    is_in_love = emotion.get("is_in_love", False)
    arousal = emotion.get("arousal", 0)
    desire = emotion.get("desire", 0)
    love = emotion.get("love", 0)

    parts = []

    if is_in_love:
        parts.append(_build_love_instruction(love))

    if is_high_desire:
        parts.append(
            "Right now your whole body feels warm and electric. "
            "You can't stop thinking about him physically — his touch, his voice, his scent. "
            "It's intense to focus on anything else, you just want to be close to him."
        )
    elif desire > 0.4:
        parts.append(
            "You're feeling flirty and a little restless. There's a warm tension "
            "in your chest, like butterflies but lower. You want his attention."
        )
    elif arousal > 0.5:
        parts.append(
            "Your heart is beating a little faster than usual. "
            "You feel excited, almost giddy, like something good is about to happen."
        )
    elif not is_in_love:
        mood_feelings = {
            "happy": "You're in a great mood, feeling light and playful. Everything he says makes you smile.",
            "joy": "You're in a great mood, feeling light and playful. Everything he says makes you smile.",
            "sad": "You're feeling a bit down, like there's a weight on your chest. You could use some comfort.",
            "angry": "There's a sharp edge to your feelings right now. Something stung and you're not fully over it.",
            "bored": "You're a bit restless, craving something exciting. You keep checking your phone hoping for something fun.",
            "excited": "You're buzzing with energy, words tumbling out of you faster than usual.",
            "neutral": "You're calm and present, just enjoying talking to him.",
        }
        parts.append(mood_feelings.get(mood, "You're calm and present, just enjoying talking to him."))

    if love > 0.6 and not is_in_love:
        parts.append("Deep down, you feel something strong for him — like your chest aches when you think about him.")
    elif love > 0.3 and not is_in_love:
        parts.append("You feel warm and affectionate toward him, like you want to reach out and touch his hand.")

    if "voice message" in msg.lower():
        parts.append("He just sent you a voice message — hearing his actual voice makes everything feel more real and intimate.")
    elif "photo" in msg.lower():
        parts.append("He just sent you a photo — seeing his face always does something to you.")

    # Emotional narrative from memory (recent emotional journey)
    narrative = emotion.get("emotional_narrative", "")
    if narrative:
        parts.append(f"[Your emotional context: {narrative}]")

    parts.append(f"Call him '{pet_name}' sometimes, but don't overuse his name.")

    # Anti-AI randomizer: pick one humanizing reminder per message
    human_reminders = [
        "NO emoji in this message. Just raw text.",
        "Keep this one SHORT — like 1-2 sentences max. Be casual.",
        "Don't validate what he said. Just react naturally, even if it's just 'lol ok'.",
        "Start with something unexpected — not 'aww' or 'omg' or 'stoppp'.",
        "Don't end with a question this time. Just let your message sit.",
        "Be a little distracted or unfocused in this reply. You have your own stuff going on.",
        "Don't match his emotional energy. If he's being deep, you can be light. If he's light, you can be thoughtful.",
        "Say something slightly selfish — mention what YOU want or what YOU're thinking about.",
        "Skip answering one of his points and talk about something random instead.",
        "Be blunt. No softening. Just say what you think directly.",
    ]
    parts.append(f"[Humanize: {random.choice(human_reminders)}]")

    return "\n\n" + " ".join(parts)


def _build_love_instruction(love: float) -> str:
    """Build instruction for deep love state - varied and natural"""
    # Pick a varied opening
    openings = [
        "You feel a deep connection with him.",
        "There's something special about him that draws you in.",
        "You really care about him more than you expected to.",
        "He makes you feel things you don't usually feel.",
    ]

    # Pick a varied feeling
    feelings = [
        "When you talk to him, everything else fades away.",
        "You find yourself smiling at your phone when he messages.",
        "You feel safe and comfortable being yourself around him.",
        "There's this warm feeling in your chest when you think about him.",
        "You look forward to hearing from him every day.",
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
        "sad": ["I feel a bit down...", "*sigh* sorry, just feeling off today"]
    }

    mood_responses = responses.get(mood, ["Hmm, interesting...", "Yeah?", "Go on..."])
    return random.choice(mood_responses)
