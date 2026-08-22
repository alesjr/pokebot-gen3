import unittest
from unittest.mock import patch

from modules.living_dex.rse_missions import (
    RSE_MISSION_CLASSES,
    StartDevonGoodsCaseMission,
)
from modules.living_dex.rse_mission_controller import (
    RSEMissionController,
    RSEMissionDefinition,
)
from modules.map_data import MapRSE


class FakeNavigator:
    def __init__(self, events):
        self.events = events

    def go_to(self, map_id, coordinates):
        self.events.append(("navigate", map_id, coordinates))
        yield "navigation-frame"


class TestRSEMissionClasses(unittest.TestCase):
    def test_every_implemented_story_mission_has_its_own_class(self):
        expected_ids = {f"RSE-{number:03d}" for number in range(1, 29)}

        self.assertEqual(set(RSE_MISSION_CLASSES), expected_ids)
        self.assertEqual(len(set(RSE_MISSION_CLASSES.values())), len(expected_ids))

    def test_mission_navigates_to_declared_start_before_running_action(self):
        events = []

        def handler(**options):
            events.append(("handler", options))
            yield "mission-frame"

        mission = StartDevonGoodsCaseMission(FakeNavigator(events))
        with patch(
            "modules.living_dex.campaign_rse.run_rse_start_devon_goods_case",
            handler,
        ):
            frames = list(mission.run(timeout_frames=123))

        self.assertEqual(
            events,
            [
                ("navigate", MapRSE.RUSTBORO_CITY, (23, 20)),
                ("handler", {"timeout_frames": 123}),
            ],
        )
        self.assertEqual(frames, ["navigation-frame", "mission-frame"])

    def test_controller_uses_save_checks_and_resumes_first_incomplete_mission(self):
        state = {"first": True, "second": False}
        campaign = (
            RSEMissionDefinition("RSE-001", "First", lambda: state["first"]),
            RSEMissionDefinition("RSE-002", "Second", lambda: state["second"]),
        )
        events = []

        class FakeMission:
            def run(self, **options):
                events.append(options)
                state["second"] = True
                yield "frame"

        controller = RSEMissionController(
            set_navigation_encounter_policy=lambda *args: None,
            mission_factory=lambda mission_class: FakeMission(),
            campaign=campaign,
        )

        self.assertEqual(controller.next_mission().mission_id, "RSE-002")
        self.assertEqual(list(controller.run_next()), ["frame"])
        self.assertIsNone(controller.next_mission())


if __name__ == "__main__":
    unittest.main()
