"""
Output: Google Cloud TTS
Text-to-speech using Google Cloud Text-to-Speech API

Uses the free tier (up to 4M chars/month) with Emma voice
"""

import aiohttp
import asyncio
import re
import tempfile
import subprocess
from pathlib import Path
from typing import Optional

VOICE_OUTPUT_PATH = "/tmp/alive_ai_voice.ogg"
MAX_CHARS = 5000  # Google TTS limit per request


class GoogleTTS:
    """Text-to-speech via Google Cloud TTS API"""

    # Available voices - Emma is the natural sounding one
    AVAILABLE_VOICES = {
        "emma": "en-US-Neural2-F",      # Emma - natural female US
        "emma-uk": "en-GB-Neural2-F",   # UK female
        "guy": "en-US-Neural2-D",       # Male US
        "guy-uk": "en-GB-Neural2-D",    # Male UK
    }

    DEFAULT_VOICE = "emma"

    # Speaking rates by mood (0.25 to 4.0, 1.0 is normal)
    MOOD_RATES = {
        "chill": 0.9, "neutral": 1.0, "happy": 1.05,
        "flirty": 1.0, "excited": 1.1, "high_desire": 0.95, "intense": 1.0,
        "sad": 0.9, "tired": 0.85
    }

    def __init__(self, api_key: str = None):
        """
        Initialize Google TTS.

        Args:
            api_key: Google Cloud API key (optional if using ADC)
        """
        self.api_key = api_key
        self.base_url = "https://texttospeech.googleapis.com/v1"

    def prepare_text(self, text: str) -> str:
        """Clean text for TTS - removes formatting and EMOJIS"""
        # Remove markdown formatting
        text = text.replace("**", "").replace("__", "").replace("*", "")
        text = text.replace("_", "").replace("~", "")
        text = re.sub(r'\*[^*]+\*', '', text)
        text = re.sub(r'\.{3,}', '...', text)
        text = re.sub(r'!{2,}', '!', text)
        text = re.sub(r'\?{2,}', '?', text)

        # Remove ALL emojis - they break TTS
        text = re.sub(r'[\U00010000-\U0010ffff]', '', text)
        text = re.sub(r'[\U0001F600-\U0001F64F]', '', text)  # emoticons
        text = re.sub(r'[\U0001F300-\U0001F5FF]', '', text)  # symbols & pictographs
        text = re.sub(r'[\U0001F680-\U0001F6FF]', '', text)  # transport & map
        text = re.sub(r'[\U0001F700-\U0001F77F]', '', text)  # alchemical
        text = re.sub(r'[\U0001F780-\U0001F7FF]', '', text)  # Geometric Shapes
        text = re.sub(r'[\U0001F800-\U0001F8FF]', '', text)  # Supplemental Arrows-C
        text = re.sub(r'[\U0001F900-\U0001F9FF]', '', text)  # Supplemental Symbols
        text = re.sub(r'[\U0001FA00-\U0001FA6F]', '', text)  # Chess Symbols
        text = re.sub(r'[\U0001FA70-\U0001FAFF]', '', text)  # Symbols Extended-A
        text = re.sub(r'[\U00002702-\U000027B0]', '', text)  # Dingbats
        text = re.sub(r'[\U000024C2-\U0001F251]', '', text)  # Enclosed characters
        text = re.sub(r'[\U0001F1E0-\U0001F1FF]', '', text)  # Flags

        # Clean up extra spaces
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def split_text(self, text: str) -> list:
        """Split long text at paragraph/sentence boundaries"""
        if len(text) <= MAX_CHARS:
            return [text]

        parts = []
        paragraphs = text.split('\n\n')
        current = ""

        for para in paragraphs:
            if len(current) + len(para) + 2 <= MAX_CHARS:
                current = current + "\n\n" + para if current else para
            else:
                if current:
                    parts.append(current)
                # If single paragraph is too long, split by sentences
                if len(para) > MAX_CHARS:
                    sentences = para.replace('. ', '.\n').split('\n')
                    chunk = ""
                    for s in sentences:
                        if len(chunk) + len(s) + 1 <= MAX_CHARS:
                            chunk = chunk + " " + s if chunk else s
                        else:
                            if chunk:
                                parts.append(chunk)
                            chunk = s
                    if chunk:
                        parts.append(chunk)
                else:
                    current = para

        if current:
            parts.append(current)

        return parts

    def get_voice_id(self, voice: str) -> str:
        """Get Google voice ID from friendly name"""
        return self.AVAILABLE_VOICES.get(voice, self.AVAILABLE_VOICES[self.DEFAULT_VOICE])

    def get_rate_for_mood(self, mood: str) -> float:
        return self.MOOD_RATES.get(mood, 1.0)

    async def generate(self, text: str, voice: str = None,
                       cfg: float = None, mood: str = "neutral") -> str:
        """Generate audio using Google Cloud TTS"""
        if voice is None:
            voice = self.DEFAULT_VOICE

        voice_id = self.get_voice_id(voice)
        speaking_rate = self.get_rate_for_mood(mood)

        text = self.prepare_text(text)
        print(f"[GoogleTTS] Generating voice for {len(text)} chars with voice {voice_id}...")

        # Split if needed
        parts = self.split_text(text)
        if len(parts) > 1:
            print(f"[GoogleTTS] Split into {len(parts)} parts")

        audio_parts = []
        for i, part in enumerate(parts):
            print(f"[GoogleTTS] Processing part {i+1}/{len(parts)} ({len(part)} chars)")
            audio = await self._generate_single(part, voice_id, speaking_rate)
            if audio:
                audio_parts.append(audio)
            else:
                print(f"[GoogleTTS] Part {i+1} failed")

        if not audio_parts:
            return ""

        # Combine all parts
        if len(audio_parts) == 1:
            Path(VOICE_OUTPUT_PATH).write_bytes(audio_parts[0])
        else:
            # Use ffmpeg to properly concatenate OGG files
            temp_files = []
            try:
                for i, part in enumerate(audio_parts):
                    tf = tempfile.NamedTemporaryFile(suffix=".ogg", delete=False)
                    tf.write(part)
                    tf.close()
                    temp_files.append(tf.name)
                list_file = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
                for tf_name in temp_files:
                    list_file.write(f"file '{tf_name}'\n")
                list_file.close()
                subprocess.run(
                    ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                     "-i", list_file.name, "-c", "copy", VOICE_OUTPUT_PATH],
                    capture_output=True, timeout=30
                )
                Path(list_file.name).unlink(missing_ok=True)
            except Exception as e:
                print(f"[GoogleTTS] ffmpeg concat failed, using first part: {e}")
                Path(VOICE_OUTPUT_PATH).write_bytes(audio_parts[0])
            finally:
                for tf_name in temp_files:
                    Path(tf_name).unlink(missing_ok=True)
        print(f"[GoogleTTS] Generated audio file")
        return VOICE_OUTPUT_PATH

    async def _generate_single(self, text: str, voice_id: str, speaking_rate: float) -> bytes:
        """Generate single audio part via Google Cloud TTS API"""
        try:
            # Build request URL
            url = f"{self.base_url}/text:synthesize"
            if self.api_key:
                url += f"?key={self.api_key}"

            # Request body
            payload = {
                "input": {"text": text},
                "voice": {
                    "languageCode": "en-US",
                    "name": voice_id
                },
                "audioConfig": {
                    "audioEncoding": "OGG_OPUS",
                    "speakingRate": speaking_rate,
                    "pitch": 0.0
                }
            }

            # Adjust language code based on voice
            if "en-GB" in voice_id:
                payload["voice"]["languageCode"] = "en-GB"

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        # Response contains base64-encoded audio
                        import base64
                        audio_content = result.get("audioContent", "")
                        if audio_content:
                            return base64.b64decode(audio_content)
                        return b""
                    else:
                        error = await resp.text()
                        print(f"[GoogleTTS] Error {resp.status}: {error[:200]}")
                        return b""
        except asyncio.TimeoutError:
            print("[GoogleTTS] Timeout")
            return b""
        except Exception as e:
            print(f"[GoogleTTS] Error: {e}")
            return b""

    async def is_available(self) -> bool:
        """Check if Google TTS is available"""
        # If we have an API key or ADC is configured, it should work
        try:
            # Try a minimal synthesis to check
            url = f"{self.base_url}/text:synthesize"
            if self.api_key:
                url += f"?key={self.api_key}"

            payload = {
                "input": {"text": "test"},
                "voice": {"languageCode": "en-US", "name": "en-US-Neural2-F"},
                "audioConfig": {"audioEncoding": "OGG_OPUS"}
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=10) as resp:
                    return resp.status == 200
        except Exception:
            return False
