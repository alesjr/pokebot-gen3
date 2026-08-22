import json
import tempfile
import unittest
from pathlib import Path

from modules.fleet.config import load_fleet_config, validate_assets
from modules.config import load_config_file
from modules.config.schemas_v1 import LivingDex
from modules.fleet.bootstrap import atomic_create, living_dex_config


class TestFleetConfig(unittest.TestCase):
    def test_repository_fleet_config_has_five_isolated_instances(self):
        root = Path(__file__).parents[1]
        config = load_fleet_config(root / "fleet.yml")
        self.assertEqual(len(config.instances), 5)
        self.assertEqual(len({item.profile for item in config.instances}), 5)
        self.assertEqual(len({item.port for item in config.instances}), 5)

    def test_duplicate_port_fails_before_start(self):
        root = Path(__file__).parents[1]
        raw = json.loads((root / "fleet.yml").read_text(encoding="utf-8"))
        raw["instances"][1]["port"] = raw["instances"][0]["port"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fleet.yml"
            path.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "ports must be unique"):
                load_fleet_config(path)

    def test_existing_profile_must_own_configured_rom(self):
        root = Path(__file__).parents[1]
        config = load_fleet_config(root / "fleet.yml")
        with tempfile.TemporaryDirectory() as directory:
            fake_root = Path(directory)
            (fake_root / "roms").mkdir()
            (fake_root / "profiles").mkdir()
            for item in config.instances:
                (fake_root / "roms" / item.rom).touch()
            profile = fake_root / "profiles" / config.instances[0].profile
            profile.mkdir()
            (profile / "metadata.yml").write_text("game_code: WRONG\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "ownership mismatch"):
                validate_assets(config, fake_root)

    def test_bootstrap_writes_game_specific_identity_and_starter_once(self):
        root = Path(__file__).parents[1]
        config = load_fleet_config(root / "fleet.yml")
        fire_red = next(item for item in config.instances if item.game == "FireRed")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "living_dex.yml"
            atomic_create(path, living_dex_config(config, fire_red))
            loaded = load_config_file(path, LivingDex, strict=True)
            self.assertEqual(loaded.gameplay.trainer_name, "Alesjr")
            self.assertEqual(loaded.gameplay.trainer_gender, "male")
            self.assertEqual(loaded.gameplay.starter, "Charmander")
            atomic_create(path, "invalid overwrite")
            self.assertEqual(load_config_file(path, LivingDex, strict=True).gameplay.starter, "Charmander")

    def test_starter_from_wrong_game_family_is_rejected(self):
        root = Path(__file__).parents[1]
        raw = json.loads((root / "fleet.yml").read_text(encoding="utf-8"))
        raw["instances"][0]["starter"] = "Charmander"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fleet.yml"
            path.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "starter must be available"):
                load_fleet_config(path)
