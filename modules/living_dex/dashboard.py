from __future__ import annotations

from datetime import datetime
from queue import Queue

from modules.clock import get_clock_time
from modules.context import context
from modules.living_dex.collection import CollectionSnapshot
from modules.living_dex.observability import runtime_events
from modules.living_dex.progress import LivingDexProgress
from modules.living_dex.quests import quest_snapshot
from modules.main import work_queue
from modules.player import get_player
from modules.pokedex import get_pokedex
from modules.pokemon import get_species_by_national_dex
from modules.pokemon_party import get_party
from modules.pokemon_storage import get_pokemon_storage


def _build_snapshot() -> dict:
    profile = context.profile.path
    player = get_player()
    pokedex = get_pokedex()
    storage = get_pokemon_storage()
    collection = CollectionSnapshot.from_storage(storage)
    progress = LivingDexProgress.load(profile)
    seen = {s.national_dex_number for s in pokedex.seen_species}
    owned = {s.national_dex_number for s in pokedex.owned_species}
    collected = collection.keys()
    species = []
    for number in range(1, 387):
        item = get_species_by_national_dex(number)
        variants = sorted(entry.variant for entry in collection.collected if entry.national_dex_number == number)
        species.append({
            "number": number,
            "name": item.name,
            "seen": number in seen,
            "owned": number in owned,
            "qualified": any(key[0] == item.name for key in collected),
            "variants": variants,
        })
    clock = get_clock_time()
    party = get_party()
    runtime = runtime_events()
    last_encounter = context.stats.last_encounter
    speed = context.emulation_speed
    runtime.update(
        {
            "status": "running",
            "bot_mode": context.bot_mode,
            "headless": not context.video,
            "video": context.video,
            "audio": context.audio,
            "speed": speed,
            "speed_label": "máxima" if speed == 0 else f"{speed:g}×",
            "host_frame": context.frame,
            "emulator_frame": context.emulator.get_frame_count(),
            "controller": (
                context.controller_stack[-1].__qualname__ if len(context.controller_stack) > 0 else None
            ),
            "last_encounter": (
                None
                if last_encounter is None
                else {
                    "species": last_encounter.species_name,
                    "level": last_encounter.pokemon.level,
                    "shiny": last_encounter.is_shiny,
                    "shiny_value": last_encounter.shiny_value,
                    "iv_sum": last_encounter.iv_sum,
                    "map": last_encounter.map,
                    "time": last_encounter.encounter_time.isoformat(),
                    "bot_mode": last_encounter.bot_mode,
                }
            ),
        }
    )
    if context.video_stream is not None:
        video = context.video_stream.stats()
        runtime["video_stream"] = {
            "subscribers": video.subscribers,
            "captured_frames": video.captured_frames,
            "encoded_frames": video.encoded_frames,
            "dropped_frames": video.dropped_frames,
        }
    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "game": context.rom.game_name,
        "profile": profile.name,
        "trainer": {"name": player.name, "tid": player.trainer_id, "sid": player.secret_id},
        "paths": {
            "profile": str(profile.resolve()),
            "save": str((profile / "current_save.sav").resolve()),
            "rom": str(context.rom.file.resolve()),
        },
        "rtc": {"days": clock.days, "hours": clock.hours, "minutes": clock.minutes, "seconds": clock.seconds},
        "runtime": runtime,
        "progress": {
            "objective": progress.current_objective,
            "founder": progress.founder_species,
            "starter_stored": progress.starter_stored,
            "qualified": len(collection.collected),
            "box_used": collection.pokemon_count,
            "box_capacity": collection.capacity,
            "missions": context.stats.get_living_dex_mission_summary(),
        },
        "party": party.to_list(),
        "boxes": storage.to_dict(),
        "quests": quest_snapshot(),
        "pokedex": species,
    }


def snapshot_via_main_thread(timeout: float = 3.0) -> dict:
    result: Queue = Queue(maxsize=1)

    def callback() -> None:
        try:
            result.put((True, _build_snapshot()))
        except Exception as error:
            result.put((False, str(error)))

    work_queue.put(callback)
    try:
        ok, value = result.get(timeout=timeout)
    except Exception:
        return {"error": "emulator did not answer", "runtime": runtime_events(), "pokedex": [], "quests": []}
    return value if ok else {"error": value, "runtime": runtime_events(), "pokedex": [], "quests": []}
