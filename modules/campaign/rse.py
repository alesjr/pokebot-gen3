from __future__ import annotations

from typing import Generator

from modules.campaign.engine import save_campaign_checkpoint
from modules.campaign.team import pokemon_identity, select_campaign_party
from modules.context import context
from modules.items import get_item_bag, get_item_by_name
from modules.keyboard import get_naming_screen_data, type_in_naming_screen
from modules.map_data import MapRSE, PokemonCenter
from modules.memory import (
    GameState,
    game_has_started,
    get_event_flag,
    get_event_var,
    get_game_state,
)
from modules.modes._interface import BotModeError
from modules.modes.util import (
    ensure_facing_direction,
    heal_in_pokemon_center,
    navigate_to,
    save_the_game,
    talk_to_npc,
    wait_for_player_avatar_to_be_controllable,
    walk_through_warp,
)
from modules.modes.util.pc_interaction import PCAction, interact_with_pc
from modules.player import (
    get_player,
    get_player_house_maps,
    get_player_location,
    player_avatar_is_controllable,
)
from modules.pokemon import Pokemon
from modules.pokemon_party import get_party
from modules.pokemon_storage import get_pokemon_storage
from modules.tasks import get_global_script_context, get_task


def run_new_game_intro(
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
        if get_game_state() is GameState.NAMING_SCREEN and get_naming_screen_data() is not None:
            naming = naming or type_in_naming_screen(trainer_name, max_length=7)
            try:
                next(naming)
            except StopIteration:
                naming = None
        elif get_task(
            "Task_NewGameBirchSpeech_ChooseGender" if context.rom.is_emerald else "Task_NewGameSpeech16"
        ) is not None:
            if gender_positioned:
                context.emulator.press_button("A")
            else:
                context.emulator.press_button("Down")
                gender_positioned = True
        elif frame % 4 == 0:
            context.emulator.press_button("A")
        yield
    raise BotModeError(f"New-game intro did not finish within {timeout_frames} frames.")


def run_meet_rival(
    trainer_gender: str,
    *,
    timeout_frames: int = 12_000,
) -> Generator:
    if get_event_var("LITTLEROOT_RIVAL_STATE") >= 3:
        return
    own_first, own_second = get_player_house_maps(trainer_gender)
    if trainer_gender == "female":
        rival_first = MapRSE.LITTLEROOT_TOWN_BRENDANS_HOUSE_1F
        rival_second = MapRSE.LITTLEROOT_TOWN_BRENDANS_HOUSE_2F
        own_stairs, own_exit, rival_door, rival_stairs = (1, 2), (2, 7), (5, 9), (8, 3)
        interaction = (1, 3) if context.rom.is_rs else (3, 5)
    else:
        rival_first = MapRSE.LITTLEROOT_TOWN_MAYS_HOUSE_1F
        rival_second = MapRSE.LITTLEROOT_TOWN_MAYS_HOUSE_2F
        own_stairs, own_exit, rival_door, rival_stairs = (7, 2), (8, 7), (14, 9), (2, 3)
        interaction = (7, 3) if context.rom.is_rs else (5, 5)

    yield from wait_for_player_avatar_to_be_controllable(
        "B", stable_frames=120, wait_for_no_script=True, timeout_frames=timeout_frames
    )
    current_map = get_player_location()[0]
    if current_map is own_second:
        yield from navigate_to(own_second, own_stairs)
        yield from walk_through_warp(own_second, "Up")
        yield from wait_for_player_avatar_to_be_controllable(
            "B", stable_frames=120, wait_for_no_script=True, timeout_frames=4_000
        )
        current_map = get_player_location()[0]
    if current_map is own_first:
        yield from walk_through_warp(
            own_first, "Down", target_x=own_exit[0], timeout_frames=5_000
        )
        yield from wait_for_player_avatar_to_be_controllable(
            "B", stable_frames=120, wait_for_no_script=True, timeout_frames=4_000
        )
        current_map = get_player_location()[0]
    if current_map is MapRSE.LITTLEROOT_TOWN:
        yield from navigate_to(MapRSE.LITTLEROOT_TOWN, rival_door)
        yield from walk_through_warp(MapRSE.LITTLEROOT_TOWN, "Up")
        yield from wait_for_player_avatar_to_be_controllable(
            "B", stable_frames=120, wait_for_no_script=True, timeout_frames=4_000
        )
        current_map = get_player_location()[0]
    if current_map is rival_first:
        yield from walk_through_warp(
            rival_first, "Up", target_x=rival_stairs[0], timeout_frames=5_000
        )
        yield from wait_for_player_avatar_to_be_controllable(
            "B", stable_frames=120, wait_for_no_script=True, timeout_frames=4_000
        )
        current_map = get_player_location()[0]
    if current_map is rival_second:
        yield from navigate_to(rival_second, interaction)
        yield from ensure_facing_direction("Up")
        context.emulator.press_button("A")
        yield
        yield from wait_for_player_avatar_to_be_controllable(
            "B", stable_frames=120, wait_for_no_script=True, timeout_frames=timeout_frames
        )
    if get_event_var("LITTLEROOT_RIVAL_STATE") < 3:
        raise BotModeError(
            f"Rival event incomplete: map={get_player_location()[0].name} "
            f"state={get_event_var('LITTLEROOT_RIVAL_STATE')}"
        )


def run_defeat_route103_rival(*, timeout_frames: int = 30_000) -> Generator:
    if get_event_flag("DEFEATED_RIVAL_ROUTE103"):
        return
    yield from wait_for_player_avatar_to_be_controllable(
        "B", stable_frames=120, wait_for_no_script=True, timeout_frames=timeout_frames
    )
    if get_player_location()[0] is MapRSE.LITTLEROOT_TOWN_PROFESSOR_BIRCHS_LAB:
        yield from walk_through_warp(
            MapRSE.LITTLEROOT_TOWN_PROFESSOR_BIRCHS_LAB,
            "Down",
            target_x=6,
            timeout_frames=5_000,
        )
        yield from wait_for_player_avatar_to_be_controllable(
            "B", stable_frames=120, wait_for_no_script=True, timeout_frames=timeout_frames
        )

    lead = get_party()[0]
    if lead.current_hp < lead.total_hp:
        yield from heal_in_pokemon_center(PokemonCenter.OldaleTown)
        yield from wait_for_player_avatar_to_be_controllable(
            "B", stable_frames=120, wait_for_no_script=True, timeout_frames=timeout_frames
        )

    rival_approach = (9, 3) if context.rom.is_emerald else (10, 3)
    yield from navigate_to(MapRSE.ROUTE103, rival_approach)
    yield from talk_to_npc(2)
    for frame in range(timeout_frames):
        if get_event_flag("DEFEATED_RIVAL_ROUTE103"):
            yield from wait_for_player_avatar_to_be_controllable(
                "B", stable_frames=120, wait_for_no_script=True, timeout_frames=timeout_frames
            )
            return
        if frame % 4 == 0:
            context.emulator.press_button("A")
        yield
    raise BotModeError("Route 103 rival battle did not set its completion flag.")


def run_receive_first_poke_balls(*, timeout_frames: int = 30_000) -> Generator:
    poke_ball = get_item_by_name("Poké Ball")
    if (
        get_event_flag("SYS_POKEDEX_GET")
        and get_event_var("BIRCH_LAB_STATE") >= 5
        and get_item_bag().quantity_of(poke_ball) >= 1
    ):
        return
    if not get_event_flag("DEFEATED_RIVAL_ROUTE103"):
        raise BotModeError("Route 103 rival must be defeated before returning to Birch's lab.")

    for _ in range(20):
        if get_player_location()[0] is MapRSE.LITTLEROOT_TOWN_PROFESSOR_BIRCHS_LAB:
            break
        if get_global_script_context().is_active or not player_avatar_is_controllable():
            yield from wait_for_player_avatar_to_be_controllable(
                "B", stable_frames=30, wait_for_no_script=True, timeout_frames=timeout_frames
            )
        else:
            yield from navigate_to(
                MapRSE.LITTLEROOT_TOWN,
                (7, 16),
                expecting_script=True,
            )
    else:
        raise BotModeError(f"Could not return to Birch's lab from {get_player_location()[0].name}.")

    for frame in range(timeout_frames):
        if (
            get_event_flag("SYS_POKEDEX_GET")
            and get_event_var("BIRCH_LAB_STATE") >= 5
            and get_item_bag().quantity_of(poke_ball) >= 1
        ):
            yield from wait_for_player_avatar_to_be_controllable(
                "B", stable_frames=120, wait_for_no_script=True, timeout_frames=timeout_frames
            )
            yield from save_campaign_checkpoint(2)
            return
        if frame % 2 == 0:
            context.emulator.press_button("A")
        yield
    raise BotModeError("Birch lab sequence did not award the first Poké Balls.")


def run_leave_birch_lab(*, timeout_frames: int = 30_000) -> Generator:
    if get_player_location()[0] is MapRSE.LITTLEROOT_TOWN:
        return
    if get_player_location()[0] is MapRSE.LITTLEROOT_TOWN_PROFESSOR_BIRCHS_LAB:
        yield from walk_through_warp(
            MapRSE.LITTLEROOT_TOWN_PROFESSOR_BIRCHS_LAB,
            "Down",
            target_x=6,
            timeout_frames=5_000,
        )
        yield from wait_for_player_avatar_to_be_controllable(
            "B", stable_frames=30, wait_for_no_script=True, timeout_frames=timeout_frames
        )
        return
    raise BotModeError(f"Cannot leave Birch's lab from {get_player_location()[0].name}.")


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
    if outgoing and not any(not pokemon.is_egg and pokemon.current_hp > 0 for pokemon in remaining):
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
    first_batch = [PCAction.deposit_pokemon_to_box(pokemon) for pokemon in first_outgoing]
    first_batch.extend(
        PCAction.withdraw_pokemon_from_box(pokemon) for pokemon in first_incoming
    )

    batches = [first_batch] if first_batch else []
    remaining_incoming = incoming[len(first_incoming) :]
    party_size_after_first_batch = len(party) - len(first_outgoing) + len(first_incoming)
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


def run_organize_party_at_pc(
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
    stored = [slot.pokemon for box in get_pokemon_storage().boxes for slot in box.slots]
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
    for actions in _pc_action_batches(selected, storage_required):
        yield from interact_with_pc(actions)
    yield from navigate_to(destination_map, (7, 8))
    yield from walk_through_warp(destination_map, "Down", target_x=7)
    yield from wait_for_player_avatar_to_be_controllable(
        "B", stable_frames=30, wait_for_no_script=True, timeout_frames=4_000
    )
    yield from save_the_game()
