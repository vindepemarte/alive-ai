"""Brain modules"""
from .emotional_memory import (
    EmotionalMemorySystem,
    EmotionalMemory,
    get_emotional_memory_system,
    reset_emotional_memory_system,
    create_from_conversation,
    get_memory_context_for_llm
)
from .default_mode import (
    DefaultModeProcessor,
    IdleThought,
    PendingInitiation,
    ConversationSeed,
    UserContactInfo,
    get_default_mode_processor,
    get_idle_thoughts_prompt_section,
    start_background_processing,
    stop_background_processing,
)
from .bid_detector import (
    BidType,
    BidIntensity,
    EmotionalBid,
    BidDetector,
    get_bid_detector,
    get_bid_awareness_prompt_section,
    get_bid_type_guidance,
    analyze_message_bids,
)

__all__ = [
    # Emotional Memory
    "EmotionalMemorySystem",
    "EmotionalMemory",
    "get_emotional_memory_system",
    "reset_emotional_memory_system",
    "create_from_conversation",
    "get_memory_context_for_llm",
    # Default Mode Network
    "DefaultModeProcessor",
    "IdleThought",
    "PendingInitiation",
    "ConversationSeed",
    "UserContactInfo",
    "get_default_mode_processor",
    "get_idle_thoughts_prompt_section",
    "start_background_processing",
    "stop_background_processing",
    # Bid Detector
    "BidType",
    "BidIntensity",
    "EmotionalBid",
    "BidDetector",
    "get_bid_detector",
    "get_bid_awareness_prompt_section",
    "get_bid_type_guidance",
    "analyze_message_bids",
]