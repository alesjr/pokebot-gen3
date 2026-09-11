from __future__ import annotations

from typing import Generator
import os

from modules.campaign import (
    CampaignExecutor,
    CartridgeStateReader,
    navigate_to_catalog_location,
    save_campaign_checkpoint,
)
from modules.campaign.capabilities import CampaignCapabilityResolver, campaign_capability
from modules.campaign.rse import run_organize_party_at_pc
from modules.battle_state import BattleOutcome, EncounterType
from modules.battle_strategies import BattleStrategy
from modules.clock import reach_bedroom_clock, set_clock
from modules.context import context
from modules.encounter import EncounterInfo
from modules.memory import get_event_flag
from modules.map_data import PokemonCenter, get_map_enum
from modules.missions import MissionsDatabase
from modules.modes._asserts import (
    assert_boxes_or_party_can_fit_pokemon,
    assert_player_has_poke_balls,
)
from modules.modes._interface import BattleAction, BotMode, BotModeError
from modules.modes.ev_train import EVTrainMode
from modules.modes.starters import (
    StartersMode,
    finish_rse_starter_sequence,
    reach_rse_starter_bag,
)
from modules.modes.util import heal_in_pokemon_center, save_the_game, spin
from modules.modes.util.map import find_closest_pokemon_center
from modules.player import get_player_location
from modules.pokemon_party import get_party
from modules.runtime import get_base_path


class CampaignMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Campaign"

    @staticmethod
    def is_selectable() -> bool:
        return bool(context.rom and context.rom.is_rse)

    def __init__(self):
        self._active_capability: object | None = None
        self._campaign_rules: dict[str, object] = {}
        self._catch_wild_encounters = False
        self._pending_shiny_personality: int | None = None
        self._shiny_deposit_pending = False
        self._defer_shiny_deposit = False
        self._required_hms: list[str] = []
        self._temporary_required_species: list[str] = []
        self._trainer_name = context.profile.trainer_name or os.environ.get("POKEBOT_CAMPAIGN_TRAINER_NAME", "Alesjr")
        self._trainer_gender = context.profile.trainer_gender
        self._starter = context.profile.starter or os.environ.get("POKEBOT_CAMPAIGN_STARTER", "Mudkip")
        super().__init__()

    def on_battle_started(
        self, encounter: EncounterInfo | None
    ) -> BattleAction | BattleStrategy | None:
        action = self._campaign_battle_action(encounter)
        if action is not None:
            return action
        return self._forward("on_battle_started", encounter, default=None)

    def on_navigation_battle_started(
        self, encounter: EncounterInfo | None
    ) -> BattleAction | BattleStrategy | None:
        action = self._campaign_battle_action(encounter)
        if action is not None:
            return action
        return self._forward("on_navigation_battle_started", encounter, default=None)

    def on_battle_ended(self, outcome: BattleOutcome) -> None:
        self._forward("on_battle_ended", outcome, default=None)
        if self._pending_shiny_personality is not None:
            if outcome is BattleOutcome.Caught:
                self._shiny_deposit_pending = any(
                    pokemon.personality_value == self._pending_shiny_personality
                    for pokemon in get_party()
                )
            self._pending_shiny_personality = None

    def on_whiteout(self) -> bool:
        return self._forward("on_whiteout", default=False)

    def on_pokemon_evolving_after_battle(self, pokemon, party_index: int) -> bool:
        return self._forward(
            "on_pokemon_evolving_after_battle", pokemon, party_index, default=True
        )

    def _forward(self, callback_name: str, *args: object, default: object) -> object:
        callback = getattr(self._active_capability, callback_name, None)
        return callback(*args) if callable(callback) else default

    def run(self) -> Generator:
        if not context.rom.is_rse:
            raise BotModeError("Campaign supports only Ruby, Sapphire and Emerald.")
        game_code = (
            "ruby" if context.rom.is_ruby else "sapphire" if context.rom.is_sapphire else "emerald"
        )
        database_path = get_base_path() / "stats" / "missions.db"
        with MissionsDatabase(database_path) as database:
            database.initialize_builtin_catalog()
            capability_resolver = CampaignCapabilityResolver(
                {
                    "profile": {
                        "trainer_name": self._trainer_name,
                        "trainer_gender": self._trainer_gender,
                        "starter": self._starter,
                    }
                },
                campaign=self,
            )
            executor = CampaignExecutor(
                database,
                context.profile.path.name,
                CartridgeStateReader(self._starter),
                capability_resolver,
                self._on_step_started,
                self._on_capability_changed,
                self._before_capability_resume,
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
                self._campaign_rules = mission.rules
                yield from executor.run(mission)
                self._active_capability = None
                last_completed_mission = mission
                context.message = f"{mission.name} concluída"
                yield

    @campaign_capability
    def _choose_starter(self, starter: str, shiny_required: bool) -> Generator:
        state_reader = CartridgeStateReader(starter)
        if not state_reader.read("other", "owns_configured_shiny_starter"):
            yield from reach_rse_starter_bag()
            if not get_event_flag("SYS_POKEMON_GET") and not get_event_flag("RESCUED_BIRCH"):
                yield from save_the_game()
            starters_mode = StartersMode(starter, stop_on_shiny=shiny_required)
            yield from self._run_with_delegate(starters_mode, starters_mode.run())
        yield from finish_rse_starter_sequence()
        yield from save_campaign_checkpoint(1)

    @campaign_capability
    def _set_bedroom_clock(self, trainer_gender: str) -> Generator:
        yield from reach_bedroom_clock(trainer_gender)
        yield from set_clock()

    @campaign_capability
    def _reach_route102(
        self, map_group: int, map_number: int, tile_x: int, tile_y: int
    ) -> Generator:
        yield from navigate_to_catalog_location(map_group, map_number, tile_x, tile_y)
        yield from save_campaign_checkpoint(3)

    @campaign_capability
    def _catch_wild_pokemon(
        self,
        target_source_type: str,
        target_source: str,
        target_count: int,
        capture_required: bool = True,
        deposit_shinies: bool = False,
    ) -> Generator:
        if not capture_required:
            return
        state_reader = CartridgeStateReader(self._starter)
        target_reached = lambda: int(
            state_reader.read(target_source_type, target_source)
        ) >= target_count
        previous = self._catch_wild_encounters
        previous_defer = self._defer_shiny_deposit
        self._catch_wild_encounters = True
        self._defer_shiny_deposit = not deposit_shinies
        try:
            while not target_reached():
                assert_player_has_poke_balls()
                assert_boxes_or_party_can_fit_pokemon()
                yield from spin(target_reached)
        finally:
            self._catch_wild_encounters = previous
            self._defer_shiny_deposit = previous_defer
            if not deposit_shinies:
                self._shiny_deposit_pending = False

    @campaign_capability
    def _heal_captured_pokemon(
        self, map_group: int, map_number: int, tile_x: int, tile_y: int
    ) -> Generator:
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

    @campaign_capability
    def _ev_train_captured_pokemon(self, target_level: int) -> Generator:
        ev_train_mode = EVTrainMode()
        yield from self._run_with_delegate(
            ev_train_mode, ev_train_mode.run_until_party_level(target_level)
        )
        yield from save_campaign_checkpoint(3)

    def _run_with_delegate(self, delegate: object, generator: Generator) -> Generator:
        previous = self._active_capability
        self._active_capability = delegate
        try:
            yield from generator
        finally:
            self._active_capability = previous

    def _campaign_battle_action(
        self, encounter: EncounterInfo | None
    ) -> BattleAction | None:
        if encounter is None or encounter.type in {
            EncounterType.Gift,
            EncounterType.Hatched,
            EncounterType.Tutorial,
        }:
            return None
        if encounter.is_shiny and bool(
            self._campaign_rules.get("shiny.capture_required", False)
        ):
            assert_player_has_poke_balls()
            assert_boxes_or_party_can_fit_pokemon()
            encounter.battle_action = BattleAction.Catch
            self._pending_shiny_personality = encounter.pokemon.personality_value
            return BattleAction.Catch
        if self._catch_wild_encounters and encounter.type.is_wild:
            assert_player_has_poke_balls()
            assert_boxes_or_party_can_fit_pokemon()
            encounter.battle_action = BattleAction.Catch
            return BattleAction.Catch
        return None

    @staticmethod
    def _party_has_shiny() -> bool:
        return any(pokemon.is_shiny for pokemon in get_party().non_eggs)

    def _on_capability_changed(self, capability: object | None) -> None:
        self._active_capability = capability
        if capability is None and not self._party_has_shiny():
            self._shiny_deposit_pending = False

    def _before_capability_resume(self) -> Generator:
        if self._defer_shiny_deposit or not self._shiny_deposit_pending:
            return
        if not self._party_has_shiny():
            self._shiny_deposit_pending = False
            return
        terminal_tile = self._campaign_rules.get("shiny.pc_terminal_tile")
        if (
            not isinstance(terminal_tile, list)
            or len(terminal_tile) != 2
            or not all(isinstance(value, int) for value in terminal_tile)
        ):
            raise BotModeError("Campaign catalog must define shiny.pc_terminal_tile.")

        source_map, source_coordinates = get_player_location()
        previous = self._active_capability
        self._active_capability = None
        try:
            yield from heal_in_pokemon_center(find_closest_pokemon_center())
            yield from run_organize_party_at_pc(
                *terminal_tile,
                storage_required=bool(
                    self._campaign_rules.get("shiny.storage_required", True)
                ),
                optimize_party=bool(
                    self._campaign_rules.get("party.optimize_on_pc_access", True)
                ),
                target_size=int(self._campaign_rules.get("party.target_size", 6)),
                required_hms=self._required_hms,
                temporary_required_species=self._temporary_required_species,
            )
            self._shiny_deposit_pending = False
            yield from navigate_to_catalog_location(
                source_map.value[0],
                source_map.value[1],
                source_coordinates[0],
                source_coordinates[1],
            )
        finally:
            self._active_capability = previous

    def _on_step_started(self, step) -> None:
        self._required_hms = list(step.action_params.get("required_hms", []))
        self._temporary_required_species = list(
            step.action_params.get("temporary_required_species", [])
        )
        location = ""
        if step.map_name is not None:
            location = f" @ {step.map_name}"
            if step.tile_x is not None:
                location += f" ({step.tile_x}, {step.tile_y})"
        context.message = f"{step.step_order}. {step.name}{location}"
