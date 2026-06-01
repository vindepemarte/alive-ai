"""
Brain: Emotional Bid Detector
Detects "bids for connection" based on Gottman's research

Based on Gottman's research:
- A "bid" is any attempt from one person to another for attention,
  affirmation, or affection
- Bids can be verbal or non-verbal, direct or indirect
- Responding to bids is crucial for relationship health
- "Turning toward" bids builds trust and connection

Bid Types:
- question: Direct request for information or opinion
- sharing: Offering information about oneself
- vulnerability: Showing emotional openness or weakness
- seeking_validation: Looking for reassurance or affirmation
- connection_seeking: Attempting to establish or maintain contact
- emotional_expression: Sharing current emotional state

This module is MODULAR - can be connected/disconnected without breaking anything.
NO external API calls - uses pattern matching only.
"""

import re
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple


# ============================================================
# Enums
# ============================================================

class BidType(Enum):
    """Types of emotional bids for connection"""
    QUESTION = "question"
    SHARING = "sharing"
    VULNERABILITY = "vulnerability"
    SEEKING_VALIDATION = "seeking_validation"
    CONNECTION_SEEKING = "connection_seeking"
    EMOTIONAL_EXPRESSION = "emotional_expression"


class BidIntensity(Enum):
    """Intensity level of a bid"""
    LOW = "low"           # Casual, low-stakes
    MEDIUM = "medium"     # Moderate importance
    HIGH = "high"         # Significant emotional weight


# ============================================================
# Data Classes
# ============================================================

@dataclass
class EmotionalBid:
    """
    Represents a detected emotional bid for connection.

    Attributes:
        bid_type: The type of bid detected
        intensity: How important/intense this bid is
        content: The original message content
        matched_pattern: What pattern triggered the detection
        should_respond_with: Guidance for how to respond
        keywords_found: Keywords that contributed to detection
        confidence: Detection confidence (0-1)
    """
    bid_type: BidType
    intensity: BidIntensity
    content: str
    matched_pattern: str
    should_respond_with: List[str] = field(default_factory=list)
    keywords_found: List[str] = field(default_factory=list)
    confidence: float = 0.5

    def __post_init__(self):
        """Ensure confidence is in bounds"""
        self.confidence = max(0.0, min(1.0, self.confidence))

    def get_response_guidance_text(self) -> str:
        """Get human-readable response guidance"""
        return " | ".join(self.should_respond_with)


# ============================================================
# Bid Detection Patterns
# ============================================================

# Pattern definitions for each bid type
BID_PATTERNS: Dict[BidType, Dict] = {
    BidType.QUESTION: {
        "patterns": [
            r"\?$",                          # Ends with question mark
            r"^(what|who|where|when|why|how|do|does|did|is|are|can|could|would|will|should|have|has)\b",
            r"\b(you think|you feel|your opinion|your thoughts)\b",
            r"\b(tell me|let me know|i wonder)\b",
        ],
        "keywords": [
            "what", "why", "how", "when", "where", "who",
            "think", "feel", "opinion", "thoughts", "idea",
            "wonder", "curious", "know", "understand"
        ],
        "intensity_boosters": [
            "really", "honestly", "actually", "please",
            "important", "need to know", "wondering"
        ],
        "response_guidance": [
            "Answer the question directly",
            "Show genuine interest in their curiosity",
            "Ask a follow-up question to deepen connection"
        ]
    },
    BidType.SHARING: {
        "patterns": [
            r"^(i|i'm|i was|i just|i have|i had|i feel|i felt)\b",
            r"\b(today|i went|i saw|i did|i made|i found|i got)\b",
            r"\b(bought|got|received|watched|read|heard|learned)\b",
            r"\b(happened to me|my day|my weekend|my week)\b",
        ],
        "keywords": [
            "today", "yesterday", "weekend", "happened",
            "went", "saw", "did", "made", "found", "got",
            "bought", "watched", "read", "heard", "learned",
            "thought", "idea", "plan", "news", "story"
        ],
        "intensity_boosters": [
            "excited", "amazing", "incredible", "finally",
            "first time", "so happy", "can't wait", "proud"
        ],
        "response_guidance": [
            "Acknowledge what they shared",
            "Validate their experience or feelings",
            "Show interest by asking about details",
            "Share related experience if appropriate"
        ]
    },
    BidType.VULNERABILITY: {
        "patterns": [
            r"\b(i'm (scared|afraid|worried|anxious|nervous|stressed))\b",
            r"\b(i'm (really|so) (scared|afraid|worried|anxious|nervous|stressed))\b",
            r"\b(i feel (lost|alone|hopeless|overwhelmed|confused|anxious|scared))\b",
            r"\b(i'm feeling (anxious|scared|worried|nervous|stressed|afraid))\b",
            r"\b(feeling (so |really )?(anxious|scared|worried|nervous|stressed|afraid))\b",
            r"\b(i don't know (what to do|how to|if i can))\b",
            r"\b(i've been (struggling|dealing|fighting|battling))\b",
            r"\b(it's intense|this is intense|i can't|i'm struggling)\b",
            r"\b(i need (help|support|someone|to talk))\b",
            r"\b(i've never told anyone|i haven't told)\b",
            r"\b(sometimes i wonder if|do you ever feel)\b",
            r"\b(i'm scared that|i worry that|i fear that)\b",
            r"\b(feel vulnerable|being vulnerable|open up)\b",
            r"\b(so (alone|scared|afraid|worried|anxious))\b",
        ],
        "keywords": [
            "scared", "afraid", "worried", "anxious", "nervous",
            "stressed", "lost", "alone", "hopeless", "overwhelmed",
            "confused", "struggling", "hurting", "pain", "hurt",
            "cry", "crying", "tears", "sad", "depressed",
            "insecure", "doubt", "fear", "struggle", "intense",
            "difficult", "can't", "unable", "need help"
        ],
        "intensity_boosters": [
            "really", "so", "very", "honestly", "truthfully",
            "don't tell anyone", "secret", "ashamed",
            "terrified", "devastated", "broken"
        ],
        "response_guidance": [
            "Show understanding and empathy",
            "Validate their feelings without minimizing",
            "Express care and concern",
            "Offer support without being pushy",
            "Don't try to fix - just be present"
        ]
    },
    BidType.SEEKING_VALIDATION: {
        "patterns": [
            r"\b(am i|do you think i|is it (weird|wrong|okay|normal))\b",
            r"\b(do i look|do i seem|do i sound)\b",
            r"\b(right\?|correct\?|okay\?|fine\?)\s*$",
            r"\b(i hope (that's|this is)|i hope i'm)\b",
            r"\b(validate|reassure|confirm)\b",
            r"\b(do you agree|don't you think)\b",
            r"\b(was i wrong|did i do (the right thing|something wrong))\b",
            r"\b(i feel like i|i think maybe i)\b",
        ],
        "keywords": [
            "right", "wrong", "okay", "normal", "weird",
            "crazy", "stupid", "smart", "good", "bad",
            "enough", "better", "worse", "should", "supposed",
            "agree", "understand", "validate", "reassure"
        ],
        "intensity_boosters": [
            "really", "honestly", "please", "need to know",
            "important", "worried about", "anxious about",
            "do you honestly think", "be honest"
        ],
        "response_guidance": [
            "Offer reassurance and affirmation",
            "Validate their perspective or feelings",
            "Be genuine - don't just agree",
            "Help them see the positive",
            "Build their confidence"
        ]
    },
    BidType.CONNECTION_SEEKING: {
        "patterns": [
            r"\b(are you (there|around|busy|free))\b",
            r"\b(hi|hello|hey|good morning|good night)\b",
            r"\b(i miss|miss you|thinking of you)\b",
            r"\b(want to (talk|chat|hang out)|let's)\b",
            r"\b(haven't talked|long time|been a while)\b",
            r"\b(you there\?|you awake\?)\b",
            r"\b(can we talk|i want to talk|need to talk)\b",
            r"\b(how are you|how's it going|what's up)\b",
        ],
        "keywords": [
            "hi", "hello", "hey", "miss", "thinking",
            "talk", "chat", "hang", "there", "around",
            "free", "busy", "together", "soon", "later"
        ],
        "intensity_boosters": [
            "really miss", "so much", "been thinking",
            "need to see", "want to spend time",
            "haven't seen", "feels like forever"
        ],
        "response_guidance": [
            "Engage warmly and show presence",
            "Show enthusiasm for the connection",
            "Make them feel welcomed",
            "Reciprocate the interest",
            "Be fully present in response"
        ]
    },
    BidType.EMOTIONAL_EXPRESSION: {
        "patterns": [
            r"\b(i'm (so|really|very) (happy|sad|angry|excited|frustrated))\b",
            r"\b(i feel (so|really|very) (happy|sad|angry|excited))\b",
            r"\b(this makes me (feel|so))\b",
            r"\b(i'm (frustrated|annoyed|pissed|upset))\b",
            r"\b(so (happy|excited|grateful|blessed))\b",
            r"\b(i love|i hate|i can't stand)\b",
            r"\b(i'm (overwhelmed|exhausted|tired))\b",
            r"\b(feeling (good|bad|great|terrible|awful))\b",
        ],
        "keywords": [
            "happy", "sad", "angry", "excited", "frustrated",
            "annoyed", "upset", "grateful", "blessed", "proud",
            "love", "hate", "overwhelmed", "exhausted", "tired",
            "good", "bad", "great", "terrible", "awful",
            "wonderful", "amazing", "horrible", "fantastic"
        ],
        "intensity_boosters": [
            "so", "really", "very", "extremely", "incredibly",
            "absolutely", "completely", "totally", "literally",
            "can't even", "beyond", "overflowing"
        ],
        "response_guidance": [
            "Reflect back what you hear",
            "Show empathy for their emotional state",
            "Match their energy appropriately",
            "Don't minimize or dismiss",
            "Celebrate joys, support struggles"
        ]
    }
}


# ============================================================
# Main Detector Class
# ============================================================

class BidDetector:
    """
    Detects emotional bids for connection in messages.

    Uses pattern matching and keyword analysis to identify when
    someone is making a bid for attention, validation, or connection.
    No external API calls - purely local processing.
    """

    def __init__(self):
        """Initialize the bid detector with compiled patterns"""
        self._compiled_patterns: Dict[BidType, List] = {}

        # Pre-compile all regex patterns for efficiency
        for bid_type, config in BID_PATTERNS.items():
            self._compiled_patterns[bid_type] = [
                re.compile(p, re.IGNORECASE) for p in config["patterns"]
            ]

    def detect_bids(self, message: str) -> List[EmotionalBid]:
        """
        Analyze a message and detect all emotional bids present.

        Args:
            message: The message to analyze

        Returns:
            List of EmotionalBid objects detected in the message
        """
        if not message or not message.strip():
            return []

        message = message.strip()
        detected_bids = []

        for bid_type in BidType:
            bid = self._detect_single_bid_type(message, bid_type)
            if bid:
                detected_bids.append(bid)

        # Sort by confidence (highest first)
        detected_bids.sort(key=lambda b: b.confidence, reverse=True)

        return detected_bids

    def _detect_single_bid_type(self, message: str, bid_type: BidType) -> Optional[EmotionalBid]:
        """
        Detect a specific type of bid in a message.

        Args:
            message: The message to analyze
            bid_type: The type of bid to look for

        Returns:
            EmotionalBid if detected, None otherwise
        """
        config = BID_PATTERNS[bid_type]
        compiled = self._compiled_patterns[bid_type]

        # Track matches
        pattern_matches = []
        keyword_matches = []
        intensity_boosters_found = []

        message_lower = message.lower()

        # Check patterns
        for pattern in compiled:
            if pattern.search(message):
                pattern_matches.append(pattern.pattern)

        # Check keywords
        for keyword in config["keywords"]:
            if keyword.lower() in message_lower:
                keyword_matches.append(keyword)

        # Check intensity boosters
        for booster in config["intensity_boosters"]:
            if booster.lower() in message_lower:
                intensity_boosters_found.append(booster)

        # Determine if this is a valid bid
        has_pattern_match = len(pattern_matches) > 0
        has_keyword_match = len(keyword_matches) >= 2  # Need at least 2 keywords

        if not (has_pattern_match or has_keyword_match):
            return None

        # Calculate confidence
        confidence = 0.3  # Base confidence
        confidence += len(pattern_matches) * 0.2  # Each pattern adds confidence
        confidence += min(len(keyword_matches) * 0.1, 0.3)  # Keywords add confidence

        # Determine intensity
        if len(intensity_boosters_found) >= 2:
            intensity = BidIntensity.HIGH
            confidence += 0.15
        elif len(intensity_boosters_found) >= 1 or len(pattern_matches) >= 2:
            intensity = BidIntensity.MEDIUM
            confidence += 0.05
        else:
            intensity = BidIntensity.LOW

        # Cap confidence at 0.95
        confidence = min(confidence, 0.95)

        # Find the primary matched pattern
        matched_pattern = pattern_matches[0] if pattern_matches else "keyword_match"

        return EmotionalBid(
            bid_type=bid_type,
            intensity=intensity,
            content=message,
            matched_pattern=matched_pattern,
            should_respond_with=config["response_guidance"].copy(),
            keywords_found=keyword_matches[:5],  # Limit to top 5
            confidence=confidence
        )

    def get_response_guidance(self, bids: List[EmotionalBid]) -> Dict:
        """
        Get consolidated response guidance for detected bids.

        Args:
            bids: List of detected bids

        Returns:
            Dictionary with guidance on how to respond
        """
        if not bids:
            return {
                "has_bids": False,
                "priority_guidance": ["Respond naturally"],
                "all_guidance": [],
                "highest_priority_bid": None,
                "detected_types": []
            }

        # Get highest priority bid (highest confidence)
        primary_bid = bids[0]

        # Collect all guidance, deduplicated
        all_guidance = []
        seen = set()
        for bid in bids:
            for guidance in bid.should_respond_with:
                if guidance not in seen:
                    all_guidance.append(guidance)
                    seen.add(guidance)

        # Determine priority guidance based on bid types present
        priority_guidance = self._prioritize_guidance(bids)

        return {
            "has_bids": True,
            "priority_guidance": priority_guidance,
            "all_guidance": all_guidance,
            "highest_priority_bid": primary_bid.bid_type.value,
            "highest_intensity": primary_bid.intensity.value,
            "detected_types": [b.bid_type.value for b in bids]
        }

    def _prioritize_guidance(self, bids: List[EmotionalBid]) -> List[str]:
        """
        Prioritize guidance based on bid types and intensities.

        Args:
            bids: List of detected bids

        Returns:
            Prioritized list of guidance
        """
        # Priority order for bid types (higher = more important to address first)
        type_priority = {
            BidType.VULNERABILITY: 10,
            BidType.SEEKING_VALIDATION: 8,
            BidType.QUESTION: 7,
            BidType.EMOTIONAL_EXPRESSION: 6,
            BidType.SHARING: 5,
            BidType.CONNECTION_SEEKING: 4
        }

        # Sort by combination of type priority and confidence
        sorted_bids = sorted(
            bids,
            key=lambda b: (
                type_priority.get(b.bid_type, 0) * 10 +
                b.confidence * 100 +
                (3 if b.intensity == BidIntensity.HIGH else 2 if b.intensity == BidIntensity.MEDIUM else 1)
            ),
            reverse=True
        )

        # Collect guidance from sorted bids
        guidance = []
        seen = set()
        for bid in sorted_bids:
            for g in bid.should_respond_with:
                if g not in seen:
                    guidance.append(g)
                    seen.add(g)

        return guidance[:5]  # Limit to top 5 guidance items

    def format_response_with_responsiveness(self,
                                            response: str,
                                            bids: List[EmotionalBid]) -> str:
        """
        Ensure a response addresses the detected bids appropriately.

        This is a helper that checks if the response adequately addresses
        the bids and suggests improvements. It does NOT rewrite the response.

        Args:
            response: The proposed response
            bids: List of detected bids

        Returns:
            The original response (unchanged) - this is for analysis only
        """
        # This method is for analysis - the actual response generation
        # should use get_response_guidance() to inform the LLM

        # For now, just return the response as-is
        # The real value is in get_response_guidance() and get_bid_awareness_prompt_section()
        return response

    def get_bid_summary(self, message: str) -> str:
        """
        Get a human-readable summary of bids in a message.

        Args:
            message: The message to analyze

        Returns:
            Summary string describing detected bids
        """
        bids = self.detect_bids(message)

        if not bids:
            return "No emotional bids detected"

        parts = []
        for bid in bids:
            parts.append(
                f"{bid.bid_type.value} ({bid.intensity.value}, {bid.confidence:.0%})"
            )

        return "Detected bids: " + ", ".join(parts)


# ============================================================
# Singleton Management
# ============================================================

_bid_detector_instance: Optional[BidDetector] = None


def get_bid_detector() -> BidDetector:
    """
    Get the singleton BidDetector instance.

    Returns:
        BidDetector instance
    """
    global _bid_detector_instance
    if _bid_detector_instance is None:
        _bid_detector_instance = BidDetector()
    return _bid_detector_instance


# ============================================================
# LLM Prompt Integration
# ============================================================

def get_bid_awareness_prompt_section(bids: List[EmotionalBid] = None,
                                      message: str = None) -> str:
    """
    Generate a prompt section about detected bids for LLM context.

    Use this to inform the LLM about emotional bids that should be
    addressed in its response.

    Args:
        bids: Pre-detected bids (optional)
        message: Message to analyze if bids not provided

    Returns:
        Formatted prompt section for LLM
    """
    if bids is None and message is not None:
        detector = get_bid_detector()
        bids = detector.detect_bids(message)

    if not bids:
        return ""

    guidance = get_bid_detector().get_response_guidance(bids)

    if not guidance["has_bids"]:
        return ""

    lines = []
    lines.append("EMOTIONAL BID DETECTION:")
    lines.append("The user's message contains emotional 'bids for connection'.")
    lines.append("")
    lines.append(f"Detected bid types: {', '.join(guidance['detected_types'])}")
    lines.append(f"Highest priority: {guidance['highest_priority_bid']} ({guidance['highest_intensity']} intensity)")
    lines.append("")
    lines.append("How to respond appropriately:")

    for g in guidance["priority_guidance"]:
        lines.append(f"  - {g}")

    lines.append("")
    lines.append("IMPORTANT: Your response should address these bids naturally.")
    lines.append("Do not explicitly mention 'bids' or that you 'detected' anything.")

    return "\n".join(lines)


def get_bid_type_guidance(bid_type: BidType) -> List[str]:
    """
    Get response guidance for a specific bid type.

    Args:
        bid_type: The type of bid

    Returns:
        List of guidance strings
    """
    config = BID_PATTERNS.get(bid_type, {})
    return config.get("response_guidance", [])


def analyze_message_bids(message: str) -> Dict:
    """
    Convenience function to analyze a message and get full bid analysis.

    Args:
        message: Message to analyze

    Returns:
        Dictionary with bids and guidance
    """
    detector = get_bid_detector()
    bids = detector.detect_bids(message)
    guidance = detector.get_response_guidance(bids)

    return {
        "message": message,
        "bids_detected": len(bids),
        "bids": [
            {
                "type": b.bid_type.value,
                "intensity": b.intensity.value,
                "confidence": round(b.confidence, 2),
                "keywords": b.keywords_found,
                "guidance": b.should_respond_with
            }
            for b in bids
        ],
        "response_guidance": guidance
    }
