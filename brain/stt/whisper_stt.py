"""
Brain: STT - Speech to Text using OpenAI Whisper API
"""

import aiohttp
from pathlib import Path

class WhisperSTT:
    """Speech-to-text using OpenAI Whisper API"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://api.openai.com/v1/audio/transcriptions"

    async def transcribe(self, audio_path: str) -> str:
        """Transcribe audio file to text"""
        if not self.api_key:
            print("[WhisperSTT] No API key configured")
            return ""

        path = Path(audio_path)
        if not path.exists():
            print(f"[WhisperSTT] File not found: {audio_path}")
            return ""

        try:
            # Read audio file synchronously (aiohttp handles async)
            with open(path, 'rb') as f:
                audio_data = f.read()

            # Create form data
            async with aiohttp.ClientSession() as session:
                form = aiohttp.FormData()
                form.add_field('file', audio_data, filename='audio.ogg',
                              content_type='audio/ogg')
                form.add_field('model', 'whisper-1')
                form.add_field('language', 'en')

                headers = {
                    "Authorization": f"Bearer {self.api_key}"
                }

                async with session.post(self.api_url, data=form, headers=headers,
                                       timeout=aiohttp.ClientTimeout(total=60)) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        text = result.get("text", "")
                        print(f"[WhisperSTT] Transcribed: {text[:100]}...")
                        return text
                    else:
                        error = await resp.text()
                        print(f"[WhisperSTT] Error {resp.status}: {error[:200]}")
                        return ""

        except Exception as e:
            print(f"[WhisperSTT] Error: {e}")
            return ""

    async def transcribe_telegram_voice(self, bot, file_id: str, save_path: str = "/tmp/voice_input.ogg") -> str:
        """Download and transcribe Telegram voice message"""
        try:
            # Get file info
            file_info = await bot.get_file(file_id)
            file_url = file_info.file_path

            # Download file
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://api.telegram.org/file/bot{bot.token}/{file_url}") as resp:
                    if resp.status == 200:
                        audio_data = await resp.read()
                        Path(save_path).write_bytes(audio_data)
                        print(f"[WhisperSTT] Downloaded voice: {len(audio_data)} bytes")
                    else:
                        print(f"[WhisperSTT] Download error: {resp.status}")
                        return ""

            # Transcribe
            return await self.transcribe(save_path)

        except Exception as e:
            print(f"[WhisperSTT] Telegram voice error: {e}")
            return ""
