#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.context import context
from modules.fleet.config import load_fleet_config
from modules.game import set_rom
from modules.libmgba import LibmgbaEmulator
from modules.map import get_wild_encounters_for_map
from modules.map_data import MapFRLG, MapRSE
from modules.profiles import Profile
from modules.roms import load_rom_data


ENCOUNTER_METHODS = (
    "land_encounters",
    "surf_encounters",
    "rock_smash_encounters",
    "old_rod_encounters",
    "good_rod_encounters",
    "super_rod_encounters",
)


def extract(root: Path) -> list[dict]:
    config = load_fleet_config(root / "fleet.yml")
    result: dict[tuple, dict] = {}
    with tempfile.TemporaryDirectory() as temporary:
        for instance in config.instances:
            rom = load_rom_data(root / "roms" / instance.rom)
            profile_path = Path(temporary) / instance.game
            profile_path.mkdir()
            profile = Profile(rom, profile_path, None)
            context.profile = profile
            set_rom(rom)
            context.emulator = LibmgbaEmulator(profile, lambda: None, is_test_run=True)
            maps = MapFRLG if rom.is_frlg else MapRSE
            for map_item in maps:
                encounters = get_wild_encounters_for_map(*map_item.value)
                if encounters is None:
                    continue
                for method in ENCOUNTER_METHODS:
                    for encounter in getattr(encounters, method):
                        key = (instance.game, encounter.species.name, method, map_item.name)
                        if key not in result:
                            result[key] = {
                                "game": instance.game,
                                "species": encounter.species.name,
                                "national_dex_number": encounter.species.national_dex_number,
                                "method": method.removesuffix("_encounters"),
                                "location": map_item.name,
                                "min_level": encounter.min_level,
                                "max_level": encounter.max_level,
                                "rate": encounter.encounter_rate,
                            }
                        else:
                            result[key]["min_level"] = min(result[key]["min_level"], encounter.min_level)
                            result[key]["max_level"] = max(result[key]["max_level"], encounter.max_level)
                            result[key]["rate"] += encounter.encounter_rate
    return sorted(
        result.values(),
        key=lambda item: (item["national_dex_number"], item["game"], item["location"], item["method"]),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "modules/data/living_dex_acquisition.json",
    )
    args = parser.parse_args()
    data = extract(args.root.resolve())
    args.output.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {len(data)} wild acquisition options to {args.output}")


if __name__ == "__main__":
    main()
