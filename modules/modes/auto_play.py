
from typing import Generator
from modules.context import context
from modules.encounter import handle_encounter, EncounterInfo
from modules.gui.multi_select_window import Selection, ask_for_choice
from modules.map_data import MapFRLG, MapRSE, get_map_enum
from modules.memory import get_event_flag, get_game_state_symbol, unpack_uint32, read_symbol, get_game_state, GameState
from modules.menuing import PokemonPartyMenuNavigator, StartMenuNavigator
from modules.player import Player, PlayerAvatar, get_player_avatar, get_player, player_avatar_is_standing_still
from modules.pokemon_party import get_party_size, get_party
from modules.runtime import get_sprites_path
from modules.gui.desktop_notification import desktop_notification
from modules.tasks import get_global_script_context, task_is_active
from modules.runtime import get_sprites_path
from modules.save_data import get_save_data
from ._asserts import SavedMapLocation, assert_save_game_exists, assert_saved_on_map
from ._interface import BattleAction, BotMode, BotModeError
from .util import (
    ensure_facing_direction,
    follow_waypoints,
    navigate_to,
    walk_one_tile,
    register_key_item,
    talk_to_npc,
    wait_for_n_frames,
    wait_for_task_to_start_and_finish,
    wait_until_task_is_not_active
)


class AutoPlayMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Auto Play"

    @staticmethod
    def is_selectable() -> bool:
        return True
    
    def __init__(self):
        super().__init__()
    
    def run(self) -> Generator:
        while context.bot_mode != "Manual":
            avatar = get_player_avatar()
            map = get_map_enum(avatar.map_group_and_number)
            
            ctx = get_global_script_context()
            if ctx.script_function_name == "Std_MsgboxDefault":
                yield from wait_for_task_to_start_and_finish("Task_FieldMessageBox", "A")   
                yield from wait_for_task_to_start_and_finish("IsFieldMessageBoxHidden", "A")                  
            
            if map.name == MapRSE.INSIDE_OF_TRUCK.name:
                yield from navigate_to(MapRSE.INSIDE_OF_TRUCK, (4, 2), True, True, True, True)                

            if map.name in (self._get_house_1f().name, self._get_house_2f().name):     
                if not get_event_flag("SET_WALL_CLOCK"): #SYS_CLOCK_SET
                    yield from navigate_to(self._get_house_1f(), (8, 2))
                    
               # while not player_avatar_is_standing_still():
               #     yield
                    yield from ensure_facing_direction("Up")
                    raise BotModeError("Set clock on the wall on second floor in your home. Changing to manual mode.")
        
            a = 1
        yield 
        

    def _get_house_1f(self) -> MapRSE:
        if get_player().gender == "female":
            return MapRSE.LITTLEROOT_TOWN_MAYS_HOUSE_1F
        return MapRSE.LITTLEROOT_TOWN_BRENDANS_HOUSE_1F
        

    def _get_house_2f(self) -> MapRSE:
        if get_player().gender == "female":
            return MapRSE.LITTLEROOT_TOWN_MAYS_HOUSE_2F
        return MapRSE.LITTLEROOT_TOWN_BRENDANS_HOUSE_2F