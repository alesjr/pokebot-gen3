import unittest

from modules.living_dex.goals import build_collection_targets, validate_collection_targets


class TestLivingDexGoals(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.targets = build_collection_targets()

    def test_global_target_contract(self):
        validate_collection_targets(self.targets)
        shiny_species = {target.species for target in self.targets if target.shiny_required}
        self.assertEqual(len(shiny_species), 385)

    def test_both_genders_are_targets_when_species_supports_them(self):
        pikachu = {target.variant for target in self.targets if target.species == "Pikachu"}
        self.assertEqual(pikachu, {"male", "female"})

    def test_special_persistent_forms_are_finite(self):
        unown = [target for target in self.targets if target.species == "Unown"]
        deoxys = [target for target in self.targets if target.species == "Deoxys"]
        spinda = [target for target in self.targets if target.species == "Spinda"]
        self.assertEqual(len(unown), 28)
        self.assertEqual({target.variant for target in deoxys}, {"normal", "attack", "defense", "speed"})
        self.assertEqual(len(spinda), 1)

    def test_celebi_is_normal_official_event_exception(self):
        celebi = [target for target in self.targets if target.species == "Celebi"]
        self.assertEqual(len(celebi), 1)
        self.assertFalse(celebi[0].shiny_required)
        self.assertTrue(celebi[0].official_event_required)
