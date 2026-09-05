from typing import Generator

from modules.context import context
from modules.debug import debug
from modules.files import get_rng_state_history, save_rng_state_history
from modules.memory import pack_uint32, read_symbol, unpack_uint32, write_symbol


RNG_MULTIPLIER = 0x41C64E6D
RNG_INCREMENT = 0x6073
RNG_MASK = 0xFFFF_FFFF


def read_rng_value() -> int:
    return unpack_uint32(read_symbol("gRngValue"))


def calculate_next_rng_value(rng_value: int, advances: int = 1) -> int:
    if advances < 0:
        raise ValueError("advances must not be negative")
    rng_value &= RNG_MASK
    for _ in range(advances):
        rng_value = (RNG_MULTIPLIER * rng_value + RNG_INCREMENT) & RNG_MASK
    return rng_value


def advance_rng(advances: int = 1) -> int:
    rng_value = calculate_next_rng_value(read_rng_value(), advances)
    write_symbol("gRngValue", pack_uint32(rng_value))
    return rng_value


@debug.track
def wait_for_unique_rng_value(max_frames: int | None = None) -> Generator:
    """Wait until the live RNG value has not been used by this profile."""
    rng_history = get_rng_state_history()
    rng_value = read_rng_value()

    context.message = "Waiting for a unique frame before continuing..."
    frames_waited = 0
    while rng_value in rng_history:
        if max_frames is not None and frames_waited >= max_frames:
            context.message = ""
            return False
        if context.config.cheats.random_soft_reset_rng:
            rng_value = advance_rng()
        else:
            rng_value = read_rng_value()
            frames_waited += 1
            yield
    context.message = ""

    rng_history.add(rng_value)
    save_rng_state_history(rng_history)
    return True
