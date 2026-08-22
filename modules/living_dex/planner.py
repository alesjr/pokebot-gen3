from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable

from modules.living_dex.goals import CollectionTarget, UNOWN_FORMS
from modules.pokemon import get_species_by_index, get_species_by_national_dex

GAMES = ("Ruby", "Sapphire", "Emerald", "FireRed", "LeafGreen")

SPECIAL_ACQUISITIONS = {
    "Aerodactyl": ("FireRed", "gift", "CINNABAR_POKEMON_LAB"),
    "Anorith": ("Emerald", "fossil", "RUSTBORO_DEVON"),
    "Articuno": ("FireRed", "static", "SEAFOAM_ISLANDS_B4F"),
    "Beldum": ("Emerald", "gift", "MOSSDEEP_STEVENS_HOUSE"),
    "Bulbasaur": ("FireRed", "starter", "PALLET_TOWN"),
    "Castform": ("Emerald", "gift", "WEATHER_INSTITUTE"),
    "Cleffa": ("FireRed", "breeding", "FOUR_ISLAND_DAY_CARE"),
    "Celebi": ("Emerald", "official_distribution", "EVENT_PROTOCOL"),
    "Charmander": ("FireRed", "starter", "PALLET_TOWN"),
    "Chikorita": ("Emerald", "gift", "LITTLEROOT_LAB_POSTGAME"),
    "Cyndaquil": ("Emerald", "gift", "LITTLEROOT_LAB_POSTGAME"),
    "Eevee": ("FireRed", "gift", "CELADON_CONDOMINIUMS"),
    "Elekid": ("FireRed", "breeding", "FOUR_ISLAND_DAY_CARE"),
    "Entei": ("FireRed", "roamer", "KANTO"),
    "Farfetch’d": ("FireRed", "npc_trade", "VERMILION_CITY"),
    "Feebas": ("Emerald", "special_fishing", "ROUTE119"),
    "Groudon": ("Ruby", "static", "CAVE_OF_ORIGIN"),
    "Hitmonchan": ("FireRed", "gift", "SAFFRON_DOJO"),
    "Hitmonlee": ("FireRed", "gift", "SAFFRON_DOJO"),
    "Ho-Oh": ("FireRed", "event_static", "NAVEL_ROCK"),
    "Jirachi": ("Ruby", "official_distribution", "EVENT_PROTOCOL"),
    "Jynx": ("FireRed", "npc_trade", "CERULEAN_CITY"),
    "Kabuto": ("FireRed", "fossil", "CINNABAR_POKEMON_LAB"),
    "Kyogre": ("Sapphire", "static", "CAVE_OF_ORIGIN"),
    "Lapras": ("FireRed", "gift", "SILPH_CO_7F"),
    "Latias": ("Sapphire", "roamer", "HOENN"),
    "Latios": ("Ruby", "roamer", "HOENN"),
    "Lickitung": ("FireRed", "npc_trade", "ROUTE18"),
    "Lileep": ("Emerald", "fossil", "RUSTBORO_DEVON"),
    "Lugia": ("FireRed", "event_static", "NAVEL_ROCK"),
    "Mew": ("Emerald", "event_static", "FARAWAY_ISLAND_JP"),
    "Mewtwo": ("FireRed", "static", "CERULEAN_CAVE_B1F"),
    "Magby": ("LeafGreen", "breeding", "FOUR_ISLAND_DAY_CARE"),
    "Moltres": ("FireRed", "static", "MT_EMBER_SUMMIT"),
    "Mr. Mime": ("FireRed", "npc_trade", "ROUTE2"),
    "Mudkip": ("Ruby", "starter", "ROUTE101"),
    "Omanyte": ("FireRed", "fossil", "CINNABAR_POKEMON_LAB"),
    "Porygon": ("FireRed", "game_corner", "CELADON_GAME_CORNER"),
    "Pichu": ("FireRed", "breeding", "FOUR_ISLAND_DAY_CARE"),
    "Raikou": ("FireRed", "roamer", "KANTO"),
    "Rayquaza": ("Emerald", "static", "SKY_PILLAR_TOP"),
    "Regice": ("Emerald", "static", "ISLAND_CAVE"),
    "Regirock": ("Emerald", "static", "DESERT_RUINS"),
    "Registeel": ("Emerald", "static", "ANCIENT_TOMB"),
    "Snorlax": ("FireRed", "static", "ROUTE12"),
    "Smoochum": ("FireRed", "breeding", "FOUR_ISLAND_DAY_CARE"),
    "Squirtle": ("LeafGreen", "starter", "PALLET_TOWN"),
    "Sudowoodo": ("Emerald", "static", "BATTLE_FRONTIER"),
    "Suicune": ("FireRed", "roamer", "KANTO"),
    "Togepi": ("FireRed", "gift_egg", "WATER_LABYRINTH"),
    "Torchic": ("Emerald", "starter", "ROUTE101"),
    "Totodile": ("Emerald", "gift", "LITTLEROOT_LAB_POSTGAME"),
    "Treecko": ("Sapphire", "starter", "ROUTE101"),
    "Tyrogue": ("FireRed", "breeding", "FOUR_ISLAND_DAY_CARE"),
    "Wynaut": ("Emerald", "gift_egg", "LAVARIDGE_TOWN"),
    "Azurill": ("Emerald", "incense_breeding", "MAUVILLE_DAY_CARE"),
    "Igglybuff": ("FireRed", "breeding", "FOUR_ISLAND_DAY_CARE"),
    "Zapdos": ("FireRed", "static", "POWER_PLANT"),
}


@dataclass(frozen=True, order=True)
class AcquisitionOption:
    cost: int
    game: str
    species: str
    method: str
    location: str
    prerequisites: tuple[str, ...] = ()
    variant: str = "any"


@dataclass(frozen=True)
class TargetAssignment:
    target: CollectionTarget
    profile: str
    option: AcquisitionOption


def choose_assignment(
    target: CollectionTarget,
    options: Iterable[AcquisitionOption],
    profiles_by_game: dict[str, str],
    completed_prerequisites: dict[str, set[str]],
) -> TargetAssignment | None:
    candidates = []
    for option in options:
        profile = profiles_by_game.get(option.game)
        if option.species != target.species or profile is None:
            continue
        if target.species in {"Unown", "Deoxys"} and option.variant != target.variant:
            continue
        completed = completed_prerequisites.get(profile, set())
        if not set(option.prerequisites).issubset(completed):
            continue
        candidates.append((option, profile))
    if not candidates:
        return None
    option, profile = min(candidates, key=lambda entry: (entry[0].cost, entry[0].game, entry[0].location))
    return TargetAssignment(target, profile, option)


def route_can_advance(*, missing_route_targets: int, lowest_usable_level: int, required_level: int) -> bool:
    return missing_route_targets == 0 and lowest_usable_level >= required_level


def validate_acquisition_matrix(
    targets: Iterable[CollectionTarget], options: Iterable[AcquisitionOption]
) -> None:
    species_with_options = {option.species for option in options}
    uncovered = sorted({target.species for target in targets} - species_with_options)
    if uncovered:
        raise ValueError(f"acquisition matrix missing species: {', '.join(uncovered)}")
    variant_species = {"Unown", "Deoxys"}
    missing_variants = sorted(
        f"{target.species}:{target.variant}"
        for target in targets
        if target.species in variant_species
        and not any(option.species == target.species and option.variant == target.variant for option in options)
    )
    if missing_variants:
        raise ValueError(f"acquisition matrix missing variants: {', '.join(missing_variants)}")


def load_acquisition_matrix(root: Path | None = None) -> tuple[AcquisitionOption, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[1]
    raw = json.loads((root / "data" / "living_dex_acquisition.json").read_text(encoding="utf-8"))
    options = [
        AcquisitionOption(
            max(1, 1000 // max(entry["rate"], 1)),
            entry["game"],
            entry["species"],
            entry["method"],
            entry["location"],
        )
        for entry in raw
    ]
    for species_name, (game, method, location) in SPECIAL_ACQUISITIONS.items():
        options.append(AcquisitionOption(100, game, species_name, method, location))
    options.extend(
        [
            AcquisitionOption(100, "Ruby", "Deoxys", "trade_form", "HOENN", (), "normal"),
            AcquisitionOption(100, "FireRed", "Deoxys", "event_static", "BIRTH_ISLAND", (), "attack"),
            AcquisitionOption(100, "LeafGreen", "Deoxys", "event_static", "BIRTH_ISLAND", (), "defense"),
            AcquisitionOption(100, "Emerald", "Deoxys", "event_static", "BIRTH_ISLAND", (), "speed"),
        ]
    )
    options.extend(
        AcquisitionOption(100, "FireRed", "Unown", "wild_form", "TANOBY_RUINS", (), form)
        for form in UNOWN_FORMS
    )
    for number in range(1, 387):
        species = get_species_by_national_dex(number)
        if species.evolves_from is None:
            continue
        predecessor = get_species_by_index(species.evolves_from).name
        for game in GAMES:
            options.append(
                AcquisitionOption(200, game, species.name, "evolution", "ANY", (f"owns:{predecessor}",))
            )
    return tuple(sorted(set(options)))
