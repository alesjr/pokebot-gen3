from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generator

from modules.context import context
from modules.items import get_item_bag, get_item_by_name
from modules.living_dex.rse_missions import RSE_MISSION_CLASSES, RSEMission
from modules.memory import get_event_flag, get_event_var
from modules.modes._interface import BotModeError


CompletionCheck = Callable[[], bool]


@dataclass(frozen=True)
class RSEMissionDefinition:
    mission_id: str
    title: str
    completion: CompletionCheck
    handles_navigation_encounters: bool = False

    def is_complete(self) -> bool:
        return self.completion()


def _flag(name: str) -> CompletionCheck:
    return lambda: get_event_flag(name)


def _var_at_least(name: str, value: int) -> CompletionCheck:
    return lambda: get_event_var(name) >= value


def _has_item(name: str) -> CompletionCheck:
    return lambda: get_item_bag().quantity_of(get_item_by_name(name)) > 0


def _petalburg_state() -> str:
    return "PETALBURG_CITY_STATE" if context.rom.is_emerald else "PETALBURG_STATE"


RSE_CAMPAIGN: tuple[RSEMissionDefinition, ...] = (
    RSEMissionDefinition("RSE-001", "Set bedroom clock", _flag("SET_WALL_CLOCK")),
    RSEMissionDefinition("RSE-002", "Meet rival", _var_at_least("LITTLEROOT_RIVAL_STATE", 3)),
    RSEMissionDefinition("RSE-003", "Obtain configured shiny starter", _flag("SYS_POKEMON_GET")),
    RSEMissionDefinition("RSE-004", "Defeat Route 103 rival", _flag("DEFEATED_RIVAL_ROUTE103"), True),
    RSEMissionDefinition("RSE-005", "Receive Pokédex and Poké Balls", _flag("SYS_POKEDEX_GET")),
    RSEMissionDefinition("RSE-006", "Receive Running Shoes", _flag("RECEIVED_RUNNING_SHOES")),
    RSEMissionDefinition("RSE-007", "Meet Norman in Petalburg Gym", lambda: get_event_var(_petalburg_state()) > 0, True),
    RSEMissionDefinition("RSE-008", "Complete Wally catching tutorial", lambda: get_event_var(_petalburg_state()) >= 3),
    RSEMissionDefinition("RSE-009", "Defeat villain in Petalburg Woods", _var_at_least("PETALBURG_WOODS_STATE", 1), True),
    RSEMissionDefinition("RSE-010", "Reach Rustboro City", _flag("VISITED_RUSTBORO_CITY"), True),
    RSEMissionDefinition("RSE-011", "Defeat Roxanne", _flag("BADGE01_GET"), True),
    RSEMissionDefinition("RSE-012", "Start Devon Goods case", _flag("DEVON_GOODS_STOLEN")),
    RSEMissionDefinition("RSE-013", "Recover Devon Goods", _flag("RECOVERED_DEVON_GOODS"), True),
    RSEMissionDefinition("RSE-014", "Return Devon Goods", _flag("RETURNED_DEVON_GOODS"), True),
    RSEMissionDefinition("RSE-015", "Receive PokéNav and Steven letter", _flag("SYS_POKENAV_GET")),
    RSEMissionDefinition("RSE-016", "Sail to Dewford", _flag("VISITED_DEWFORD_TOWN"), True),
    RSEMissionDefinition("RSE-017", "Receive HM05 Flash", _has_item("HM05"), True),
    RSEMissionDefinition("RSE-018", "Deliver Steven letter", _flag("DELIVERED_STEVEN_LETTER"), True),
    RSEMissionDefinition("RSE-019", "Defeat Brawly", _flag("BADGE02_GET"), True),
    RSEMissionDefinition("RSE-020", "Sail to Slateport", _flag("VISITED_SLATEPORT_CITY"), True),
    RSEMissionDefinition("RSE-021", "Talk to Dock", _flag("DOCK_REJECTED_DEVON_GOODS")),
    RSEMissionDefinition("RSE-022", "Deliver Devon Goods", _flag("DELIVERED_DEVON_GOODS"), True),
    RSEMissionDefinition("RSE-023", "Defeat Route 110 rival", _var_at_least("ROUTE110_STATE", 1), True),
    RSEMissionDefinition("RSE-024", "Reach Mauville", _flag("VISITED_MAUVILLE_CITY"), True),
    RSEMissionDefinition("RSE-025", "Defeat Wally", _flag("DEFEATED_WALLY_MAUVILLE"), True),
    RSEMissionDefinition("RSE-026", "Receive HM06 Rock Smash", _has_item("HM06")),
    RSEMissionDefinition("RSE-027", "Defeat Wattson", _flag("BADGE03_GET"), True),
    RSEMissionDefinition("RSE-028", "Open Rusturf Tunnel", _flag("RUSTURF_TUNNEL_OPENED"), True),
)


class RSEMissionController:
    """Selects next mission exclusively from current cartridge state."""

    def __init__(
        self,
        *,
        set_navigation_encounter_policy: Callable[..., None],
        mission_factory: Callable[[type[RSEMission]], RSEMission] | None = None,
        campaign: tuple[RSEMissionDefinition, ...] = RSE_CAMPAIGN,
    ):
        self._set_navigation_encounter_policy = set_navigation_encounter_policy
        self._mission_factory = mission_factory or (lambda mission_class: mission_class())
        self._campaign = campaign

    def next_mission(self) -> RSEMissionDefinition | None:
        return next((mission for mission in self._campaign if not mission.is_complete()), None)

    def run_next(self) -> Generator:
        definition = self.next_mission()
        if definition is None:
            return
        mission_class = RSE_MISSION_CLASSES[definition.mission_id]
        mission = self._mission_factory(mission_class)
        options = {}
        if definition.handles_navigation_encounters:
            options["set_navigation_encounter_policy"] = self._set_navigation_encounter_policy
        yield from mission.run(**options)
        if not definition.is_complete():
            raise BotModeError(f"{definition.mission_id} returned without satisfying its save-state completion check.")
