"""
Output: gTTS (Google Translate TTS)
Free text-to-speech using Google Translate's TTS API
No API key required!
"""

import asyncio
import re
import tempfile
import subprocess
from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

VOICE_OUTPUT_PATH = "/tmp/alive_ai_voice.ogg"
MAX_CHARS = 5000  # gTTS limit

# Thread pool for blocking gTTS calls
_executor = ThreadPoolExecutor(max_workers=2)


class GTTS:
    """Text-to-speech via gTTS (Google Translate TTS) - Completely free!"""

    # Available voices are language codes
    # gTTS doesn't have named voices like "Emma", just languages/accents
    AVAILABLE_VOICES = {
        "en": "en",           # English (default)
        "en-us": "en",        # US English
        "en-uk": "co.uk",     # UK English
        "en-au": "com.au",    # Australian English
        "en-in": "co.in",     # Indian English
        "it": "it",           # Italian
        "es": "es",           # Spanish
        "fr": "fr",           # French
        "de": "de",           # German
        "pt": "pt",           # Portuguese
    }

    DEFAULT_VOICE = "en"
    DEFAULT_LANG = "en"

    def __init__(self):
        """Initialize gTTS - no API key needed!"""
        self._available = None

    def prepare_text(self, text: str) -> str:
        """Clean text for TTS"""
        # Remove markdown formatting
        text = text.replace("**", "").replace("__", "").replace("*", "")
        text = text.replace("_", "").replace("~", "")
        text = re.sub(r'\*[^*]+\*', '', text)
        text = re.sub(r'\.{3,}', '...', text)
        text = re.sub(r'!{2,}', '!', text)
        text = re.sub(r'\?{2,}', '?', text)

        # Remove ALL emojis
        text = re.sub(r'[\U00010000-\U0010ffff]', '', text)
        text = re.sub(r'[\U0001F600-\U0001F64F]', '', text)
        text = re.sub(r'[\U0001F300-\U0001F5FF]', '', text)
        text = re.sub(r'[\U0001F680-\U0001F6FF]', '', text)
        text = re.sub(r'[\U00002702-\U000027B0]', '', text)
        text = re.sub(r'[\U000024C2-\U0001F251]', '', text)
        text = re.sub(r'[\U0001F1E0-\U0001F1FF]', '', text)

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

    def _generate_blocking(self, text: str, lang: str) -> bytes:
        """Generate audio in a blocking manner (runs in thread pool)"""
        try:
            from gtts import gTTS
            import io

            tts = gTTS(text=text, lang=lang, slow=False)
            mp3_buffer = io.BytesIO()
            tts.write_to_fp(mp3_buffer)
            mp3_buffer.seek(0)

            # Convert MP3 to OGG for Telegram
            # If pydub is available, convert to OGG
            try:
                from pydub import AudioSegment
                audio = AudioSegment.from_mp3(mp3_buffer)
                ogg_buffer = io.BytesIO()
                audio.export(ogg_buffer, format="ogg")
                ogg_buffer.seek(0)
                return ogg_buffer.read()
            except ImportError:
                # No pydub - return MP3, Telegram accepts it too
                mp3_buffer.seek(0)
                return mp3_buffer.read()

        except ImportError:
            print("[GTTS] gtts not installed. Run: pip install gtts")
            return b""
        except Exception as e:
            print(f"[GTTS] Error: {e}")
            return b""

    async def generate(self, text: str, voice: str = None,
                       cfg: float = None, mood: str = "neutral") -> str:
        """Generate audio using gTTS"""
        if voice is None:
            voice = self.DEFAULT_VOICE

        # Map voice to language code
        lang = self.AVAILABLE_VOICES.get(voice, self.DEFAULT_LANG)

        text = self.prepare_text(text)
        print(f"[GTTS] Generating voice for {len(text)} chars with lang={lang}...")

        # Split if needed
        parts = self.split_text(text)
        if len(parts) > 1:
            print(f"[GTTS] Split into {len(parts)} parts")

        audio_parts = []
        loop = asyncio.get_running_loop()

        for i, part in enumerate(parts):
            print(f"[GTTS] Processing part {i+1}/{len(parts)} ({len(part)} chars)")
            audio = await loop.run_in_executor(_executor, self._generate_blocking, part, lang)
            if audio:
                audio_parts.append(audio)
            else:
                print(f"[GTTS] Part {i+1} failed")

        if not audio_parts:
            return ""

        # Determine extension based on format
        ext = ".ogg" if audio_parts[0][:4] == b'OggS' else ".mp3"
        output_path = VOICE_OUTPUT_PATH.replace(".ogg", ext)

        # Combine all parts
        if len(audio_parts) == 1:
            Path(output_path).write_bytes(audio_parts[0])
        else:
            # Use ffmpeg to properly concatenate audio files
            temp_files = []
            try:
                for i, part in enumerate(audio_parts):
                    tf = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
                    tf.write(part)
                    tf.close()
                    temp_files.append(tf.name)
                list_file = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
                for tf_name in temp_files:
                    list_file.write(f"file '{tf_name}'\n")
                list_file.close()
                subprocess.run(
                    ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                     "-i", list_file.name, "-c", "copy", output_path],
                    capture_output=True, timeout=30
                )
                Path(list_file.name).unlink(missing_ok=True)
            except Exception as e:
                print(f"[GTTS] ffmpeg concat failed, using first part: {e}")
                Path(output_path).write_bytes(audio_parts[0])
            finally:
                for tf_name in temp_files:
                    Path(tf_name).unlink(missing_ok=True)
        print(f"[GTTS] Generated audio file")
        return output_path

    async def is_available(self) -> bool:
        """Check if gTTS is available"""
        if self._available is not None:
            return self._available

        try:
            from gtts import gTTS
            self._available = True
            return True
        except ImportError:
            self._available = False
            return False
