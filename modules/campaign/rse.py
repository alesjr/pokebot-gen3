from __future__ import annotations

from collections.abc import Callable
from typing import Generator

from modules.campaign.engine import save_campaign_checkpoint
from modules.context import context
from modules.items import get_item_bag, get_item_by_name
from modules.keyboard import get_naming_screen_data, type_in_naming_screen
from modules.map_data import MapRSE, PokemonCenter, get_map_enum
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
from modules.pokemon_party import get_party
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


def run_catch_new_route102_pokemon(
    target_reached: Callable[[], bool],
) -> Generator:
    if target_reached():
        return
    # TODO: integrar captura/cura da missão 3 aos handlers originais de batalha,
    # get_last_heal_location(), PokemonCenter e busca de centro mais próximo.
    raise BotModeError("TODO: integração de captura/cura da missão 3 pendente.")
    yield


def run_deposit_shiny_starter(
    starter_name: str,
    map_group: int,
    map_number: int,
    tile_x: int,
    tile_y: int,
) -> Generator:
    starter = next(
        (
            pokemon
            for pokemon in get_party()
            if pokemon.is_shiny and pokemon.species.name == starter_name
        ),
        None,
    )
    if starter is None:
        return

    destination_map = get_map_enum((map_group, map_number))
    if get_player_location()[0] is MapRSE.OLDALE_TOWN:
        yield from navigate_to(MapRSE.OLDALE_TOWN, PokemonCenter.OldaleTown.value[1])
        yield from walk_through_warp(MapRSE.OLDALE_TOWN, "Up", target_x=6)
        yield from wait_for_player_avatar_to_be_controllable(
            "B", stable_frames=30, wait_for_no_script=True, timeout_frames=4_000
        )
    if get_player_location()[0] is not destination_map:
        raise BotModeError(
            f"Could not enter the Oldale Pokémon Center: {get_player_location()[0].name}."
        )

    yield from navigate_to(destination_map, (tile_x, tile_y))
    yield from ensure_facing_direction("Up")
    yield from interact_with_pc([PCAction.deposit_pokemon_to_box(starter)])
    yield from navigate_to(destination_map, (7, 8))
    yield from walk_through_warp(destination_map, "Down", target_x=7)
    yield from wait_for_player_avatar_to_be_controllable(
        "B", stable_frames=30, wait_for_no_script=True, timeout_frames=4_000
    )
    yield from save_campaign_checkpoint(3)
