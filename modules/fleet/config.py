from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


EXPECTED_GAMES = {"Ruby", "Sapphire", "Emerald", "FireRed", "LeafGreen"}


@dataclass(frozen=True)
class FleetInstance:
    game: str
    profile: str
    rom: str
    game_code: str
    revision: int
    starter: str
    port: int
    priority: int


@dataclass(frozen=True)
class FleetConfig:
    trainer_name: str
    trainer_gender: str
    dashboard_port: int
    video_fps: int
    jpeg_quality: int
    instances: tuple[FleetInstance, ...]


def load_fleet_config(path: Path) -> FleetConfig:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        instances = tuple(FleetInstance(**item) for item in raw["instances"])
        config = FleetConfig(
            trainer_name=raw["trainer"]["name"],
            trainer_gender=raw["trainer"]["gender"],
            dashboard_port=raw["dashboard_port"],
            video_fps=raw["video"]["fps"],
            jpeg_quality=raw["video"]["jpeg_quality"],
            instances=instances,
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid fleet config: {error}") from error
    validate_fleet_config(config)
    return config


def validate_fleet_config(config: FleetConfig) -> None:
    errors: list[str] = []
    games = [item.game for item in config.instances]
    profiles = [item.profile for item in config.instances]
    ports = [config.dashboard_port, *(item.port for item in config.instances)]
    priorities = [item.priority for item in config.instances]
    starters = {item.game: item.starter for item in config.instances}

    if set(games) != EXPECTED_GAMES or len(games) != len(EXPECTED_GAMES):
        errors.append("instances must contain all five supported games exactly once")
    if len(profiles) != len(set(profiles)):
        errors.append("profile names must be unique")
    if any(not name or "/" in name or "\\" in name or name in {".", ".."} for name in profiles):
        errors.append("profile names must be safe directory names")
    if len(ports) != len(set(ports)):
        errors.append("dashboard and instance ports must be unique")
    if any(not isinstance(port, int) or not 1 <= port <= 65535 for port in ports):
        errors.append("ports must be integers between 1 and 65535")
    if len(priorities) != len(set(priorities)):
        errors.append("priorities must be unique")
    if config.trainer_name != "Alesjr" or config.trainer_gender != "male":
        errors.append("trainer identity must be Alesjr/male")
    expected_starters = {
        "Ruby": {"Treecko", "Torchic", "Mudkip"},
        "Sapphire": {"Treecko", "Torchic", "Mudkip"},
        "Emerald": {"Treecko", "Torchic", "Mudkip"},
        "FireRed": {"Bulbasaur", "Charmander", "Squirtle"},
        "LeafGreen": {"Bulbasaur", "Charmander", "Squirtle"},
    }
    if any(starters.get(game) not in allowed for game, allowed in expected_starters.items()):
        errors.append("starter must be available in its configured game family")
    if not 1 <= config.video_fps <= 60 or not 1 <= config.jpeg_quality <= 95:
        errors.append("video fps/quality out of range")
    if errors:
        raise ValueError("; ".join(errors))


def validate_assets(config: FleetConfig, root: Path) -> None:
    errors: list[str] = []
    for item in config.instances:
        if not (root / "roms" / item.rom).is_file():
            errors.append(f"ROM missing: {item.rom}")
        metadata = root / "profiles" / item.profile / "metadata.yml"
        if metadata.exists():
            text = metadata.read_text(encoding="utf-8")
            if f"file_name: {item.rom}" not in text or f"game_code: {item.game_code}" not in text:
                errors.append(f"profile ownership mismatch: {item.profile}")
    if errors:
        raise ValueError("; ".join(errors))
