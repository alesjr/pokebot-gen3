from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path


def _epoch_for_rom(rom, config) -> str:
    return config.emerald_epoch if rom.is_emerald else config.ruby_sapphire_epoch


def configure_historical_rtc(core, profile, rom, config) -> None:
    """Anchor mGBA wall clock to release-era date while time advances normally."""
    if not rom.is_rse or config.mode != "historical_wallclock":
        return

    path = profile.path / "rtc_anchor.json"
    now = datetime.now().astimezone()
    if path.is_file():
        anchor = json.loads(path.read_text(encoding="utf-8"))
        real_anchor = datetime.fromisoformat(anchor["real_anchor"])
        virtual_anchor = datetime.fromisoformat(anchor["virtual_anchor"])
    else:
        epoch = datetime.fromisoformat(_epoch_for_rom(rom, config)).date()
        virtual_anchor = now.replace(year=epoch.year, month=epoch.month, day=epoch.day)
        real_anchor = now
        anchor = {
            "real_anchor": real_anchor.isoformat(),
            "virtual_anchor": virtual_anchor.isoformat(),
            "game": rom.game_name,
        }
        path.write_text(json.dumps(anchor, indent=2), encoding="utf-8")
        _backup_existing_clock_files(profile.path)

    desired_now = virtual_anchor + (now - real_anchor)
    offset_seconds = round(desired_now.timestamp() - now.timestamp())
    core.rtc.use_real_time_with_offset(offset_seconds)


def _backup_existing_clock_files(profile_path: Path) -> None:
    backup_dir = profile_path / "rtc_migration_backup"
    backup_dir.mkdir(exist_ok=True)
    for name in ("current_save.sav", "current_state.ss1"):
        source = profile_path / name
        target = backup_dir / name
        if source.is_file() and not target.exists():
            shutil.copy2(source, target)
