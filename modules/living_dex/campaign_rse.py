from __future__ import annotations

from typing import Callable, Generator

from modules.context import context
from modules.game import get_symbol_name_before
from modules.items import get_item_bag, get_item_by_name
from modules.map import get_map_data, get_map_objects
from modules.map_data import MapRSE, PokemonCenter, get_map_enum
from modules.map_path import PathFindingError, calculate_path
from modules.menuing import use_field_move
from modules.menu_parsers import parse_menu
from modules.memory import (
    GameState,
    get_event_flag,
    get_event_var,
    get_game_state,
    get_game_state_symbol,
    read_symbol,
    unpack_uint16,
    unpack_uint32,
)
from modules.modes._interface import BotModeError
from modules.modes.util import (
    ensure_facing_direction,
    heal_in_pokemon_center,
    navigate_to,
    save_the_game,
    soft_reset,
    spin,
    wait_for_yes_no_question,
)
from modules.modes.util.items import teach_hm_or_tm
from modules.player import get_player_avatar, get_player_location, player_avatar_is_controllable
from modules.pokemon_party import get_party
from modules.tasks import get_global_script_context, get_task, get_tasks
from modules.text_printer import TextPrinterState, get_text_printer


def _player_house_maps() -> tuple[MapRSE, MapRSE]:
    if context.config.living_dex.gameplay.trainer_gender == "female":
        return MapRSE.LITTLEROOT_TOWN_MAYS_HOUSE_1F, MapRSE.LITTLEROOT_TOWN_MAYS_HOUSE_2F
    return MapRSE.LITTLEROOT_TOWN_BRENDANS_HOUSE_1F, MapRSE.LITTLEROOT_TOWN_BRENDANS_HOUSE_2F


def _current_map() -> MapRSE:
    return get_map_enum(get_player_avatar().map_group_and_number)


def _wait_for_control(*, timeout: int = 4_000, stable_frames: int = 120) -> Generator:
    stable = 0
    pokenav_menu_frames = 0
    pokenav_device_frames = 0
    context.emulator.reset_held_buttons()
    for frame in range(timeout):
        script_active = get_global_script_context().is_active
        script_stack = get_global_script_context().stack if script_active else []
        if (
            context.rom.is_emerald
            and script_active
            and get_player_avatar().map_group_and_number == MapRSE.RUSTBORO_CITY.value
            and get_event_flag("ADDED_MATCH_CALL_TO_POKENAV")
            and "RustboroCity_EventScript_PleaseSelectPokenav" not in script_stack
            and (
                get_task("Task_Pokenav") is not None
                or get_task("Task_CurrentMenuOptionGlow") is not None
                or get_task("Task_HandleMultichoiceInput") is not None
            )
        ):
            pokenav_menu_frames += 1
            if get_task("Task_CurrentMenuOptionGlow") is not None:
                pokenav_device_frames += 1
                resources = unpack_uint32(read_symbol("gPokenavResources", size=4))
                if resources == 0:
                    yield
                    continue
                pokenav_mode = unpack_uint16(context.emulator.read_bytes(resources + 8, 2))
                menu = unpack_uint32(context.emulator.read_bytes(resources + 20, 4))
                current_item = unpack_uint16(context.emulator.read_bytes(menu + 4, 2))
                if pokenav_device_frames % 4 == 0:
                    if pokenav_mode == 2:
                        context.emulator.press_button("B")
                    else:
                        context.emulator.press_button("A" if current_item == 2 else "Down")
            elif get_task("Task_RunLoopedTask") is not None:
                loop_task = get_task("Task_RunLoopedTask")
                loop_pointer = unpack_uint32(loop_task.data[2:6])
                loop_name = get_symbol_name_before(loop_pointer - 1, pretty_name=True)
                if (
                    loop_name == "DoMatchCallMessage"
                    and loop_task.data_value(0) >= 2
                ):
                    context.emulator.reset_held_buttons()
                    context.emulator.press_button("B")
                pokenav_device_frames += 1
            elif get_task("Task_Pokenav") is not None:
                context.emulator.reset_held_buttons()
                pokenav_device_frames += 1
                if pokenav_device_frames % 4 == 0:
                    resources = unpack_uint32(read_symbol("gPokenavResources", size=4))
                    if resources == 0:
                        yield
                        continue
                    pokenav_mode = unpack_uint16(context.emulator.read_bytes(resources + 8, 2))
                    context.emulator.press_button("B" if pokenav_mode == 2 else "A")
            elif pokenav_menu_frames in {20, 24, 28}:
                context.emulator.press_button("Down")
            elif pokenav_menu_frames == 32:
                context.emulator.press_button("A")
            yield
            continue
        if context.rom.is_emerald and "RustboroCity_EventScript_PleaseSelectPokenav" in script_stack:
            printer = get_text_printer()
            if printer.state is TextPrinterState.WaitForButton:
                context.emulator.press_button("A")
            elif not printer.active:
                pokenav_menu_frames += 1
                if pokenav_menu_frames in {30, 34, 38}:
                    context.emulator.press_button("Down")
                elif pokenav_menu_frames == 42:
                    context.emulator.press_button("A")
                elif pokenav_menu_frames > 90 and pokenav_menu_frames % 4 == 0:
                    context.emulator.press_button("B")
            yield
            continue
        if (
            get_game_state() is GameState.OVERWORLD
            and player_avatar_is_controllable()
            and not script_active
        ):
            stable += 1
            if stable >= stable_frames:
                return
        else:
            stable = 0
            if frame % 2 == 0:
                context.emulator.press_button("B")
        yield
    script = get_global_script_context()
    printer = get_text_printer()
    loop_task = get_task("Task_RunLoopedTask")
    loop_state = None
    if loop_task is not None:
        loop_pointer = unpack_uint32(loop_task.data[2:6])
        loop_state = (
            get_symbol_name_before(loop_pointer - 1, pretty_name=True),
            [loop_task.data_value(index) for index in range(4)],
        )
    active_printers = [
        (index, candidate.raw_state)
        for index in range(32)
        if (candidate := get_text_printer(index)).active
    ]
    raise BotModeError(
        "RSE intro did not return player control: "
        f"map={_current_map().name} position={get_player_avatar().local_coordinates} "
        f"script={script.script_function_name if script.is_active else 'inactive'} "
        f"stack={script.stack if script.is_active else []} "
        f"printer={printer.raw_state}/{printer.active} "
        f"tasks={[task.symbol for task in get_tasks()]} loop={loop_state} active_printers={active_printers}"
    )


def _walk_through_warp(
    source_map: MapRSE,
    direction: str,
    *,
    target_x: int | None = None,
    timeout: int = 600,
) -> Generator:
    for frame in range(timeout):
        if _current_map() is not source_map:
            return
        if (
            get_game_state() is GameState.OVERWORLD
            and player_avatar_is_controllable()
            and not get_global_script_context().is_active
        ):
            x = get_player_avatar().local_coordinates[0]
            if target_x is not None and x != target_x:
                context.emulator.press_button("Right" if x < target_x else "Left")
            else:
                context.emulator.press_button(direction)
        elif frame % 3 == 0:
            context.emulator.press_button("A")
        yield
    script = get_global_script_context()
    raise BotModeError(
        f"Could not leave map through warp: {source_map.name} at {get_player_avatar().local_coordinates}; "
        f"controllable={player_avatar_is_controllable()} "
        f"script={script.script_function_name if script.is_active else 'inactive'}"
    )


def _leave_building_for(destination: MapRSE, *, timeout: int = 4_000) -> Generator:
    """Leave current interior through its real warp when a utility stops indoors."""
    if _current_map() is destination:
        return
    source = _current_map()
    source_data = get_map_data(source, (0, 0))
    exit_warp = next(
        (
            warp
            for warp in source_data.warps
            if (warp.destination_map_group, warp.destination_map_number) == destination.value
        ),
        None,
    )
    if exit_warp is None:
        raise BotModeError(f"No warp from {source.name} to {destination.name}.")
    x, y = exit_warp.local_coordinates
    yield from navigate_to(source, (x, y - 1))
    yield from _walk_through_warp(source, "Down", target_x=x, timeout=timeout)
    yield from _wait_for_control(timeout=timeout)


def _take_warp_to(destination: MapRSE, *, timeout: int = 4_000) -> Generator:
    """Walk onto a warp from current map that leads to destination."""
    if _current_map() is destination:
        return
    source = _current_map()
    source_data = get_map_data(source, (0, 0))
    warp = next(
        (
            candidate
            for candidate in source_data.warps
            if (candidate.destination_map_group, candidate.destination_map_number) == destination.value
        ),
        None,
    )
    if warp is None:
        raise BotModeError(f"No warp from {source.name} to {destination.name}.")
    yield from navigate_to(source, warp.local_coordinates)
    for _ in range(timeout):
        if _current_map() is destination:
            yield from _wait_for_control(timeout=timeout)
            return
        context.emulator.press_button("Down")
        yield
    raise BotModeError(f"Warp from {source.name} did not reach {destination.name}.")


def _advance_until_lab_yes_no(*, timeout: int, stop_at_state: int | None = None) -> Generator:
    context.emulator.reset_held_buttons()
    for frame in range(timeout):
        if stop_at_state is not None and get_event_var("BIRCH_LAB_STATE") >= stop_at_state:
            return False
        if get_task("Task_HandleYesNoInput") is not None:
            return True
        if frame % 4 == 0:
            context.emulator.press_button("A")
        yield
    raise BotModeError("RSE-003 lab yes/no prompt did not appear.")


def run_rse_finish_starter_lab(*, timeout_frames: int = 20_000) -> Generator:
    """Finish post-starter choices using task and persistent story state."""
    if get_event_var("BIRCH_LAB_STATE") >= 3:
        yield from _wait_for_control(timeout=timeout_frames)
        return
    first_prompt = yield from _advance_until_lab_yes_no(timeout=timeout_frames)
    if first_prompt:
        yield from wait_for_yes_no_question("No")
    second_prompt = yield from _advance_until_lab_yes_no(timeout=timeout_frames, stop_at_state=3)
    if second_prompt:
        yield from wait_for_yes_no_question("Yes")
    for frame in range(timeout_frames):
        if get_event_var("BIRCH_LAB_STATE") >= 3:
            yield from _wait_for_control(timeout=timeout_frames)
            return
        if frame % 4 == 0:
            context.emulator.press_button("A")
        yield
    raise BotModeError("RSE-003 Birch lab state did not reach 3.")


def starter_qualifies(pokemon: object, *, require_shiny: bool = True) -> bool:
    return bool(getattr(pokemon, "is_shiny")) or not require_shiny


def run_rse_clock_setup(*, timeout_frames: int = 20_000) -> Generator:
    """Reach and set the RSE bedroom clock from a fresh or interrupted intro."""
    if get_event_flag("SET_WALL_CLOCK"):
        return
    first_floor, second_floor = _player_house_maps()
    wall_clock_callbacks = {"CB2_WALLCLOCK", "WALLCLOCKMAINCALLBACK"}

    if get_game_state_symbol() not in wall_clock_callbacks:
        yield from _wait_for_control()
        if get_event_flag("SET_WALL_CLOCK"):
            return
        current_map = _current_map()
        if current_map is MapRSE.INSIDE_OF_TRUCK:
            yield from navigate_to(MapRSE.INSIDE_OF_TRUCK, (4, 2), True, True, True, True)
            yield from _wait_for_control()
            current_map = _current_map()

        if current_map is MapRSE.LITTLEROOT_TOWN:
            for _ in range(600):
                if _current_map() is not MapRSE.LITTLEROOT_TOWN:
                    break
                context.emulator.press_button("Up")
                yield
            else:
                raise BotModeError("Could not enter the player's Littleroot house.")
            yield from _wait_for_control()
            current_map = _current_map()

        if current_map is first_floor:
            for frame in range(4_000):
                if _current_map() is not first_floor:
                    break
                context.emulator.press_button("Up")
                if frame % 4 == 0:
                    context.emulator.press_button("A")
                yield
            else:
                raise BotModeError("Could not reach the player's bedroom.")
            yield from _wait_for_control()
            current_map = _current_map()

        if current_map is not second_floor:
            raise BotModeError(f"Clock setup cannot recover from map: {current_map.name}")

        yield from navigate_to(second_floor, (5, 2))
        yield from ensure_facing_direction("Up")

    confirm_cursor_positioned = False
    for frame in range(timeout_frames):
        if get_event_flag("SET_WALL_CLOCK"):
            break
        symbol = get_game_state_symbol()
        if symbol in wall_clock_callbacks:
            input_task = get_task("Task_SetClock_HandleInput") or get_task("Task_SetClock2")
            confirm_task = get_task("Task_SetClock_HandleConfirmInput") or get_task("Task_SetClock4")
            if input_task is not None and input_task.data_value(0) % 6 == 0:
                confirm_cursor_positioned = False
                context.emulator.press_button("A")
            elif confirm_task is not None:
                if confirm_cursor_positioned:
                    context.emulator.press_button("A")
                else:
                    context.emulator.press_button("Up")
                    confirm_cursor_positioned = True
        elif frame % 4 == 0:
            context.emulator.press_button("A")
        yield
    else:
        active_tasks = ",".join(task.symbol for task in get_tasks())
        raise BotModeError(
            "RSE clock setup timed out before FLAG_SET_WALL_CLOCK: "
            f"callback={get_game_state_symbol()} tasks={active_tasks}"
        )
    yield from _wait_for_control()


def run_rse_meet_rival(*, timeout_frames: int = 12_000) -> Generator:
    """Complete RSE-002 from cartridge position after clock setup."""
    if get_event_var("LITTLEROOT_RIVAL_STATE") >= 3:
        return
    own_first, own_second = _player_house_maps()
    if context.config.living_dex.gameplay.trainer_gender == "female":
        rival_first = MapRSE.LITTLEROOT_TOWN_BRENDANS_HOUSE_1F
        rival_second = MapRSE.LITTLEROOT_TOWN_BRENDANS_HOUSE_2F
        own_stairs = (1, 2)
        own_exit = (2, 7)
        rival_door = (5, 9)
        rival_stairs = (8, 3)
        interaction_position = (1, 3) if context.rom.is_rs else (3, 5)
        interaction_facing = "Up"
    else:
        rival_first = MapRSE.LITTLEROOT_TOWN_MAYS_HOUSE_1F
        rival_second = MapRSE.LITTLEROOT_TOWN_MAYS_HOUSE_2F
        own_stairs = (7, 2)
        own_exit = (8, 7)
        rival_door = (14, 9)
        rival_stairs = (2, 3)
        interaction_position = (7, 3) if context.rom.is_rs else (5, 5)
        interaction_facing = "Up"

    yield from _wait_for_control(timeout=timeout_frames)
    if get_event_var("LITTLEROOT_RIVAL_STATE") >= 3:
        return
    current_map = _current_map()
    if current_map is own_second:
        yield from navigate_to(own_second, own_stairs)
        yield from _walk_through_warp(own_second, "Up")
        yield from _wait_for_control()
        current_map = _current_map()
    if current_map is own_first:
        yield from _walk_through_warp(own_first, "Down", target_x=own_exit[0], timeout=5_000)
        yield from _wait_for_control()
        current_map = _current_map()
    if current_map is MapRSE.LITTLEROOT_TOWN:
        yield from navigate_to(MapRSE.LITTLEROOT_TOWN, rival_door)
        yield from _walk_through_warp(MapRSE.LITTLEROOT_TOWN, "Up")
        yield from _wait_for_control()
        current_map = _current_map()
    if current_map is rival_first:
        yield from _walk_through_warp(rival_first, "Up", target_x=rival_stairs[0], timeout=5_000)
        yield from _wait_for_control()
        current_map = _current_map()
    if current_map is rival_second:
        yield from navigate_to(rival_second, interaction_position)
        yield from ensure_facing_direction(interaction_facing)
        context.emulator.press_button("A")
        yield
        yield from _wait_for_control(timeout=timeout_frames)

    if get_event_var("LITTLEROOT_RIVAL_STATE") < 3:
        raise BotModeError(
            "RSE-002 completion not observed: "
            f"map={_current_map().name} rival_state={get_event_var('LITTLEROOT_RIVAL_STATE')}"
        )


def run_rse_reach_starter_bag(*, timeout_frames: int = 12_000) -> Generator:
    """Start Birch's Route 101 rescue and stop beside the starter bag."""
    if get_event_flag("SYS_POKEMON_GET") or get_event_flag("RESCUED_BIRCH"):
        return

    yield from _wait_for_control(timeout=timeout_frames)
    current_map = _current_map()
    rival_houses = {
        MapRSE.LITTLEROOT_TOWN_MAYS_HOUSE_2F: (MapRSE.LITTLEROOT_TOWN_MAYS_HOUSE_1F, (1, 1), 1),
        MapRSE.LITTLEROOT_TOWN_BRENDANS_HOUSE_2F: (MapRSE.LITTLEROOT_TOWN_BRENDANS_HOUSE_1F, (7, 1), 8),
    }
    if current_map in rival_houses:
        first_floor, stairs, _ = rival_houses[current_map]
        yield from navigate_to(current_map, stairs)
        yield from _walk_through_warp(current_map, "Up")
        yield from _wait_for_control()
        current_map = first_floor

    first_floor_exits = {
        MapRSE.LITTLEROOT_TOWN_MAYS_HOUSE_1F: 1,
        MapRSE.LITTLEROOT_TOWN_BRENDANS_HOUSE_1F: 8,
    }
    if current_map in first_floor_exits:
        yield from _walk_through_warp(
            current_map, "Down", target_x=first_floor_exits[current_map], timeout=5_000
        )
        yield from _wait_for_control()
        current_map = _current_map()

    if current_map is MapRSE.LITTLEROOT_TOWN:
        yield from navigate_to(MapRSE.LITTLEROOT_TOWN, (11, 1))
        yield from _walk_through_warp(MapRSE.LITTLEROOT_TOWN, "Up", target_x=11)
        yield from _wait_for_control(timeout=timeout_frames)
        current_map = _current_map()

    if current_map is MapRSE.ROUTE101:
        yield from navigate_to(MapRSE.ROUTE101, (7, 15))
        yield from ensure_facing_direction("Up")

    if _current_map() is not MapRSE.ROUTE101 or get_event_var("ROUTE101_STATE") < 2:
        raise BotModeError(
            "RSE-003 starter bag not reached: "
            f"map={_current_map().name} position={get_player_avatar().local_coordinates} "
            f"route101_state={get_event_var('ROUTE101_STATE')}"
        )


def run_rse_choose_starter(
    *,
    require_shiny: bool = True,
    qualifies: Callable[[object], bool] | None = None,
    attempt_observer: Callable[[int], None] | None = None,
    timeout_frames: int = 20_000,
) -> Generator:
    """Save at Birch's bag, reset until configured starter qualifies, then finish rescue."""
    starter_name = context.config.living_dex.gameplay.starter
    if get_event_flag("RESCUED_BIRCH") and any(
        pokemon.species.name == starter_name for pokemon in get_party()
    ):
        return

    yield from run_rse_reach_starter_bag(timeout_frames=timeout_frames)
    yield from save_the_game()
    choose_tasks = {"Task_StarterChoose2", "Task_HandleStarterChooseInput"}
    qualification = qualifies or (lambda pokemon: starter_qualifies(pokemon, require_shiny=require_shiny))

    for attempt in range(1, 100_001):
        if attempt > 1:
            yield from soft_reset(mash_random_keys=True)
            yield from _wait_for_control(timeout=timeout_frames)
            yield from ensure_facing_direction("Up")
        if attempt_observer is not None:
            attempt_observer(attempt)

        context.emulator.press_button("A")
        for frame in range(timeout_frames):
            active = {task.symbol for task in get_tasks()}
            if active & choose_tasks:
                break
            if frame % 3 == 0:
                context.emulator.press_button("A")
            yield
        else:
            raise BotModeError(f"RSE-003 starter chooser did not open on attempt {attempt}.")

        yield
        if starter_name == "Treecko":
            context.emulator.press_button("Left")
            yield
        elif starter_name == "Mudkip":
            context.emulator.press_button("Right")
            yield
        elif starter_name != "Torchic":
            raise BotModeError(f"Unsupported configured Hoenn starter: {starter_name}")
        context.emulator.press_button("A")
        yield

        candidate_checked = False
        accepted = False
        for frame in range(timeout_frames):
            party = get_party()
            starter = next((pokemon for pokemon in party if pokemon.species.name == starter_name), None)
            if starter is not None and not candidate_checked:
                candidate_checked = True
                accepted = qualification(starter)
                if not accepted:
                    break
            if accepted and _current_map() is MapRSE.LITTLEROOT_TOWN_PROFESSOR_BIRCHS_LAB:
                if not get_event_flag("SYS_POKEMON_GET") or not get_event_flag("RESCUED_BIRCH"):
                    raise BotModeError("RSE-003 lab dialogue finished without persistent rescue flags.")
                yield from run_rse_finish_starter_lab(timeout_frames=timeout_frames)
                return
            if frame % 2 == 0:
                context.emulator.press_button("A")
            yield
        if accepted:
            raise BotModeError(
                "RSE-003 accepted starter but rescue did not finish: "
                f"map={_current_map().name} state={get_game_state().name}"
            )

    raise BotModeError("RSE-003 shiny starter attempt limit reached (100000).")


def run_rse_defeat_route103_rival(
    *,
    set_navigation_encounter_policy: Callable[[bool], None],
    timeout_frames: int = 30_000,
) -> Generator:
    """RSE-004: defeat the Route 103 rival."""
    if get_event_flag("DEFEATED_RIVAL_ROUTE103"):
        yield from _wait_for_control(timeout=timeout_frames)
        return

    lab = MapRSE.LITTLEROOT_TOWN_PROFESSOR_BIRCHS_LAB
    yield from _wait_for_control(timeout=timeout_frames)
    house_1f, house_2f = _player_house_maps()
    if _current_map() is house_2f:
        yield from _take_warp_to(house_1f, timeout=timeout_frames)
    if _current_map() is house_1f:
        yield from _leave_building_for(MapRSE.LITTLEROOT_TOWN, timeout=timeout_frames)
    if _current_map() is lab:
        yield from navigate_to(lab, (6, 11))
        yield from _walk_through_warp(lab, "Down", target_x=6)
        yield from _wait_for_control(timeout=timeout_frames)

    set_navigation_encounter_policy(True)
    try:
        if context.rom.is_emerald and get_party()[0].level < 6:
            set_navigation_encounter_policy(True, True)
            yield from heal_in_pokemon_center(PokemonCenter.OldaleTown)
            yield from _leave_building_for(MapRSE.OLDALE_TOWN)
            yield from navigate_to(MapRSE.ROUTE103, (12, 13))
            yield from spin(
                stop_condition=lambda: get_party()[0].level >= 6 or get_party()[0].current_hp == 0
            )
            if get_party()[0].current_hp == 0:
                yield from heal_in_pokemon_center(PokemonCenter.OldaleTown)
                yield from _leave_building_for(MapRSE.OLDALE_TOWN)
            set_navigation_encounter_policy(True)
        for _attempt in range(10):
            if get_event_flag("DEFEATED_RIVAL_ROUTE103"):
                break
            yield from heal_in_pokemon_center(PokemonCenter.OldaleTown)
            yield from _leave_building_for(MapRSE.OLDALE_TOWN)
            rival_y = 3 if context.rom.is_emerald else 2
            yield from navigate_to(MapRSE.ROUTE103, (10, rival_y + 1))
            yield from ensure_facing_direction("Up")
            context.emulator.press_button("A")
            for frame in range(timeout_frames):
                if get_event_flag("DEFEATED_RIVAL_ROUTE103"):
                    break
                if frame > 600 and _current_map() is not MapRSE.ROUTE103 and player_avatar_is_controllable():
                    break
                if frame % 4 == 0:
                    context.emulator.press_button("A")
                yield
            if get_event_flag("DEFEATED_RIVAL_ROUTE103"):
                yield from _wait_for_control(timeout=timeout_frames)
                break
        else:
            raise BotModeError("RSE-004 rival defeat flag was not observed after 10 attempts.")
    finally:
        set_navigation_encounter_policy(False)


def run_rse_receive_pokedex(*, timeout_frames: int = 30_000) -> Generator:
    """RSE-005: return to Birch and receive the Pokédex and Poké Balls."""
    poke_ball = get_item_by_name("Poké Ball")
    if get_event_flag("SYS_POKEDEX_GET") and get_item_bag().quantity_of(poke_ball) > 0:
        yield from _wait_for_control(timeout=timeout_frames)
        return
    if not get_event_flag("DEFEATED_RIVAL_ROUTE103"):
        raise BotModeError("RSE-005 requires the Route 103 rival victory.")

    yield from _wait_for_control(timeout=timeout_frames)
    lab = MapRSE.LITTLEROOT_TOWN_PROFESSOR_BIRCHS_LAB
    if _current_map() is lab:
        yield from navigate_to(lab, (6, 4))
    else:
        if _current_map() is MapRSE.ROUTE103:
            yield from navigate_to(MapRSE.ROUTE103, (10, 16))
            yield from _walk_through_warp(MapRSE.ROUTE103, "Down", target_x=10)
            yield from _wait_for_control(timeout=timeout_frames)
        if _current_map() is MapRSE.OLDALE_TOWN:
            yield from navigate_to(MapRSE.OLDALE_TOWN, (10, 18))
            yield from _walk_through_warp(MapRSE.OLDALE_TOWN, "Down", target_x=10)
            yield from _wait_for_control(timeout=timeout_frames)
        yield from navigate_to(MapRSE.LITTLEROOT_TOWN, (7, 17))
        yield from _walk_through_warp(MapRSE.LITTLEROOT_TOWN, "Up", target_x=7)
    for frame in range(timeout_frames):
        if get_event_flag("SYS_POKEDEX_GET") and get_item_bag().quantity_of(poke_ball) > 0:
            yield from _wait_for_control(timeout=timeout_frames)
            return
        if frame % 4 == 0:
            context.emulator.press_button("A")
        yield
    raise BotModeError("RSE-005 Pokédex/Poké Balls completion was not observed.")


def run_rse_route103_and_receive_pokedex(
    *,
    set_navigation_encounter_policy: Callable[[bool], None],
    timeout_frames: int = 30_000,
) -> Generator:
    """Backward-compatible RSE-004 + RSE-005 combined runner."""
    yield from run_rse_defeat_route103_rival(
        set_navigation_encounter_policy=set_navigation_encounter_policy,
        timeout_frames=timeout_frames,
    )
    yield from run_rse_receive_pokedex(timeout_frames=timeout_frames)


def run_rse_receive_running_shoes(*, timeout_frames: int = 20_000) -> Generator:
    """Leave Littleroot after receiving the Pokédex and collect the Running Shoes."""
    if get_event_flag("RECEIVED_RUNNING_SHOES"):
        yield from _wait_for_control(timeout=timeout_frames)
        return
    if not get_event_flag("SYS_POKEDEX_GET"):
        raise BotModeError("RSE-006 requires the Pokédex before leaving Littleroot.")

    lab = MapRSE.LITTLEROOT_TOWN_PROFESSOR_BIRCHS_LAB
    yield from _wait_for_control(timeout=timeout_frames)
    if _current_map() is lab:
        yield from navigate_to(lab, (6, 11))
        yield from _walk_through_warp(lab, "Down", target_x=6)
        yield from _wait_for_control(timeout=timeout_frames)
    if _current_map() is MapRSE.LITTLEROOT_TOWN:
        yield from navigate_to(
            MapRSE.LITTLEROOT_TOWN,
            (11, 1),
            avoid_scripted_events=False,
            expecting_script=True,
        )

    for frame in range(timeout_frames):
        if get_event_flag("RECEIVED_RUNNING_SHOES"):
            yield from _wait_for_control(timeout=timeout_frames)
            return
        if frame % 4 == 0:
            if get_global_script_context().is_active:
                context.emulator.press_button("A")
            elif player_avatar_is_controllable():
                context.emulator.press_button("Up")
        yield
    script = get_global_script_context()
    raise BotModeError(
        "RSE-006 Running Shoes flag was not observed: "
        f"map={_current_map().name} position={get_player_avatar().local_coordinates} "
        f"controllable={player_avatar_is_controllable()} "
        f"script={script.script_function_name if script.is_active else 'inactive'}"
    )


def run_rse_meet_norman(
    *,
    set_navigation_encounter_policy: Callable[[bool], None],
    timeout_frames: int = 30_000,
) -> Generator:
    """Reach Petalburg Gym and complete the first conversation with Norman."""
    state_name = "PETALBURG_CITY_STATE" if context.rom.is_emerald else "PETALBURG_STATE"
    initial_state = get_event_var(state_name)
    if initial_state > 0:
        yield from _wait_for_control(timeout=timeout_frames)
        return

    yield from _wait_for_control(timeout=timeout_frames)
    if _current_map() is MapRSE.OLDALE_TOWN_POKEMON_CENTER_1F:
        yield from _leave_building_for(MapRSE.OLDALE_TOWN, timeout=timeout_frames)

    gym = MapRSE.PETALBURG_CITY_GYM
    city = get_map_data(MapRSE.PETALBURG_CITY, (0, 0))
    gym_warp = next(
        (warp for warp in city.warps if (warp.destination_map_group, warp.destination_map_number) == gym.value),
        None,
    )
    if gym_warp is None:
        raise BotModeError("RSE-007 Petalburg Gym entrance warp was not found.")

    set_navigation_encounter_policy(True)
    try:
        for attempt in range(3):
            if _current_map() is MapRSE.OLDALE_TOWN_POKEMON_CENTER_1F:
                yield from _leave_building_for(MapRSE.OLDALE_TOWN, timeout=timeout_frames)
            try:
                yield from navigate_to(MapRSE.PETALBURG_CITY, gym_warp.local_coordinates)
                break
            except BotModeError as error:
                recoverable = "not controllable" in str(error) or "not on connected maps" in str(error)
                if not recoverable or attempt == 2:
                    raise
                yield from _wait_for_control(timeout=timeout_frames)
        yield from _wait_for_control(timeout=timeout_frames)
        if context.rom.is_emerald and get_player_avatar().local_coordinates[1] > 100:
            for _ in range(600):
                if get_player_avatar().local_coordinates[1] < 100:
                    break
                context.emulator.press_button("Up")
                yield
            yield from _wait_for_control(timeout=timeout_frames)
        if _current_map() is not gym:
            raise BotModeError(f"RSE-007 failed to enter Petalburg Gym: map={_current_map().name}")
        if get_event_var(state_name) > initial_state:
            return
        if context.rom.is_emerald:
            interaction_position = (
                (4, 108) if get_player_avatar().local_coordinates[1] > 100 else (8, 6)
            )
        else:
            interaction_position = (4, 108)
        yield from navigate_to(gym, interaction_position)
        yield from ensure_facing_direction("Up")
        context.emulator.press_button("A")
        for frame in range(timeout_frames):
            if get_event_var(state_name) > initial_state and player_avatar_is_controllable():
                yield from _wait_for_control(timeout=timeout_frames)
                return
            if frame % 4 == 0:
                context.emulator.press_button("A")
            yield
        raise BotModeError(
            f"RSE-007 Petalburg state did not advance: {state_name}={get_event_var(state_name)}"
        )
    finally:
        set_navigation_encounter_policy(False)


def run_rse_wally_tutorial(*, timeout_frames: int = 40_000) -> Generator:
    """Complete Wally's scripted Route 102 catching tutorial."""
    state_name = "PETALBURG_CITY_STATE" if context.rom.is_emerald else "PETALBURG_STATE"
    if get_event_var(state_name) >= 3:
        yield from _wait_for_control(timeout=timeout_frames)
        return
    if _current_map() is not MapRSE.PETALBURG_CITY_GYM:
        raise BotModeError(f"RSE-008 must start in Petalburg Gym: map={_current_map().name}")

    yield from navigate_to(MapRSE.PETALBURG_CITY_GYM, (8, 6))
    yield from ensure_facing_direction("Up")
    context.emulator.press_button("A")
    for frame in range(timeout_frames):
        if (
            get_event_var(state_name) >= 3
            and _current_map() is MapRSE.PETALBURG_CITY_GYM
            and player_avatar_is_controllable()
        ):
            yield from _wait_for_control(timeout=timeout_frames)
            return
        if frame % 4 == 0:
            context.emulator.press_button("A")
        yield
    raise BotModeError(f"RSE-008 Wally tutorial did not finish: {state_name}={get_event_var(state_name)}")


def run_rse_defeat_petalburg_woods_villain(
    *,
    set_navigation_encounter_policy: Callable[[bool], None],
    timeout_frames: int = 40_000,
) -> Generator:
    """Reach Petalburg Woods and defeat the scripted villain grunt."""
    initial_state = get_event_var("PETALBURG_WOODS_STATE")
    if initial_state > 0:
        yield from _wait_for_control(timeout=timeout_frames)
        return

    woods = get_map_data(MapRSE.PETALBURG_WOODS, (0, 0))
    trigger = next(
        (
            event
            for event in woods.coord_events
            if event.type == "script" and event.to_dict()["trigger_var"] == "PETALBURG_WOODS_STATE"
        ),
        None,
    )
    if trigger is None:
        raise BotModeError("RSE-009 Petalburg Woods story trigger was not found.")

    set_navigation_encounter_policy(True)
    try:
        if _current_map() is MapRSE.PETALBURG_CITY_GYM:
            gym = get_map_data(MapRSE.PETALBURG_CITY_GYM, (0, 0))
            exit_warp = next(
                warp
                for warp in gym.warps
                if (warp.destination_map_group, warp.destination_map_number)
                == MapRSE.PETALBURG_CITY.value
            )
            yield from navigate_to(MapRSE.PETALBURG_CITY_GYM, exit_warp.local_coordinates)
            yield from _wait_for_control(timeout=timeout_frames)
        yield from heal_in_pokemon_center(PokemonCenter.PetalburgCity)
        yield from _leave_building_for(MapRSE.PETALBURG_CITY)
        route104 = get_map_data(MapRSE.ROUTE104, (0, 0))
        woods_entrances = [
            warp
            for warp in route104.warps
            if (warp.destination_map_group, warp.destination_map_number)
            == MapRSE.PETALBURG_WOODS.value
        ]
        reachable_entrances = []
        for warp in woods_entrances:
            try:
                path = calculate_path(get_player_location(), (MapRSE.ROUTE104, warp.local_coordinates))
            except PathFindingError:
                continue
            reachable_entrances.append((len(path), warp))
        if not reachable_entrances:
            raise BotModeError("RSE-009 no reachable Petalburg Woods entrance was found.")
        woods_entrance = min(reachable_entrances, key=lambda candidate: candidate[0])[1]
        if context.rom.is_emerald:
            for _ in range(3):
                yield from navigate_to(
                    MapRSE.ROUTE104,
                    woods_entrance.local_coordinates,
                    avoid_scripted_events=False,
                    expecting_script=True,
                )
                yield from _wait_for_control(timeout=timeout_frames)
                if _current_map() is MapRSE.PETALBURG_WOODS:
                    break
        else:
            yield from navigate_to(MapRSE.ROUTE104, woods_entrance.local_coordinates)
        yield from _wait_for_control(timeout=timeout_frames)
        yield from navigate_to(
            MapRSE.PETALBURG_WOODS,
            trigger.local_coordinates,
            avoid_scripted_events=False,
            expecting_script=True,
        )
        for frame in range(timeout_frames):
            if get_event_var("PETALBURG_WOODS_STATE") > initial_state and player_avatar_is_controllable():
                yield from _wait_for_control(timeout=timeout_frames)
                return
            if frame % 4 == 0:
                context.emulator.press_button("A")
            yield
        raise BotModeError(
            "RSE-009 Petalburg Woods state did not advance: "
            f"state={get_event_var('PETALBURG_WOODS_STATE')}"
        )
    finally:
        set_navigation_encounter_policy(False)


def run_rse_reach_rustboro(
    *,
    set_navigation_encounter_policy: Callable[[bool], None],
    timeout_frames: int = 40_000,
) -> Generator:
    """Cross northern Route 104 and enter Rustboro City."""
    if get_event_flag("VISITED_RUSTBORO_CITY"):
        yield from _wait_for_control(timeout=timeout_frames)
        return

    set_navigation_encounter_policy(True)
    try:
        if _current_map() is MapRSE.PETALBURG_WOODS:
            woods = get_map_data(MapRSE.PETALBURG_WOODS, (0, 0))
            exits = [
                warp
                for warp in woods.warps
                if (warp.destination_map_group, warp.destination_map_number) == MapRSE.ROUTE104.value
            ]
            reachable_exits = []
            for warp in exits:
                try:
                    path = calculate_path(
                        get_player_location(),
                        (MapRSE.PETALBURG_WOODS, warp.local_coordinates),
                    )
                except PathFindingError:
                    continue
                reachable_exits.append((warp.destination_location.local_position[1], len(path), warp))
            if not reachable_exits:
                raise BotModeError("RSE-010 no reachable Petalburg Woods exit was found.")
            north_exit = min(reachable_exits, key=lambda candidate: (candidate[0], candidate[1]))[2]
            yield from navigate_to(MapRSE.PETALBURG_WOODS, north_exit.local_coordinates)
            yield from _wait_for_control(timeout=timeout_frames)
        pokemon_center_door = PokemonCenter.RustboroCity.value[1]
        yield from navigate_to(
            MapRSE.RUSTBORO_CITY,
            (pokemon_center_door[0], pokemon_center_door[1] + 1),
        )
        if not get_event_flag("VISITED_RUSTBORO_CITY"):
            raise BotModeError("RSE-010 Rustboro visited flag was not observed.")
        yield from _wait_for_control(timeout=timeout_frames)
    finally:
        set_navigation_encounter_policy(False)


def run_rse_defeat_roxanne(
    *,
    set_navigation_encounter_policy: Callable[[bool], None],
    timeout_frames: int = 40_000,
) -> Generator:
    """Defeat Rustboro Gym trainers and Roxanne using the central battle engine."""
    if get_event_flag("BADGE01_GET"):
        yield from _wait_for_control(timeout=timeout_frames)
        return

    gym = get_map_data(MapRSE.RUSTBORO_CITY_GYM, (0, 0))
    if not gym.objects:
        raise BotModeError("RSE-011 Rustboro Gym has no object templates.")
    roxanne = min(gym.objects, key=lambda object_template: object_template.local_coordinates[1])
    interaction_position = (roxanne.local_coordinates[0], roxanne.local_coordinates[1] + 1)
    city = get_map_data(MapRSE.RUSTBORO_CITY, (0, 0))
    gym_entrance = next(
        warp
        for warp in city.warps
        if (warp.destination_map_group, warp.destination_map_number)
        == MapRSE.RUSTBORO_CITY_GYM.value
    )

    set_navigation_encounter_policy(True)
    try:
        if context.rom.is_emerald and get_party()[0].level < 16:
            set_navigation_encounter_policy(True, True)
            training_map = MapRSE.ROUTE116
            while get_party()[0].level < 16:
                yield from heal_in_pokemon_center(PokemonCenter.RustboroCity)
                yield from _leave_building_for(MapRSE.RUSTBORO_CITY)
                route = get_map_data(training_map, (0, 0))
                encounter_tiles = []
                width, height = route.map_size
                for y in range(height):
                    for x in range(width):
                        if not get_map_data(training_map, (x, y)).has_encounters:
                            continue
                        try:
                            path = calculate_path(
                                get_player_location(),
                                (training_map, (x, y)),
                            )
                        except PathFindingError:
                            continue
                        encounter_tiles.append((len(path), (x, y)))
                if not encounter_tiles:
                    raise BotModeError("RSE-011 no reachable Emerald training tile was found.")
                training_tile = min(encounter_tiles)[1]
                yield from navigate_to(training_map, training_tile)
                yield from spin(
                    stop_condition=lambda: (
                        get_party()[0].level >= 16
                        or get_party()[0].current_hp == 0
                        or _current_map() is not training_map
                    )
                )
            set_navigation_encounter_policy(True)

        max_attempts = 10
        for _attempt in range(max_attempts):
            yield from heal_in_pokemon_center(PokemonCenter.RustboroCity)
            yield from _leave_building_for(MapRSE.RUSTBORO_CITY)
            yield from navigate_to(MapRSE.RUSTBORO_CITY, gym_entrance.local_coordinates)
            yield from _wait_for_control(timeout=timeout_frames)
            yield from navigate_to(MapRSE.RUSTBORO_CITY_GYM, interaction_position)
            yield from ensure_facing_direction("Up")
            context.emulator.press_button("A")
            for frame in range(timeout_frames):
                if get_event_flag("BADGE01_GET"):
                    yield from _wait_for_control(timeout=timeout_frames)
                    return
                if frame > 600 and _current_map() is not MapRSE.RUSTBORO_CITY_GYM and player_avatar_is_controllable():
                    break
                if frame % 4 == 0:
                    context.emulator.press_button("A")
                yield
        raise BotModeError(f"RSE-011 Stone Badge was not obtained after {max_attempts} attempts.")
    finally:
        set_navigation_encounter_policy(False)


def run_rse_start_devon_goods_case(*, timeout_frames: int = 20_000) -> Generator:
    """Trigger the Devon employee chase after leaving Rustboro Gym."""
    if get_event_flag("DEVON_GOODS_STOLEN"):
        yield from _wait_for_control(timeout=timeout_frames)
        return
    if _current_map() is MapRSE.RUSTBORO_CITY_GYM:
        gym = get_map_data(MapRSE.RUSTBORO_CITY_GYM, (0, 0))
        exit_warp = next(
            warp
            for warp in gym.warps
            if (warp.destination_map_group, warp.destination_map_number) == MapRSE.RUSTBORO_CITY.value
        )
        x, y = exit_warp.local_coordinates
        yield from navigate_to(MapRSE.RUSTBORO_CITY_GYM, (x, y - 1))
        yield from _walk_through_warp(MapRSE.RUSTBORO_CITY_GYM, "Down", target_x=x)
        yield from _wait_for_control(timeout=timeout_frames)
    yield from navigate_to(
        MapRSE.RUSTBORO_CITY,
        (23, 20),
        avoid_scripted_events=False,
        expecting_script=True,
    )
    for frame in range(timeout_frames):
        if get_event_flag("DEVON_GOODS_STOLEN") and player_avatar_is_controllable():
            yield from _wait_for_control(timeout=timeout_frames)
            return
        if frame % 4 == 0:
            context.emulator.press_button("A")
        yield
    raise BotModeError("RSE-012 Devon Goods stolen flag was not observed.")


def run_rse_recover_devon_goods(
    *,
    set_navigation_encounter_policy: Callable[[bool], None],
    timeout_frames: int = 40_000,
) -> Generator:
    """Rescue Peeko and recover the Devon Goods in Rusturf Tunnel."""
    if get_event_flag("RECOVERED_DEVON_GOODS"):
        yield from _wait_for_control(timeout=timeout_frames)
        return

    set_navigation_encounter_policy(True)
    try:
        yield from heal_in_pokemon_center(PokemonCenter.RustboroCity)
        yield from _leave_building_for(MapRSE.RUSTBORO_CITY)
        for _attempt in range(6):
            if _current_map() is MapRSE.ROUTE116:
                break
            yield from navigate_to(
                MapRSE.ROUTE116,
                (47, 9),
                avoid_scripted_events=False,
                expecting_script=True,
            )
            yield from _wait_for_control(timeout=timeout_frames)
        else:
            raise BotModeError(
                f"RSE-013 could not reach Route 116; stopped on {_current_map().name} "
                f"at {get_player_avatar().local_coordinates}."
            )

        route = get_map_data(MapRSE.ROUTE116, (0, 0))
        tunnel_warp = next(
            warp
            for warp in route.warps
            if (warp.destination_map_group, warp.destination_map_number) == MapRSE.RUSTURF_TUNNEL.value
        )
        yield from navigate_to(MapRSE.ROUTE116, tunnel_warp.local_coordinates)
        if _current_map() is MapRSE.ROUTE116:
            yield from _walk_through_warp(
                MapRSE.ROUTE116,
                "Up",
                target_x=tunnel_warp.local_coordinates[0],
            )
        yield from _wait_for_control(timeout=timeout_frames)
        tunnel = get_map_data(MapRSE.RUSTURF_TUNNEL, (0, 0))
        grunt = next(object_template for object_template in tunnel.objects if object_template.local_id == 6)
        grunt_x, grunt_y = grunt.local_coordinates
        if get_event_var("RUSTURF_TUNNEL_STATE") == 2:
            grunt_x = 13
        interaction_candidates = (
            ((grunt_x - 1, grunt_y), "Right"),
            ((grunt_x + 1, grunt_y), "Left"),
            ((grunt_x, grunt_y + 1), "Up"),
            ((grunt_x, grunt_y - 1), "Down"),
        )
        location = get_player_location()
        reachable_interactions = []
        for coordinates, direction in interaction_candidates:
            try:
                path = calculate_path(location, (MapRSE.RUSTURF_TUNNEL, coordinates))
            except PathFindingError:
                continue
            reachable_interactions.append((len(path), coordinates, direction))
        if not reachable_interactions:
            raise BotModeError(
                f"RSE-013 cannot reach any tile adjacent to grunt at {(grunt_x, grunt_y)}."
            )
        _, interaction_position, facing = min(reachable_interactions)
        for _attempt in range(6):
            current_grunt_x = 13 if get_event_var("RUSTURF_TUNNEL_STATE") == 2 else grunt.local_coordinates[0]
            if current_grunt_x != grunt_x:
                grunt_x = current_grunt_x
                interaction_position = (grunt_x - 1, grunt_y)
                facing = "Right"
            yield from navigate_to(
                MapRSE.RUSTURF_TUNNEL,
                interaction_position,
                avoid_scripted_events=False,
                expecting_script=True,
            )
            if not player_avatar_is_controllable() or get_global_script_context().is_active:
                yield from _wait_for_control(timeout=timeout_frames)
                if get_event_flag("RECOVERED_DEVON_GOODS"):
                    return
                continue
            yield from ensure_facing_direction(facing)
            context.emulator.press_button("A")
            break
        else:
            raise BotModeError("RSE-013 exhausted scripted-event retries before reaching the grunt.")
        for frame in range(timeout_frames):
            if get_event_flag("RECOVERED_DEVON_GOODS") and player_avatar_is_controllable():
                yield from _wait_for_control(timeout=timeout_frames)
                return
            if frame % 4 == 0:
                context.emulator.press_button("A")
            yield
        script = get_global_script_context()
        raise BotModeError(
            "RSE-013 recovered Devon Goods flag was not observed: "
            f"map={_current_map().name} position={get_player_avatar().local_coordinates} "
            f"tunnel_state={get_event_var('RUSTURF_TUNNEL_STATE')} "
            f"script={script.script_function_name if script.is_active else 'inactive'}."
        )
    finally:
        set_navigation_encounter_policy(False)


def run_rse_return_devon_goods(
    *,
    set_navigation_encounter_policy: Callable[[bool], None],
    timeout_frames: int = 40_000,
) -> Generator:
    set_navigation_encounter_policy(True)
    try:
        yield from _run_rse_return_devon_goods(timeout_frames=timeout_frames)
    finally:
        set_navigation_encounter_policy(False)


def _run_rse_return_devon_goods(*, timeout_frames: int = 40_000) -> Generator:
    """Return the recovered Devon Goods to the Rustboro employee."""
    if get_event_flag("RETURNED_DEVON_GOODS"):
        yield from _wait_for_control(timeout=timeout_frames)
        return
    if _current_map() is MapRSE.RUSTURF_TUNNEL:
        tunnel = get_map_data(MapRSE.RUSTURF_TUNNEL, (0, 0))
        route_warps = [
            warp
            for warp in tunnel.warps
            if (warp.destination_map_group, warp.destination_map_number) == MapRSE.ROUTE116.value
        ]
        reachable_warps = []
        for warp in route_warps:
            try:
                path = calculate_path(
                    get_player_location(),
                    (MapRSE.RUSTURF_TUNNEL, warp.local_coordinates),
                )
            except PathFindingError:
                continue
            reachable_warps.append((len(path), warp))
        if not reachable_warps:
            raise BotModeError("RSE-014 found no reachable Rusturf Tunnel exit to Route 116.")
        _, exit_warp = min(reachable_warps, key=lambda candidate: candidate[0])
        yield from navigate_to(MapRSE.RUSTURF_TUNNEL, exit_warp.local_coordinates)
        if _current_map() is MapRSE.RUSTURF_TUNNEL:
            yield from _walk_through_warp(
                MapRSE.RUSTURF_TUNNEL,
                "Down",
                target_x=exit_warp.local_coordinates[0],
            )
        yield from _wait_for_control(timeout=timeout_frames)
    yield from navigate_to(
        MapRSE.RUSTBORO_CITY,
        (30, 11),
        avoid_scripted_events=False,
        expecting_script=True,
    )
    for frame in range(timeout_frames):
        if get_event_flag("RETURNED_DEVON_GOODS") and player_avatar_is_controllable():
            yield from _wait_for_control(timeout=timeout_frames)
            return
        if frame % 4 == 0:
            context.emulator.press_button("A")
        yield
    raise BotModeError("RSE-014 returned Devon Goods flag was not observed.")


def run_rse_receive_pokenav(*, timeout_frames: int = 40_000) -> Generator:
    """Receive Mr. Stone's letter and the PokéNav in Devon Corporation."""
    if get_event_flag("SYS_POKENAV_GET"):
        yield from _wait_for_control(timeout=timeout_frames)
        return
    yield from navigate_to(MapRSE.RUSTBORO_CITY_DEVON_CORP_3F, (3, 6))
    yield from ensure_facing_direction("Up")
    context.emulator.press_button("A")
    for frame in range(timeout_frames):
        if get_event_flag("SYS_POKENAV_GET") and player_avatar_is_controllable():
            yield from _wait_for_control(timeout=timeout_frames)
            return
        if frame % 4 == 0:
            context.emulator.press_button("A")
        yield
    raise BotModeError("RSE-015 PokéNav system flag was not observed.")


def run_rse_sail_to_dewford(
    *,
    set_navigation_encounter_policy: Callable[[bool], None],
    timeout_frames: int = 40_000,
) -> Generator:
    """Ask Mr. Briney to sail from Route 104 to Dewford."""
    if get_event_flag("VISITED_DEWFORD_TOWN"):
        yield from _wait_for_control(timeout=timeout_frames)
        return
    set_navigation_encounter_policy(True)
    try:
        if _current_map() is MapRSE.RUSTBORO_CITY_DEVON_CORP_3F:
            yield from _take_warp_to(MapRSE.RUSTBORO_CITY_DEVON_CORP_2F, timeout=timeout_frames)
        if _current_map() is MapRSE.RUSTBORO_CITY_DEVON_CORP_2F:
            yield from _take_warp_to(MapRSE.RUSTBORO_CITY_DEVON_CORP_1F, timeout=timeout_frames)
        if _current_map() is MapRSE.RUSTBORO_CITY_DEVON_CORP_1F:
            yield from _take_warp_to(
                MapRSE.RUSTBORO_CITY,
                timeout=timeout_frames * 5 if context.rom.is_emerald else timeout_frames,
            )
        route = get_map_data(MapRSE.ROUTE104, (0, 0))
        woods_entrances = [
            warp
            for warp in route.warps
            if (warp.destination_map_group, warp.destination_map_number)
            == MapRSE.PETALBURG_WOODS.value
        ]
        reachable_entrances = []
        for warp in woods_entrances:
            try:
                path = calculate_path(get_player_location(), (MapRSE.ROUTE104, warp.local_coordinates))
            except PathFindingError:
                continue
            reachable_entrances.append((len(path), warp))
        if not reachable_entrances:
            raise BotModeError("RSE-016 no reachable north Petalburg Woods entrance was found.")
        north_entrance = min(reachable_entrances, key=lambda candidate: candidate[0])[1]
        if context.rom.is_emerald:
            for _ in range(3):
                yield from navigate_to(
                    MapRSE.ROUTE104,
                    north_entrance.local_coordinates,
                    avoid_scripted_events=False,
                    expecting_script=True,
                )
                yield from _wait_for_control(timeout=timeout_frames)
                if _current_map() is MapRSE.PETALBURG_WOODS:
                    break
        else:
            yield from navigate_to(MapRSE.ROUTE104, north_entrance.local_coordinates)
        yield from _wait_for_control(timeout=timeout_frames)

        woods = get_map_data(MapRSE.PETALBURG_WOODS, (0, 0))
        route_exits = [
            warp
            for warp in woods.warps
            if (warp.destination_map_group, warp.destination_map_number) == MapRSE.ROUTE104.value
        ]
        reachable_exits = []
        for warp in route_exits:
            try:
                path = calculate_path(
                    get_player_location(),
                    (MapRSE.PETALBURG_WOODS, warp.local_coordinates),
                )
            except PathFindingError:
                continue
            reachable_exits.append((warp.destination_location.local_position[1], len(path), warp))
        if not reachable_exits:
            raise BotModeError("RSE-016 no reachable south Petalburg Woods exit was found.")
        south_exit = max(reachable_exits, key=lambda candidate: (candidate[0], -candidate[1]))[2]
        for attempt in range(6):
            try:
                calculate_path(
                    get_player_location(),
                    (MapRSE.PETALBURG_WOODS, south_exit.local_coordinates),
                )
                yield from navigate_to(MapRSE.PETALBURG_WOODS, south_exit.local_coordinates)
                break
            except (PathFindingError, BotModeError):
                if attempt == 5:
                    raise
                for _ in range(30):
                    yield
        yield from _wait_for_control(timeout=timeout_frames)

        house_warp = next(
            warp
            for warp in route.warps
            if (warp.destination_map_group, warp.destination_map_number)
            == MapRSE.ROUTE104_MR_BRINEYS_HOUSE.value
        )
        yield from navigate_to(MapRSE.ROUTE104, house_warp.local_coordinates)
        if _current_map() is MapRSE.ROUTE104:
            yield from _walk_through_warp(
                MapRSE.ROUTE104,
                "Up",
                target_x=house_warp.local_coordinates[0],
                timeout=timeout_frames,
            )
        yield from _wait_for_control(timeout=timeout_frames)
        for attempt in range(30):
            try:
                yield from navigate_to(MapRSE.ROUTE104_MR_BRINEYS_HOUSE, (5, 5))
                break
            except BotModeError:
                if attempt == 29:
                    raise
                for _ in range(30):
                    yield
        for frame in range(5_000):
            briney = next((obj for obj in get_map_objects() if obj.local_id == 1), None)
            if briney is not None:
                bx, by = briney.current_coords
                px, py = get_player_avatar().local_coordinates
                if abs(px - bx) + abs(py - by) == 1:
                    direction = "Right" if bx > px else "Left" if bx < px else "Down" if by > py else "Up"
                    context.emulator.press_button(direction)
                    yield
                    yield
                    context.emulator.press_button("A")
            yield
            if get_global_script_context().is_active or not player_avatar_is_controllable():
                break
        for frame in range(timeout_frames):
            if get_event_flag("VISITED_DEWFORD_TOWN") and player_avatar_is_controllable():
                yield from _wait_for_control(timeout=timeout_frames)
                return
            if frame % 4 == 0:
                context.emulator.press_button("A")
            yield
        script = get_global_script_context()
        raise BotModeError(
            "RSE-016 Dewford visited flag was not observed: "
            f"map={_current_map().name} position={get_player_avatar().local_coordinates} "
            f"briney_state={get_event_var('BRINEY_HOUSE_STATE')} "
            f"objects={[(obj.local_id, obj.current_coords) for obj in get_map_objects()]} "
            f"script={script.script_function_name if script.is_active else 'inactive'}."
        )
    finally:
        set_navigation_encounter_policy(False)


def run_rse_receive_flash(
    *,
    set_navigation_encounter_policy: Callable[[bool], None],
    timeout_frames: int = 30_000,
) -> Generator:
    """Receive HM05 Flash from the hiker at Granite Cave entrance."""
    flash = get_item_by_name("HM05")
    if get_item_bag().quantity_of(flash) > 0:
        yield from _wait_for_control(timeout=timeout_frames)
        return
    set_navigation_encounter_policy(True)
    try:
        if _current_map() in {MapRSE.DEWFORD_TOWN, MapRSE.ROUTE106}:
            yield from heal_in_pokemon_center(PokemonCenter.DewfordTown)
            yield from _leave_building_for(MapRSE.DEWFORD_TOWN)
        if _current_map() is not MapRSE.GRANITE_CAVE_1F:
            route = get_map_data(MapRSE.ROUTE106, (0, 0))
            cave_warp = next(
                warp
                for warp in route.warps
                if (warp.destination_map_group, warp.destination_map_number)
                == MapRSE.GRANITE_CAVE_1F.value
            )
            yield from navigate_to(MapRSE.ROUTE106, cave_warp.local_coordinates)
            if _current_map() is MapRSE.ROUTE106:
                yield from _walk_through_warp(
                    MapRSE.ROUTE106,
                    "Up",
                    target_x=cave_warp.local_coordinates[0],
                    timeout=timeout_frames,
                )
            yield from _wait_for_control(timeout=timeout_frames)
        yield from navigate_to(MapRSE.GRANITE_CAVE_1F, (36, 10))
        yield from ensure_facing_direction("Up")
        context.emulator.press_button("A")
        for frame in range(timeout_frames):
            if get_item_bag().quantity_of(flash) > 0 and player_avatar_is_controllable():
                yield from _wait_for_control(timeout=timeout_frames)
                return
            if frame % 4 == 0:
                context.emulator.press_button("A")
            yield
        raise BotModeError("RSE-017 HM05 Flash was not received.")
    finally:
        set_navigation_encounter_policy(False)


def run_rse_deliver_steven_letter(
    *,
    set_navigation_encounter_policy: Callable[[bool], None],
    timeout_frames: int = 40_000,
) -> Generator:
    """Reach Steven's room in Granite Cave and deliver Mr. Stone's letter."""
    if get_event_flag("DELIVERED_STEVEN_LETTER"):
        yield from _wait_for_control(timeout=timeout_frames)
        return
    set_navigation_encounter_policy(True)
    try:
        cave_maps = {
            MapRSE.GRANITE_CAVE_1F,
            MapRSE.GRANITE_CAVE_B1F,
            MapRSE.GRANITE_CAVE_B2F,
            MapRSE.GRANITE_CAVE_STEVENS_ROOM,
        }
        visited_maps = {_current_map()}
        traversed_edges: set[tuple[MapRSE, tuple[int, int]]] = set()
        previous_map: MapRSE | None = None
        for _step in range(30):
            yield from _wait_for_control(timeout=timeout_frames)
            if _current_map() is MapRSE.GRANITE_CAVE_STEVENS_ROOM:
                break
            if _current_map() is MapRSE.DEWFORD_TOWN_POKEMON_CENTER_1F:
                yield from _leave_building_for(MapRSE.DEWFORD_TOWN, timeout=timeout_frames)
            if _current_map() not in cave_maps:
                route = get_map_data(MapRSE.ROUTE106, (0, 0))
                cave_warp = next(
                    warp
                    for warp in route.warps
                    if (warp.destination_map_group, warp.destination_map_number)
                    == MapRSE.GRANITE_CAVE_1F.value
                )
                yield from navigate_to(MapRSE.ROUTE106, cave_warp.local_coordinates)
                yield from _wait_for_control(timeout=timeout_frames)
                continue
            current = _current_map()
            current_data = get_map_data(current, (0, 0))
            candidates = []
            for warp in current_data.warps:
                destination = get_map_enum((warp.destination_map_group, warp.destination_map_number))
                if destination not in cave_maps:
                    continue
                try:
                    path = calculate_path(get_player_location(), (current, warp.local_coordinates))
                except PathFindingError:
                    continue
                edge = (current, warp.local_coordinates)
                score = (
                    100 if destination is MapRSE.GRANITE_CAVE_STEVENS_ROOM else 0
                ) + (50 if destination not in visited_maps else 0) + (
                    20 if destination is not previous_map else 0
                ) + (10 if edge not in traversed_edges else 0)
                candidates.append((score, -len(path), warp, destination, edge))
            if not candidates:
                raise BotModeError(
                    f"RSE-018 no reachable cave warp from {current.name} "
                    f"at {get_player_avatar().local_coordinates}."
                )
            _, _, warp, destination, edge = max(candidates, key=lambda candidate: (candidate[0], candidate[1]))
            try:
                yield from navigate_to(current, warp.local_coordinates)
            except BotModeError as error:
                if "not controllable" not in str(error) and "not on connected maps" not in str(error):
                    raise
                yield from _wait_for_control(timeout=timeout_frames)
                continue
            traversed_edges.add(edge)
            previous_map = current
            yield from _wait_for_control(timeout=timeout_frames)
            visited_maps.add(destination)
        else:
            raise BotModeError("RSE-018 exceeded Granite Cave warp traversal limit.")
        yield from navigate_to(MapRSE.GRANITE_CAVE_STEVENS_ROOM, (7, 9))
        yield from ensure_facing_direction("Up")
        context.emulator.press_button("A")
        for frame in range(timeout_frames):
            if get_event_flag("DELIVERED_STEVEN_LETTER") and player_avatar_is_controllable():
                yield from _wait_for_control(timeout=timeout_frames)
                return
            if frame % 4 == 0:
                context.emulator.press_button("A")
            yield
        raise BotModeError("RSE-018 Steven letter delivery flag was not observed.")
    finally:
        set_navigation_encounter_policy(False)


def run_rse_defeat_brawly(
    *,
    set_navigation_encounter_policy: Callable[[bool], None],
    timeout_frames: int = 40_000,
) -> Generator:
    """Defeat Dewford Gym trainers and Brawly using the central battle engine."""
    if get_event_flag("BADGE02_GET"):
        yield from _wait_for_control(timeout=timeout_frames)
        return
    gym = get_map_data(MapRSE.DEWFORD_TOWN_GYM, (0, 0))
    leaders = [object_template for object_template in gym.objects if object_template.trainer_type == "None"]
    brawly = min(leaders, key=lambda object_template: object_template.local_coordinates[1])
    interaction_position = (brawly.local_coordinates[0], brawly.local_coordinates[1] + 1)
    set_navigation_encounter_policy(True)
    try:
        cave_maps = {
            MapRSE.GRANITE_CAVE_1F,
            MapRSE.GRANITE_CAVE_B1F,
            MapRSE.GRANITE_CAVE_B2F,
            MapRSE.GRANITE_CAVE_STEVENS_ROOM,
        }
        previous_map: MapRSE | None = None
        traversed_edges: set[tuple[MapRSE, tuple[int, int]]] = set()
        for _step in range(12):
            yield from _wait_for_control(timeout=timeout_frames)
            if _current_map() not in cave_maps:
                break
            current = _current_map()
            candidates = []
            for warp in get_map_data(current, (0, 0)).warps:
                destination = get_map_enum((warp.destination_map_group, warp.destination_map_number))
                if destination not in cave_maps and destination is not MapRSE.ROUTE106:
                    continue
                try:
                    path = calculate_path(get_player_location(), (current, warp.local_coordinates))
                except PathFindingError:
                    continue
                edge = (current, warp.local_coordinates)
                score = (100 if destination is MapRSE.ROUTE106 else 0) + (
                    20 if destination is not previous_map else 0
                ) + (10 if edge not in traversed_edges else 0)
                candidates.append((score, -len(path), warp, edge))
            if not candidates:
                raise BotModeError(f"RSE-019 no reachable exit warp from {current.name}.")
            _, _, warp, edge = max(candidates, key=lambda candidate: (candidate[0], candidate[1]))
            try:
                yield from navigate_to(current, warp.local_coordinates)
            except BotModeError as error:
                if "not controllable" not in str(error) and "not on connected maps" not in str(error):
                    raise
                yield from _wait_for_control(timeout=timeout_frames)
                continue
            traversed_edges.add(edge)
            previous_map = current
            yield from _wait_for_control(timeout=timeout_frames)
        else:
            raise BotModeError("RSE-019 exceeded Granite Cave exit traversal limit.")

        if get_party()[0].species.name in {"Treecko", "Grovyle"} and get_party()[0].level < 20:
            set_navigation_encounter_policy(True, True)
            training_map = MapRSE.GRANITE_CAVE_1F
            while get_party()[0].level < 20:
                yield from heal_in_pokemon_center(PokemonCenter.DewfordTown)
                yield from _leave_building_for(MapRSE.DEWFORD_TOWN, timeout=timeout_frames)
                route106 = get_map_data(MapRSE.ROUTE106, (0, 0))
                cave_warp = next(
                    warp
                    for warp in route106.warps
                    if (warp.destination_map_group, warp.destination_map_number) == training_map.value
                )
                yield from navigate_to(MapRSE.ROUTE106, cave_warp.local_coordinates)
                if _current_map() is not training_map:
                    yield from _take_warp_to(training_map, timeout=timeout_frames)
                cave = get_map_data(training_map, (0, 0))
                encounter_tiles = []
                width, height = cave.map_size
                for y in range(height):
                    for x in range(width):
                        if not get_map_data(training_map, (x, y)).has_encounters:
                            continue
                        try:
                            path = calculate_path(get_player_location(), (training_map, (x, y)))
                        except PathFindingError:
                            continue
                        encounter_tiles.append((len(path), (x, y)))
                if not encounter_tiles:
                    raise BotModeError("RSE-019 no reachable Granite Cave training tile was found.")
                yield from navigate_to(training_map, min(encounter_tiles)[1])
                yield from spin(
                    stop_condition=lambda: (
                        get_party()[0].level >= 20
                        or get_party()[0].current_hp == 0
                        or _current_map() is not training_map
                    )
                )
            set_navigation_encounter_policy(True)
            if _current_map() is training_map:
                yield from _take_warp_to(MapRSE.ROUTE106, timeout=timeout_frames)

        for _attempt in range(40):
            yield from heal_in_pokemon_center(PokemonCenter.DewfordTown)
            yield from _leave_building_for(MapRSE.DEWFORD_TOWN)
            yield from _take_warp_to(MapRSE.DEWFORD_TOWN_GYM, timeout=timeout_frames)
            yield from navigate_to(MapRSE.DEWFORD_TOWN_GYM, interaction_position)
            yield from ensure_facing_direction("Up")
            context.emulator.press_button("A")
            for frame in range(timeout_frames):
                if get_event_flag("BADGE02_GET"):
                    yield from _wait_for_control(timeout=timeout_frames)
                    return
                if frame > 600 and _current_map() is not MapRSE.DEWFORD_TOWN_GYM and player_avatar_is_controllable():
                    break
                if frame % 4 == 0:
                    context.emulator.press_button("A")
                yield
        raise BotModeError("RSE-019 Knuckle Badge was not obtained after 40 attempts.")
    finally:
        set_navigation_encounter_policy(False)


def run_rse_sail_to_slateport(
    *,
    set_navigation_encounter_policy: Callable[[bool], None],
    timeout_frames: int = 40_000,
) -> Generator:
    set_navigation_encounter_policy(True)
    try:
        yield from _run_rse_sail_to_slateport(timeout_frames=timeout_frames)
    finally:
        set_navigation_encounter_policy(False)


def _run_rse_sail_to_slateport(*, timeout_frames: int = 40_000) -> Generator:
    """Ask Mr. Briney to sail from Dewford to Slateport."""
    if get_event_flag("VISITED_SLATEPORT_CITY"):
        yield from _wait_for_control(timeout=timeout_frames)
        return
    if _current_map() is MapRSE.DEWFORD_TOWN_GYM:
        yield from _take_warp_to(MapRSE.DEWFORD_TOWN, timeout=timeout_frames)
    yield from heal_in_pokemon_center(PokemonCenter.DewfordTown)
    yield from _leave_building_for(MapRSE.DEWFORD_TOWN, timeout=timeout_frames)
    yield from navigate_to(MapRSE.DEWFORD_TOWN, (11, 9))
    yield from ensure_facing_direction("Right")
    context.emulator.press_button("A")
    destination_selected = False
    for frame in range(timeout_frames):
        if _current_map() is MapRSE.ROUTE109 and destination_selected:
            yield from _wait_for_control(timeout=timeout_frames)
            pokemon_center_door = PokemonCenter.SlateportCity.value[1]
            for _attempt in range(6):
                try:
                    yield from navigate_to(
                        MapRSE.SLATEPORT_CITY,
                        (pokemon_center_door[0], pokemon_center_door[1] + 1),
                        avoid_scripted_events=False,
                        expecting_script=True,
                    )
                except BotModeError as error:
                    if "not controllable" not in str(error):
                        raise
                yield from _wait_for_control(timeout=timeout_frames)
                if get_event_flag("VISITED_SLATEPORT_CITY"):
                    return
            raise BotModeError("RSE-020 could not cross Route 109 into Slateport after scripted events.")
        if get_event_flag("VISITED_SLATEPORT_CITY") and player_avatar_is_controllable():
            yield from _wait_for_control(timeout=timeout_frames)
            return
        if get_task("Task_HandleMultichoiceInput") is not None and not destination_selected:
            if context.rom.is_emerald:
                # Emerald defaults Briney's three-option menu to Cancel (index 2).
                # Confirm only after RAM reports Slateport (index 1); otherwise a
                # delayed DPAD input can close the menu on Cancel.
                cursor = parse_menu()["cursorPos"]
                if cursor == 1:
                    context.emulator.press_button("A")
                    destination_selected = True
                elif frame % 4 == 0:
                    context.emulator.press_button("Up" if cursor > 1 else "Down")
            else:
                context.emulator.press_button("Up")
                yield
                yield
                context.emulator.press_button("A")
                destination_selected = True
        elif destination_selected:
            if context.rom.is_emerald:
                if frame % 4 == 0:
                    context.emulator.press_button("A")
            elif frame % 4 == 0:
                context.emulator.press_button("A")
            elif frame % 4 == 2:
                context.emulator.press_button("B")
        elif frame % 4 == 0:
            context.emulator.press_button("A")
        yield
    script = get_global_script_context()
    raise BotModeError(
        "RSE-020 Slateport visited flag was not observed: "
        f"map={_current_map().name} position={get_player_avatar().local_coordinates} "
        f"objects={[(obj.local_id, obj.current_coords) for obj in get_map_objects()]} "
        f"tasks={[task.symbol for task in get_tasks()]} selected={destination_selected} "
        f"script={script.script_function_name if script.is_active else 'inactive'}."
    )


def run_rse_talk_to_dock(*, timeout_frames: int = 30_000) -> Generator:
    """Ask Dock where Captain Stern is."""
    if get_event_flag("DOCK_REJECTED_DEVON_GOODS"):
        yield from _wait_for_control(timeout=timeout_frames)
        return
    if _current_map() is MapRSE.SLATEPORT_CITY:
        city = get_map_data(MapRSE.SLATEPORT_CITY, (0, 0))
        shipyard_warp = next(
            warp
            for warp in city.warps
            if (warp.destination_map_group, warp.destination_map_number)
            == MapRSE.SLATEPORT_CITY_STERNS_SHIPYARD_1F.value
        )
        yield from navigate_to(MapRSE.SLATEPORT_CITY, shipyard_warp.local_coordinates)
        yield from _wait_for_control(timeout=timeout_frames)
    for _ in range(30):
        if get_player_avatar().local_coordinates[1] < 14:
            break
        context.emulator.press_button("Up")
        yield
    dock = get_map_data(MapRSE.SLATEPORT_CITY_STERNS_SHIPYARD_1F, (0, 0)).object_by_local_id(1)
    if dock is None:
        raise BotModeError("RSE-021 Dock object was not found.")
    dx, dy = dock.local_coordinates
    candidates = (
        ((dx - 1, dy), "Right"),
        ((dx + 1, dy), "Left"),
        ((dx, dy - 1), "Down"),
        ((dx, dy + 1), "Up"),
    )
    reachable = []
    for coordinates, direction in candidates:
        try:
            path = calculate_path(
                get_player_location(),
                (MapRSE.SLATEPORT_CITY_STERNS_SHIPYARD_1F, coordinates),
            )
        except PathFindingError:
            continue
        reachable.append((len(path), coordinates, direction))
    if not reachable:
        raise BotModeError("RSE-021 no reachable tile adjacent to Dock was found.")
    _, interaction_position, facing = min(reachable)
    yield from navigate_to(MapRSE.SLATEPORT_CITY_STERNS_SHIPYARD_1F, interaction_position)
    yield from ensure_facing_direction(facing)
    context.emulator.press_button("A")
    for frame in range(timeout_frames):
        if get_event_flag("DOCK_REJECTED_DEVON_GOODS") and player_avatar_is_controllable():
            yield from _wait_for_control(timeout=timeout_frames)
            return
        if frame % 4 == 0:
            context.emulator.press_button("A")
        yield
    raise BotModeError("RSE-021 Dock rejection flag was not observed.")


def run_rse_deliver_devon_goods(
    *, set_navigation_encounter_policy: Callable[[bool], None], timeout_frames: int = 60_000
) -> Generator:
    """Deliver the Devon Goods to Captain Stern and defeat the thieves."""
    if get_event_flag("DELIVERED_DEVON_GOODS"):
        yield from _wait_for_control(timeout=timeout_frames)
        return
    stern_map = (
        MapRSE.SLATEPORT_CITY_OCEANIC_MUSEUM_2F
        if context.rom.is_emerald
        else MapRSE.SLATEPORT_CITY_OCEANIC_MUSEUM_1F
    )
    stern_position = (13, 7)
    set_navigation_encounter_policy(True)
    try:
        if _current_map() is MapRSE.SLATEPORT_CITY_STERNS_SHIPYARD_1F:
            yield from _take_warp_to(MapRSE.SLATEPORT_CITY, timeout=timeout_frames)
        if _current_map() is MapRSE.SLATEPORT_CITY:
            city = get_map_data(MapRSE.SLATEPORT_CITY, (0, 0))
            exterior_destination = (
                MapRSE.SLATEPORT_CITY_OCEANIC_MUSEUM_1F
                if context.rom.is_emerald
                else MapRSE.SLATEPORT_CITY_POKEMON_FAN_CLUB
            )
            museum_warps = [
                warp
                for warp in city.warps
                if (warp.destination_map_group, warp.destination_map_number)
                == exterior_destination.value
            ]
            reachable_museum_warps = []
            for warp in museum_warps:
                try:
                    path = calculate_path(
                        get_player_location(),
                        (MapRSE.SLATEPORT_CITY, warp.local_coordinates),
                    )
                except PathFindingError:
                    continue
                reachable_museum_warps.append((len(path), warp))
            if not reachable_museum_warps:
                raise BotModeError("RSE-022 no reachable Oceanic Museum entrance was found.")
            museum_warp = min(reachable_museum_warps, key=lambda candidate: candidate[0])[1]
            yield from navigate_to(
                MapRSE.SLATEPORT_CITY,
                museum_warp.local_coordinates,
                avoid_scripted_events=False,
                expecting_script=True,
            )
            stable = 0
            for frame in range(timeout_frames):
                if player_avatar_is_controllable() and not get_global_script_context().is_active:
                    stable += 1
                    if stable >= 120:
                        break
                else:
                    stable = 0
                    if frame % 4 == 0:
                        context.emulator.press_button("A")
                yield
            else:
                raise BotModeError("RSE-022 museum admission dialogue did not finish.")
        if _current_map() is not stern_map:
            if get_event_var("SLATEPORT_MUSEUM_1F_STATE") == 0:
                for frame in range(timeout_frames):
                    if (
                        get_event_var("SLATEPORT_MUSEUM_1F_STATE") >= 1
                        and player_avatar_is_controllable()
                        and not get_global_script_context().is_active
                    ):
                        break
                    if get_global_script_context().is_active or not player_avatar_is_controllable():
                        if frame % 4 == 0:
                            context.emulator.press_button("A")
                    else:
                        context.emulator.press_button("Up")
                    yield
                else:
                    raise BotModeError("RSE-022 museum admission state did not advance.")
            starting_position = get_player_avatar().local_coordinates
            escape_directions = ("Up", "Left", "Right")
            for frame in range(90):
                if get_player_avatar().local_coordinates != starting_position:
                    break
                if frame % 3 == 0:
                    context.emulator.press_button(escape_directions[(frame // 3) % len(escape_directions)])
                yield
            for _attempt in range(10):
                if _current_map() is stern_map:
                    break
                source = _current_map()
                stair_warp = next(
                    warp
                    for warp in get_map_data(source, (0, 0)).warps
                    if (warp.destination_map_group, warp.destination_map_number) == stern_map.value
                )
                try:
                    yield from navigate_to(
                        source,
                        stair_warp.local_coordinates,
                        avoid_scripted_events=False,
                    )
                except BotModeError as error:
                    if "triggered a scripted event" not in str(error) and "not controllable" not in str(error):
                        raise
                yield from _wait_for_control(timeout=timeout_frames)
            else:
                raise BotModeError(
                    "RSE-022 could not reach Oceanic Museum upper floor: "
                    f"map={_current_map().name} position={get_player_avatar().local_coordinates} "
                    f"tasks={[task.symbol for task in get_tasks()]}."
                )
        if context.rom.is_emerald:
            # Emerald keeps Stern on 2F at (13, 6). A museum visitor may occupy
            # (13, 7), so select among the other live reachable adjacencies.
            interaction_candidates = (
                ((12, 6), "Right"),
                ((14, 6), "Left"),
                ((13, 5), "Down"),
                ((13, 7), "Up"),
            )
            reachable_interactions = []
            for coordinates, direction in interaction_candidates:
                try:
                    path = calculate_path(get_player_location(), (stern_map, coordinates))
                except PathFindingError:
                    continue
                reachable_interactions.append((len(path), coordinates, direction))
            if not reachable_interactions:
                raise BotModeError("RSE-022 no reachable Emerald tile adjacent to Captain Stern was found.")
            _, stern_position, stern_facing = min(reachable_interactions)
        else:
            stern = get_map_data(stern_map, (0, 0)).object_by_local_id(1)
            if stern is None:
                raise BotModeError("RSE-022 Captain Stern object was not found.")
            sx, sy = stern.local_coordinates
            interaction_candidates = (
                ((sx - 1, sy), "Right"),
                ((sx + 1, sy), "Left"),
                ((sx, sy - 1), "Down"),
                ((sx, sy + 1), "Up"),
            )
            reachable_interactions = []
            for coordinates, direction in interaction_candidates:
                try:
                    path = calculate_path(get_player_location(), (stern_map, coordinates))
                except PathFindingError:
                    continue
                reachable_interactions.append((len(path), coordinates, direction))
            if not reachable_interactions:
                raise BotModeError("RSE-022 no reachable tile adjacent to Captain Stern was found.")
            _, stern_position, stern_facing = min(reachable_interactions)
        yield from navigate_to(stern_map, stern_position, avoid_scripted_events=False, expecting_script=True)
        if player_avatar_is_controllable() and not get_global_script_context().is_active:
            yield from ensure_facing_direction(stern_facing)
        context.emulator.press_button("A")
        for frame in range(timeout_frames):
            if get_event_flag("DELIVERED_DEVON_GOODS") and player_avatar_is_controllable():
                yield from _wait_for_control(timeout=timeout_frames)
                if context.rom.is_emerald:
                    if _current_map() is MapRSE.SLATEPORT_CITY_OCEANIC_MUSEUM_2F:
                        yield from _take_warp_to(
                            MapRSE.SLATEPORT_CITY_OCEANIC_MUSEUM_1F,
                            timeout=timeout_frames,
                        )
                    if _current_map() is MapRSE.SLATEPORT_CITY_OCEANIC_MUSEUM_1F:
                        yield from _take_warp_to(MapRSE.SLATEPORT_CITY, timeout=timeout_frames)
                return
            if frame % 4 == 0:
                context.emulator.press_button("A")
            yield
        raise BotModeError("RSE-022 Devon Goods delivery flag was not observed.")
    finally:
        set_navigation_encounter_policy(False)


def run_rse_defeat_route110_rival(
    *, set_navigation_encounter_policy: Callable[[bool], None], timeout_frames: int = 60_000
) -> Generator:
    """Cross Route 110 and defeat the rival encounter."""
    if get_event_var("ROUTE110_STATE") > 0:
        yield from _wait_for_control(timeout=timeout_frames)
        return
    set_navigation_encounter_policy(True)
    try:
        if context.rom.is_rs and _current_map() is MapRSE.SLATEPORT_CITY_OCEANIC_MUSEUM_1F:
            yield from _take_warp_to(
                MapRSE.SLATEPORT_CITY_POKEMON_FAN_CLUB,
                timeout=timeout_frames,
            )
        if _current_map() in {
            MapRSE.SLATEPORT_CITY_POKEMON_FAN_CLUB,
            MapRSE.SLATEPORT_CITY_OCEANIC_MUSEUM_1F,
        }:
            yield from _take_warp_to(MapRSE.SLATEPORT_CITY, timeout=timeout_frames)
        if context.rom.is_rs and _current_map() is MapRSE.SLATEPORT_CITY_HOUSE:
            yield from _take_warp_to(MapRSE.SLATEPORT_CITY, timeout=timeout_frames)
        for _attempt in range(40):
            yield from heal_in_pokemon_center(PokemonCenter.SlateportCity)
            yield from _leave_building_for(MapRSE.SLATEPORT_CITY)
            if _current_map() is not MapRSE.SLATEPORT_CITY:
                yield from _take_warp_to(MapRSE.SLATEPORT_CITY, timeout=timeout_frames)
            if context.rom.is_emerald and get_event_var("REGISTER_BIRCH_STATE") == 1:
                # Emerald inserts Birch's PokéNav registration scene across
                # Route 110 (y=85) before the rival trigger farther north.
                try:
                    yield from navigate_to(
                        MapRSE.ROUTE110,
                        (33, 57),
                        avoid_scripted_events=False,
                        expecting_script=True,
                    )
                except BotModeError as error:
                    if "not controllable" not in str(error):
                        raise
                yield from _wait_for_control(timeout=timeout_frames)
            try:
                yield from navigate_to(MapRSE.ROUTE110, (33, 57))
                yield from navigate_to(
                    MapRSE.ROUTE110, (33, 56), avoid_scripted_events=False, expecting_script=True
                )
            except BotModeError as error:
                if "not controllable" not in str(error) and "not on connected maps" not in str(error):
                    raise
                yield from _wait_for_control(timeout=timeout_frames)
                continue
            for frame in range(timeout_frames):
                if get_event_var("ROUTE110_STATE") > 0 and player_avatar_is_controllable():
                    yield from _wait_for_control(timeout=timeout_frames)
                    return
                if (
                    frame > 600
                    and _current_map() is not MapRSE.ROUTE110
                    and player_avatar_is_controllable()
                ):
                    break
                if frame % 4 == 0:
                    context.emulator.press_button("A")
                yield
        script = get_global_script_context()
        raise BotModeError(
            "RSE-023 Route 110 rival state was not observed: "
            f"map={_current_map().name} position={get_player_avatar().local_coordinates} "
            f"state={get_event_var('ROUTE110_STATE')} "
            f"party={[(pokemon.species.name, pokemon.level, pokemon.current_hp) for pokemon in get_party()]} "
            f"script={script.script_function_name if script.is_active else 'inactive'}."
        )
    finally:
        set_navigation_encounter_policy(False)


def run_rse_reach_mauville(
    *, set_navigation_encounter_policy: Callable[[bool], None], timeout_frames: int = 40_000
) -> Generator:
    """Reach Mauville City from Route 110."""
    if get_event_flag("VISITED_MAUVILLE_CITY"):
        yield from _wait_for_control(timeout=timeout_frames)
        return
    set_navigation_encounter_policy(True)
    try:
        if _current_map() is MapRSE.ROUTE110:
            # Ruby keeps the defeated rival's moving object in the active-object
            # cache until the map reloads. On the one-tile corridor this splits
            # the path graph, so reload Route 110 through Slateport first.
            yield from heal_in_pokemon_center(PokemonCenter.SlateportCity)
            yield from _leave_building_for(MapRSE.SLATEPORT_CITY)
        for route_waypoint in ((33, 40), (6, 40)):
            yield from navigate_to(
                MapRSE.ROUTE110,
                route_waypoint,
                avoid_scripted_events=False,
                expecting_script=True,
            )
        for frame in range(600):
            if get_player_avatar().local_coordinates[1] <= 38:
                break
            if frame % 2 == 0:
                context.emulator.press_button("Up")
            yield
        yield from navigate_to(MapRSE.ROUTE110, (3, 38))
        for frame in range(timeout_frames):
            if _current_map() is MapRSE.ROUTE110 and get_player_avatar().local_coordinates[1] <= 20:
                break
            if player_avatar_is_controllable() and frame % 2 == 0:
                context.emulator.press_button("Up")
            elif frame % 4 == 0:
                context.emulator.press_button("A")
            yield
        else:
            raise BotModeError(
                "RSE-024 could not cross beneath Cycling Road: "
                f"map={_current_map().name} position={get_player_avatar().local_coordinates}."
            )
        for frame in range(600):
            if get_player_avatar().local_coordinates[1] <= 18:
                break
            if player_avatar_is_controllable() and frame % 2 == 0:
                context.emulator.press_button("Up")
            elif frame % 4 == 0:
                context.emulator.press_button("A")
            yield
        yield from navigate_to(MapRSE.ROUTE110, (10, 18))
        for frame in range(2_000):
            if get_player_avatar().local_coordinates[1] <= 13:
                break
            if player_avatar_is_controllable() and frame % 2 == 0:
                context.emulator.press_button("Up")
            elif frame % 4 == 0:
                context.emulator.press_button("A")
            yield
        else:
            raise BotModeError(
                "RSE-024 could not cross the north Cycling Road underpass: "
                f"position={get_player_avatar().local_coordinates}."
            )
        for frame in range(600):
            if get_player_avatar().local_coordinates[1] <= 10:
                break
            if frame % 2 == 0:
                context.emulator.press_button("Up")
            yield
        for frame in range(600):
            if get_player_avatar().local_coordinates[1] <= 6:
                break
            if frame % 2 == 0:
                context.emulator.press_button("Up")
            yield
        for frame in range(600):
            if get_player_avatar().local_coordinates[0] >= 13:
                break
            if frame % 2 == 0:
                context.emulator.press_button("Right")
            yield
        for frame in range(timeout_frames):
            if _current_map() is MapRSE.MAUVILLE_CITY:
                break
            if player_avatar_is_controllable() and frame % 2 == 0:
                context.emulator.press_button("Up")
            elif frame % 4 == 0:
                context.emulator.press_button("A")
            yield
        else:
            raise BotModeError(
                "RSE-024 Mauville transition was not reached: "
                f"map={_current_map().name} position={get_player_avatar().local_coordinates}."
            )
        for _ in range(timeout_frames):
            if get_event_flag("VISITED_MAUVILLE_CITY"):
                yield from _wait_for_control(timeout=timeout_frames)
                return
            yield
        raise BotModeError("RSE-024 Mauville visited flag was not observed.")
    finally:
        set_navigation_encounter_policy(False)


def run_rse_defeat_wally(
    *, set_navigation_encounter_policy: Callable[[bool], None], timeout_frames: int = 60_000
) -> Generator:
    """Defeat Wally outside Mauville Gym."""
    if get_event_flag("DEFEATED_WALLY_MAUVILLE"):
        yield from _wait_for_control(timeout=timeout_frames)
        return
    set_navigation_encounter_policy(True)
    try:
        yield from navigate_to(MapRSE.MAUVILLE_CITY, (8, 7))
        yield from ensure_facing_direction("Up")
        context.emulator.press_button("A")
        for frame in range(timeout_frames):
            if get_event_flag("DEFEATED_WALLY_MAUVILLE") and player_avatar_is_controllable():
                yield from _wait_for_control(timeout=timeout_frames)
                return
            if frame % 4 == 0:
                context.emulator.press_button("A")
            yield
        raise BotModeError("RSE-025 Wally defeated flag was not observed.")
    finally:
        set_navigation_encounter_policy(False)


def run_rse_receive_rock_smash(*, timeout_frames: int = 20_000) -> Generator:
    """Receive HM06 from the Rock Smash NPC in Mauville."""
    rock_smash = get_item_by_name("HM06")
    if get_item_bag().quantity_of(rock_smash) > 0:
        yield from _wait_for_control(timeout=timeout_frames)
        return
    if _current_map() is not MapRSE.MAUVILLE_CITY_HOUSE1:
        yield from _take_warp_to(MapRSE.MAUVILLE_CITY_HOUSE1, timeout=timeout_frames)
    if get_player_avatar().local_coordinates[1] == 7:
        starting_position = get_player_avatar().local_coordinates
        for _ in range(300):
            if get_player_avatar().local_coordinates != starting_position:
                break
            context.emulator.press_button("Up")
            yield
    for target, direction in (((3, 5), "Up"), ((3, 4), "Up")):
        for _ in range(600):
            if get_player_avatar().local_coordinates == target:
                break
            context.emulator.press_button(direction)
            yield
        else:
            raise BotModeError(
                "RSE-026 could not approach Rock Smash NPC: "
                f"position={get_player_avatar().local_coordinates} target={target}."
            )
    yield from ensure_facing_direction("Right")
    context.emulator.press_button("A")
    for frame in range(timeout_frames):
        if get_item_bag().quantity_of(rock_smash) > 0 and player_avatar_is_controllable():
            yield from _wait_for_control(timeout=timeout_frames)
            return
        if frame % 4 == 0:
            context.emulator.press_button("A")
        yield
    raise BotModeError("RSE-026 HM06 was not received.")


def _walk_mauville_gym_axis(
    direction: str, axis: int, target: int, *, timeout_frames: int
) -> Generator:
    for _frame in range(timeout_frames):
        if get_player_avatar().local_coordinates[axis] == target:
            return
        if player_avatar_is_controllable():
            context.emulator.press_button(direction)
        yield
    raise BotModeError(
        "RSE-027 axis movement timed out: "
        f"position={get_player_avatar().local_coordinates} direction={direction} target={target}."
    )


def run_rse_defeat_wattson(
    *, set_navigation_encounter_policy: Callable[[bool], None], timeout_frames: int = 40_000
) -> Generator:
    """Defeat Mauville Gym trainers and Wattson using the central battle engine."""
    if get_event_flag("BADGE03_GET"):
        yield from _wait_for_control(timeout=timeout_frames)
        return
    gym = get_map_data(MapRSE.MAUVILLE_CITY_GYM, (0, 0))
    leaders = [object_template for object_template in gym.objects if object_template.trainer_type == "None"]
    wattson = min(leaders, key=lambda object_template: object_template.local_coordinates[1])
    interaction_position = (wattson.local_coordinates[0], wattson.local_coordinates[1] + 1)
    set_navigation_encounter_policy(True)
    try:
        if _current_map() is MapRSE.MAUVILLE_CITY_HOUSE1:
            yield from _take_warp_to(MapRSE.MAUVILLE_CITY, timeout=timeout_frames)
        if get_party()[0].species.name in {"Treecko", "Grovyle"} and get_party()[0].level < 30:
            set_navigation_encounter_policy(True, True)
            training_map = MapRSE.ROUTE117
            while get_party()[0].level < 30:
                yield from heal_in_pokemon_center(PokemonCenter.MauvilleCity)
                yield from _leave_building_for(MapRSE.MAUVILLE_CITY, timeout=timeout_frames)
                route = get_map_data(training_map, (0, 0))
                encounter_tiles = []
                width, height = route.map_size
                for y in range(height):
                    for x in range(width):
                        if not get_map_data(training_map, (x, y)).has_encounters:
                            continue
                        try:
                            path = calculate_path(
                                get_player_location(),
                                (training_map, (x, y)),
                            )
                        except PathFindingError:
                            continue
                        encounter_tiles.append((len(path), (x, y)))
                if not encounter_tiles:
                    raise BotModeError("RSE-027 no reachable Route 117 training tile was found.")
                yield from navigate_to(training_map, min(encounter_tiles)[1])
                yield from spin(
                    stop_condition=lambda: (
                        get_party()[0].level >= 30
                        or get_party()[0].current_hp == 0
                        or _current_map() is not training_map
                    )
                )
            set_navigation_encounter_policy(True)
        for _attempt in range(40):
            yield from heal_in_pokemon_center(PokemonCenter.MauvilleCity)
            yield from _leave_building_for(MapRSE.MAUVILLE_CITY, timeout=timeout_frames)
            yield from _take_warp_to(MapRSE.MAUVILLE_CITY_GYM, timeout=timeout_frames)
            switches = [
                event.local_coordinates
                for event in reversed(gym.coord_events)
                if event.type == "script"
            ]
            if context.rom.is_emerald:
                switches_by_script = {
                    event.to_dict()["script"].rsplit("_", 1)[-1]: event.local_coordinates
                    for event in gym.coord_events
                    if event.type == "script"
                }
                switch1 = switches_by_script["Switch1"]
                switch2 = switches_by_script["Switch2"]
                switch3 = switches_by_script["Switch3"]
                yield from _walk_mauville_gym_axis("Up", 1, 17, timeout_frames=timeout_frames)
                yield from _walk_mauville_gym_axis("Left", 0, 2, timeout_frames=timeout_frames)
                yield from _walk_mauville_gym_axis("Up", 1, switch1[1], timeout_frames=timeout_frames)
                yield from _walk_mauville_gym_axis("Left", 0, switch1[0], timeout_frames=timeout_frames)
                yield from _wait_for_control(timeout=timeout_frames)
                yield from _walk_mauville_gym_axis("Right", 0, switch2[0], timeout_frames=timeout_frames)
                yield from _walk_mauville_gym_axis("Up", 1, switch2[1], timeout_frames=timeout_frames)
                yield from _wait_for_control(timeout=timeout_frames)
                yield from _walk_mauville_gym_axis("Up", 1, switch3[1], timeout_frames=timeout_frames)
                yield from _walk_mauville_gym_axis("Left", 0, switch3[0], timeout_frames=timeout_frames)
                yield from _wait_for_control(timeout=timeout_frames)
                yield from _walk_mauville_gym_axis(
                    "Right", 0, interaction_position[0], timeout_frames=timeout_frames
                )
                yield from _walk_mauville_gym_axis(
                    "Up", 1, interaction_position[1], timeout_frames=timeout_frames
                )
                yield from ensure_facing_direction("Up")
                context.emulator.press_button("A")
                for frame in range(timeout_frames):
                    if get_event_flag("BADGE03_GET"):
                        yield from _wait_for_control(timeout=timeout_frames)
                        return
                    if frame > 600 and _current_map() is not MapRSE.MAUVILLE_CITY_GYM and player_avatar_is_controllable():
                        break
                    if frame % 4 == 0:
                        context.emulator.press_button("A")
                    yield
                continue
            if len(switches) != 3:
                raise BotModeError(f"RSE-027 expected 3 electric switches, found {len(switches)}.")
            lower, right, left = switches
            yield from _walk_mauville_gym_axis("Up", 1, lower[1], timeout_frames=timeout_frames)
            yield from _wait_for_control(timeout=timeout_frames)
            yield from _walk_mauville_gym_axis("Up", 1, 12, timeout_frames=timeout_frames)
            yield from _walk_mauville_gym_axis("Right", 0, right[0], timeout_frames=timeout_frames)
            yield from _walk_mauville_gym_axis("Up", 1, right[1], timeout_frames=timeout_frames)
            yield from _wait_for_control(timeout=timeout_frames)
            yield from _walk_mauville_gym_axis("Up", 1, 10, timeout_frames=timeout_frames)
            yield from _walk_mauville_gym_axis("Left", 0, 4, timeout_frames=timeout_frames)
            yield from _walk_mauville_gym_axis("Down", 1, 12, timeout_frames=timeout_frames)
            yield from _walk_mauville_gym_axis("Left", 0, left[0], timeout_frames=timeout_frames)
            yield from _walk_mauville_gym_axis("Right", 0, 2, timeout_frames=timeout_frames)
            yield from _walk_mauville_gym_axis("Up", 1, left[1], timeout_frames=timeout_frames)
            yield from _walk_mauville_gym_axis("Left", 0, left[0], timeout_frames=timeout_frames)
            yield from _wait_for_control(timeout=timeout_frames)
            yield from _walk_mauville_gym_axis(
                "Right", 0, interaction_position[0], timeout_frames=timeout_frames
            )
            yield from _walk_mauville_gym_axis(
                "Up", 1, interaction_position[1], timeout_frames=timeout_frames
            )
            yield from ensure_facing_direction("Up")
            context.emulator.press_button("A")
            for frame in range(timeout_frames):
                if get_event_flag("BADGE03_GET"):
                    yield from _wait_for_control(timeout=timeout_frames)
                    return
                if frame > 600 and _current_map() is not MapRSE.MAUVILLE_CITY_GYM and player_avatar_is_controllable():
                    break
                if frame % 4 == 0:
                    context.emulator.press_button("A")
                yield
        raise BotModeError("RSE-027 Dynamo Badge was not obtained after 40 attempts.")
    finally:
        set_navigation_encounter_policy(False)


def run_rse_open_rusturf_tunnel(
    *, set_navigation_encounter_policy: Callable[..., None], timeout_frames: int = 40_000
) -> Generator:
    """Smash the Rusturf Tunnel barrier and receive HM04 Strength."""
    strength = get_item_by_name("HM04")
    if get_event_flag("RUSTURF_TUNNEL_OPENED") and get_item_bag().quantity_of(strength) > 0:
        yield from _wait_for_control(timeout=timeout_frames)
        return
    rock_smash_hm = get_item_by_name("HM06")
    if not get_event_flag("BADGE03_GET") or get_item_bag().quantity_of(rock_smash_hm) == 0:
        raise BotModeError("RSE-028 requires the Dynamo Badge and HM06 Rock Smash.")

    set_navigation_encounter_policy(True)
    try:
        if _current_map() is MapRSE.MAUVILLE_CITY_GYM:
            exit_x = 5 if context.rom.is_emerald else 4
            if context.rom.is_emerald:
                gym = get_map_data(MapRSE.MAUVILLE_CITY_GYM, (0, 0))
                switches = {
                    event.to_dict()["script"].rsplit("_", 1)[-1]: event.local_coordinates
                    for event in gym.coord_events
                    if event.type == "script"
                }
                switch1, switch2, switch3 = (
                    switches["Switch1"],
                    switches["Switch2"],
                    switches["Switch3"],
                )
                yield from _walk_mauville_gym_axis("Down", 1, switch3[1], timeout_frames=timeout_frames)
                yield from _walk_mauville_gym_axis("Left", 0, switch3[0], timeout_frames=timeout_frames)
                yield from _wait_for_control(timeout=timeout_frames)
                yield from _walk_mauville_gym_axis("Right", 0, switch2[0], timeout_frames=timeout_frames)
                yield from _walk_mauville_gym_axis("Down", 1, switch2[1], timeout_frames=timeout_frames)
                yield from _wait_for_control(timeout=timeout_frames)
                yield from _walk_mauville_gym_axis("Left", 0, switch1[0], timeout_frames=timeout_frames)
                yield from _walk_mauville_gym_axis("Down", 1, switch1[1], timeout_frames=timeout_frames)
                yield from _wait_for_control(timeout=timeout_frames)
                yield from _walk_mauville_gym_axis("Right", 0, 2, timeout_frames=timeout_frames)
                yield from _walk_mauville_gym_axis("Down", 1, 17, timeout_frames=timeout_frames)
                yield from _walk_mauville_gym_axis("Right", 0, exit_x, timeout_frames=timeout_frames)
            yield from _walk_mauville_gym_axis("Down", 1, 19, timeout_frames=timeout_frames)
            yield from _walk_mauville_gym_axis("Right", 0, exit_x, timeout_frames=timeout_frames)
            yield from _walk_through_warp(
                MapRSE.MAUVILLE_CITY_GYM,
                "Down",
                target_x=exit_x,
                timeout=timeout_frames,
            )
            yield from _wait_for_control(timeout=timeout_frames)
        yield from heal_in_pokemon_center(PokemonCenter.VerdanturfTown)
        yield from _leave_building_for(MapRSE.VERDANTURF_TOWN, timeout=timeout_frames)

        compatible_non_shiny = [
            (index, pokemon)
            for index, pokemon in enumerate(get_party())
            if index > 0 and not pokemon.is_shiny and pokemon.species.can_learn_tm_hm(rock_smash_hm)
        ]
        if not compatible_non_shiny:
            hm_support_species = "Marill" if context.rom.is_emerald else "Zigzagoon"
            party_size_before = len(get_party())
            route = get_map_data(MapRSE.ROUTE117, (0, 0))
            encounter_tiles = []
            width, height = route.map_size
            for y in range(height):
                for x in range(width):
                    if not get_map_data(MapRSE.ROUTE117, (x, y)).has_encounters:
                        continue
                    try:
                        path = calculate_path(get_player_location(), (MapRSE.ROUTE117, (x, y)))
                    except PathFindingError:
                        continue
                    encounter_tiles.append((len(path), (x, y)))
            if not encounter_tiles:
                raise BotModeError("RSE-028 no reachable Route 117 encounter tile was found.")
            set_navigation_encounter_policy(True, False, hm_support_species)
            yield from navigate_to(MapRSE.ROUTE117, min(encounter_tiles)[1])
            yield from spin(
                stop_condition=lambda: any(
                    pokemon.species.name == hm_support_species and not pokemon.is_shiny
                    for pokemon in get_party()
                )
            )
            if len(get_party()) <= party_size_before:
                raise BotModeError(
                    f"RSE-028 failed to catch a non-shiny {hm_support_species} for HM support."
                )
            set_navigation_encounter_policy(True)

        if not any(
            move is not None and move.move.name == "Rock Smash"
            for pokemon in get_party()
            for move in pokemon.moves
        ):
            party_index = next(
                index
                for index, pokemon in enumerate(get_party())
                if index > 0 and not pokemon.is_shiny and pokemon.species.can_learn_tm_hm(rock_smash_hm)
            )
            if party_index is None:
                raise BotModeError("RSE-028 has no party Pokémon compatible with HM06 Rock Smash.")
            yield from teach_hm_or_tm(rock_smash_hm, party_index)
            yield from _wait_for_control(timeout=timeout_frames)
            if not any(
                move is not None and move.move.name == "Rock Smash"
                for pokemon in get_party()
                for move in pokemon.moves
            ):
                party_moves = [
                    (pokemon.species.name, [move.move.name if move is not None else None for move in pokemon.moves])
                    for pokemon in get_party()
                ]
                raise BotModeError(f"RSE-028 HM06 teaching returned without Rock Smash learned: {party_moves}.")

        if _current_map() is not MapRSE.VERDANTURF_TOWN:
            yield from heal_in_pokemon_center(PokemonCenter.VerdanturfTown)
            yield from _leave_building_for(MapRSE.VERDANTURF_TOWN, timeout=timeout_frames)
        yield from _take_warp_to(MapRSE.RUSTURF_TUNNEL, timeout=timeout_frames)
        tunnel = get_map_data(MapRSE.RUSTURF_TUNNEL, (0, 0))
        rock = next(
            object_template
            for object_template in tunnel.objects
            if object_template.to_dict()["flag"] == "HIDE_RUSTURF_TUNNEL_ROCK_1"
        )
        rock_x, rock_y = rock.local_coordinates
        reachable = []
        for coordinates, direction in (
            ((rock_x - 1, rock_y), "Right"),
            ((rock_x + 1, rock_y), "Left"),
            ((rock_x, rock_y - 1), "Down"),
            ((rock_x, rock_y + 1), "Up"),
        ):
            try:
                path = calculate_path(
                    get_player_location(),
                    (MapRSE.RUSTURF_TUNNEL, coordinates),
                )
            except PathFindingError:
                continue
            reachable.append((len(path), coordinates, direction))
        if not reachable:
            raise BotModeError("RSE-028 no reachable tile adjacent to the tunnel rock was found.")
        _, interaction_position, facing = min(reachable)
        yield from navigate_to(MapRSE.RUSTURF_TUNNEL, interaction_position)
        yield from ensure_facing_direction(facing)
        yield from use_field_move("Rock Smash")
        for frame in range(timeout_frames):
            if (
                get_event_flag("RUSTURF_TUNNEL_OPENED")
                and get_item_bag().quantity_of(strength) > 0
                and player_avatar_is_controllable()
            ):
                yield from _wait_for_control(timeout=timeout_frames)
                return
            if frame % 4 == 0:
                context.emulator.press_button("A")
            yield
        raise BotModeError(
            "RSE-028 tunnel completion was not observed: "
            f"opened={get_event_flag('RUSTURF_TUNNEL_OPENED')} "
            f"hm04={get_item_bag().quantity_of(strength)}."
        )
    finally:
        set_navigation_encounter_policy(False)
