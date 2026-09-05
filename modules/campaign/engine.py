from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Generator
from typing import Protocol

from modules.context import context
from modules.map_data import get_map_enum
from modules.missions.database import MissionPlan, MissionStep, MissionsDatabase, StepCondition
from modules.modes._interface import BotModeError
from modules.modes.util import (
    navigate_to,
    save_the_game,
    wait_for_player_avatar_to_be_controllable,
)
from modules.player import get_player_avatar, get_player_location


def save_campaign_checkpoint(mission_number: int) -> Generator:
    yield from save_the_game()
    context.emulator.create_save_state(f"Campaign_Mission_{mission_number}")


def navigate_to_catalog_location(
    map_group: int,
    map_number: int,
    tile_x: int,
    tile_y: int,
    *,
    timeout_frames: int = 30_000,
) -> Generator:
    destination = get_map_enum((map_group, map_number))
    destination_tile = (tile_x, tile_y)
    for _ in range(20):
        if get_player_location()[0] is destination and get_player_avatar().local_coordinates == destination_tile:
            return
        yield from wait_for_player_avatar_to_be_controllable(
            "B", stable_frames=30, wait_for_no_script=True, timeout_frames=timeout_frames
        )
        yield from navigate_to(destination, destination_tile, expecting_script=True)
    raise BotModeError(
        f"Could not reach catalog location {destination.name} {destination_tile} "
        f"from {get_player_location()[0].name}."
    )


class StateReader(Protocol):
    def read(self, source_type: str, source_key: str) -> object: ...


class CartridgeStateReader:
    """Read persistent campaign evidence from current cartridge."""

    def __init__(self, expected_starter: str | None = None):
        self._expected_starter = expected_starter

    def _configured_starter_species(self) -> set[str]:
        evolution_families = {
            "Treecko": {"Treecko", "Grovyle", "Sceptile"},
            "Torchic": {"Torchic", "Combusken", "Blaziken"},
            "Mudkip": {"Mudkip", "Marshtomp", "Swampert"},
        }
        return evolution_families.get(
            self._expected_starter, {self._expected_starter} if self._expected_starter else set()
        )

    def read(self, source_type: str, source_key: str) -> object:
        from modules.memory import game_has_started, get_event_flag, get_event_var
        from modules.player import get_player_avatar

        if source_type == "flag":
            return get_event_flag(source_key)
        if source_type == "var":
            return get_event_var(source_key)
        if source_type == "map":
            group, number = get_player_avatar().map_group_and_number
            return f"{group}:{number}"
        if source_type == "tile":
            x, y = get_player_avatar().local_coordinates
            return f"{x}:{y}"
        if source_type == "item":
            from modules.items import get_item_bag, get_item_by_name

            return get_item_bag().quantity_of(get_item_by_name(source_key))
        if source_type == "party":
            from modules.pokemon_party import get_party

            party = list(get_party().non_eggs)
            if source_key == "count":
                return len(party)
            if source_key == "minimum_level":
                return min((pokemon.level for pokemon in party), default=0)
            if source_key == "all_healthy":
                return bool(party) and all(
                    pokemon.current_hp == pokemon.total_hp
                    and pokemon.status_condition.name == "Healthy"
                    for pokemon in party
                )
            if source_key == "configured_starter_count":
                expected_species = self._configured_starter_species()
                return sum(pokemon.species.name in expected_species for pokemon in party)
            if source_key == "non_starter_count":
                expected_species = self._configured_starter_species()
                return sum(pokemon.species.name not in expected_species for pokemon in party)
        if source_type == "other" and source_key == "game_started":
            return game_has_started()
        if source_type == "other" and source_key == "pokedex_owned_count":
            from modules.pokedex import get_pokedex

            return len(get_pokedex().owned_species)
        if source_type == "other" and source_key == "shiny_starter_in_storage":
            from modules.pokemon_storage import get_pokemon_storage

            expected_species = self._configured_starter_species()
            return any(
                slot.pokemon.is_shiny and slot.pokemon.species.name in expected_species
                for box in get_pokemon_storage().boxes
                for slot in box.slots
            )
        if source_type == "other" and source_key == "owns_configured_shiny_starter":
            if not game_has_started() or self._expected_starter is None:
                return False
            from modules.pokemon_party import get_party
            from modules.pokemon_storage import get_pokemon_storage

            expected_species = self._configured_starter_species()
            owned = list(get_party()) + [
                slot.pokemon
                for box in get_pokemon_storage().boxes
                for slot in box.slots
            ]
            return any(
                pokemon.is_shiny and pokemon.species.name in expected_species
                for pokemon in owned
            )
        raise BotModeError(f"Unsupported campaign condition source: {source_type}:{source_key}")


class CampaignExecutor:
    """Execute ordered database steps through an explicit action registry."""

    def __init__(
        self,
        database: MissionsDatabase,
        profile: str,
        state_reader: StateReader,
        actions: dict[str, Callable[[], Generator]],
        on_step_started: Callable[[MissionStep], None] | None = None,
    ):
        self._database = database
        self._profile = profile
        self._state_reader = state_reader
        self._actions = actions
        self._on_step_started = on_step_started

    def is_complete(self, mission: MissionPlan) -> bool:
        if not mission.steps:
            raise BotModeError(f"Campaign mission has no steps: {mission.code}")
        complete, _ = self._evaluate(mission.steps[-1], "complete", required=True)
        return complete

    def run(self, mission: MissionPlan) -> Generator:
        if not mission.steps:
            raise BotModeError(f"Campaign mission has no steps: {mission.code}")
        self._database.update_progress(
            self._profile,
            mission.mission_game_id,
            status="available",
            current_step_id=mission.steps[0].id,
        )
        for step in mission.steps:
            complete, observations = self._evaluate(step, "complete", required=True)
            self._database.record_observations(
                self._profile, mission.mission_game_id, observations
            )
            if complete:
                continue
            for purpose in ("unlock", "start"):
                allowed, prerequisite_observations = self._evaluate(step, purpose, required=False)
                if prerequisite_observations:
                    self._database.record_observations(
                        self._profile, mission.mission_game_id, prerequisite_observations
                    )
                if not allowed:
                    raise BotModeError(
                        f"Campaign step prerequisite not satisfied: {step.code}:{purpose}"
                    )
            action = self._actions.get(step.action)
            if action is None:
                raise BotModeError(f"Campaign action is not registered: {step.action}")
            self._database.update_progress(
                self._profile,
                mission.mission_game_id,
                status="in_progress",
                current_step_id=step.id,
            )
            if self._on_step_started is not None:
                self._on_step_started(step)
            yield from action()
            complete, observations = self._evaluate(step, "complete", required=True)
            self._database.record_observations(
                self._profile, mission.mission_game_id, observations
            )
            if not complete:
                raise BotModeError(
                    f"Campaign step returned without satisfying completion conditions: {step.code}"
                )

        self._database.update_progress(
            self._profile,
            mission.mission_game_id,
            status="available",
            current_step_id=None,
        )

    def _evaluate(
        self, step: MissionStep, purpose: str, *, required: bool
    ) -> tuple[bool, tuple[tuple[StepCondition, object, bool], ...]]:
        conditions = tuple(
            condition for condition in step.conditions if condition.purpose == purpose
        )
        if not conditions:
            if required:
                raise BotModeError(f"Campaign step has no {purpose} conditions: {step.code}")
            return True, ()
        groups: dict[int, list[bool]] = defaultdict(list)
        observations = []
        for condition in conditions:
            actual = self._state_reader.read(condition.source_type, condition.source_key)
            matched = self._compare(actual, condition)
            groups[condition.condition_group].append(matched)
            observations.append((condition, actual, matched))
        return any(all(results) for results in groups.values()), tuple(observations)

    @staticmethod
    def _compare(actual: object, condition: StepCondition) -> bool:
        if condition.value_type == "integer":
            left, right = int(actual), int(condition.expected_value, 0)
        elif condition.value_type == "boolean":
            left = bool(actual)
            right = condition.expected_value.lower() in {"1", "true", "yes"}
        else:
            left, right = str(actual), condition.expected_value

        match condition.operator:
            case "=":
                return left == right
            case "!=":
                return left != right
            case ">":
                return left > right
            case ">=":
                return left >= right
            case "<":
                return left < right
            case "<=":
                return left <= right
            case "set":
                return bool(left)
            case "unset":
                return not bool(left)
            case "contains":
                return str(right) in str(left)
            case "not_contains":
                return str(right) not in str(left)
        raise BotModeError(f"Unsupported campaign condition operator: {condition.operator}")
