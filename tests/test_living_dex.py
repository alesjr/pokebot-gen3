import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from modules.living_dex.distributions import InvalidDistributionDump, inspect_distribution
from modules.living_dex.collection import storage_has_space
from modules.living_dex.campaign_rse import starter_qualifies
from modules.living_dex.missions import (
    MissionTracker,
    RouteHuntRequirement,
    load_mission_catalog,
    validate_mission_graph,
)
from modules.living_dex.rng import advance, find_method1_target, method1_frame
from modules.living_dex.quests import QUESTS, next_quest


class TestStarterPolicy(unittest.TestCase):
    def test_production_policy_requires_shiny(self):
        self.assertFalse(starter_qualifies(SimpleNamespace(is_shiny=False)))
        self.assertTrue(starter_qualifies(SimpleNamespace(is_shiny=True)))
        self.assertTrue(starter_qualifies(SimpleNamespace(is_shiny=False), require_shiny=False))


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
    class _Stats:
        def __init__(self):
            self.statuses = []

        def set_living_dex_mission_status(self, family, mission_id, status, evidence):
            self.statuses.append((family, mission_id, status, evidence))

    def test_documented_mission_catalog_is_complete(self):
        catalog = load_mission_catalog(Path(__file__).parents[1])
        self.assertEqual(len([mission for mission in catalog if mission.family == "RSE"]), 139)
        self.assertEqual(len([mission for mission in catalog if mission.family == "FRLG"]), 178)
        validate_mission_graph(catalog)

    def test_documented_fields_override_id_prefix_inference(self):
        catalog = load_mission_catalog(Path(__file__).parents[1])
        emerald_postgame = next(mission for mission in catalog if mission.mission_id == "E-POST-016")
        self.assertEqual(emerald_postgame.category, "POSTGAME")
        self.assertEqual(emerald_postgame.games, ("E",))

    def test_mission_flags_are_normalized_for_runtime_lookup(self):
        catalog = load_mission_catalog(Path(__file__).parents[1])
        starter = next(
            mission for mission in catalog if mission.family == "RSE" and mission.mission_id == "RSE-003"
        )
        self.assertIn("SYS_POKEMON_GET", starter.flags)
        self.assertIn("RESCUED_BIRCH", starter.flags)

    def test_route_requires_shinies_and_strength_before_departure(self):
        self.assertFalse(RouteHuntRequirement(16, 1, 20).can_leave_route)
        self.assertFalse(RouteHuntRequirement(16, 0, 15).can_leave_route)
        self.assertTrue(RouteHuntRequirement(16, 0, 16).can_leave_route)

    def test_hunt_pauses_before_capture_when_boxes_are_full(self):
        self.assertTrue(storage_has_space(SimpleNamespace(pokemon_count=419)))
        self.assertFalse(storage_has_space(SimpleNamespace(pokemon_count=420)))

    def test_sapphire_kyogre_reconciles_save_and_advances_story(self):
        rom = SimpleNamespace(
            is_ruby=False,
            is_sapphire=True,
            is_emerald=False,
            is_frlg=False,
        )
        stats = self._Stats()
        tracker = MissionTracker(rom, stats)
        encounter = SimpleNamespace(
            name="Groudon/Kyogre",
            map=SimpleNamespace(name="CAVE_OF_ORIGIN_B1F"),
        )

        current = tracker.activate_static_encounter(encounter)
        self.assertEqual(current.mission_id, "S-067")
        self.assertIn(("RSE", "S-067", "IN_PROGRESS", "static_encounter:Groudon/Kyogre"), stats.statuses)
        self.assertTrue(
            any(mission_id == "RS-066" and status == "COMPLETED" for _, mission_id, status, _ in stats.statuses)
        )

        following = tracker.complete_active_static()
        self.assertEqual(following.mission_id, "RS-068")
        self.assertIn(("RSE", "S-067", "COMPLETED", "shiny_caught_and_game_saved"), stats.statuses)
        self.assertIn(("RSE", "RS-068", "AVAILABLE", "previous_completed:S-067"), stats.statuses)

    def test_next_quest_returns_first_incomplete_milestone(self):
        completed = {QUESTS[0].flag, QUESTS[1].flag}
        self.assertEqual(next_quest(lambda flag: flag in completed), QUESTS[2])

    def test_next_quest_returns_none_when_story_is_complete(self):
        self.assertIsNone(next_quest(lambda flag: True))


if __name__ == "__main__":
    unittest.main()
