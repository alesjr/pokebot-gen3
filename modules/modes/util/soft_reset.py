import random
from typing import Generator

from modules.context import context
from modules.debug import debug
from modules.memory import GameState, get_game_state, read_symbol
from modules.rng_manipulation import wait_for_unique_rng_value
from .tasks_scripts import wait_for_task_to_start_and_finish
from .walking import wait_for_player_avatar_to_be_controllable


@debug.track
def soft_reset(mash_random_keys: bool = True) -> Generator:
    """
    Soft-resets the emulation. This only works if there is a save game, otherwise it will
    get stuck in the main menu.
    :param mash_random_keys: Whether to press random keys while on the title screen, which
                             will advance the RNG value and so result in unique RNG values
                             faster (on FRLG.)
    """
    context.emulator.reset()
    yield

    was_in_title_screen = False
    while True:
        match get_game_state():
            case GameState.TITLE_SCREEN:
                was_in_title_screen = True
                if mash_random_keys:
                    context.emulator.press_button(random.choice(["A", "Start", "Left", "Right", "Up"]))
            case GameState.MAIN_MENU:
                context.emulator.press_button("A")
            case GameState.QUEST_LOG:
                context.emulator.press_button("B")
            case GameState.OVERWORLD:
                if was_in_title_screen:
                    if context.rom.is_frlg:
                        while read_symbol("gQuestLogState") != b"\x00":
                            context.emulator.press_button("B")
                            yield
                        yield from wait_for_task_to_start_and_finish("Task_EndQuestLog", "B")
                    yield from wait_for_player_avatar_to_be_controllable()
                    return

        yield
