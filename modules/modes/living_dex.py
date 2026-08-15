from __future__ import annotations

from typing import Generator

from modules.context import context
from modules.battle_state import BattleOutcome
from modules.encounter import EncounterInfo
from modules.items import get_item_bag
from modules.living_dex.collection import CollectionSnapshot, is_founder_candidate, is_qualified
from modules.living_dex.progress import LivingDexProgress
from modules.memory import GameState, get_game_state
from modules.map_data import MapRSE
from modules.modes._interface import BattleAction, BotMode, BotModeError
from modules.modes.util import ensure_facing_direction, navigate_to
from modules.modes.util.pc_interaction import PCAction, interact_with_pc
from modules.pokemon_party import get_party
from modules.pokemon_storage import get_pokemon_storage


class LivingDexMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Living Dex RSE"

    @staticmethod
    def is_selectable() -> bool:
        return bool(context.rom and context.rom.is_rse)

    def __init__(self):
        super().__init__()
        self.progress = LivingDexProgress.load(context.profile.path)
        self._pending_founder: tuple[int, str] | None = None

    def on_battle_started(self, encounter: EncounterInfo | None) -> BattleAction | None:
        if encounter is None:
            return BattleAction.Fight

        pokemon = encounter.pokemon
        has_poke_balls = any(slot.quantity > 0 for slot in get_item_bag().poke_balls)
        if is_qualified(pokemon):
            # Direct catch keeps perfect-IV encounters even when global filters do not.
            return BattleAction.Catch if has_poke_balls else BattleAction.RunAway

        if has_poke_balls and self.progress.founder_personality_value is None and is_founder_candidate(
            pokemon, context.config.living_dex.gameplay.founder_min_iv_sum
        ):
            self.progress.current_objective = f"Catch founder {pokemon.species.name}"
            self.progress.save(context.profile.path)
            self._pending_founder = (pokemon.personality_value, pokemon.species.name)
            return BattleAction.Catch

        return BattleAction.RunAway

    def on_battle_ended(self, outcome: BattleOutcome) -> None:
        if self._pending_founder is None:
            return
        personality, species = self._pending_founder
        self._pending_founder = None
        if outcome is BattleOutcome.Caught:
            self.progress.founder_personality_value = personality
            self.progress.founder_species = species
            self.progress.current_objective = f"Founder protected: {species}"
            self.progress.save(context.profile.path)

    def _store_shiny_starter(self) -> Generator:
        starter_name = context.config.living_dex.gameplay.starter
        starter = next(
            (
                pokemon
                for pokemon in get_party()
                if pokemon.species.name == starter_name
                and pokemon.is_shiny
                and pokemon.personality_value != self.progress.founder_personality_value
            ),
            None,
        )
        if starter is None or len(get_party()) < 2:
            return

        self.progress.current_objective = f"Store shiny {starter_name} in Oldale PC"
        self.progress.save(context.profile.path)
        yield from navigate_to(MapRSE.OLDALE_TOWN_POKEMON_CENTER_1F, (14, 6))
        yield from ensure_facing_direction("Up")
        yield from interact_with_pc([PCAction.deposit_pokemon_to_box(starter)])
        self.progress.starter_stored = True
        self.progress.current_objective = f"Shiny {starter_name} stored; founder remains operational"
        self.progress.save(context.profile.path)

    def run(self) -> Generator:
        if not context.rom.is_rse:
            raise BotModeError("Living Dex RSE only supports Ruby, Sapphire, and Emerald.")
        if context.config.cheats.random_soft_reset_rng:
            raise BotModeError("Disable random_soft_reset_rng: it writes directly to game RNG memory.")

        while context.bot_mode == self.name():
            if get_game_state() == GameState.OVERWORLD:
                if self.progress.founder_personality_value is not None and not self.progress.starter_stored:
                    yield from self._store_shiny_starter()
                storage = CollectionSnapshot.from_storage(get_pokemon_storage())
                founder = self.progress.founder_species or "pending"
                self.progress.current_objective = (
                    f"Area collection active | qualified {len(storage.collected)} | "
                    f"free slots {storage.free_slots} | founder {founder}"
                )
                context.message = self.progress.current_objective
            yield
