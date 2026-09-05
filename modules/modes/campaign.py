from __future__ import annotations

from typing import Generator
import os

from modules.campaign import (
    CampaignExecutor,
    CartridgeStateReader,
    navigate_to_catalog_location,
    save_campaign_checkpoint,
)
from modules.campaign.rse import (
    run_catch_new_route102_pokemon,
    run_defeat_route103_rival,
    run_deposit_shiny_starter,
    run_leave_birch_lab,
    run_meet_rival,
    run_new_game_intro,
    run_receive_first_poke_balls,
)
from modules.battle_strategies import BattleStrategy
from modules.clock import reach_bedroom_clock, set_clock
from modules.context import context
from modules.encounter import EncounterInfo, handle_encounter
from modules.memory import get_event_flag
from modules.map_data import PokemonCenter, get_map_enum
from modules.missions import MissionsDatabase
from modules.modes._interface import BattleAction, BotMode, BotModeError
from modules.modes.ev_train import EVTrainMode
from modules.modes.starters import (
    StartersMode,
    finish_rse_starter_sequence,
    reach_rse_starter_bag,
)
from modules.modes.util import heal_in_pokemon_center, save_the_game
from modules.pokedex import get_pokedex
from modules.runtime import get_base_path


class CampaignMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Campaign"

    @staticmethod
    def is_selectable() -> bool:
        return bool(context.rom and context.rom.is_rse)

    def __init__(self):
        self._active_action: str | None = None
        self._active_step = None
        self._trainer_name = context.profile.trainer_name or os.environ.get("POKEBOT_CAMPAIGN_TRAINER_NAME", "Alesjr")
        self._trainer_gender = context.profile.trainer_gender
        self._starter = context.profile.starter or os.environ.get("POKEBOT_CAMPAIGN_STARTER", "Mudkip")
        self._starters_mode = StartersMode(self._starter, stop_on_shiny=True)
        self._ev_train_mode = EVTrainMode()
        super().__init__()

    def on_battle_started(
        self, encounter: EncounterInfo | None
    ) -> BattleAction | BattleStrategy | None:
        if self._active_action == "choose_starter":
            return self._starters_mode.on_battle_started(encounter)
        if self._active_action == "catch_new_route102_pokemon" and encounter is not None:
            action = handle_encounter(encounter)
            if encounter.pokemon.species not in get_pokedex().owned_species:
                encounter.battle_action = BattleAction.Catch
                return BattleAction.Catch
            return action
        if self._active_action == "ev_train_captured_pokemon":
            return self._ev_train_mode.on_battle_started(encounter)
        return None

    def on_battle_ended(self, outcome) -> None:
        if self._active_action == "ev_train_captured_pokemon":
            self._ev_train_mode.on_battle_ended(outcome)

    def on_whiteout(self) -> bool:
        if self._active_action == "ev_train_captured_pokemon":
            return self._ev_train_mode.on_whiteout()
        return False

    def run(self) -> Generator:
        if not context.rom.is_rse:
            raise BotModeError("Campaign supports only Ruby, Sapphire and Emerald.")
        game_code = (
            "ruby" if context.rom.is_ruby else "sapphire" if context.rom.is_sapphire else "emerald"
        )
        database_path = get_base_path() / "stats" / "missions.db"
        with MissionsDatabase(database_path) as database:
            database.initialize_builtin_catalog()
            executor = CampaignExecutor(
                database,
                context.profile.path.name,
                CartridgeStateReader(self._starter),
                {
                    "new_game_intro": self._new_game_intro,
                    "set_bedroom_clock": self._set_bedroom_clock,
                    "meet_rival": self._meet_rival,
                    "reach_starter_bag": reach_rse_starter_bag,
                    "choose_starter": self._choose_starter,
                    "defeat_route103_rival": run_defeat_route103_rival,
                    "receive_first_poke_balls": run_receive_first_poke_balls,
                    "leave_birch_lab": self._leave_birch_lab,
                    "navigate_to_catalog_location": self._navigate_to_catalog_location,
                    "reach_route102": self._reach_route102,
                    "catch_new_route102_pokemon": self._catch_new_route102_pokemon,
                    "heal_captured_pokemon_oldale": self._heal_captured_pokemon,
                    "deposit_shiny_starter": self._deposit_shiny_starter,
                    "ev_train_captured_pokemon": self._ev_train_captured_pokemon,
                },
                self._on_step_started,
            )
            last_completed_mission = None
            while context.bot_mode == self.name():
                mission = next(
                    (plan for plan in database.mission_plans(game_code) if not executor.is_complete(plan)),
                    None,
                )
                if mission is None:
                    if last_completed_mission is None:
                        context.message = "Nenhuma missão pendente conforme o save atual."
                    yield
                    continue
                yield from executor.run(mission)
                self._active_action = None
                self._active_step = None
                last_completed_mission = mission
                context.message = f"{mission.name} concluída"
                yield

    def _new_game_intro(self) -> Generator:
        yield from run_new_game_intro(
            self._trainer_name,
            self._trainer_gender,
        )

    def _choose_starter(self) -> Generator:
        state_reader = CartridgeStateReader(self._starter)
        if not state_reader.read("other", "owns_configured_shiny_starter"):
            yield from reach_rse_starter_bag()
            if not get_event_flag("SYS_POKEMON_GET") and not get_event_flag("RESCUED_BIRCH"):
                yield from save_the_game()
            yield from self._starters_mode.run()
        yield from finish_rse_starter_sequence()
        yield from save_campaign_checkpoint(1)

    def _set_bedroom_clock(self) -> Generator:
        yield from reach_bedroom_clock(self._trainer_gender)
        yield from set_clock()

    def _meet_rival(self) -> Generator:
        yield from run_meet_rival(self._trainer_gender)

    def _catalog_location(self) -> tuple[int, int, int, int]:
        step = self._active_step
        if (
            step is None
            or step.map_group is None
            or step.map_number is None
            or step.tile_x is None
            or step.tile_y is None
        ):
            raise BotModeError("Campaign navigation step has no catalog location.")
        return step.map_group, step.map_number, step.tile_x, step.tile_y

    def _navigate_to_catalog_location(self) -> Generator:
        yield from navigate_to_catalog_location(*self._catalog_location())

    def _leave_birch_lab(self) -> Generator:
        yield from run_leave_birch_lab()

    def _reach_route102(self) -> Generator:
        yield from navigate_to_catalog_location(*self._catalog_location())
        yield from save_campaign_checkpoint(3)

    def _catch_new_route102_pokemon(self) -> Generator:
        target_count = self._condition_integer("party", "non_starter_count")
        state_reader = CartridgeStateReader(self._starter)
        yield from run_catch_new_route102_pokemon(
            lambda: int(state_reader.read("party", "non_starter_count")) >= target_count,
        )

    def _deposit_shiny_starter(self) -> Generator:
        yield from run_deposit_shiny_starter(self._starter, *self._catalog_location())

    def _heal_captured_pokemon(self) -> Generator:
        map_group, map_number, tile_x, tile_y = self._catalog_location()
        destination_map = get_map_enum((map_group, map_number))
        pokemon_center = next(
            (
                center
                for center in PokemonCenter
                if center.value == (destination_map, (tile_x, tile_y))
            ),
            None,
        )
        if pokemon_center is None:
            raise BotModeError(
                f"Campaign catalog location is not a known Pokémon Center: "
                f"{destination_map.name} {(tile_x, tile_y)}."
            )
        yield from heal_in_pokemon_center(pokemon_center)

    def _condition_integer(self, source_type: str, source_key: str) -> int:
        step = self._active_step
        if step is not None:
            for condition in step.conditions:
                if (
                    condition.purpose == "complete"
                    and condition.source_type == source_type
                    and condition.source_key == source_key
                ):
                    return int(condition.expected_value, 0)
        raise BotModeError(
            f"Campaign step has no integer condition for {source_type}:{source_key}."
        )

    def _ev_train_captured_pokemon(self) -> Generator:
        target_level = self._condition_integer("party", "minimum_level")
        yield from self._ev_train_mode.run_until_party_level(target_level)
        yield from save_campaign_checkpoint(3)

    def _on_step_started(self, step) -> None:
        self._active_action = step.action
        self._active_step = step
        location = ""
        if step.map_name is not None:
            location = f" @ {step.map_name}"
            if step.tile_x is not None:
                location += f" ({step.tile_x}, {step.tile_y})"
        context.message = f"{step.step_order}. {step.name}{location}"
