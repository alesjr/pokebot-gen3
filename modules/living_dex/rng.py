from __future__ import annotations

from dataclasses import dataclass


MULTIPLIER = 0x41C64E6D
INCREMENT = 0x6073
MASK = 0xFFFFFFFF


def advance(seed: int) -> int:
    return (seed * MULTIPLIER + INCREMENT) & MASK


def rand16(seed: int) -> tuple[int, int]:
    next_seed = advance(seed)
    return next_seed, next_seed >> 16


@dataclass(frozen=True)
class Method1Frame:
    advance: int
    seed: int
    pid: int
    ivs: tuple[int, int, int, int, int, int]

    def is_shiny(self, trainer_id: int, secret_id: int) -> bool:
        return (trainer_id ^ secret_id ^ (self.pid & 0xFFFF) ^ (self.pid >> 16)) < 8

    @property
    def is_perfect(self) -> bool:
        return all(value == 31 for value in self.ivs)


def method1_frame(seed: int, frame: int = 0) -> Method1Frame:
    current = seed
    for _ in range(frame):
        current = advance(current)
    origin = current
    current, low = rand16(current)
    current, high = rand16(current)
    pid = (high << 16) | low
    current, iv1 = rand16(current)
    current, iv2 = rand16(current)
    ivs = (
        iv1 & 31,
        (iv1 >> 5) & 31,
        (iv1 >> 10) & 31,
        (iv2 >> 5) & 31,
        (iv2 >> 10) & 31,
        iv2 & 31,
    )
    return Method1Frame(frame, origin, pid, ivs)


def find_method1_target(seed: int, trainer_id: int, secret_id: int, limit: int = 100_000) -> Method1Frame | None:
    current = seed
    for frame in range(limit):
        result = method1_frame(current)
        if result.is_shiny(trainer_id, secret_id) or result.is_perfect:
            return Method1Frame(frame, result.seed, result.pid, result.ivs)
        current = advance(current)
    return None


def read_current_seed() -> int:
    """Read RSE RNG state. Predictor never writes emulator memory."""
    from modules.memory import read_symbol, unpack_uint32

    return unpack_uint32(read_symbol("gRngValue", size=4))


def predict_current(trainer_id: int, secret_id: int, limit: int = 100_000) -> Method1Frame | None:
    return find_method1_target(read_current_seed(), trainer_id, secret_id, limit)
