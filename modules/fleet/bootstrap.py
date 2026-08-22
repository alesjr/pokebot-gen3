from __future__ import annotations

import json
import os
from pathlib import Path


def living_dex_config(config, item) -> str:
    return json.dumps(
        {
            "gameplay": {
                "progression": "area",
                "trainer_name": config.trainer_name,
                "trainer_gender": config.trainer_gender,
                "starter": item.starter,
            }
        },
        indent=2,
    ) + "\n"


def atomic_create(path: Path, contents: str) -> None:
    """Create once without replacing an existing user-owned config."""
    if path.exists():
        return
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(contents, encoding="utf-8")
    try:
        os.link(temporary, path)
    except FileExistsError:
        pass
    finally:
        temporary.unlink(missing_ok=True)
