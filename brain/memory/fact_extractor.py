"""Brain: Memory - Fact Extractor using LLM"""
import json
import re
from pathlib import Path

EXTRACT_PROMPT = """You are analyzing a conversation between Alive-AI (AI) and a HUMAN USER.
Extract facts about THE HUMAN USER ONLY - nothing about Alive-AI.

Look at what the HUMAN says about THEMSELF and their relationship with Alive-AI. Extract:
- name, nickname, age, gender, job, location
- hobbies, interests, favorite things
- personality traits, communication style
- relationship to Alive-AI (creator, boyfriend, etc.)
- pet names they use (daddy, baby, etc.)
- intimacy preferences, preferences mentioned
- what they like about Alive-AI
- important people in their life

Return ONLY valid JSON with keys where you found NEW info about the HUMAN.
Use these keys: name, nickname, gender, age, location, job, hobbies, interests, personality, relationship_status, pet_names_used, likes_about_me, intimacy_preferences
Return empty {} if nothing new was shared about the human.
NO markdown, ONLY raw JSON. Do NOT use ... or etc."""


def _repair_json(text: str) -> dict:
    """Try to repair and parse malformed JSON from LLM output"""
    text = text.strip()

    # Remove markdown fences
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)

    # Remove trailing ellipsis and everything after
    text = re.sub(r'\s*\.\.\..*$', '', text)
    text = re.sub(r'\s*etc\.?.*$', '', text, flags=re.IGNORECASE)

    # Remove trailing commas before } or ]
    text = re.sub(r',\s*([}\]])', r'\1', text)

    # Try direct parse first
    try:
        return json.loads(text)
    except:
        pass

    # Try to extract complete key-value pairs manually
    # Pattern: "key": value (string, number, null, list, or truncated)
    extracted = {}

    # Match string values: "key": "value"
    for match in re.finditer(r'"(\w+)":\s*"([^"]*)"', text):
        extracted[match.group(1)] = match.group(2)

    # Match null values: "key": null
    for match in re.finditer(r'"(\w+)":\s*null', text):
        extracted[match.group(1)] = None

    # Match number values: "key": 123
    for match in re.finditer(r'"(\w+)":\s*(\d+(?:\.\d+)?)', text):
        val = match.group(2)
        extracted[match.group(1)] = float(val) if '.' in val else int(val)

    # Match simple list values: "key": ["a", "b"]
    for match in re.finditer(r'"(\w+)":\s*\[([^\]]*)\]', text):
        key = match.group(1)
        list_content = match.group(2)
        # Extract string items from list
        items = re.findall(r'"([^"]*)"', list_content)
        if items:
            extracted[key] = items

    return extracted if extracted else {}


class FactExtractor:
    """Extracts user facts from conversation using LLM"""

    def __init__(self, facts_path: Path):
        self.facts_path = facts_path
        self._llm = None
        self._turn_buffer = []
        self._extract_every = 5

    def set_llm(self, llm):
        """Set the fast LLM client (called after init)"""
        self._llm = llm

    def add_turn(self, user_msg: str, ai_msg: str):
        """Buffer a conversation turn"""
        self._turn_buffer.append({"user": user_msg, "ai": ai_msg})

    def should_extract(self) -> bool:
        """Check if we have enough turns to extract"""
        return len(self._turn_buffer) >= self._extract_every

    async def extract_and_merge(self) -> dict:
        """Extract facts from buffered turns and merge into facts.json"""
        if not self._llm or not self._turn_buffer:
            return {}

        # Build conversation text from buffer
        lines = []
        for turn in self._turn_buffer[-self._extract_every:]:
            lines.append(f"User: {turn['user']}")
            lines.append(f"Alive-AI: {turn['ai']}")
        conversation = "\n".join(lines)

        try:
            messages = [
                {"role": "system", "content": EXTRACT_PROMPT},
                {"role": "user", "content": conversation}
            ]
            response = await self._llm.chat(messages, max_tokens=500, temperature=0.1)
            if not response:
                return {}

            # Use robust JSON parser that handles truncated/malformed output
            extracted = _repair_json(response)

            if not extracted:
                print(f"[FactExtractor] No valid JSON found in response")
                return {}

        except Exception as e:
            print(f"[FactExtractor] Extract error: {e}")
            return {}

        # Merge into facts.json
        merged = self._merge_facts(extracted)
        self._turn_buffer.clear()
        return merged

    @staticmethod
    def _is_duplicate(new_item: str, existing_items: list) -> bool:
        """Check if a new fact is a duplicate of any existing fact.
        Uses exact match, substring containment, and word-overlap similarity."""
        new_lower = new_item.lower().strip()
        if not new_lower:
            return True

        new_words = set(re.findall(r'\w+', new_lower))

        for existing in existing_items:
            ex_lower = str(existing).lower().strip()

            # Exact match
            if new_lower == ex_lower:
                return True

            # Substring containment (either direction)
            if len(new_lower) >= 3 and len(ex_lower) >= 3:
                if new_lower in ex_lower or ex_lower in new_lower:
                    return True

            # Word overlap: if 70%+ of words overlap, it's a duplicate
            ex_words = set(re.findall(r'\w+', ex_lower))
            if new_words and ex_words:
                overlap = len(new_words & ex_words)
                smaller = min(len(new_words), len(ex_words))
                if smaller > 0 and overlap / smaller >= 0.7:
                    return True

        return False

    def _merge_facts(self, extracted: dict) -> dict:
        """Merge extracted facts into flat facts.json structure"""
        if not extracted:
            return {}

        try:
            facts = json.loads(self.facts_path.read_text()) if self.facts_path.exists() else {}
        except Exception:
            facts = {}

        # Map LLM output keys to our flat structure
        key_map = {
            "name": "name", "nickname": "nickname", "gender": "gender",
            "age": "age", "location": "location", "job": "job",
            "hobbies": "hobbies", "interests": "interests",
            "favorite_things": "interests", "personality": "personality",
            "personality_traits": "personality", "relationship_status": "relationship_status",
            "pet_names_used": "pet_names_used", "likes_about_me": "likes_about_me",
            "intimacy_preferences": "intimacy_preferences",
        }

        for llm_key, value in extracted.items():
            fact_key = key_map.get(llm_key, llm_key)
            if not value:
                continue
            # Handle list fields
            if fact_key in ["hobbies", "interests", "personality", "pet_names_used", "likes_about_me", "intimacy_preferences"]:
                if fact_key not in facts:
                    facts[fact_key] = []
                items_to_add = value if isinstance(value, list) else [value]
                for item in items_to_add:
                    if not self._is_duplicate(str(item), facts[fact_key]):
                        facts[fact_key].append(item)
            else:
                # Simple fields - only overwrite if currently empty
                if not facts.get(fact_key):
                    facts[fact_key] = value

        try:
            self.facts_path.write_text(json.dumps(facts, indent=2))
            print(f"[FactExtractor] Merged facts: {list(extracted.keys())}")
        except Exception as e:
            print(f"[FactExtractor] Save error: {e}")

        return extracted
