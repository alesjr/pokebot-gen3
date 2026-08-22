import unittest

from modules.living_dex.campaign import (
    CampaignAction,
    CampaignBlocked,
    CampaignCondition,
    CampaignEngine,
    CampaignNode,
    CartridgeSnapshot,
)


def node(mission_id, prerequisites=(), flag=None, attempts=2):
    return CampaignNode(
        mission_id,
        prerequisites,
        (),
        CampaignAction.TALK,
        (CampaignCondition("flag", flag or mission_id),),
        f"saved:{mission_id}",
        attempts,
    )


class TestCampaignEngine(unittest.TestCase):
    def test_cartridge_state_overrides_empty_history_after_restart(self):
        engine = CampaignEngine(
            (node("FIRST"), node("SECOND", ("FIRST",))),
            {CampaignAction.TALK: lambda mission: mission.mission_id},
        )
        completed, current = engine.reconcile(CartridgeSnapshot(flags=frozenset({"FIRST"})))
        self.assertEqual(completed, {"FIRST"})
        self.assertEqual(current.mission_id, "SECOND")

    def test_checkpoint_requires_observed_completion(self):
        engine = CampaignEngine((node("FIRST"),), {CampaignAction.TALK: lambda mission: None})
        engine.start_current(CartridgeSnapshot())
        with self.assertRaisesRegex(CampaignBlocked, "completion_not_observed"):
            engine.confirm_checkpoint(CartridgeSnapshot())
        self.assertEqual(
            engine.confirm_checkpoint(CartridgeSnapshot(flags=frozenset({"FIRST"}))),
            "saved:FIRST",
        )

    def test_attempt_limit_blocks_with_explainable_reason(self):
        engine = CampaignEngine(
            (node("FIRST", attempts=1),), {CampaignAction.TALK: lambda mission: None}
        )
        engine.start_current(CartridgeSnapshot())
        with self.assertRaisesRegex(CampaignBlocked, "attempt_limit:FIRST"):
            engine.start_current(CartridgeSnapshot())

    def test_missing_handler_blocks_instead_of_advancing(self):
        engine = CampaignEngine((node("FIRST"),), {})
        with self.assertRaisesRegex(CampaignBlocked, "missing_action_handler:talk"):
            engine.start_current(CartridgeSnapshot())

    def test_rejects_cycle_and_unknown_prerequisite(self):
        with self.assertRaisesRegex(ValueError, "cycle"):
            CampaignEngine((node("A", ("B",)), node("B", ("A",))), {})
        with self.assertRaisesRegex(ValueError, "unknown prerequisite"):
            CampaignEngine((node("A", ("MISSING",)),), {})

    def test_preconditions_cover_map_inventory_party_storage_and_state(self):
        conditions = tuple(
            CampaignCondition(kind, value)
            for kind, value in (
                ("map", "ROUTE1"),
                ("item", "POKE_BALL"),
                ("party", "Pikachu"),
                ("storage", "Bulbasaur"),
                ("game_state", "OVERWORLD"),
            )
        )
        campaign_node = CampaignNode(
            "A", (), conditions, CampaignAction.NAVIGATE,
            (CampaignCondition("flag", "DONE"),), "safe-save", 1,
        )
        snapshot = CartridgeSnapshot(
            map_name="ROUTE1",
            inventory=frozenset({"POKE_BALL"}),
            party_species=("Pikachu",),
            storage_species=frozenset({"Bulbasaur"}),
            game_state="OVERWORLD",
        )
        self.assertTrue(campaign_node.is_available(snapshot, set()))


if __name__ == "__main__":
    unittest.main()
