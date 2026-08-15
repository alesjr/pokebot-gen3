from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class LivingDexProgress:
    founder_personality_value: int | None = None
    founder_species: str | None = None
    starter_stored: bool = False
    current_objective: str = "Detecting save progress"
    completed_quests: list[str] = field(default_factory=list)
    unavailable: dict[str, str] = field(default_factory=dict)
    retry_counts: dict[str, int] = field(default_factory=dict)

    @classmethod
    def load(cls, profile_path: Path) -> "LivingDexProgress":
        path = profile_path / "living_dex_progress.json"
        if not path.is_file():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls(**{key: value for key, value in data.items() if key in cls.__dataclass_fields__})
        except (OSError, ValueError, TypeError):
            return cls()

    def save(self, profile_path: Path) -> None:
        path = profile_path / "living_dex_progress.json"
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8")
        temporary.replace(path)
