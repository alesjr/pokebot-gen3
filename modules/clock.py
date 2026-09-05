from dataclasses import dataclass
from typing import Generator

from modules.context import context
from modules.memory import (
    get_event_flag,
    get_game_state_symbol,
    get_save_block,
    read_symbol,
    unpack_uint16,
)
from modules.map_data import MapRSE
from modules.modes._interface import BotModeError
from modules.modes.util import (
    ensure_facing_direction,
    navigate_to,
    wait_for_player_avatar_to_be_controllable,
    walk_through_warp,
)
from modules.player import (
    get_player_avatar,
    get_player_house_maps,
    get_player_location,
    player_avatar_is_controllable,
)
from modules.tasks import get_global_script_context, get_task


@dataclass
class ClockTime:
    days: int
    hours: int
    minutes: int
    seconds: int

    def __str__(self):
        return f"{self.days} day{'s' if self.days != 1 else ''}, {self.hours:02d}:{self.minutes:02d}:{self.seconds:02d}"

    def total_minutes(self) -> int:
        return self.days * 24 * 60 + self.hours * 60 + self.minutes


def get_clock_time() -> ClockTime:
    """
    Returns the in-game time that clock events are based on. This clock is based on
    the GBA's/emulator's real-time clock, which in this bot is tied to the actual
    system clock.

    So regardless of the speed multiplier, this time will always advance in real time.

    :return: The current clock time as reported by the game. Note that the game does
             not update this value all the time, so it is normal for it to return the
             same value when called multiple times within a couple of seconds.
    """

    # There is no RTC-based clock in FR/LG.
    if context.rom.is_frlg:
        return ClockTime(0, 0, 0, 0)

    data = read_symbol("gLocalTime")
    return ClockTime(unpack_uint16(data[0:2]), data[2], data[3], data[4])


def set_clock(*, timeout_frames: int = 20_000) -> Generator:
    """Set RSE wall clock after player is positioned in front of it."""
    if get_event_flag("SET_WALL_CLOCK"):
        return

    targeted_tile = get_player_avatar().map_location_in_front
    clock_locations = {
        (MapRSE.LITTLEROOT_TOWN_BRENDANS_HOUSE_2F.value, (5, 1)),
        (MapRSE.LITTLEROOT_TOWN_MAYS_HOUSE_2F.value, (5, 1)),
    }
    if targeted_tile is None or (
        (targeted_tile.map_group, targeted_tile.map_number),
        targeted_tile.local_position,
    ) not in clock_locations:
        raise BotModeError("The player is not facing the bedroom clock.")

    confirm_positioned = False
    callbacks = {"CB2_WALLCLOCK", "WALLCLOCKMAINCALLBACK"}
    for frame in range(timeout_frames):
        if get_event_flag("SET_WALL_CLOCK"):
            while get_global_script_context().is_active or not player_avatar_is_controllable():
                yield
            return
        if get_game_state_symbol() in callbacks:
            input_task = get_task("Task_SetClock_HandleInput") or get_task("Task_SetClock2")
            confirm_task = get_task("Task_SetClock_HandleConfirmInput") or get_task("Task_SetClock4")
            if input_task is not None and input_task.data_value(0) % 6 == 0:
                confirm_positioned = False
                context.emulator.press_button("A")
            elif confirm_task is not None:
                context.emulator.press_button("A" if confirm_positioned else "Up")
                confirm_positioned = True
        elif frame % 4 == 0:
            context.emulator.press_button("A")
        yield
    raise BotModeError("Clock setup timed out before SET_WALL_CLOCK.")


def reach_bedroom_clock(trainer_gender: str) -> Generator:
    if get_event_flag("SET_WALL_CLOCK"):
        return
    first_floor, second_floor = get_player_house_maps(trainer_gender)
    callbacks = {"CB2_WALLCLOCK", "WALLCLOCKMAINCALLBACK"}
    if get_game_state_symbol() in callbacks:
        return

    yield from wait_for_player_avatar_to_be_controllable(
        "B", stable_frames=120, wait_for_no_script=True, timeout_frames=4_000
    )
    current_map = get_player_location()[0]
    if current_map is MapRSE.INSIDE_OF_TRUCK:
        yield from navigate_to(MapRSE.INSIDE_OF_TRUCK, (4, 2), True, True, True, True)
        yield from wait_for_player_avatar_to_be_controllable(
            "B", stable_frames=120, wait_for_no_script=True, timeout_frames=4_000
        )
        current_map = get_player_location()[0]
    if current_map is MapRSE.LITTLEROOT_TOWN:
        yield from walk_through_warp(current_map, "Up")
        yield from wait_for_player_avatar_to_be_controllable(
            "B", stable_frames=120, wait_for_no_script=True, timeout_frames=4_000
        )
        current_map = get_player_location()[0]
    if current_map is first_floor:
        yield from walk_through_warp(first_floor, "Up", timeout_frames=4_000)
        yield from wait_for_player_avatar_to_be_controllable(
            "B", stable_frames=120, wait_for_no_script=True, timeout_frames=4_000
        )
        current_map = get_player_location()[0]
    if current_map is not second_floor:
        raise BotModeError(f"Clock setup cannot recover from map: {current_map.name}")
    yield from navigate_to(second_floor, (5, 2))
    yield from ensure_facing_direction("Up")


@dataclass
class PlayTime:
    hours: int
    minutes: int
    seconds: int
    frames: int

    def __str__(self):
        return f"{self.hours:02d}:{self.minutes:02d}:{self.seconds:02d} +{self.frames} frames"


def get_play_time() -> PlayTime:
    """
    Returns the play time counter. This gets advanced every frame and so is tied to
    the emulation speed as well.

    It's the time the game will display on the trainer card, while saving, etc.

    :return: Time played as reported by the game. This has a maximum value of 999 days,
             59 minutes, 59 seconds, and 59 frames. Once that value is reached, this
             time will not advance anymore.
    """
    save_block_time = get_save_block(2, offset=0x0E, size=0x5)
    return PlayTime(unpack_uint16(save_block_time[0:2]), save_block_time[2], save_block_time[3], save_block_time[4])
