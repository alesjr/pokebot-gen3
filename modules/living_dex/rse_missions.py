from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generator

from modules.context import context
from modules.living_dex import campaign_rse
from modules.map import get_map_data
from modules.map_data import MapRSE
from modules.navigation import Navigator


@dataclass(frozen=True)
class MissionStart:
    map: MapRSE
    coordinates: tuple[int, int]


class RSEMission:
    """Resumable story mission with an explicit, inspectable entry point."""

    mission_id: str
    handler_name: str
    start: MissionStart

    def __init__(self, navigator: Navigator | None = None):
        self.navigator = navigator or Navigator()

    def start_location(self) -> MissionStart:
        return self.start

    def run(self, **options) -> Generator:
        start = self.start_location()
        yield from self.navigator.go_to(start.map, start.coordinates)
        handler: Callable[..., Generator] = getattr(campaign_rse, self.handler_name)
        yield from handler(**options)


def _player_second_floor() -> MapRSE:
    if context.config.living_dex.gameplay.trainer_gender == "female":
        return MapRSE.LITTLEROOT_TOWN_MAYS_HOUSE_2F
    return MapRSE.LITTLEROOT_TOWN_BRENDANS_HOUSE_2F


def _rival_start() -> MissionStart:
    if context.config.living_dex.gameplay.trainer_gender == "female":
        map_id = MapRSE.LITTLEROOT_TOWN_BRENDANS_HOUSE_2F
        coordinates = (1, 3) if context.rom.is_rs else (3, 5)
    else:
        map_id = MapRSE.LITTLEROOT_TOWN_MAYS_HOUSE_2F
        coordinates = (7, 3) if context.rom.is_rs else (5, 5)
    return MissionStart(map_id, coordinates)


def _object_interaction_start(map_id: MapRSE, *, northmost: bool = True) -> MissionStart:
    objects = get_map_data(map_id, (0, 0)).objects
    target = min(objects, key=lambda item: item.local_coordinates[1]) if northmost else objects[0]
    x, y = target.local_coordinates
    return MissionStart(map_id, (x, y + 1))


class SetBedroomClockMission(RSEMission):
    mission_id = "RSE-001"
    handler_name = "run_rse_clock_setup"
    start = MissionStart(MapRSE.LITTLEROOT_TOWN_BRENDANS_HOUSE_2F, (5, 2))

    def start_location(self) -> MissionStart:
        return MissionStart(_player_second_floor(), (5, 2))


class MeetRivalMission(RSEMission):
    mission_id = "RSE-002"
    handler_name = "run_rse_meet_rival"
    start = MissionStart(MapRSE.LITTLEROOT_TOWN_MAYS_HOUSE_2F, (5, 5))

    def start_location(self) -> MissionStart:
        return _rival_start()


class ChooseStarterMission(RSEMission):
    mission_id = "RSE-003"
    handler_name = "run_rse_choose_starter"
    start = MissionStart(MapRSE.ROUTE101, (7, 15))


class Route103PokedexMission(RSEMission):
    mission_id = "RSE-004"
    handler_name = "run_rse_defeat_route103_rival"
    start = MissionStart(MapRSE.ROUTE103, (10, 16))


class ReceivePokedexMission(RSEMission):
    mission_id = "RSE-005"
    handler_name = "run_rse_receive_pokedex"
    start = MissionStart(MapRSE.LITTLEROOT_TOWN_PROFESSOR_BIRCHS_LAB, (6, 4))


class ReceiveRunningShoesMission(RSEMission):
    mission_id = "RSE-006"
    handler_name = "run_rse_receive_running_shoes"
    start = MissionStart(MapRSE.LITTLEROOT_TOWN, (11, 2))


class MeetNormanMission(RSEMission):
    mission_id = "RSE-007"
    handler_name = "run_rse_meet_norman"
    start = MissionStart(MapRSE.PETALBURG_CITY_GYM, (8, 8))


class WallyTutorialMission(RSEMission):
    mission_id = "RSE-008"
    handler_name = "run_rse_wally_tutorial"
    start = MissionStart(MapRSE.PETALBURG_CITY_GYM, (8, 6))


class PetalburgWoodsVillainMission(RSEMission):
    mission_id = "RSE-009"
    handler_name = "run_rse_defeat_petalburg_woods_villain"
    start = MissionStart(MapRSE.PETALBURG_WOODS, (5, 34))


class ReachRustboroMission(RSEMission):
    mission_id = "RSE-010"
    handler_name = "run_rse_reach_rustboro"
    start = MissionStart(MapRSE.PETALBURG_WOODS, (4, 4))


class DefeatRoxanneMission(RSEMission):
    mission_id = "RSE-011"
    handler_name = "run_rse_defeat_roxanne"
    start = MissionStart(MapRSE.RUSTBORO_CITY_GYM, (8, 13))

    def start_location(self) -> MissionStart:
        return _object_interaction_start(MapRSE.RUSTBORO_CITY_GYM)


class StartDevonGoodsCaseMission(RSEMission):
    mission_id = "RSE-012"
    handler_name = "run_rse_start_devon_goods_case"
    start = MissionStart(MapRSE.RUSTBORO_CITY, (23, 20))


class RecoverDevonGoodsMission(RSEMission):
    mission_id = "RSE-013"
    handler_name = "run_rse_recover_devon_goods"
    start = MissionStart(MapRSE.ROUTE116, (47, 9))


class ReturnDevonGoodsMission(RSEMission):
    mission_id = "RSE-014"
    handler_name = "run_rse_return_devon_goods"
    start = MissionStart(MapRSE.RUSTBORO_CITY, (30, 11))


class ReceivePokenavMission(RSEMission):
    mission_id = "RSE-015"
    handler_name = "run_rse_receive_pokenav"
    start = MissionStart(MapRSE.RUSTBORO_CITY_DEVON_CORP_3F, (3, 6))


class SailToDewfordMission(RSEMission):
    mission_id = "RSE-016"
    handler_name = "run_rse_sail_to_dewford"
    start = MissionStart(MapRSE.ROUTE104_MR_BRINEYS_HOUSE, (5, 5))


class ReceiveFlashMission(RSEMission):
    mission_id = "RSE-017"
    handler_name = "run_rse_receive_flash"
    start = MissionStart(MapRSE.GRANITE_CAVE_1F, (36, 10))


class DeliverStevenLetterMission(RSEMission):
    mission_id = "RSE-018"
    handler_name = "run_rse_deliver_steven_letter"
    start = MissionStart(MapRSE.GRANITE_CAVE_STEVENS_ROOM, (7, 9))


class DefeatBrawlyMission(RSEMission):
    mission_id = "RSE-019"
    handler_name = "run_rse_defeat_brawly"
    start = MissionStart(MapRSE.DEWFORD_TOWN_GYM, (5, 5))

    def start_location(self) -> MissionStart:
        return _object_interaction_start(MapRSE.DEWFORD_TOWN_GYM)


class SailToSlateportMission(RSEMission):
    mission_id = "RSE-020"
    handler_name = "run_rse_sail_to_slateport"
    start = MissionStart(MapRSE.DEWFORD_TOWN, (11, 9))


class TalkToDockMission(RSEMission):
    mission_id = "RSE-021"
    handler_name = "run_rse_talk_to_dock"
    start = MissionStart(MapRSE.SLATEPORT_CITY_STERNS_SHIPYARD_1F, (11, 13))


class DeliverDevonGoodsMission(RSEMission):
    mission_id = "RSE-022"
    handler_name = "run_rse_deliver_devon_goods"
    start = MissionStart(MapRSE.SLATEPORT_CITY_OCEANIC_MUSEUM_2F, (13, 7))

    def start_location(self) -> MissionStart:
        map_id = (
            MapRSE.SLATEPORT_CITY_OCEANIC_MUSEUM_2F
            if context.rom.is_emerald
            else MapRSE.SLATEPORT_CITY_OCEANIC_MUSEUM_1F
        )
        return MissionStart(map_id, (13, 7))


class DefeatRoute110RivalMission(RSEMission):
    mission_id = "RSE-023"
    handler_name = "run_rse_defeat_route110_rival"
    start = MissionStart(MapRSE.ROUTE110, (33, 57))


class ReachMauvilleMission(RSEMission):
    mission_id = "RSE-024"
    handler_name = "run_rse_reach_mauville"
    start = MissionStart(MapRSE.ROUTE110, (33, 40))


class DefeatWallyMission(RSEMission):
    mission_id = "RSE-025"
    handler_name = "run_rse_defeat_wally"
    start = MissionStart(MapRSE.MAUVILLE_CITY, (8, 7))


class ReceiveRockSmashMission(RSEMission):
    mission_id = "RSE-026"
    handler_name = "run_rse_receive_rock_smash"
    start = MissionStart(MapRSE.MAUVILLE_CITY_HOUSE1, (3, 5))


class DefeatWattsonMission(RSEMission):
    mission_id = "RSE-027"
    handler_name = "run_rse_defeat_wattson"
    start = MissionStart(MapRSE.MAUVILLE_CITY_GYM, (4, 5))

    def start_location(self) -> MissionStart:
        return _object_interaction_start(MapRSE.MAUVILLE_CITY_GYM)


class OpenRusturfTunnelMission(RSEMission):
    mission_id = "RSE-028"
    handler_name = "run_rse_open_rusturf_tunnel"
    start = MissionStart(MapRSE.RUSTURF_TUNNEL, (7, 4))


RSE_MISSION_CLASSES: dict[str, type[RSEMission]] = {
    mission.mission_id: mission
    for mission in (
        SetBedroomClockMission,
        MeetRivalMission,
        ChooseStarterMission,
        Route103PokedexMission,
        ReceivePokedexMission,
        ReceiveRunningShoesMission,
        MeetNormanMission,
        WallyTutorialMission,
        PetalburgWoodsVillainMission,
        ReachRustboroMission,
        DefeatRoxanneMission,
        StartDevonGoodsCaseMission,
        RecoverDevonGoodsMission,
        ReturnDevonGoodsMission,
        ReceivePokenavMission,
        SailToDewfordMission,
        ReceiveFlashMission,
        DeliverStevenLetterMission,
        DefeatBrawlyMission,
        SailToSlateportMission,
        TalkToDockMission,
        DeliverDevonGoodsMission,
        DefeatRoute110RivalMission,
        ReachMauvilleMission,
        DefeatWallyMission,
        ReceiveRockSmashMission,
        DefeatWattsonMission,
        OpenRusturfTunnelMission,
    )
}
