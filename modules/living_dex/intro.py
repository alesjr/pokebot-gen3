from __future__ import annotations

from typing import Generator

from modules.context import context
from modules.keyboard import get_naming_screen_data, type_in_naming_screen
from modules.memory import GameState, game_has_started, get_game_state
from modules.modes._interface import BotModeError
from modules.player import get_player


def run_new_game_intro(
    trainer_name: str,
    trainer_gender: str,
    *,
    timeout_frames: int = 30_000,
) -> Generator:
    """Boot a save-less English Gen III ROM through its deterministic intro."""
    if trainer_gender != "male":
        raise BotModeError("Automated new-game intro currently supports male trainer only.")
    if not trainer_name or len(trainer_name) > 7:
        raise BotModeError("Gen III trainer name must contain 1 to 7 characters.")

    naming: Generator | None = None
    for frame in range(timeout_frames):
        if game_has_started():
            player = get_player()
            if player.name != trainer_name or player.gender != trainer_gender:
                raise BotModeError(
                    f"New-game identity mismatch: expected {trainer_name}/{trainer_gender}, "
                    f"observed {player.name}/{player.gender}."
                )
            return

        state = get_game_state()
        if state is GameState.NAMING_SCREEN and get_naming_screen_data() is not None:
            naming = naming or type_in_naming_screen(trainer_name, max_length=7)
            try:
                next(naming)
            except StopIteration:
                naming = None
        elif frame % 4 == 0:
            # With no save, New Game and the configured male avatar are default
            # selections in all five supported English ROMs.
            context.emulator.press_button("A")
        yield

    raise BotModeError(f"New-game intro did not finish within {timeout_frames} frames.")
