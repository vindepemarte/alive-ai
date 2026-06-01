"""
Output: Fal.ai Image Generator
Generate images using fal.ai API
"""

import aiohttp

class FalImageGen:
    """Image generator via fal.ai"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://queue.fal.run/fal-ai/flux/schnell"

    async def generate(self, prompt: str, size: str = "square_hd") -> str:
        """Generate image, return URL"""
        if not self.api_key:
            print("[Fal.ai] No API key configured")
            return ""

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Key {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "prompt": prompt,
                        "image_size": size
                    },
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return result.get("images", [{}])[0].get("url", "")
                    else:
                        print(f"[Fal.ai] Error: {resp.status}")
                        return ""
        except Exception as e:
            print(f"[Fal.ai] Error: {e}")
            return ""
