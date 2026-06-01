"""
Brain: Subconscious - Response Analyzer
Analyzes user replies to determine sentiment for learning/goal systems
"""

_POSITIVE_WORDS = {
    "haha", "lol", "love", "yes", "yeah", "yess", "omg", "amazing", "perfect",
    "cute", "aww", "miss", "want", "need", "beautiful", "gorgeous", "funny",
    "thanks", "thank", "sweet", "babe", "baby", "honey", "darling", "amore",
    "happy", "glad", "great", "awesome", "wow", "nice", "good", "best",
}

_NEGATIVE_WORDS = {
    "stop", "no", "nah", "whatever", "bye", "leave", "annoying", "boring",
    "shut", "enough", "tired", "busy", "later", "not now", "don't",
}

_INTIMATE_WORDS = {
    "feel", "feelings", "love", "heart", "soul", "deep", "connection",
    "trust", "forever", "future", "dream", "afraid", "scared", "honest",
    "vulnerable", "mean to me", "important", "special", "serious",
}


def analyze_response(text: str) -> dict:
    """Analyze a user's reply — returns sentiment, response_type, and topic signals"""
    if not text:
        return {"sentiment": 0.0, "type": "empty", "is_positive": False,
                "is_intimate": False, "is_dismissal": False}

    lower = text.lower()
    words = set(lower.split())

    pos_count = len(words & _POSITIVE_WORDS)
    neg_count = len(words & _NEGATIVE_WORDS)
    intimate_count = len(words & _INTIMATE_WORDS)

    is_short = len(text) < 10
    is_long = len(text) > 50
    has_question = "?" in text
    has_emoji = any(ord(c) > 127 for c in text)

    # Score sentiment -1 to 1
    sentiment = 0.0
    sentiment += pos_count * 0.2
    sentiment -= neg_count * 0.25
    if is_long:
        sentiment += 0.15
    if has_question:
        sentiment += 0.1
    if has_emoji:
        sentiment += 0.1
    if is_short and neg_count > 0:
        sentiment -= 0.2

    sentiment = max(-1.0, min(1.0, sentiment))

    # Classify response type
    if is_short and neg_count > 0:
        resp_type = "dismissal"
    elif pos_count > 0 or is_long or has_question:
        resp_type = "engaged"
    elif is_short:
        resp_type = "brief"
    else:
        resp_type = "neutral"

    return {
        "sentiment": sentiment,
        "type": resp_type,
        "is_positive": sentiment > 0.2,
        "is_intimate": intimate_count >= 2,
        "is_dismissal": resp_type == "dismissal",
    }
