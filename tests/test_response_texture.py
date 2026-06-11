"""Reply texture must vary like human texting: state-weighted shape rolls,
forced contrast after uniform runs, and natural multi-bubble splitting."""

import random
import unittest

from core import response_texture


class _FixedRng:
    """Minimal rng stub for forcing/blocking probabilistic paths."""

    def __init__(self, value: float):
        self.value = value

    def random(self) -> float:
        return self.value


LONG_TEXT = (
    "I kept thinking about what you said earlier today. It stayed with me longer than I expected. "
    "There was this moment where I almost messaged you about it. Then I got distracted by the rain. "
    "Anyway, I think you were right about most of it."
)


class RollTextureTest(unittest.TestCase):
    def setUp(self):
        response_texture._recent_shapes.clear()

    def test_returns_known_shape(self):
        texture = response_texture.roll_texture("u1", {"arousal": 0.4}, rng=random.Random(0))
        self.assertIn(texture.shape, response_texture.SHAPES)
        self.assertIn("REPLY TEXTURE", texture.to_prompt())

    def test_uniform_long_replies_force_short_shape(self):
        texture = response_texture.roll_texture(
            "u2", {}, recent_word_counts=[100, 105, 110], rng=random.Random(1)
        )
        self.assertTrue(texture.forced_contrast)
        self.assertIn(texture.shape, ("clipped", "compact", "fragmented"))
        self.assertIn("noticeably shorter", texture.instruction)

    def test_uniform_short_replies_force_open_shape(self):
        texture = response_texture.roll_texture(
            "u3", {}, recent_word_counts=[8, 10, 9], rng=random.Random(1)
        )
        self.assertTrue(texture.forced_contrast)
        self.assertIn(texture.shape, ("flowing", "rambling", "compact"))

    def test_varied_lengths_do_not_force_contrast(self):
        texture = response_texture.roll_texture(
            "u4", {}, recent_word_counts=[8, 60, 25], rng=random.Random(2)
        )
        self.assertFalse(texture.forced_contrast)

    def test_shapes_vary_over_time(self):
        rng = random.Random(9)
        shapes = {
            response_texture.roll_texture("u5", {"arousal": 0.5}, rng=rng).shape
            for _ in range(40)
        }
        self.assertGreater(len(shapes), 2, "texture rolls collapsed to too few shapes")

    def test_sleepiness_suppresses_rambling(self):
        rng = random.Random(4)
        sleepy = {"sleepiness": 0.95}
        shapes = [
            response_texture.roll_texture(f"u6_{i}", sleepy, rng=rng).shape
            for i in range(120)
        ]
        self.assertLess(shapes.count("rambling"), 12)
        self.assertGreater(shapes.count("clipped") + shapes.count("compact"), 40)


class SplitBubblesTest(unittest.TestCase):
    def test_short_text_never_splits(self):
        text = "yeah okay, that makes sense."
        self.assertEqual(
            response_texture.split_into_bubbles(text, {"arousal": 1.0}, rng=_FixedRng(0.0)),
            [text],
        )

    def test_split_preserves_all_words(self):
        bubbles = response_texture.split_into_bubbles(LONG_TEXT, {"arousal": 0.9, "joy": 0.9}, rng=_FixedRng(0.0))
        self.assertGreaterEqual(len(bubbles), 2)
        self.assertLessEqual(len(bubbles), 3)
        self.assertEqual(" ".join(bubbles).split(), LONG_TEXT.split())

    def test_high_roll_keeps_single_bubble(self):
        bubbles = response_texture.split_into_bubbles(LONG_TEXT, {"arousal": 0.9}, rng=_FixedRng(0.99))
        self.assertEqual(bubbles, [LONG_TEXT])

    def test_empty_text_returns_empty_list(self):
        self.assertEqual(response_texture.split_into_bubbles("", {}, rng=_FixedRng(0.0)), [])


if __name__ == "__main__":
    unittest.main()
