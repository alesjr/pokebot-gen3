from __future__ import annotations

from typing import Generator

from modules.campaign.capabilities import CampaignGameInterface
from modules.campaign.team import pokemon_identity, select_campaign_party
from modules.context import context
from modules.keyboard import get_naming_screen_data, type_in_naming_screen
from modules.memory import (
    GameState,
    game_has_started,
    get_game_state,
)
from modules.modes._interface import BotModeError
from modules.modes.util import (
    ensure_facing_direction,
    navigate_to,
    save_the_game,
    wait_for_player_avatar_to_be_controllable,
    walk_through_warp,
)
from modules.modes.util.pc_interaction import PCAction, interact_with_pc
from modules.player import (
    get_player,
    get_player_location,
)
from modules.pokemon import Pokemon
from modules.pokemon_party import get_party
from modules.pokemon_storage import get_pokemon_storage
from modules.tasks import get_task


class RSECampaignController(CampaignGameInterface):
    """RSE implementation of indivisible Campaign game operations."""

    def start_new_game(
        self,
        trainer_name: str,
        trainer_gender: str,
        *,
        timeout_frames: int = 30_000,
    ) -> Generator:
        if trainer_gender not in {"male", "female"}:
            raise BotModeError("Trainer gender must be male or female.")
        if not trainer_name or len(trainer_name) > 7:
            raise BotModeError("Gen III trainer name must contain 1 to 7 characters.")

        naming: Generator | None = None
        gender_positioned = trainer_gender == "male"
        for frame in range(timeout_frames):
            if game_has_started():
                player = get_player()
                if player.name != trainer_name or player.gender != trainer_gender:
                    raise BotModeError(
                        f"New-game identity mismatch: expected {trainer_name}/{trainer_gender}, "
                        f"observed {player.name}/{player.gender}."
                    )
                return
            if (
                get_game_state() is GameState.NAMING_SCREEN
                and get_naming_screen_data() is not None
            ):
                naming = naming or type_in_naming_screen(trainer_name, max_length=7)
                try:
                    next(naming)
                except StopIteration:
                    naming = None
            elif get_task(
                "Task_NewGameBirchSpeech_ChooseGender"
                if context.rom.is_emerald
                else "Task_NewGameSpeech16"
            ) is not None:
                if gender_positioned:
                    context.emulator.press_button("A")
                else:
                    context.emulator.press_button("Down")
                    gender_positioned = True
            elif frame % 4 == 0:
                context.emulator.press_button("A")
            yield
        raise BotModeError(
            f"New-game intro did not finish within {timeout_frames} frames."
        )

    @staticmethod
    def _pc_action_batches(
        selected: list[Pokemon], storage_required: bool
    ) -> list[list[PCAction]]:
        party = list(get_party())
        selected_ids = {pokemon_identity(pokemon) for pokemon in selected}
        if not storage_required:
            selected_ids.update(
                pokemon_identity(pokemon) for pokemon in party if pokemon.is_shiny
            )
        outgoing = [
            pokemon for pokemon in party if pokemon_identity(pokemon) not in selected_ids
        ]
        party_ids = {pokemon_identity(pokemon) for pokemon in party}
        incoming = [
            pokemon for pokemon in selected if pokemon_identity(pokemon) not in party_ids
        ]

        protected = None
        remaining = [pokemon for pokemon in party if pokemon not in outgoing]
        if outgoing and not any(
            not pokemon.is_egg and pokemon.current_hp > 0 for pokemon in remaining
        ):
            protected = next(
                (
                    pokemon
                    for pokemon in outgoing
                    if not pokemon.is_egg and pokemon.current_hp > 0
                ),
                outgoing[-1],
            )

        first_outgoing = [pokemon for pokemon in outgoing if pokemon is not protected]
        first_capacity = 6 - (len(party) - len(first_outgoing))
        first_incoming = incoming[:first_capacity]
        first_batch = [
            PCAction.deposit_pokemon_to_box(pokemon) for pokemon in first_outgoing
        ]
        first_batch.extend(
            PCAction.withdraw_pokemon_from_box(pokemon) for pokemon in first_incoming
        )

        batches = [first_batch] if first_batch else []
        remaining_incoming = incoming[len(first_incoming) :]
        party_size_after_first_batch = (
            len(party) - len(first_outgoing) + len(first_incoming)
        )
        if protected is not None and (
            remaining_incoming or party_size_after_first_batch > 1
        ):
            batches.append(
                [PCAction.deposit_pokemon_to_box(protected)]
                + [
                    PCAction.withdraw_pokemon_from_box(pokemon)
                    for pokemon in remaining_incoming
                ]
            )
        return batches

    def organize_party_at_pc(
        self,
        tile_x: int,
        tile_y: int,
        storage_required: bool = True,
        optimize_party: bool = True,
        target_size: int = 6,
        required_hms: list[str] | None = None,
        temporary_required_species: list[str] | None = None,
    ) -> Generator:
        destination_map = get_player_location()[0]
        if not destination_map.name.endswith("POKEMON_CENTER_1F"):
            raise BotModeError(
                f"Cannot deposit party shinies outside a Pokémon Center: {destination_map.name}."
            )

        yield from navigate_to(destination_map, (tile_x, tile_y))
        yield from ensure_facing_direction("Up")
        party = list(get_party())
        stored = [
            slot.pokemon for box in get_pokemon_storage().boxes for slot in box.slots
        ]
        selected = (
            select_campaign_party(
                party,
                stored,
                target_size=target_size,
                required_hms=required_hms or (),
                temporary_required_species=temporary_required_species or (),
            )
            if optimize_party
            else [pokemon for pokemon in party if not pokemon.is_shiny]
        )
        for actions in self._pc_action_batches(selected, storage_required):
            yield from interact_with_pc(actions)
        yield from navigate_to(destination_map, (7, 8))
        yield from walk_through_warp(destination_map, "Down", target_x=7)
        yield from wait_for_player_avatar_to_be_controllable(
            "B", stable_frames=30, wait_for_no_script=True, timeout_frames=4_000
        )
        yield from save_the_game()
