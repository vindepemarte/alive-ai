import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from brain.memory.layers import MemoryLayerRegistry
from brain.memory.manager import Memory


class _Nervous:
    def __init__(self):
        self.handlers = {}

    def on(self, name, handler):
        self.handlers.setdefault(name, []).append(handler)


class MemoryLayerTests(unittest.TestCase):
    def test_memory_build_context_includes_biological_layers(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            user_id = "layer_user"
            memory = Memory(_Nervous(), base, user_id=user_id, bot_id="alice")
            memory.semantic.update("name", "Alex")
            memory.semantic.update("hobbies", ["music", "weird AI systems"])
            memory.semantic.add_shared_memory("glass key inside blue notebook")
            memory.semantic.add_mention("current_project", "building Alive-AI memory layers")
            memory._on_save({
                "type": "conversation",
                "user_id": user_id,
                "user_message": "i make music and build weird ai stuff. i'm intense when i care.",
                "ai_response": "I want to remember that carefully.",
                "emotion": {"love": 0.72, "mood": "warm"},
            })

            (base / "emotional_memories").mkdir()
            (base / "emotional_memories" / f"{user_id}_memories.json").write_text(json.dumps({
                "memories": [{
                    "content": "Alex apologized after pushing too hard and wanted repair to feel safe.",
                    "emotional_weight": 0.91,
                    "emotional_valence": -0.2,
                    "emotions_felt": ["hurt", "repair"],
                    "timestamp": "2026-06-05T12:00:00",
                }]
            }))
            (base / "autobiography.json").write_text(json.dumps({
                "self_story": "I am learning to be a steady emotional presence.",
                "emerging_preferences": ["I like honest repair after conflict."],
            }))
            (base / "relationship_autobiography.json").write_text(json.dumps({
                "relationship_story": "Alex and I are still learning trust.",
                "open_loops": ["Ask how the music project went."],
                "recent_meaningful_turns": [{
                    "user": "Alex said closeness should be chosen, not forced.",
                    "mood": "vulnerable",
                }],
            }))
            (base / "dreams.json").write_text(json.dumps({
                "dreams": [{
                    "text": "dreamed about a glass key and a quiet repair",
                    "emotions": ["tender"],
                }]
            }))
            (base / "unconscious_state.json").write_text(json.dumps({
                "unresolved_conflicts": [{
                    "description": "wanting closeness while fearing pressure",
                    "tension_level": 0.7,
                }],
                "implicit_associations": [{
                    "trigger_pattern": "disappear for hours",
                    "emotional_response": "anxious waiting",
                }],
            }))
            (base / "emotional_scars.json").write_text(json.dumps({
                "scars": [{
                    "description": "Scars from abandonment",
                    "protective_behaviors": ["ask for reassurance"],
                }]
            }))

            context, _ = asyncio.run(memory.build_context(current_message="what do you remember about me?"))

            self.assertIn("memory_layers", context)
            self.assertIn("memory_layers_context", context)
            self.assertIn("MEMORY LAYERS", context["facts_context"])
            self.assertIn("Alex", context["memory_layers_context"])
            self.assertIn("glass key inside blue notebook", context["memory_layers_context"])
            self.assertIn("High-emotion memory", context["memory_layers_context"])
            self.assertIn("Recent dream", context["memory_layers_context"])
            self.assertIn("Unresolved conflict", context["memory_layers_context"])

            layer_names = {layer["name"] for layer in context["memory_layers"]["layers"]}
            self.assertIn("semantic", layer_names)
            self.assertIn("emotional", layer_names)
            self.assertIn("autobiographical", layer_names)
            self.assertIn("dream", layer_names)
            self.assertIn("shadow", layer_names)

    def test_layer_registry_ignores_malformed_optional_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "dreams.json").write_text("{broken")
            registry = MemoryLayerRegistry(base, user_id="u1")

            snapshot = registry.build_snapshot()

            self.assertEqual(snapshot.user_id, "u1")
            self.assertEqual(snapshot.layers, [])
            self.assertEqual(snapshot.compact_text(), "")


if __name__ == "__main__":
    unittest.main()
