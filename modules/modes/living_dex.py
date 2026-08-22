from __future__ import annotations

from typing import Generator

from modules.context import context
from modules.battle_state import BattleOutcome
from modules.encounter import EncounterInfo
from modules.items import get_item_bag, get_item_by_name
from modules.living_dex.collection import CollectionSnapshot, is_founder_candidate, is_qualified, storage_has_space
from modules.living_dex.progress import LivingDexProgress
from modules.living_dex.observability import record_event
from modules.living_dex.intro import run_new_game_intro
from modules.living_dex.rse_mission_controller import RSEMissionController
from modules.living_dex.quests import next_quest
from modules.memory import GameState, game_has_started, get_event_flag, get_event_var, get_game_state
from modules.map_data import MapRSE
from modules.modes._interface import BattleAction, BotMode, BotModeError
from modules.modes.static_soft_resets import (
    StaticSoftResetController,
    get_static_encounter_in_current_battle,
    get_targeted_encounter,
)
from modules.modes.util import ensure_facing_direction, navigate_to, save_the_game
from modules.modes.util.pc_interaction import PCAction, interact_with_pc
from modules.pokemon_party import get_party
from modules.pokemon_storage import get_pokemon_storage


class LivingDexMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Living Dex Gen III"

    @staticmethod
    def is_selectable() -> bool:
        return bool(context.rom and (context.rom.is_rse or context.rom.is_frlg))

    def __init__(self):
        super().__init__()
        self.progress = LivingDexProgress.load(context.profile.path)
        self._pending_founder: tuple[int, str] | None = None
        self._static_reset: StaticSoftResetController | None = None
        self._run_from_navigation_encounters = False
        self._fight_navigation_encounters = False
        self._navigation_catch_species: str | None = None
        self._battle_config_before_campaign = None

    def on_navigation_battle_started(self, encounter: EncounterInfo | None) -> BattleAction | None:
        if self._run_from_navigation_encounters and encounter is not None:
            if encounter.pokemon.is_shiny:
                return None
            if encounter.pokemon.species.name == self._navigation_catch_species:
                return BattleAction.Catch
            return BattleAction.Fight if self._fight_navigation_encounters else BattleAction.RunAway
        return None

    def _set_navigation_encounter_policy(
        self, enabled: bool, fight_wild: bool = False, catch_species: str | None = None
    ) -> None:
        self._run_from_navigation_encounters = enabled
        self._fight_navigation_encounters = enabled and fight_wild
        self._navigation_catch_species = catch_species if enabled else None
        if enabled and self._battle_config_before_campaign is None:
            self._battle_config_before_campaign = context.config.battle
            context.config.battle = context.config.battle.model_copy(
                update={
                    "hp_threshold": 0,
                    "new_move": "learn_best",
                    "stop_evolution": False,
                }
            )
        elif not enabled and self._battle_config_before_campaign is not None:
            context.config.battle = self._battle_config_before_campaign
            self._battle_config_before_campaign = None

    def on_whiteout(self) -> bool:
        return self._run_from_navigation_encounters

    def on_battle_started(self, encounter: EncounterInfo | None) -> BattleAction | None:
        if encounter is not None and encounter.pokemon.is_shiny and not storage_has_space(get_pokemon_storage()):
            self._pause_for_protected_shiny(encounter, "Pokémon storage is full")
            return BattleAction.CustomAction
        if self._static_reset is None and encounter is not None:
            static_encounter = get_static_encounter_in_current_battle(encounter.pokemon.species.name)
            quest_key = None if static_encounter is None else f"static:{static_encounter.name}"
            if static_encounter is not None and quest_key not in self.progress.completed_quests:
                self._start_static_hunt(static_encounter)
        if self._static_reset is not None:
            action = self._static_reset.on_battle_started(encounter)
            if encounter is not None:
                pokemon = encounter.pokemon
                record_event(
                    "encounter",
                    f"{pokemon.species.name} encontrado: {action.name}",
                    shiny=pokemon.is_shiny,
                    iv_sum=pokemon.ivs.sum(),
                    personality=f"{pokemon.personality_value:08X}",
                )
            return action
        if encounter is None:
            return BattleAction.Fight

        pokemon = encounter.pokemon
        has_poke_balls = any(slot.quantity > 0 for slot in get_item_bag().poke_balls)
        if is_qualified(pokemon):
            if has_poke_balls:
                return BattleAction.Catch
            self._pause_for_protected_shiny(encounter, "No Poké Balls available")
            return BattleAction.CustomAction

        if has_poke_balls and self.progress.founder_personality_value is None and is_founder_candidate(
            pokemon, context.config.living_dex.gameplay.founder_min_iv_sum
        ):
            self.progress.current_objective = f"Catch founder {pokemon.species.name}"
            self.progress.save(context.profile.path)
            self._pending_founder = (pokemon.personality_value, pokemon.species.name)
            return BattleAction.Catch

        return BattleAction.RunAway

    def _pause_for_protected_shiny(self, encounter: EncounterInfo, reason: str) -> None:
        pokemon = encounter.pokemon
        self.progress.current_objective = f"Protected shiny blocked: {pokemon.species.name}: {reason}"
        self.progress.save(context.profile.path)
        record_event(
            "blocked_storage" if "storage" in reason.lower() else "blocked_poke_balls",
            self.progress.current_objective,
            personality=f"{pokemon.personality_value:08X}",
        )
        context.message = self.progress.current_objective
        context.set_manual_mode(enable_video_and_slow_down=False)

    def _start_static_hunt(self, targeted_encounter) -> None:
        mission = (
            context.mission_tracker.activate_static_encounter(targeted_encounter)
            if context.mission_tracker is not None
            else None
        )
        mission_label = f"{mission.mission_id}: {mission.title}" if mission is not None else targeted_encounter.name
        self.progress.current_objective = f"Static hunt active: {mission_label}"
        self.progress.save(context.profile.path)
        record_event("hunt", f"Caça estática iniciada: {targeted_encounter.name}")
        self._static_reset = StaticSoftResetController(
            targeted_encounter,
            auto_catch=True,
            qualifies=(
                (lambda candidate: candidate.pokemon.is_shiny)
                if targeted_encounter.shiny_only
                else (lambda candidate: is_qualified(candidate.pokemon))
            ),
        )

    def _run_static_hunt(self) -> Generator:
        targeted_encounter = self._static_reset.encounter
        quest_key = f"static:{targeted_encounter.name}"
        yield from self._static_reset.run(stop_when_caught=True)

        if self._static_reset.caught:
            # Mandatory durability barrier. Never allow another reset before
            # the caught Pokémon has reached the cartridge save file.
            self.progress.current_objective = f"Saving caught {targeted_encounter.name}"
            context.message = self.progress.current_objective
            record_event("save", f"Salvando captura: {targeted_encounter.name}")
            yield from save_the_game()
            self.progress.completed_quests.append(quest_key)
            documented_next = (
                context.mission_tracker.complete_active_static()
                if context.mission_tracker is not None
                else None
            )
            if documented_next is not None:
                self.progress.current_objective = (
                    f"Next story quest: {documented_next.mission_id}: {documented_next.title}"
                )
            else:
                story_quest = next_quest(get_event_flag)
                self.progress.current_objective = (
                    f"Next story quest: {story_quest.name}"
                    if story_quest is not None
                    else "Main story milestones complete"
                )
            self.progress.save(context.profile.path)
            record_event("quest", self.progress.current_objective)
        self._static_reset = None

    def on_battle_ended(self, outcome: BattleOutcome) -> None:
        if self._static_reset is not None:
            self._static_reset.on_battle_ended(outcome)
            record_event("battle", f"Batalha encerrada: {outcome.name}")
            return
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
        if not (context.rom.is_rse or context.rom.is_frlg):
            raise BotModeError("Living Dex Gen III only supports RSE and FRLG.")
        if context.config.cheats.random_soft_reset_rng:
            raise BotModeError("Disable random_soft_reset_rng: it writes directly to game RNG memory.")

        if not game_has_started():
            self.progress.current_objective = "Starting new game"
            self.progress.save(context.profile.path)
            yield from run_new_game_intro(
                context.config.living_dex.gameplay.trainer_name,
                context.config.living_dex.gameplay.trainer_gender,
            )
            self.progress.current_objective = "New-game intro complete; reconciling cartridge state"
            self.progress.save(context.profile.path)

        if context.rom.is_rse:
            controller = RSEMissionController(
                set_navigation_encounter_policy=self._set_navigation_encounter_policy
            )
            while (mission := controller.next_mission()) is not None:
                self.progress.current_objective = f"{mission.mission_id}: {mission.title}"
                self.progress.save(context.profile.path)
                yield from controller.run_next()
                self.progress.current_objective = f"{mission.mission_id} complete: save state observed"
                self.progress.save(context.profile.path)

        while context.bot_mode in (self.name(), "Living Dex RSE"):
            if self._static_reset is not None:
                yield from self._run_static_hunt()
                continue
            if get_game_state() == GameState.OVERWORLD:
                targeted_encounter = get_targeted_encounter()
                quest_key = None if targeted_encounter is None else f"static:{targeted_encounter.name}"
                if targeted_encounter is not None and quest_key not in self.progress.completed_quests:
                    self._start_static_hunt(targeted_encounter)
                    continue
                if (
                    context.rom.is_rse
                    and self.progress.founder_personality_value is not None
                    and not self.progress.starter_stored
                ):
                    yield from self._store_shiny_starter()
                storage = CollectionSnapshot.from_storage(get_pokemon_storage())
                founder = self.progress.founder_species or "pending"
                if context.rom.is_rse:
                    story_quest = next_quest(get_event_flag)
                    story_objective = story_quest.name if story_quest is not None else "story complete"
                else:
                    story_objective = "FRLG campaign graph pending action executor"
                self.progress.current_objective = (
                    f"Next quest: {story_objective} | qualified {len(storage.collected)} | "
                    f"free slots {storage.free_slots} | founder {founder}"
                )
                context.message = self.progress.current_objective
            yield
