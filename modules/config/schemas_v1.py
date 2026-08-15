"""Contains default schemas for configuration files."""

from __future__ import annotations

from typing import Literal

from confz import BaseConfig
from pydantic import Field
from pydantic.types import Annotated, ClassVar, NonNegativeInt, PositiveInt


class Battle(BaseConfig):
    """Schema for the catch_block configuration."""

    filename: ClassVar = "battle.yml"
    auto_catch: bool = True
    save_after_catching: bool = False
    pickup: bool = True
    pickup_threshold: Annotated[int, Field(gt=0, lt=7)] = 1
    pickup_check_frequency: Annotated[int, Field(gt=0)] = 5
    hp_threshold: Annotated[float, Field(ge=0, le=100)] = 20
    lead_cannot_battle_action: Literal["stop", "flee", "rotate"] = "flee"
    faint_action: Literal["stop", "flee", "rotate"] = "flee"
    new_move: Literal["stop", "cancel", "learn_best"] = "stop"
    stop_evolution: bool = True
    switch_strategy: Literal["first_available", "lowest_level"] = "first_available"
    banned_moves: list[str] = [
        "None",
        # 2-turn
        "Bounce",
        "Dig",
        "Dive",
        "Fly",
        "Sky Attack",
        "Razor Wind",
        "Doom Desire",
        "Solar Beam",
        # Inconsistent
        "Fake Out",
        "False Swipe",
        "Nature Power",
        "Present",
        "Destiny Bond",
        "Wrap",
        "Snore",
        "Spit Up",
        "Bide",
        "Bind",
        "Counter",
        "Future Sight",
        "Mirror Coat",
        "Grudge",
        "Snatch",
        "Spite",
        "Curse",
        "Endeavor",
        "Revenge",
        "Assist",
        "Focus Punch",
        "Eruption",
        "Flail",
        # Ends battle
        "Roar",
        "Whirlwind",
        "Selfdestruct",
        "Perish Song",
        "Explosion",
        "Memento",
    ]
    avoided_pokemon: list[str] = []
    targeted_pokemon: list[str] = []


class CatchBlock(BaseConfig):
    """Schema for the catch_block configuration."""

    filename: ClassVar = "catch_block.yml"
    block_list: list[str] = ["MissingNo"]


class Cheats(BaseConfig):
    """Schema for the cheat configuration."""

    filename: ClassVar = "cheats.yml"
    random_soft_reset_rng: bool = False
    faster_pickup: bool = False


class Dashboard(BaseConfig):
    """Read-only Living Dex dashboard."""

    filename: ClassVar = "dashboard.yml"
    enable: bool = True
    host: str = "0.0.0.0"
    port: Annotated[int, Field(gt=0, lt=65536)] = 8888
    expose_trainer_ids: bool = True
    expose_paths: bool = True


class LivingDexGameplay(BaseConfig):
    progression: Literal["area"] = "area"
    starter: Literal["Treecko", "Torchic", "Mudkip"] = "Mudkip"
    fossil: Literal["Root Fossil", "Claw Fossil"] = "Root Fossil"
    founder_min_iv_sum: Annotated[int, Field(ge=0, le=186)] = 93


class LivingDexQuality(BaseConfig):
    shiny: bool = True
    perfect_ivs: bool = True


class LivingDexRecovery(BaseConfig):
    mode: Literal["rollback"] = "rollback"
    max_attempts: Annotated[int, Field(gt=0, le=10)] = 3


class LivingDexRng(BaseConfig):
    mode: Literal["disabled", "predictive"] = "disabled"
    targets: list[Literal["wild", "static", "starter"]] = ["wild", "static", "starter"]


class LivingDexRTC(BaseConfig):
    mode: Literal["historical_wallclock"] = "historical_wallclock"
    ruby_sapphire_epoch: str = "2003-08-25"
    emerald_epoch: str = "2005-11-21"


class LivingDexTransfer(BaseConfig):
    gen4_game: Literal["Diamond", "Pearl"] = "Diamond"
    pal_park_date: str = "2007-08-27"


class LivingDex(BaseConfig):
    """Living Dex automation configuration shared by R/S/E profiles."""

    filename: ClassVar = "living_dex.yml"
    gameplay: LivingDexGameplay = Field(default_factory=LivingDexGameplay)
    quality: LivingDexQuality = Field(default_factory=LivingDexQuality)
    duplicates: Literal["keep_until_full"] = "keep_until_full"
    recovery: LivingDexRecovery = Field(default_factory=LivingDexRecovery)
    rtc: LivingDexRTC = Field(default_factory=LivingDexRTC)
    rng: LivingDexRng = Field(default_factory=LivingDexRng)
    transfer: LivingDexTransfer = Field(default_factory=LivingDexTransfer)
    distributions_directory: str = "distributions"


class Keys(BaseConfig):
    """Schema for GBA key configuration."""

    filename: ClassVar = "keys.yml"
    gba: KeysGBA = Field(default_factory=lambda: KeysGBA())
    emulator: KeysEmulator = Field(default_factory=lambda: KeysEmulator())


class KeysEmulator(BaseConfig):
    """Schema for the emulator keys section in the Keys config."""

    zoom_in: str = "plus"
    zoom_out: str = "minus"
    toggle_manual: str = "Tab"
    toggle_video: str = "v"
    toggle_audio: str = "b"
    set_speed_1x: str = "1"
    set_speed_2x: str = "2"
    set_speed_3x: str = "3"
    set_speed_4x: str = "4"
    set_speed_8x: str = "5"
    set_speed_16x: str = "6"
    set_speed_32x: str = "7"
    set_speed_unthrottled: str = "0"
    reset: str = "Ctrl+R"
    reload_config: str = "Ctrl+C"
    exit: str = "Ctrl+Q"
    save_state: str = "Ctrl+S"
    load_state: str = "Ctrl+L"
    toggle_stepping_mode: str = "Ctrl+P"
    screenshot: str = "F12"


class KeysGBA(BaseConfig):
    """Schema for the GBA keys section in the Keys config."""

    Up: str = "Up"
    Down: str = "Down"
    Left: str = "Left"
    Right: str = "Right"
    A: str = "x"
    B: str = "z"
    L: str = "a"
    R: str = "s"
    Start: str = "Return"
    Select: str = "BackSpace"


class Logging(BaseConfig):
    """Schema for the logging configuration."""

    filename: ClassVar = "logging.yml"
    save_pk3: LoggingSavePK3 = Field(default_factory=lambda: LoggingSavePK3())
    create_save_state_for_shiny: bool = True
    log_encounters: bool = False
    log_encounters_to_console: bool = True
    desktop_notifications: bool = True


class LoggingSavePK3(BaseConfig):
    """Schema for the save_pk3 section in the Logging config."""

    shiny: bool = True
    custom: bool = True
    roamer: bool = True


class ProfileMetadata(BaseConfig):
    """Schema for the metadata configuration file part of profiles."""

    filename: ClassVar = "metadata.yml"
    version: PositiveInt = 1
    rom: ProfileMetadataROM = Field(default_factory=lambda: ProfileMetadataROM())


class ProfileMetadataROM(BaseConfig):
    """Schema for the rom section of the metadata config."""

    file_name: str = ""
    game_code: str = ""
    revision: NonNegativeInt = 0
    language: Literal["E", "F", "D", "I", "J", "S"] = ""
