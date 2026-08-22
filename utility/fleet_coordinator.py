#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aiohttp import web

from modules.fleet.config import load_fleet_config
from modules.fleet.coordinator import create_coordinator_app


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("fleet.yml"))
    parser.add_argument("--database", type=Path, default=Path("stats/fleet.db"))
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int)
    args = parser.parse_args()
    token = os.environ.get("POKEBOT_FLEET_TOKEN", "")
    config = load_fleet_config(args.config)
    web.run_app(
        create_coordinator_app(config, args.database, token),
        host=args.host,
        port=args.port or config.dashboard_port,
        print=None,
    )


if __name__ == "__main__":
    main()
