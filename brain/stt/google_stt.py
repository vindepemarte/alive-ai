"""
Brain: STT - Speech to Text using Google Speech Recognition (Free)
"""

import speech_recognition as sr
from pathlib import Path
import subprocess
import asyncio
import os

class GoogleSTT:
    """Speech-to-text using Google's free Speech Recognition API"""

    def __init__(self):
        self.recognizer = sr.Recognizer()

    def _transcribe_sync(self, audio_path: str) -> str:
        """Synchronous transcription (runs in executor to avoid blocking event loop)"""
        wav_path = audio_path.replace('.ogg', '.wav')
        try:
            result = subprocess.run(
                ['ffmpeg', '-i', audio_path, '-ar', '16000', '-ac', '1', wav_path, '-y'],
                capture_output=True,
                timeout=30
            )

            if not Path(wav_path).exists():
                print(f"[GoogleSTT] FFmpeg conversion failed: {result.stderr.decode()[:200]}")
                return ""

            with sr.AudioFile(wav_path) as source:
                audio = self.recognizer.record(source)

            text = self.recognizer.recognize_google(audio)
            print(f"[GoogleSTT] Transcribed: {text}")
            return text

        except sr.UnknownValueError:
            print("[GoogleSTT] Could not understand audio")
            return ""
        except sr.RequestError as e:
            print(f"[GoogleSTT] Google API error: {e}")
            return ""
        except subprocess.TimeoutExpired:
            print("[GoogleSTT] FFmpeg timeout")
            return ""
        except Exception as e:
            print(f"[GoogleSTT] Error: {e}")
            return ""
        finally:
            # Clean up temp WAV file
            try:
                if Path(wav_path).exists():
                    os.remove(wav_path)
            except Exception:
                pass

    async def transcribe(self, audio_path: str) -> str:
        """Transcribe audio file to text (non-blocking)"""
        path = Path(audio_path)
        if not path.exists():
            print(f"[GoogleSTT] File not found: {audio_path}")
            return ""

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._transcribe_sync, audio_path)

    async def transcribe_telegram_voice(self, bot, file_id: str, save_path: str = "/tmp/voice_input.ogg") -> str:
        """Download and transcribe Telegram voice message"""
        try:
            # Get file info from Telegram
            file = await bot.get_file(file_id)

            # Download using python-telegram-bot's built-in method
            await file.download_to_drive(save_path)
            print(f"[GoogleSTT] Downloaded voice to: {save_path}")

            # Transcribe
            return await self.transcribe(save_path)

        except Exception as e:
            print(f"[GoogleSTT] Telegram voice error: {e}")
            return ""
