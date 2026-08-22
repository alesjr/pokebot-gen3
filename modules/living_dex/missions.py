from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

_MISSION_HEADING = re.compile(
    r"^### (?P<mission_id>[A-Z]+(?:-[A-Z]+)*-\d+[A-Z]?) \u2014 (?P<title>.+)$",
    re.MULTILINE,
)
_FLAG_NAME = re.compile(r"\bFLAG_[A-Z][A-Z0-9_]*\b")
_SECTION_END = re.compile(r"^#{1,3} ", re.MULTILINE)
_MISSION_ID = re.compile(r"\b[A-Z]+(?:-[A-Z0-9]+)*-\d+[A-Z]?\b")
_FIELD = re.compile(r"^- \*\*(?P<name>[^*]+):\*\*\s*(?P<value>.+)$", re.MULTILINE)


@dataclass(frozen=True)
class MissionDefinition:
    family: str
    mission_id: str
    order: int
    title: str
    category: str
    games: tuple[str, ...]
    flags: tuple[str, ...]
    prerequisites: tuple[str, ...]
    source_document: str
    source_line: int
    definition_markdown: str
    required_level: int | None = None
    hunt_until_route_shinies: bool = True


@dataclass(frozen=True)
class RouteHuntRequirement:
    required_level: int
    missing_shiny_targets: int
    lowest_usable_party_level: int

    @property
    def can_leave_route(self) -> bool:
        """Story travel resumes only after collection and strength gates pass."""
        return self.missing_shiny_targets == 0 and self.lowest_usable_party_level >= self.required_level


def _category(mission_id: str, fields: dict[str, str]) -> str:
    explicit = fields.get("Categoria")
    if explicit:
        return explicit.split()[0].strip().upper()
    parts = mission_id.split("-")
    if "POST" in parts:
        return "POSTGAME"
    prefix = parts[0]
    return {
        "OPT": "OPTIONAL",
        "SIDE": "OPTIONAL",
        "REGI": "SIDE_STORY",
        "SEVII": "SEVII",
        "POST": "POSTGAME",
        "EVENT": "EVENT",
    }.get(prefix, "MAIN")


def _games(family: str, mission_id: str, fields: dict[str, str]) -> tuple[str, ...]:
    explicit = fields.get("Jogos")
    if explicit:
        normalized = explicit.upper().replace("FIRERED", "FR").replace("LEAFGREEN", "LG")
        if "FRLG" in normalized:
            return ("FR", "LG")
        selected = tuple(game for game in ("R", "S", "E", "FR", "LG") if game in re.split(r"[^A-Z]+", normalized))
        if selected:
            return selected
    prefix = mission_id.split("-", 1)[0]
    if family == "FRLG":
        return ("FR", "LG")
    if prefix == "R":
        return ("R",)
    if prefix == "S":
        return ("S",)
    if prefix == "E":
        return ("E",)
    if prefix == "RS":
        return ("R", "S")
    return ("R", "S", "E")


def parse_mission_document(path: Path, family: str) -> list[MissionDefinition]:
    text = path.read_text(encoding="utf-8")
    matches = list(_MISSION_HEADING.finditer(text))
    missions: list[MissionDefinition] = []
    for index, match in enumerate(matches):
        next_heading = _SECTION_END.search(text, match.end())
        end = next_heading.start() if next_heading is not None else len(text)
        markdown = text[match.start():end].rstrip()
        fields = {field.group("name").strip(): field.group("value").strip() for field in _FIELD.finditer(markdown)}
        flags = tuple(sorted({name.removeprefix("FLAG_") for name in _FLAG_NAME.findall(markdown)}))
        prerequisite_text = " ".join(
            value for name, value in fields.items() if name.startswith("Pré-requisito")
        )
        prerequisites = tuple(dict.fromkeys(_MISSION_ID.findall(prerequisite_text)))
        missions.append(
            MissionDefinition(
                family=family,
                mission_id=match.group("mission_id"),
                order=index + 1,
                title=match.group("title").strip(),
                category=_category(match.group("mission_id"), fields),
                games=_games(family, match.group("mission_id"), fields),
                flags=flags,
                prerequisites=prerequisites,
                source_document=path.name,
                source_line=text.count("\n", 0, match.start()) + 1,
                definition_markdown=markdown,
            )
        )
    return missions


def load_mission_catalog(base_path: Path | None = None) -> list[MissionDefinition]:
    if base_path is None:
        from modules.runtime import get_base_path

        root = get_base_path()
    else:
        root = base_path
    documents = (
        ("RSE", root / "docs" / "pokemon_ruby_sapphire_emerald_missoes_save_flags.md"),
        ("FRLG", root / "docs" / "pokemon_firered_leafgreen_missoes_save_flags.md"),
    )
    catalog: list[MissionDefinition] = []
    for family, path in documents:
        if path.is_file():
            catalog.extend(parse_mission_document(path, family))
    return catalog


def validate_mission_graph(missions: Iterable[MissionDefinition]) -> None:
    catalog = list(missions)
    by_family = {
        family: {mission.mission_id: mission for mission in catalog if mission.family == family}
        for family in {mission.family for mission in catalog}
    }
    errors: list[str] = []
    for mission in catalog:
        for prerequisite in mission.prerequisites:
            target = by_family[mission.family].get(prerequisite)
            if target is None:
                errors.append(f"{mission.mission_id}: unknown prerequisite {prerequisite}")
            elif target.order >= mission.order:
                errors.append(f"{mission.mission_id}: prerequisite {prerequisite} is not earlier")
    if errors:
        raise ValueError("; ".join(errors))


def missions_for_rom(catalog: Iterable[MissionDefinition], rom) -> list[MissionDefinition]:
    if rom.is_ruby:
        game = "R"
    elif rom.is_sapphire:
        game = "S"
    elif rom.is_emerald:
        game = "E"
    elif rom.is_frlg:
        game = "FR" if rom.game_code == "BPR" else "LG"
    else:
        return []
    return [mission for mission in catalog if game in mission.games]


class MissionTracker:
    def __init__(self, rom, stats, *, poll_interval: float = 2.0):
        self._rom = rom
        self._stats = stats
        self._missions = missions_for_rom(load_mission_catalog(), rom)
        self._poll_interval = poll_interval
        self._next_poll = 0.0
        self._previous_values: dict[str, tuple[bool, bool]] = {}
        self._active_static_mission: MissionDefinition | None = None

    def install_catalog(self) -> None:
        self._stats.sync_living_dex_missions(self._missions)

    def activate_static_encounter(self, encounter) -> MissionDefinition | None:
        """Reconcile an existing save to its documented static-encounter mission."""
        mission_id = self._static_mission_id(encounter)
        mission = next((item for item in self._missions if item.mission_id == mission_id), None)
        if mission is None:
            return None

        # Reaching this unique encounter proves earlier main-story steps happened.
        # Optional/side missions remain unknown: position alone cannot prove them.
        for previous in self._missions:
            if previous.order >= mission.order:
                break
            if previous.category == "MAIN":
                self._stats.set_living_dex_mission_status(
                    previous.family,
                    previous.mission_id,
                    "COMPLETED",
                    f"reconciled_by_reaching:{mission.mission_id}",
                )
        self._stats.set_living_dex_mission_status(
            mission.family,
            mission.mission_id,
            "IN_PROGRESS",
            f"static_encounter:{encounter.name}",
        )
        self._active_static_mission = mission
        return mission

    def complete_active_static(self) -> MissionDefinition | None:
        """Persist caught+saved completion and expose next main-story mission."""
        mission = self._active_static_mission
        if mission is None:
            return None
        self._stats.set_living_dex_mission_status(
            mission.family,
            mission.mission_id,
            "COMPLETED",
            "shiny_caught_and_game_saved",
        )
        next_mission = next(
            (
                item
                for item in self._missions
                if item.order > mission.order and item.category == "MAIN"
            ),
            None,
        )
        if next_mission is not None:
            self._stats.set_living_dex_mission_status(
                next_mission.family,
                next_mission.mission_id,
                "AVAILABLE",
                f"previous_completed:{mission.mission_id}",
            )
        self._active_static_mission = None
        return next_mission

    def _static_mission_id(self, encounter) -> str | None:
        map_name = getattr(encounter.map, "name", "")
        if encounter.name == "Groudon/Kyogre":
            return "R-067" if self._rom.is_ruby else "S-067" if self._rom.is_sapphire else None
        mapping = {
            ("Kecleon", "ROUTE119"): "RSE-046",
            ("Regirock", "DESERT_RUINS"): "REGI-002",
            ("Regice", "ISLAND_CAVE"): "REGI-003",
            ("Registeel", "ANCIENT_TOMB"): "REGI-004",
            ("Rayquaza", "SKY_PILLAR_TOP"): "E-POST-016",
            ("Snorlax", "ROUTE12"): "FRLG-056",
            ("Snorlax", "ROUTE16"): "FRLG-057",
            ("Hypno", "THREE_ISLAND_BERRY_FOREST"): "SEVII-011",
            ("Zapdos", "POWER_PLANT"): "SIDE-002",
            ("Articuno", "SEAFOAM_ISLANDS_B4F"): "SIDE-006",
            ("Moltres", "MT_EMBER_SUMMIT"): "SIDE-008",
            ("Mewtwo", "CERULEAN_CAVE_B1F"): "POST-040",
        }
        return mapping.get((encounter.name, map_name))

    def observe_if_due(self) -> None:
        from modules.game import get_event_flag_offset
        from modules.memory import game_has_started, get_event_flag

        now = time.monotonic()
        if now < self._next_poll:
            return
        self._next_poll = now + self._poll_interval
        if not game_has_started():
            return

        observations: dict[str, tuple[bool, bool]] = {}
        for flag_name in sorted({flag for mission in self._missions for flag in mission.flags}):
            try:
                get_event_flag_offset(flag_name)
            except KeyError:
                observations[flag_name] = (False, False)
            else:
                observations[flag_name] = (True, get_event_flag(flag_name))

        changed = {
            flag_name: state
            for flag_name, state in observations.items()
            if self._previous_values.get(flag_name) != state
        }
        if changed:
            self._stats.record_living_dex_flags(changed)
            self._previous_values.update(changed)
