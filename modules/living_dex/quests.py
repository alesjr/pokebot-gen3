from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Quest:
    key: str
    name: str
    flag: str | None


QUESTS = (
    Quest("adventure_started", "Start the adventure", "ADVENTURE_STARTED"),
    Quest("clock", "Set the bedroom clock", "SET_WALL_CLOCK"),
    Quest("birch", "Rescue Professor Birch", "RESCUED_BIRCH"),
    Quest("rival_103", "Defeat the rival on Route 103", "DEFEATED_RIVAL_ROUTE103"),
    Quest("badge_1", "Stone Badge", "BADGE01_GET"),
    Quest("badge_2", "Knuckle Badge", "BADGE02_GET"),
    Quest("badge_3", "Dynamo Badge", "BADGE03_GET"),
    Quest("badge_4", "Heat Badge", "BADGE04_GET"),
    Quest("badge_5", "Balance Badge", "BADGE05_GET"),
    Quest("badge_6", "Feather Badge", "BADGE06_GET"),
    Quest("badge_7", "Mind Badge", "BADGE07_GET"),
    Quest("badge_8", "Rain Badge", "BADGE08_GET"),
)


def read_quest_status(get_flag) -> list[dict]:
    result = []
    previous_complete = True
    for quest in QUESTS:
        try:
            complete = bool(quest.flag and get_flag(quest.flag))
        except (KeyError, RuntimeError):
            complete = False
        status = "completed" if complete else ("current" if previous_complete else "locked")
        result.append({"key": quest.key, "name": quest.name, "status": status})
        previous_complete = previous_complete and complete
    return result


def quest_snapshot() -> list[dict]:
    from modules.memory import get_event_flag

    return [
        {**item, "done": item["status"] == "completed"}
        for item in read_quest_status(get_event_flag)
    ]
