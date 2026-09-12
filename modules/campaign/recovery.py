from __future__ import annotations

from typing import Generator

from modules.campaign.engine import navigate_to_catalog_location
from modules.context import context
from modules.map_data import PokemonCenter, get_map_enum
from modules.modes import BotModeError
from modules.modes.util import heal_in_pokemon_center
from modules.modes.util.map import find_closest_pokemon_center
from modules.player import get_player_location
from modules.pokemon import StatusCondition
from modules.pokemon_party import get_party
from modules.save_data import get_last_heal_location


def party_needs_healing() -> bool:
    combatants = get_party().non_eggs
    return bool(combatants) and any(
        pokemon.current_hp_percentage <= context.config.battle.hp_threshold
        or pokemon.status_condition is not StatusCondition.Healthy
        for pokemon in combatants
    )


def _last_heal_pokemon_center() -> PokemonCenter | None:
    last_heal_map = get_map_enum(get_last_heal_location())
    return next(
        (
            pokemon_center
            for pokemon_center in PokemonCenter
            if pokemon_center.value[0] is last_heal_map
        ),
        None,
    )


def find_recovery_pokemon_center() -> PokemonCenter:
    try:
        return find_closest_pokemon_center(get_player_location())
    except BotModeError:
        last_heal_center = _last_heal_pokemon_center()
        if last_heal_center is None:
            raise
        return last_heal_center


def heal_party_and_return() -> Generator:
    source_map, source_coordinates = get_player_location()
    yield from heal_in_pokemon_center(find_recovery_pokemon_center())
    yield from navigate_to_catalog_location(
        source_map.value[0],
        source_map.value[1],
        source_coordinates[0],
        source_coordinates[1],
    )
