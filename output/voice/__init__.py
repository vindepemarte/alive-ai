"""
Output: Voice TTS Factory
Creates the appropriate TTS provider based on settings
"""

from typing import Optional


async def create_tts(provider: str = "vibe", **kwargs) -> Optional[object]:
    """
    Create a TTS instance based on provider setting.

    Args:
        provider: "vibe", "google", or "gtts"
        **kwargs: Provider-specific arguments:
            - vibe: url (required)
            - google: api_key (optional)
            - gtts: no arguments needed

    Returns:
        TTS instance or None if unavailable
    """
    provider = provider.lower()

    if provider == "vibe" or provider == "vibevoice":
        from .vibe_tts import VibeTTS
        url = kwargs.get("url", "http://localhost:8080")
        tts = VibeTTS(url)
        if await tts.is_available():
            print(f"[TTS] Connected to VibeVoice at {url}")
            return tts
        else:
            print(f"[TTS] VibeVoice not available at {url}")
            return None

    elif provider == "google" or provider == "google-tts":
        from .google_tts import GoogleTTS
        api_key = kwargs.get("api_key")
        tts = GoogleTTS(api_key)
        if await tts.is_available():
            print(f"[TTS] Connected to Google Cloud TTS")
            return tts
        else:
            print(f"[TTS] Google Cloud TTS not available")
            return None

    elif provider == "gtts" or provider == "gtranslate":
        from .gtts_tts import GTTS
        tts = GTTS()
        if await tts.is_available():
            print(f"[TTS] Connected to gTTS (Google Translate - FREE)")
            return tts
        else:
            print(f"[TTS] gTTS not available. Install with: pip install gtts")
            return None

    else:
        print(f"[TTS] Unknown provider: {provider}")
        return None


def get_available_providers() -> list:
    """Get list of available TTS providers"""
    return ["vibe", "google", "gtts"]
