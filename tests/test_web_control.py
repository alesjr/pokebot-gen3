import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from modules.web.control import GBA_BUTTONS, _profile_file, reset_profile, send_button

class TestWebControl(unittest.TestCase):
    def test_expected_gba_buttons_are_allowlisted(self):
        self.assertEqual(GBA_BUTTONS, {"A", "B", "L", "R", "Start", "Select", "Up", "Down", "Left", "Right"})

    def test_unknown_button_is_rejected_before_queueing(self):
        with patch("modules.web.control.on_main_thread") as queue:
            with self.assertRaises(ValueError):
                send_button("Escape", "hold")
            queue.assert_not_called()

    def test_unknown_action_is_rejected_before_queueing(self):
        with patch("modules.web.control.on_main_thread") as queue:
            with self.assertRaises(ValueError):
                send_button("A", "execute")
            queue.assert_not_called()

    def test_profile_file_rejects_path_traversal(self):
        with self.assertRaises(ValueError):
            _profile_file("state", "../../secret.ss1")

    def test_profile_file_rejects_unknown_kind(self):
        with self.assertRaises(ValueError):
            _profile_file("rom", "game.gba")

    def test_reset_profile_requires_exact_confirmation(self):
        profile = SimpleNamespace(path=Path("/profiles/Ruby"))
        with (
            patch("modules.profiles.list_available_profiles", return_value=[profile]),
            patch("modules.web.control.context.profile", profile),
        ):
            with self.assertRaises(ValueError):
                reset_profile("Ruby", "ruby")

    def test_active_profile_reset_moves_runtime_data_and_preserves_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            profile_path = Path(directory) / "Ruby"
            profile_path.mkdir()
            (profile_path / "metadata.yml").write_text("version: 1")
            (profile_path / "living_dex.yml").write_text("quality: {}")
            (profile_path / "current_save.sav").write_bytes(b"save")
            (profile_path / "states").mkdir()
            (profile_path / "states" / "old.ss1").write_bytes(b"state")
            profile = SimpleNamespace(path=profile_path)
            with (
                patch("modules.profiles.list_available_profiles", return_value=[profile]),
                patch("modules.web.control.context.profile", profile),
                patch("modules.web.control.context.emulator"),
                patch("modules.web.control.context.set_manual_mode"),
                patch("modules.web.control._schedule_profile_restart"),
                patch("modules.web.control.on_main_thread", side_effect=lambda callback, timeout=5: callback()),
            ):
                result = reset_profile("Ruby", "Ruby")
            backup = next((profile_path / "reset_backups").iterdir())
            self.assertTrue((backup / "current_save.sav").is_file())
            self.assertTrue((backup / "states" / "old.ss1").is_file())
            self.assertTrue((profile_path / "metadata.yml").is_file())
            self.assertTrue((profile_path / "living_dex.yml").is_file())
            self.assertTrue(result["restarting"])

if __name__ == "__main__":
    unittest.main()
