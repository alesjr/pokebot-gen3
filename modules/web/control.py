"""Validated dashboard commands executed on emulator main thread."""

from __future__ import annotations

import hmac
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from queue import Queue
from threading import Thread
from typing import Any, Callable

from modules.config.schemas_v1 import LivingDex
from modules.context import context
from modules.main import work_queue

GBA_BUTTONS = frozenset({"A", "B", "L", "R", "Start", "Select", "Up", "Down", "Left", "Right"})
SPEEDS = frozenset({0, 1, 2, 3, 4, 8, 16, 32})


def on_main_thread(callback: Callable[[], Any], timeout: float = 5.0) -> Any:
    result: Queue = Queue(maxsize=1)

    def run() -> None:
        try:
            result.put((True, callback()))
        except Exception as error:
            result.put((False, error))

    work_queue.put(run)
    try:
        ok, value = result.get(timeout=timeout)
    except Exception as error:
        raise TimeoutError("emulator did not answer") from error
    if not ok:
        raise value
    return value


def send_button(button: str, action: str) -> None:
    if button not in GBA_BUTTONS or action not in {"press", "hold", "release"}:
        raise ValueError("Comando de teclado inválido.")

    def command() -> None:
        context.set_manual_mode(enable_video_and_slow_down=False)
        method_name = {"press": "press_button", "hold": "hold_button", "release": "release_button"}[action]
        getattr(context.emulator, method_name)(button)

    on_main_thread(command)


def emulator_action(action: str, speed: int | None = None) -> dict[str, str]:
    def command() -> dict[str, str]:
        if action == "play":
            mode = context._previous_bot_mode if context._previous_bot_mode != "Manual" else "Living Dex Gen III"
            context.bot_mode = mode
            return {"message": f"Automação iniciada: {mode}"}
        if action == "pause_save":
            context.set_manual_mode(enable_video_and_slow_down=False)
            context.emulator.reset_held_buttons()
            context.emulator.create_save_state("Web")
            return {"message": "Automação pausada e save state criado."}
        if action == "save":
            context.emulator.create_save_state("Web")
            return {"message": "Save state criado."}
        if action == "reset":
            context.emulator.reset()
            return {"message": "Emulador reiniciado."}
        if action == "speed" and speed in SPEEDS:
            context.emulation_speed = speed
            return {"message": "Velocidade atualizada."}
        raise ValueError("Ação inválida.")

    return on_main_thread(command)


def read_living_dex_config() -> dict:
    return context.config.living_dex.model_dump()


def update_living_dex_config(payload: dict) -> dict:
    validated = LivingDex(**payload)

    def command() -> dict:
        previous = context.config.living_dex
        context.config.living_dex = validated
        try:
            context.config.save_file("living_dex")
            context.reload_config()
        except Exception:
            context.config.living_dex = previous
            raise
        return context.config.living_dex.model_dump()

    return on_main_thread(command)


def _profile_file(kind: str, name: str):
    if not name or name != Path(name).name:
        raise ValueError("Nome de arquivo inválido.")
    if kind not in {"state", "save"}:
        raise ValueError("Tipo de arquivo inválido.")
    profile = context.profile.path
    if kind == "state":
        candidates = [profile / "current_state.ss1", profile / "states" / name]
        suffix = ".ss1"
    elif kind == "save":
        candidates = [profile / "current_save.sav", profile / "saves" / name]
        suffix = ".sav"
    if not name.endswith(suffix):
        raise ValueError("Extensão de arquivo inválida.")
    for candidate in candidates:
        if candidate.name == name and candidate.is_file() and not candidate.is_symlink():
            return candidate
    raise ValueError("Arquivo não encontrado.")


def list_profile_files() -> dict[str, list[dict]]:
    profile = context.profile.path

    def collect(current_name: str, directory_name: str, suffix: str) -> list[dict]:
        paths = [profile / current_name, *(profile / directory_name).glob(f"*{suffix}")]
        unique = {str(path.resolve()): path for path in paths if path.is_file()}
        ordered = sorted(unique.values(), key=lambda path: path.stat().st_mtime, reverse=True)[:128]
        return [
            {"name": path.name, "modified": path.stat().st_mtime, "size": path.stat().st_size}
            for path in ordered
        ]

    return {
        "states": collect("current_state.ss1", "states", ".ss1"),
        "saves": collect("current_save.sav", "saves", ".sav"),
    }


def load_profile_file(kind: str, name: str) -> dict[str, str]:
    source = _profile_file(kind, name)

    def command() -> dict[str, str]:
        context.set_manual_mode(enable_video_and_slow_down=False)
        context.emulator.reset_held_buttons()
        if kind == "state":
            data = source.read_bytes()
            context.emulator.create_save_state("BeforeWebLoad")
            context.emulator.load_save_state(data)
            context.frame = 0
            temporary = context.profile.path / "current_state.ss1.tmp"
            temporary.write_bytes(data)
            os.replace(temporary, context.profile.path / "current_state.ss1")
            return {"message": f"Save state carregado: {name}"}

        context.emulator.create_save_state("BeforeSaveLoad")
        context.emulator.backup_current_save_game()
        current_save = context.profile.path / "current_save.sav"
        if source.resolve() != current_save.resolve():
            temporary = context.profile.path / "current_save.sav.tmp"
            shutil.copyfile(source, temporary)
            os.replace(temporary, current_save)
        import mgba.vfs

        context.emulator._save = mgba.vfs.open_path(str(current_save), "r+")
        context.emulator._core.load_save(context.emulator._save)
        context.emulator.reset()
        context.frame = 0
        context.emulator.create_save_state("LoadedSave")
        return {"message": f"Save carregado e emulador reiniciado: {name}"}

    return on_main_thread(command, timeout=10.0)


def list_profiles() -> dict:
    from modules.profiles import list_available_profiles

    profiles = sorted(list_available_profiles(), key=lambda profile: profile.path.name.lower())
    ports = {}
    for entry in os.environ.get("POKEBOT_PROFILE_PORTS", "").split(","):
        name, separator, port = entry.partition(":")
        if separator and port.isdigit() and 0 < int(port) < 65536:
            ports[name] = int(port)
    return {
        "active": context.profile.path.name,
        "profiles": [
            {
                "name": profile.path.name,
                "game": profile.rom.game_name,
                "last_played": profile.last_played.isoformat() if profile.last_played else None,
                "port": ports.get(profile.path.name),
            }
            for profile in profiles
        ],
    }


def _schedule_profile_restart(profile_name: str) -> None:
    def restart() -> None:
        time.sleep(0.75)
        arguments = [sys.executable, sys.argv[0], profile_name, *sys.argv[2:]]
        os.execv(sys.executable, arguments)

    Thread(target=restart, name="profile-restart", daemon=True).start()


RESET_FILES = frozenset(
    {
        "current_save.sav",
        "current_state.ss1",
        "stats.db",
        "stats.db-shm",
        "stats.db-wal",
        "living_dex_progress.json",
        "soft_reset_frames.json",
        "rtc_anchor.json",
    }
)
RESET_DIRECTORIES = frozenset({"saves", "states", "pokemon", "screenshots"})


def reset_profile(profile_name: str, confirmation: str) -> dict[str, str]:
    from modules.profiles import list_available_profiles

    profiles = {profile.path.name: profile for profile in list_available_profiles()}
    if profile_name not in profiles:
        raise ValueError("Profile não encontrado.")
    if not hmac.compare_digest(profile_name, confirmation):
        raise ValueError("Confirmação não corresponde ao nome do profile.")
    profile_path = profiles[profile_name].path
    active = profile_name == context.profile.path.name
    if not active:
        raise ValueError("Abra a aba deste profile para resetá-lo com segurança.")

    def command() -> dict[str, str]:
        context.set_manual_mode(enable_video_and_slow_down=False)
        context.emulator.reset_held_buttons()
        context.emulator.create_save_state("BeforeProfileReset")
        timestamp = datetime.now().astimezone().strftime("%Y-%m-%d_%H-%M-%S_%f")
        backup = profile_path / "reset_backups" / timestamp
        backup.mkdir(parents=True, exist_ok=False)
        for item in profile_path.iterdir():
            if item.name in RESET_FILES or item.name in RESET_DIRECTORIES:
                shutil.move(str(item), backup / item.name)
        _schedule_profile_restart(profile_name)
        return {
            "message": f"Profile {profile_name} resetado. Backup: {backup.relative_to(profile_path)}",
            "restarting": True,
        }

    return on_main_thread(command, timeout=15.0)
