import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from modules.living_dex.distributions import InvalidDistributionDump, inspect_distribution
from modules.living_dex.rng import advance, find_method1_target, method1_frame
from modules.living_dex.quests import QUESTS, next_quest


class TestLivingDexRng(unittest.TestCase):
    def test_lcrng_known_step(self):
        self.assertEqual(advance(0), 0x6073)

    def test_method1_is_deterministic(self):
        first = method1_frame(0x12345678, 42)
        second = method1_frame(0x12345678, 42)
        self.assertEqual(first, second)
        self.assertEqual(len(first.ivs), 6)
        self.assertTrue(all(0 <= iv <= 31 for iv in first.ivs))

    def test_predictor_respects_limit(self):
        self.assertIsNone(find_method1_target(0x12345678, 1, 2, limit=0))

    def test_distribution_rejects_non_gba_data(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "event.gba"
            path.write_bytes(bytes(0x1000))
            with self.assertRaises(InvalidDistributionDump):
                inspect_distribution(path)


class TestLivingDexQuests(unittest.TestCase):
    def test_next_quest_returns_first_incomplete_milestone(self):
        completed = {QUESTS[0].flag, QUESTS[1].flag}
        self.assertEqual(next_quest(lambda flag: flag in completed), QUESTS[2])

    def test_next_quest_returns_none_when_story_is_complete(self):
        self.assertIsNone(next_quest(lambda flag: True))


if __name__ == "__main__":
    unittest.main()
