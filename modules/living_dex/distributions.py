"""Validation boundary for user-supplied official Gen III distribution ROMs."""

from __future__ import annotations

import binascii
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DistributionDump:
    path: Path
    game_code: str
    language: str
    crc32: str


class InvalidDistributionDump(ValueError):
    pass


def inspect_distribution(path: Path) -> DistributionDump:
    """Validate GBA header/checksum. Does not fetch or bundle copyrighted dumps."""
    data = path.read_bytes()
    if len(data) < 0xC0 or len(data) % 0x1000:
        raise InvalidDistributionDump("invalid GBA ROM size")
    if data[0xB2] != 0x96:
        raise InvalidDistributionDump("invalid GBA fixed header byte")
    checksum = (-(sum(data[0xA0:0xBD]) + 0x19)) & 0xFF
    if checksum != data[0xBD]:
        raise InvalidDistributionDump("invalid GBA header checksum")
    code = data[0xAC:0xB0].decode("ascii", errors="strict")
    return DistributionDump(
        path=path.resolve(),
        game_code=code,
        language=code[-1],
        crc32=f"{binascii.crc32(data) & 0xFFFFFFFF:08X}",
    )


def validate_distribution(path: Path, allowed_crc32: set[str], game_codes: set[str], language: str) -> DistributionDump:
    dump = inspect_distribution(path)
    if dump.game_code not in game_codes:
        raise InvalidDistributionDump(f"unexpected game code: {dump.game_code}")
    if dump.language != language:
        raise InvalidDistributionDump(f"unexpected language: {dump.language}")
    if dump.crc32 not in {value.upper() for value in allowed_crc32}:
        raise InvalidDistributionDump(f"unapproved checksum: {dump.crc32}")
    return dump
