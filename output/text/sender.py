"""
Output: Text Sender
Send text messages
"""

class TextSender:
    """Text message sender"""

    def __init__(self, nervous, config):
        self.nervous = nervous
        self.config = config

        # Listen for send events
        nervous.on("send_text", self._send)

    async def _send(self, data: dict):
        """Handle text send (actual sending done by TelegramListener)"""
        text = data.get("text", "")
        mood = data.get("mood", "neutral")

        # Log the message
        print(f"[Outgoing {mood}] {text[:100]}{'...' if len(text) > 100 else ''}")
