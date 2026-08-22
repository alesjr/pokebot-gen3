import unittest

from modules.living_dex.goals import CollectionTarget, build_collection_targets
from modules.living_dex.planner import (
    AcquisitionOption,
    choose_assignment,
    load_acquisition_matrix,
    route_can_advance,
    validate_acquisition_matrix,
)


class TestLivingDexPlanner(unittest.TestCase):
    def setUp(self):
        self.target = CollectionTarget(270, "Lotad", "female", True)

    def test_assigns_lowest_cost_available_version(self):
        options = [
            AcquisitionOption(20, "Emerald", "Lotad", "wild", "Route 102"),
            AcquisitionOption(10, "Sapphire", "Lotad", "wild", "Route 102"),
        ]
        assignment = choose_assignment(
            self.target,
            options,
            {"Emerald": "LivingDex-Emerald", "Sapphire": "LivingDex-Sapphire"},
            {},
        )
        self.assertEqual(assignment.profile, "LivingDex-Sapphire")

    def test_locked_option_is_not_assigned(self):
        options = [AcquisitionOption(1, "Emerald", "Lotad", "breeding", "Day Care", ("RSE-039",))]
        self.assertIsNone(
            choose_assignment(self.target, options, {"Emerald": "LivingDex-Emerald"}, {},)
        )

    def test_route_barrier_requires_collection_and_strength(self):
        self.assertFalse(route_can_advance(missing_route_targets=1, lowest_usable_level=20, required_level=10))
        self.assertFalse(route_can_advance(missing_route_targets=0, lowest_usable_level=9, required_level=10))
        self.assertTrue(route_can_advance(missing_route_targets=0, lowest_usable_level=10, required_level=10))

    def test_generated_matrix_covers_every_species(self):
        validate_acquisition_matrix(build_collection_targets(), load_acquisition_matrix())

    def test_deoxys_form_is_assigned_to_matching_game(self):
        target = CollectionTarget(386, "Deoxys", "speed", True)
        assignment = choose_assignment(
            target,
            load_acquisition_matrix(),
            {game: f"LivingDex-{game}" for game in ("Ruby", "FireRed", "LeafGreen", "Emerald")},
            {},
        )
        self.assertEqual(assignment.profile, "LivingDex-Emerald")
