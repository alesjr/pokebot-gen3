import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from modules.fleet.config import load_fleet_config
from modules.fleet.database import FleetDatabase, FleetSpecimen, LeaseUnavailable
from modules.living_dex.goals import build_collection_targets
from modules.living_dex.planner import AcquisitionOption


class TestFleetDatabase(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        path = Path(self.temporary.name) / "fleet.db"
        self.first = FleetDatabase(path)
        self.second = FleetDatabase(path)
        config = load_fleet_config(Path(__file__).parents[1] / "fleet.yml")
        self.first.sync_instances(config.instances)
        self.first.sync_collection_targets(build_collection_targets())
        self.first.sync_acquisition_options(
            (
                AcquisitionOption(1, "Ruby", "Pikachu", "wild", "ROUTE1"),
                AcquisitionOption(1, "Sapphire", "Pikachu", "wild", "ROUTE2"),
            )
        )

    def tearDown(self):
        self.first.close()
        self.second.close()
        self.temporary.cleanup()

    def test_only_one_writer_can_lease_profile(self):
        lease = self.first.acquire_lease("LivingDex-Ruby", "bot-ruby", "bot")
        with self.assertRaises(LeaseUnavailable):
            self.second.acquire_lease("LivingDex-Ruby", "trade-worker", "trade")
        self.assertTrue(self.first.release_lease(lease.token))
        self.second.acquire_lease("LivingDex-Ruby", "trade-worker", "trade")

    def test_expired_lease_can_be_replaced(self):
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.first.acquire_lease("LivingDex-Emerald", "old", "bot", ttl_seconds=5, now=now)
        replacement = self.second.acquire_lease(
            "LivingDex-Emerald", "new", "recovery", now=now + timedelta(seconds=6)
        )
        self.assertEqual(replacement.owner, "new")

    def test_wrong_token_cannot_release_lease(self):
        self.first.acquire_lease("LivingDex-FireRed", "bot", "bot")
        self.assertFalse(self.second.release_lease("wrong-token"))
        self.assertEqual(self.first.state()[3]["lease_owner"], "bot")

    def test_same_specimen_observed_twice_appears_once(self):
        specimen = FleetSpecimen(123, "Pikachu", 25, "Alesjr", 1, 2, "LivingDex-Ruby", "male", "any", True)
        self.first.register_specimen(specimen)
        self.second.register_specimen(specimen)
        summary = self.first.collection_summary()
        self.assertEqual(summary["specimens"], 1)
        missing_pikachu = [item for item in summary["missing"] if item["species"] == "Pikachu"]
        self.assertEqual({item["variant"] for item in missing_pikachu}, {"female"})

    def test_normal_celebi_requires_official_event_provenance(self):
        unofficial = FleetSpecimen(200, "Celebi", 251, "Alesjr", 1, 2, "LivingDex-Ruby", "any", "any", False)
        self.first.register_specimen(unofficial)
        self.assertTrue(any(item["species"] == "Celebi" for item in self.first.collection_summary()["missing"]))
        official = FleetSpecimen(201, "Celebi", 251, "EVENT", 3, 4, "LivingDex-Ruby", "any", "any", False, True)
        self.first.register_specimen(official)
        self.assertFalse(any(item["species"] == "Celebi" for item in self.first.collection_summary()["missing"]))

    def test_reconciliation_removes_specimens_no_longer_in_profile(self):
        specimen = FleetSpecimen(300, "Raichu", 26, "Alesjr", 1, 2, "LivingDex-Ruby", "female", "any", True)
        self.first.reconcile_specimens("LivingDex-Ruby", [specimen])
        self.assertEqual(self.first.collection_summary()["specimens"], 1)
        self.second.reconcile_specimens("LivingDex-Ruby", [])
        self.assertEqual(self.first.collection_summary()["specimens"], 0)

    def test_target_assignment_is_exclusive_and_recovers_after_expiry(self):
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        ruby = self.first.acquire_target("LivingDex-Ruby", set(), ttl_seconds=5, now=now)
        sapphire = self.second.acquire_target("LivingDex-Sapphire", set(), now=now)
        self.assertEqual(ruby["species"], "Pikachu")
        self.assertNotEqual(
            (ruby["national_dex_number"], ruby["variant"]),
            (sapphire["national_dex_number"], sapphire["variant"]),
        )
        replacement = self.second.acquire_target(
            "LivingDex-Sapphire", set(), now=now + timedelta(seconds=6)
        )
        self.assertEqual(
            (replacement["national_dex_number"], replacement["variant"]),
            (ruby["national_dex_number"], ruby["variant"]),
        )

    def test_target_assignment_survives_option_resync(self):
        assignment = self.first.acquire_target("LivingDex-Ruby", set())
        self.second.sync_collection_targets(build_collection_targets())
        self.second.sync_acquisition_options(
            (AcquisitionOption(2, "Ruby", "Pikachu", "wild", "ROUTE1"),)
        )
        self.assertEqual(self.first.assignments()[0]["profile"], assignment["profile"])

    def test_reconciliation_completes_matching_assignment(self):
        assignment = self.first.acquire_target("LivingDex-Ruby", set())
        specimen = FleetSpecimen(
            999,
            assignment["species"],
            assignment["national_dex_number"],
            "Alesjr",
            1,
            2,
            "LivingDex-Ruby",
            assignment["variant"],
            assignment["variant"],
            True,
        )
        self.first.reconcile_specimens("LivingDex-Ruby", [specimen])
        self.assertEqual(self.first.prune_satisfied_assignments(), 1)
        self.assertEqual(self.first.assignments(), [])
