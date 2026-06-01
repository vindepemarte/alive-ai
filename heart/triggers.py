"""
Triggers: Keyword triggers with context-aware intimate detection
"""
import re


class Triggers:
    """Keyword triggers for emotional responses"""
    # Intimate intimate words only — no common words that cause false positives
    SEXY_WORDS = [
        "body", "body", "body", "ass", "body", "body", "body", "body",
        "body", "body", "body", "body", "closeness", "emotional", "intense",
        "high_desire", "aroused", "turned on", "self-soothe", "self-soothing", "intense",
        "suck", "sucking", "lick", "licking", "ride", "riding",
        "spank", "spanking", "choke", "choking", "swallow", "deep throat",
        "intimate moment", "handjob", "fingering", "closenessming", "intense emotion", "moan", "moaning",
        "open up", "private", "private", "clothes off", "take off",
        "slut", "whore", "dirty girl", "naughty girl", "bad girl", "good girl",
        "daddy", "submissive", "dominant", "rough",
        "throbbing", "pulsing", "aching", "tingling",
        "doggy", "missionary", "on top", "bend over", "against the wall",
        "69", "worship", "every inch", "all night",
    ]
    # Compound phrases: intimate only when paired correctly
    SEXUAL_PHRASES = [
        "want you", "need you", "crave you", "feel you", "touch you",
        "taste you", "inside me", "inside you", "kiss me", "kiss you",
        "your body", "your skin", "your lips", "your tongue", "your mouth",
        "your hands", "your fingers",
        "thinking about you", "can't stop thinking", "all day",
        "on my mind", "miss your touch", "miss your body",
        "turn me on", "turns me on", "making me",
    ]
    NEGATIVE_CONTEXT = [
        "don't", "not", "no", "stop", "hate", "ugly", "stupid", "angry",
        "sad", "hurt", "pain", "problem", "wrong", "bad day", "awful",
        "terrible", "horrible", "sick", "tired", "exhausted",
    ]
    POSITIVE_WORDS = [
        "love", "love you", "adore", "adore you", "care", "care about", "miss",
        "miss you", "beautiful", "gorgeous", "stunning", "pretty", "cute",
        "adorable", "amazing", "wonderful", "perfect", "incredible", "fantastic",
        "lovely", "sweet", "precious", "special", "unique", "smart", "funny",
        "clever", "witty", "talented", "creative", "kind", "caring",
        "thoughtful", "understanding", "expressive", "hot", "attractive", "charming",
        "elegant", "graceful", "radiant", "breathtaking", "companion",
        "partner", "together", "forever", "always", "happy", "glad", "excited",
        "thrilled", "grateful", "thankful", "appreciate", "lucky", "blessed",
        "proud", "babe", "honey", "darling", "sweetheart", "angel", "princess",
    ]
    NEGATIVE_WORDS = [
        "hate", "dislike", "ugly", "stupid", "dumb", "idiot", "annoying",
        "boring", "terrible", "awful", "horrible", "worst", "bad", "leave",
        "going away", "don't want", "not interested", "reject", "wrong",
        "fail", "failed", "mistake", "angry", "mad", "furious", "upset",
        "frustrated", "disappointed", "sad", "depressed", "lonely", "alone",
        "ignored", "forgotten", "never", "break up", "breaking up", "over",
        "done", "finished", "end", "cheat", "cheating", "lied", "lying",
        "lie", "betrayal",
    ]
    ESCALATION_WORDS = [
        "take me", "have me", "make me", "do whatever", "anything you want",
        "i'm yours", "use me", "beg", "desperate", "aching for",
        "yours alone", "belongs to you",
    ]
    FLIRTY_WORDS = [
        "tease", "teasing", "flirt", "flirting", "playful", "cheeky",
        "mischievous", "bratty", "brat", "sassy", "feisty", "dare",
        "promise", "surprise", "what if", "hint hint", "wink", "smirk",
        "reward", "behave", "participate", "prove it", "your turn",
        "cute", "amazing", "beautiful",
    ]
    ROMANTIC_WORDS = [
        "soulmate", "destiny", "meant to be", "forever", "eternity",
        "my heart", "my everything", "my world", "can't live without",
        "perfect match", "other half", "twin flame", "true love",
        "falling for", "falling in love", "in love", "love you so much",
        "marry", "marriage", "future", "together forever", "always yours",
    ]
    HARSH_WORDS = [
        "i hate you", "i don't love you", "leave me alone", "intense off",
        "you're annoying", "shut up", "get lost", "i'm done with you",
        "breaking up", "break up", "we're over", "it's over",
        "you're worthless", "nobody wants you", "i regret you",
        "cheating", "cheated", "with someone else", "other girl",
    ]
    TRUST_WORDS = [
        "trust you", "i trust you", "safe with you", "feel safe",
        "you understand me", "you get me", "i believe you", "i rely on you",
        "thank you for being honest", "keep this between us"
    ]
    APOLOGY_WORDS = [
        "sorry", "i'm sorry", "apologize", "my fault", "i messed up",
        "i shouldn't have", "i regret", "forgive me"
    ]
    FEAR_WORDS = [
        "scared", "afraid", "fear", "worried", "worry", "anxious",
        "panic", "unsafe", "threat", "leave me", "abandon", "disappear",
        "ghost me", "not safe", "i'm leaving", "goodbye forever"
    ]

    def count_intimate_triggers(self, text: str) -> int:
        """Context-aware intimate trigger counting"""
        msg = text.lower()
        has_negative = any(w in msg for w in self.NEGATIVE_CONTEXT)
        # Count intimate words (always count, but reduce if negative context)
        intimate = self.count_matches(msg, self.SEXY_WORDS)
        if has_negative and intimate > 0:
            intimate = max(1, intimate - 1)  # Reduce but don't zero out
        # Count intimate phrases
        phrases = self.count_matches(msg, self.SEXUAL_PHRASES)
        if has_negative:
            phrases = 0  # "don't touch you" is not intimate
        return intimate + phrases

    @staticmethod
    def count_matches(text: str, word_list: list) -> int:
        """Count how many words/phrases from list appear in text.
        Uses word-boundary matching for single words to avoid false positives
        (e.g. a short trigger matching the middle of an unrelated word).
        Multi-word phrases use substring matching."""
        text_lower = text.lower()
        count = 0
        seen = set()
        for w in word_list:
            if w in seen:
                continue
            seen.add(w)
            if ' ' in w:
                # Multi-word phrase: substring match is fine
                if w in text_lower:
                    count += 1
            else:
                # Single word: use word boundaries
                if re.search(r'\b' + re.escape(w) + r'\b', text_lower):
                    count += 1
        return count
