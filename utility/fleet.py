#!/usr/bin/env python3
from __future__ import annotations

import argparse
import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.fleet.config import load_fleet_config, validate_assets
from modules.fleet.bootstrap import atomic_create, living_dex_config


def _metadata(item) -> str:
    return (
        "version: 1\n"
        "rom:\n"
        f"  file_name: {item.rom}\n"
        f"  game_code: {item.game_code}\n"
        f"  revision: {item.revision}\n"
        "  language: E\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("validate", "check-ports", "init-profiles", "list"))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--config", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    config = load_fleet_config(args.config or root / "fleet.yml")
    validate_assets(config, root)

    if args.command == "check-ports":
        sockets = []
        try:
            for port in [config.dashboard_port, *(item.port for item in config.instances)]:
                listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                listener.bind(("0.0.0.0", port))
                sockets.append(listener)
        except OSError as error:
            raise ValueError(f"port unavailable: {port}: {error}") from error
        finally:
            for listener in sockets:
                listener.close()
    elif args.command == "init-profiles":
        for item in config.instances:
            directory = root / "profiles" / item.profile
            metadata = directory / "metadata.yml"
            directory.mkdir(parents=False, exist_ok=True)
            atomic_create(metadata, _metadata(item))
            atomic_create(directory / "living_dex.yml", living_dex_config(config, item))
    elif args.command == "list":
        for item in sorted(config.instances, key=lambda entry: entry.priority):
            print(f"{item.profile}|{item.port}|{item.game}|{item.starter}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as error:
        print(f"Erro: {error}", file=sys.stderr)
        raise SystemExit(1)
