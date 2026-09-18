from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Callable, Generator
from datetime import datetime
from typing import Protocol

from modules.campaign.capabilities import CampaignCapabilityResolver, ResolvedCapability
from modules.context import context
from modules.map import get_map_data
from modules.map_data import get_map_enum
from modules.missions.database import MissionPlan, MissionStep, StepCondition
from modules.modes._interface import BotModeError
from modules.modes.util import (
    ensure_facing_direction,
    navigate_to,
    save_the_game,
    talk_to_npc,
    wait_for_player_avatar_to_be_controllable,
    walk_through_warp,
)
from modules.player import get_player_avatar, get_player_location
from modules.tasks import get_global_script_context, is_waiting_for_input


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
        from modules.player import get_player_avatar, player_avatar_is_controllable

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
        if source_type == "script" and source_key == "active":
            return get_global_script_context().is_active
        if source_type == "other" and source_key == "avatar_controllable":
            return player_avatar_is_controllable()
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
            if source_key == "shiny_count":
                return sum(pokemon.is_shiny for pokemon in party)
            if source_key == "non_shiny_count":
                return sum(not pokemon.is_shiny for pokemon in party)
        if source_type == "other" and source_key == "game_started":
            return game_has_started()
        if source_type == "other" and source_key == "player_identity":
            from modules.player import get_player

            return "brendan" if get_player().gender == "male" else "may"
        if source_type == "other" and source_key == "rival_identity":
            from modules.player import get_player

            return "brendan" if get_player().gender == "female" else "may"
        if source_type == "other" and source_key == "pokedex_owned_count":
            from modules.pokedex import get_pokedex

            return len(get_pokedex().owned_species)
        if source_type == "other" and source_key == "owned_non_starter_count":
            from modules.pokemon_party import get_party
            from modules.pokemon_storage import get_pokemon_storage

            expected_species = self._configured_starter_species()
            owned = list(get_party().non_eggs) + [
                slot.pokemon
                for box in get_pokemon_storage().boxes
                for slot in box.slots
                if not slot.pokemon.is_egg
            ]
            return sum(
                pokemon.species.name not in expected_species for pokemon in owned
            )
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
        if source_type == "other" and source_key.startswith(
            ("owns_species:", "owns_shiny_species:")
        ):
            condition, _, species_name = source_key.partition(":")
            from modules.pokemon_party import get_party
            from modules.pokemon_storage import get_pokemon_storage

            owned = list(get_party()) + [
                slot.pokemon
                for box in get_pokemon_storage().boxes
                for slot in box.slots
            ]
            return any(
                pokemon.species.name == species_name
                and (condition != "owns_shiny_species" or pokemon.is_shiny)
                for pokemon in owned
            )
        raise BotModeError(f"Unsupported campaign condition source: {source_type}:{source_key}")


class CampaignExecutor:
    """Execute ordered database steps through resolved internal capabilities."""

    def __init__(
        self,
        state_reader: StateReader,
        capability_resolver: CampaignCapabilityResolver,
        on_step_started: Callable[[MissionStep], None] | None = None,
        on_capability_changed: Callable[[object | None], None] | None = None,
        before_capability_resume: Callable[[], Generator] | None = None,
    ):
        self._state_reader = state_reader
        self._capability_resolver = capability_resolver
        self._on_step_started = on_step_started
        self._on_capability_changed = on_capability_changed
        self._before_capability_resume = before_capability_resume
        self._state_snapshot: dict[tuple[str, str], object] | None = None

    def is_complete(self, mission: MissionPlan) -> bool:
        if not mission.steps:
            raise BotModeError(f"Campaign mission has no steps: {mission.code}")
        complete, _ = self._evaluate(mission.steps[-1], "complete", required=True)
        return complete

    def run(self, mission: MissionPlan) -> Generator:
        if not mission.steps:
            raise BotModeError(f"Campaign mission has no steps: {mission.code}")
        while True:
            step = self._select_next_step(mission)
            if step is None:
                return
            allowed, _ = self._evaluate(step, "unlock", required=False)
            if not allowed:
                raise BotModeError(
                    f"Campaign step prerequisite not satisfied: {step.code}:unlock"
                )
            if self._on_step_started is not None:
                self._on_step_started(step)
            context.emulator.create_save_state(
                f"Campaign_Mission_{mission.id}_Step_{step.step_order}"
            )
            while (yield from self._run_step_action(step, mission.rules)):
                complete, _ = self._evaluate(step, "complete", required=True)
                if complete:
                    break
            complete, _ = self._evaluate(step, "complete", required=True)
            if not complete and step.recovery_action is not None:
                recovery = self._capability_resolver.resolve(
                    step.recovery_action, step.recovery_params, step, mission.rules
                )
                while (yield from self._run_capability(recovery)):
                    complete, _ = self._evaluate(step, "complete", required=True)
                    if complete:
                        break
                    recovery = self._capability_resolver.resolve(
                        step.recovery_action,
                        step.recovery_params,
                        step,
                        mission.rules,
                    )
                complete, _ = self._evaluate(step, "complete", required=True)
            if not complete:
                raise BotModeError(
                    f"Campaign step returned without satisfying completion conditions: {step.code}"
                )

    def _select_next_step(self, mission: MissionPlan) -> MissionStep | None:
        rejected: list[str] = []
        incomplete = False
        self._state_snapshot = {}
        try:
            for step in mission.steps:
                complete, _ = self._evaluate(step, "complete", required=True)
                if complete:
                    continue
                incomplete = True
                start_conditions = tuple(
                    condition
                    for condition in step.conditions
                    if condition.purpose == "start"
                )
                if not start_conditions:
                    rejected.append(f"{step.code}: missing start conditions")
                    continue
                applicable, observations = self._evaluate(
                    step, "start", required=True
                )
                if not applicable:
                    rejected.append(
                        f"{step.code}: "
                        + ", ".join(
                            f"{condition.source_type}:{condition.source_key}="
                            f"{actual!r} {condition.operator} "
                            f"{condition.expected_value!r} ({matched})"
                            for condition, actual, matched in observations
                        )
                    )
                    continue
                if not self._step_is_enabled(step, mission.rules):
                    rejected.append(f"{step.code}: action conditions not satisfied")
                    continue
                return step
        finally:
            self._state_snapshot = None
        if not incomplete:
            return None
        raise BotModeError(
            f"Campaign mission {mission.code} has no applicable incomplete step. "
            + "Rejected: "
            + "; ".join(rejected)
        )

    def _run_step_action(
        self, step: MissionStep, rules: dict[str, object]
    ) -> Generator:
        if step.action.startswith("operation:"):
            operation = step.action.removeprefix("operation:")
            parameters = self._capability_resolver.resolve_data(
                step.action_params, step, rules
            )
            if not isinstance(parameters, dict):
                raise BotModeError(
                    f"Campaign operation parameters must be an object: {step.code}"
                )
            parameters = self._select_operation_variant(parameters, step.code)
            action = {"operation": operation, **parameters}
            capability = ResolvedCapability(
                step.action,
                self._run_catalog_action,
                {"action": action, "step_code": step.code, "index": 1},
            )
            return (yield from self._run_capability(capability))
        if step.action != "sequence":
            capability = self._capability_resolver.resolve(
                step.action, step.action_params, step, rules
            )
            return (yield from self._run_capability(capability))

        parameters = self._capability_resolver.resolve_data(
            step.action_params, step, rules
        )
        if not isinstance(parameters, dict):
            raise BotModeError(
                f"Campaign sequence parameters must be an object: {step.code}"
            )
        required_hms = parameters.get("required_hms", [])
        if not isinstance(required_hms, list) or not all(
            isinstance(move, str) for move in required_hms
        ):
            raise BotModeError(
                f"Campaign required_hms must be a list of names: {step.code}"
            )
        if required_hms:
            capability = ResolvedCapability(
                f"sequence:{step.code}:required_hms",
                self._ensure_required_hms,
                {"required_hms": required_hms},
            )
            if (yield from self._run_capability(capability)):
                return True

        actions = self._select_sequence_actions(parameters, step.code)
        for index, action in enumerate(actions, start=1):
            if not self._catalog_action_is_enabled(action, step.code, index):
                continue
            reference = action.get("capability")
            if reference is None:
                capability = ResolvedCapability(
                    f"sequence:{step.code}:{index}",
                    self._run_catalog_action,
                    {"action": action, "step_code": step.code, "index": index},
                )
            else:
                capability_parameters = action.get("parameters", {})
                if not isinstance(reference, str) or not isinstance(
                    capability_parameters, dict
                ):
                    raise BotModeError(
                        f"Campaign sequence capability is invalid: {step.code}:{index}"
                    )
                capability = self._capability_resolver.resolve(
                    reference, capability_parameters, step, rules
                )
            if (yield from self._run_capability(capability)):
                return True
        return False

    def _step_is_enabled(
        self, step: MissionStep, rules: dict[str, object]
    ) -> bool:
        if not step.action.startswith("operation:"):
            return True
        parameters = self._capability_resolver.resolve_data(
            step.action_params, step, rules
        )
        if not isinstance(parameters, dict):
            raise BotModeError(
                f"Campaign operation parameters must be an object: {step.code}"
            )
        parameters = self._select_operation_variant(parameters, step.code)
        return self._catalog_action_is_enabled(parameters, step.code, 1)

    def _select_operation_variant(
        self, parameters: dict[str, object], step_code: str
    ) -> dict[str, object]:
        variant_source = parameters.get("variant_source")
        variants = parameters.get("variants")
        if variant_source is None and variants is None:
            return parameters
        if not isinstance(variant_source, dict) or not isinstance(variants, dict):
            raise BotModeError(
                f"Campaign operation variant configuration is invalid: {step_code}"
            )
        try:
            source_type = str(variant_source["source_type"])
            source_key = str(variant_source["source_key"])
        except KeyError as error:
            raise BotModeError(
                f"Campaign operation variant source is incomplete: {step_code}"
            ) from error
        variant_name = str(self._read_state(source_type, source_key))
        selected = variants.get(variant_name)
        if not isinstance(selected, dict):
            raise BotModeError(
                f"Campaign operation variant {variant_name!r} is unavailable: {step_code}"
            )
        common = {
            key: value
            for key, value in parameters.items()
            if key not in {"variant_source", "variants"}
        }
        return {**common, **selected}

    @staticmethod
    def _select_sequence_actions(
        parameters: dict[str, object], step_code: str
    ) -> list[dict[str, object]]:
        actions = parameters.get("actions")
        if not isinstance(actions, list) or not actions:
            raise BotModeError(
                f"Campaign sequence actions must be a non-empty list: {step_code}"
            )
        if not all(isinstance(action, dict) for action in actions):
            raise BotModeError(
                f"Campaign sequence actions must be objects: {step_code}"
            )
        return actions

    def _catalog_action_is_enabled(
        self, action: dict[str, object], step_code: str, index: int
    ) -> bool:
        binding_conditions = action.get("when_binding", [])
        if isinstance(binding_conditions, dict):
            binding_conditions = [binding_conditions]
        if not isinstance(binding_conditions, list):
            raise BotModeError(
                f"Campaign binding conditions must be a list: {step_code}:{index}"
            )
        for condition in binding_conditions:
            if not isinstance(condition, dict) or "value" not in condition:
                raise BotModeError(
                    f"Campaign binding condition is invalid: {step_code}:{index}"
                )
            if "equals" in condition and condition["value"] != condition["equals"]:
                return False
            if "not_equals" in condition and condition["value"] == condition["not_equals"]:
                return False
        conditions = action.get("when", [])
        if isinstance(conditions, dict):
            conditions = [conditions]
        if not isinstance(conditions, list):
            raise BotModeError(
                f"Campaign action conditions must be a list: {step_code}:{index}"
            )
        for condition_data in conditions:
            if not isinstance(condition_data, dict):
                raise BotModeError(
                    f"Campaign action condition must be an object: {step_code}:{index}"
                )
            try:
                condition = StepCondition(
                    id=0,
                    purpose="start",
                    condition_group=1,
                    source_type=str(condition_data["source_type"]),
                    source_key=str(condition_data["source_key"]),
                    operator=str(condition_data["operator"]),
                    expected_value=str(condition_data["expected_value"]),
                    value_type=str(condition_data.get("value_type", "text")),
                )
            except KeyError as error:
                raise BotModeError(
                    f"Campaign action condition is incomplete: {step_code}:{index}"
                ) from error
            actual = self._read_state(condition.source_type, condition.source_key)
            if not self._compare(actual, condition):
                return False
        return True

    def _run_catalog_action(
        self, action: dict[str, object], step_code: str, index: int
    ) -> Generator:
        operation = action.get("operation")
        if operation == "navigate":
            destination = get_map_enum(
                (
                    self._action_integer(action, "map_group", step_code, index),
                    self._action_integer(action, "map_number", step_code, index),
                )
            )
            coordinates = (
                self._action_integer(action, "tile_x", step_code, index),
                self._action_integer(action, "tile_y", step_code, index),
            )
            yield from wait_for_player_avatar_to_be_controllable(
                str(action.get("button", "B")),
                wait_for_no_script=True,
                timeout_frames=self._action_timeout(action, step_code, index),
            )
            expecting_script = bool(action.get("expecting_script", True))
            yield from navigate_to(
                destination, coordinates, expecting_script=expecting_script
            )
            if expecting_script:
                yield from self._wait_for_catalog_control(action)
            return
        if operation == "warp":
            source_map = get_map_enum(
                (
                    self._action_integer(action, "map_group", step_code, index),
                    self._action_integer(action, "map_number", step_code, index),
                )
            )
            if action.get("navigate_to_warp", False) and get_player_location()[0] is source_map:
                target = (
                    self._action_integer(action, "target_map_group", step_code, index),
                    self._action_integer(action, "target_map_number", step_code, index),
                )
                warps = [
                    warp
                    for warp in get_map_data(source_map, (0, 0)).warps
                    if (warp.destination_map_group, warp.destination_map_number) == target
                ]
                if len(warps) != 1:
                    raise BotModeError(
                        f"Expected one warp from {source_map.name} to {target}, "
                        f"found {len(warps)}: {step_code}:{index}"
                    )
                yield from wait_for_player_avatar_to_be_controllable(
                    "B", wait_for_no_script=True,
                    timeout_frames=self._action_timeout(action, step_code, index),
                )
                yield from navigate_to(
                    source_map, warps[0].local_coordinates, expecting_script=True
                )
            target_x = action.get("target_x")
            if target_x is not None:
                target_x = self._action_integer(
                    action, "target_x", step_code, index
                )
            yield from walk_through_warp(
                source_map,
                self._action_direction(action, step_code, index),
                target_x=target_x,
                timeout_frames=self._action_timeout(action, step_code, index),
            )
            if not action.get("handoff_on_target_map", False):
                yield from self._wait_for_catalog_control(action)
            if "target_map_group" in action or "target_map_number" in action:
                target_map = get_map_enum(
                    (
                        self._action_integer(action, "target_map_group", step_code, index),
                        self._action_integer(action, "target_map_number", step_code, index),
                    )
                )
                if get_player_location()[0] is not target_map:
                    raise BotModeError(
                        f"Campaign warp reached {get_player_location()[0].name}; "
                        f"expected {target_map.name}: {step_code}:{index}"
                    )
            return
        if operation == "talk_to_npc":
            yield from talk_to_npc(
                self._action_integer(action, "local_object_id", step_code, index)
            )
            yield from self._wait_for_catalog_control(action)
            return
        if operation == "interact":
            if "tile_x" in action or "tile_y" in action:
                nested = dict(action)
                nested["operation"] = "navigate"
                yield from self._run_catalog_action(nested, step_code, index)
            yield from ensure_facing_direction(
                self._action_direction(action, step_code, index)
            )
            context.emulator.press_button("A")
            yield
            yield from self._wait_for_catalog_control(action)
            return
        if operation == "wait_for_control":
            yield from self._wait_for_catalog_control(action)
            return
        if operation == "save":
            yield from save_the_game()
            return
        if operation == "checkpoint":
            yield from save_campaign_checkpoint(
                self._action_integer(action, "mission_number", step_code, index)
            )
            return
        if operation == "puzzle_solver":
            from modules.modes.puzzle_solver import PuzzleSolverMode

            yield from PuzzleSolverMode().run(return_to_caller=True)
            return
        raise BotModeError(
            f"Unsupported Campaign operation {operation!r}: {step_code}:{index}"
        )

    @staticmethod
    def _wait_for_catalog_control(action: dict[str, object]) -> Generator:
        yield from wait_for_player_avatar_to_be_controllable(
            str(action.get("button", "B")),
            stable_frames=int(action.get("stable_frames", 30)),
            wait_for_no_script=True,
            timeout_frames=int(action.get("timeout_frames", 30_000)),
        )

    @staticmethod
    def _action_direction(
        action: dict[str, object], step_code: str, index: int
    ) -> str:
        direction = action.get("direction", "Up")
        if direction not in {"Up", "Down", "Left", "Right"}:
            raise BotModeError(
                f"Campaign action has invalid direction: {step_code}:{index}"
            )
        return str(direction)

    @classmethod
    def _action_timeout(
        cls, action: dict[str, object], step_code: str, index: int
    ) -> int:
        return cls._action_integer(
            action, "timeout_frames", step_code, index, default=30_000
        )

    @staticmethod
    def _action_integer(
        action: dict[str, object],
        key: str,
        step_code: str,
        index: int,
        *,
        default: int | None = None,
    ) -> int:
        value = action.get(key, default)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise BotModeError(
                f"Campaign action requires non-negative integer {key}: "
                f"{step_code}:{index}"
            )
        return value

    @staticmethod
    def _ensure_required_hms(required_hms: list[str]) -> Generator:
        from modules.campaign.team import combat_potential, hm_coverage
        from modules.items import get_item_bag
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

    def _run_capability(self, capability: ResolvedCapability) -> Generator:
        if self._on_capability_changed is not None:
            self._on_capability_changed(capability.delegate)
        try:
            generator = capability.run()
            action = capability.arguments.get("action")
            while True:
                if self._before_capability_resume is not None:
                    restart_required = yield from self._before_capability_resume()
                    if restart_required:
                        return True
                if isinstance(action, dict) and action.get("handoff_on_target_map", False):
                    target_map = get_map_enum(
                        (
                            self._action_integer(action, "target_map_group", capability.reference, 1),
                            self._action_integer(action, "target_map_number", capability.reference, 1),
                        )
                    )
                    target_group, target_number = target_map.value
                    if self._read_state("map", "current") == f"{target_group}:{target_number}":
                        yield
                        return False
                script_context = get_global_script_context()
                if (
                    script_context is not None
                    and script_context.is_active
                    and not (isinstance(action, dict) and action.get("local_dialogue_control", False))
                    and is_waiting_for_input()
                ):
                    context.emulator.press_button("A")
                    yield
                    continue
                try:
                    yielded = next(generator)
                except StopIteration:
                    break
                yield yielded
            return False
        finally:
            if self._on_capability_changed is not None:
                self._on_capability_changed(None)

    def _evaluate(
        self, step: MissionStep, purpose: str, *, required: bool
    ) -> tuple[bool, tuple[tuple[StepCondition, object, bool], ...]]:
        conditions = tuple(
            condition for condition in step.conditions if condition.purpose == purpose
        )
        if not conditions:
            if required:
                self._log_step_evaluation(step, purpose, False, ())
                raise BotModeError(f"Campaign step has no {purpose} conditions: {step.code}")
            self._log_step_evaluation(step, purpose, True, ())
            return True, ()
        groups: dict[int, list[bool]] = defaultdict(list)
        observations = []
        for condition in conditions:
            actual = self._read_state(condition.source_type, condition.source_key)
            matched = self._compare(actual, condition)
            groups[condition.condition_group].append(matched)
            observations.append((condition, actual, matched))
        result = any(all(results) for results in groups.values())
        observations = tuple(observations)
        self._log_step_evaluation(step, purpose, result, observations)
        return result, observations

    def _read_state(self, source_type: str, source_key: str) -> object:
        key = source_type, source_key
        if self._state_snapshot is not None:
            if key not in self._state_snapshot:
                self._state_snapshot[key] = self._state_reader.read(
                    source_type, source_key
                )
            return self._state_snapshot[key]
        return self._state_reader.read(source_type, source_key)

    @staticmethod
    def _log_step_evaluation(
        step: MissionStep,
        purpose: str,
        passed: bool,
        observations: tuple[tuple[StepCondition, object, bool], ...],
    ) -> None:
        record = {
            "timestamp": datetime.now().astimezone().isoformat(),
            "mission_game_id": step.mission_game_id,
            "step_id": step.id,
            "step": step.step_order,
            "code": step.code,
            "name": step.name,
            "purpose": purpose,
            "passed": passed,
            "conditions": [
                {
                    "group": condition.condition_group,
                    "source": f"{condition.source_type}:{condition.source_key}",
                    "actual": actual,
                    "operator": condition.operator,
                    "expected": condition.expected_value,
                    "value_type": condition.value_type,
                    "passed": matched,
                }
                for condition, actual, matched in observations
            ],
        }
        with (context.profile.path / "campaign_steps.jsonl").open(
            "a", encoding="utf-8"
        ) as log_file:
            log_file.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

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
