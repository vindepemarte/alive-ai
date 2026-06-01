"""
Output: Vibe TTS
Connect to VibeVoice server for natural text-to-speech

Max 5000 chars per request - splits longer texts into parts
"""

import aiohttp
import asyncio
import re
import tempfile
import subprocess
from pathlib import Path

VOICE_OUTPUT_PATH = "/tmp/alive_ai_voice.ogg"
MAX_CHARS = 5000  # VibeTTS limit


class VibeTTS:
    """Text-to-speech via VibeVoice server"""

    DEFAULT_VOICE = "en-Emma_woman"

    CFG_MOOD = {
        "chill": 1.5, "neutral": 1.5, "happy": 1.6,
        "flirty": 1.6, "excited": 1.7, "high_desire": 1.9, "intense": 2.0
    }

    def __init__(self, url: str = "http://localhost:8080"):
        self.url = url.rstrip("/")

    def prepare_text(self, text: str) -> str:
        """Clean text for TTS - removes formatting and EMOJIS"""
        # Remove markdown formatting
        text = re.sub(r'\*+[^*]+\*+', '', text)  # Remove *bold*/**bold** content
        text = text.replace("__", "").replace("_", "").replace("~", "")
        text = re.sub(r'\.{3,}', '...', text)
        text = re.sub(r'!{2,}', '!', text)
        text = re.sub(r'\?{2,}', '?', text)

        # Remove ALL emojis - they break TTS
        text = re.sub(r'[\U00010000-\U0010ffff]', '', text)
        # Remove common emoji ranges
        text = re.sub(r'[\U0001F600-\U0001F64F]', '', text)  # emoticons
        text = re.sub(r'[\U0001F300-\U0001F5FF]', '', text)  # symbols & pictographs
        text = re.sub(r'[\U0001F680-\U0001F6FF]', '', text)  # transport & map
        text = re.sub(r'[\U0001F700-\U0001F77F]', '', text)  # alchemical
        text = re.sub(r'[\U0001F780-\U0001F7FF]', '', text)  # Geometric Shapes
        text = re.sub(r'[\U0001F800-\U0001F8FF]', '', text)  # Supplemental Arrows-C
        text = re.sub(r'[\U0001F900-\U0001F9FF]', '', text)  # Supplemental Symbols and Pictographs
        text = re.sub(r'[\U0001FA00-\U0001FA6F]', '', text)  # Chess Symbols
        text = re.sub(r'[\U0001FA70-\U0001FAFF]', '', text)  # Symbols and Pictographs Extended-A
        text = re.sub(r'[\U00002702-\U000027B0]', '', text)  # Dingbats
        text = re.sub(r'[\U000024C2-\U0001F251]', '', text)  # Enclosed characters
        text = re.sub(r'[\U0001F1E0-\U0001F1FF]', '', text)  # Flags

        # Clean up extra spaces
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def split_text(self, text: str) -> list:
        """Split long text at paragraph boundaries"""
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

    def get_cfg_for_mood(self, mood: str) -> float:
        return self.CFG_MOOD.get(mood, 1.5)

    async def generate(self, text: str, voice: str = None,
                       cfg: float = None, mood: str = "neutral") -> str:
        """Generate audio - handles long texts by splitting"""
        if voice is None:
            voice = self.DEFAULT_VOICE
        if cfg is None:
            cfg = self.get_cfg_for_mood(mood)

        text = self.prepare_text(text)
        print(f"[VibeTTS] Generating voice for {len(text)} chars...")

        # Split if needed
        parts = self.split_text(text)
        if len(parts) > 1:
            print(f"[VibeTTS] Split into {len(parts)} parts")

        audio_parts = []
        for i, part in enumerate(parts):
            print(f"[VibeTTS] Processing part {i+1}/{len(parts)} ({len(part)} chars)")
            audio = await self._generate_single(part, voice, cfg)
            if audio:
                audio_parts.append(audio)
            else:
                print(f"[VibeTTS] Part {i+1} failed")

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
                # Create concat list file
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
                print(f"[VibeTTS] ffmpeg concat failed, using first part: {e}")
                Path(VOICE_OUTPUT_PATH).write_bytes(audio_parts[0])
            finally:
                for tf_name in temp_files:
                    Path(tf_name).unlink(missing_ok=True)
        print(f"[VibeTTS] Generated audio file")
        return VOICE_OUTPUT_PATH

    async def _generate_single(self, text: str, voice: str, cfg: float) -> bytes:
        """Generate single audio part"""
        try:
            async with aiohttp.ClientSession() as session:
                params = {"text": text, "voice": voice, "cfg": str(cfg)}
                async with session.get(
                    f"{self.url}/tts",
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=600)
                ) as resp:
                    if resp.status == 200:
                        return await resp.read()
                    else:
                        error = await resp.text()
                        print(f"[VibeTTS] Error {resp.status}: {error[:200]}")
                        return b""
        except asyncio.TimeoutError:
            print("[VibeTTS] Timeout")
            return b""
        except Exception as e:
            print(f"[VibeTTS] Error: {e}")
            return b""

    async def is_available(self) -> bool:
        """Check if server is available"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.url}/health", timeout=2) as resp:
                    return resp.status == 200
        except:
            return False
