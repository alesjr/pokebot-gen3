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
from modules.campaign.rse import (
    run_catch_new_route102_pokemon,
)
from modules.battle_strategies import BattleStrategy
from modules.clock import reach_bedroom_clock, set_clock
from modules.context import context
from modules.encounter import EncounterInfo
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
        self._trainer_name = context.profile.trainer_name or os.environ.get("POKEBOT_CAMPAIGN_TRAINER_NAME", "Alesjr")
        self._trainer_gender = context.profile.trainer_gender
        self._starter = context.profile.starter or os.environ.get("POKEBOT_CAMPAIGN_STARTER", "Mudkip")
        super().__init__()

    def on_battle_started(
        self, encounter: EncounterInfo | None
    ) -> BattleAction | BattleStrategy | None:
        return self._forward("on_battle_started", encounter, default=None)

    def on_navigation_battle_started(
        self, encounter: EncounterInfo | None
    ) -> BattleAction | BattleStrategy | None:
        return self._forward("on_navigation_battle_started", encounter, default=None)

    def on_battle_ended(self, outcome) -> None:
        self._forward("on_battle_ended", outcome, default=None)

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
    def _catch_new_route102_pokemon(self, minimum_non_starter_count: int) -> Generator:
        state_reader = CartridgeStateReader(self._starter)
        yield from run_catch_new_route102_pokemon(
            lambda: int(state_reader.read("party", "non_starter_count"))
            >= minimum_non_starter_count,
        )

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

    def _on_capability_changed(self, capability: object | None) -> None:
        self._active_capability = capability

    def _on_step_started(self, step) -> None:
        location = ""
        if step.map_name is not None:
            location = f" @ {step.map_name}"
            if step.tile_x is not None:
                location += f" ({step.tile_x}, {step.tile_y})"
        context.message = f"{step.step_order}. {step.name}{location}"
