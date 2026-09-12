from __future__ import annotations

from collections.abc import Generator

from modules.context import context
from modules.items import get_item_bag
from modules.map_data import get_map_enum
from modules.modes._interface import BotModeError
from modules.modes.util import (
    ensure_facing_direction,
    navigate_to,
    save_the_game,
    talk_to_npc,
    wait_for_n_frames,
    wait_for_player_avatar_to_be_controllable,
    walk_one_tile,
)


def run_catalog_actions(
    actions: list[dict[str, object]],
    *,
    required_hms: list[str] | None = None,
    temporary_required_species: list[str] | None = None,
) -> Generator:
    """Execute a trusted sequence whose game-specific data lives in the catalogue."""
    del temporary_required_species
    if not isinstance(actions, list) or not actions:
        raise BotModeError("Campaign catalog actions must be a non-empty list.")

    if required_hms:
        yield from _ensure_required_hms(required_hms)

    for index, action in enumerate(actions, start=1):
        if not isinstance(action, dict):
            raise BotModeError(f"Campaign catalog action #{index} must be an object.")
        operation = action.get("operation")
        if operation == "navigate":
            yield from _navigate(action, index)
        elif operation == "talk_to_npc":
            yield from talk_to_npc(_integer(action, "local_object_id", index))
            yield from _wait_for_control(action)
        elif operation == "interact":
            yield from _interact(action, index)
        elif operation == "walk":
            direction = _direction(action, index)
            for _ in range(_integer(action, "count", index, default=1)):
                yield from walk_one_tile(direction)
        elif operation == "wait":
            yield from wait_for_n_frames(_integer(action, "frames", index))
        elif operation == "save":
            yield from save_the_game()
        elif operation == "puzzle_solver":
            from modules.modes.puzzle_solver import PuzzleSolverMode

            yield from PuzzleSolverMode().run(return_to_caller=True)
        else:
            raise BotModeError(
                f"Unsupported Campaign catalog operation #{index}: {operation!r}."
            )


def _navigate(action: dict[str, object], index: int) -> Generator:
    destination = get_map_enum(
        (_integer(action, "map_group", index), _integer(action, "map_number", index))
    )
    coordinates = (_integer(action, "tile_x", index), _integer(action, "tile_y", index))
    yield from wait_for_player_avatar_to_be_controllable(
        "B", wait_for_no_script=True, timeout_frames=_timeout(action, index)
    )
    expecting_script = bool(action.get("expecting_script", True))
    yield from navigate_to(
        destination,
        coordinates,
        expecting_script=expecting_script,
    )
    if expecting_script:
        yield from _wait_for_control(action)


def _interact(action: dict[str, object], index: int) -> Generator:
    if "tile_x" in action or "tile_y" in action:
        yield from _navigate(action, index)
    yield from ensure_facing_direction(_direction(action, index))
    context.emulator.press_button("A")
    yield
    yield from _wait_for_control(action)


def _wait_for_control(action: dict[str, object]) -> Generator:
    yield from wait_for_player_avatar_to_be_controllable(
        str(action.get("button", "B")),
        stable_frames=int(action.get("stable_frames", 30)),
        wait_for_no_script=True,
        timeout_frames=int(action.get("timeout_frames", 30_000)),
    )


def _direction(action: dict[str, object], index: int) -> str:
    direction = action.get("direction", "Up")
    if direction not in {"Up", "Down", "Left", "Right"}:
        raise BotModeError(
            f"Campaign catalog action #{index} has invalid direction: {direction!r}."
        )
    return str(direction)


def _timeout(action: dict[str, object], index: int) -> int:
    return _integer(action, "timeout_frames", index, default=30_000)


def _integer(
    action: dict[str, object], key: str, index: int, *, default: int | None = None
) -> int:
    value = action.get(key, default)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise BotModeError(
            f"Campaign catalog action #{index} requires non-negative integer {key}."
        )
    return value


def _ensure_required_hms(required_hms: list[str]) -> Generator:
    from modules.campaign.team import combat_potential, hm_coverage
    from modules.modes.util.items import teach_hm_or_tm
    from modules.pokemon_party import get_party

    for move_name in dict.fromkeys(required_hms):
        party = list(get_party().non_eggs)
        if any(
            learned_move is not None
            and learned_move.move.name.casefold() == move_name.casefold()
            for pokemon in party
            for learned_move in pokemon.moves
        ):
            continue

        candidates = [
            pokemon
            for pokemon in party
            if not pokemon.is_shiny and hm_coverage(pokemon, (move_name,))
        ]
        if not candidates:
            raise BotModeError(
                f"Campaign party has no non-shiny Pokémon compatible with required HM {move_name}."
            )
        candidate = max(
            candidates,
            key=lambda pokemon: (
                len(hm_coverage(pokemon, required_hms)),
                combat_potential(pokemon),
            ),
        )
        hm_entry = next(
            entry
            for entry in candidate.species.learnset.tm_hm
            if entry.move.name.casefold() == move_name.casefold()
        )
        if get_item_bag().quantity_of(hm_entry.item) == 0:
            raise BotModeError(f"Campaign does not own required HM {move_name}.")
        yield from teach_hm_or_tm(hm_entry.item, candidate.index)
