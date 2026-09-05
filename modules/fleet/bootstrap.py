from __future__ import annotations

import os
from pathlib import Path


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
