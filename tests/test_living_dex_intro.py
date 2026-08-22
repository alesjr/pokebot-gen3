import tempfile
import unittest
import os
from datetime import datetime
from pathlib import Path

from modules.context import context
from modules.fleet.config import load_fleet_config
from modules.game import set_rom
from modules.libmgba import LibmgbaEmulator
from modules.living_dex.intro import run_new_game_intro
from modules.living_dex.campaign_rse import (
    run_rse_choose_starter,
    run_rse_clock_setup,
    run_rse_defeat_petalburg_woods_villain,
    run_rse_defeat_roxanne,
    run_rse_defeat_brawly,
    run_rse_defeat_route110_rival,
    run_rse_defeat_wally,
    run_rse_defeat_wattson,
    run_rse_open_rusturf_tunnel,
    run_rse_deliver_devon_goods,
    run_rse_deliver_steven_letter,
    run_rse_receive_flash,
    run_rse_finish_starter_lab,
    run_rse_meet_norman,
    run_rse_meet_rival,
    run_rse_reach_starter_bag,
    run_rse_reach_rustboro,
    run_rse_receive_pokenav,
    run_rse_receive_rock_smash,
    run_rse_recover_devon_goods,
    run_rse_return_devon_goods,
    run_rse_start_devon_goods_case,
    run_rse_sail_to_dewford,
    run_rse_sail_to_slateport,
    run_rse_talk_to_dock,
    run_rse_receive_running_shoes,
    run_rse_reach_mauville,
    run_rse_route103_and_receive_pokedex,
    run_rse_wally_tutorial,
)
from modules.map_data import MapRSE, get_map_enum
from modules.memory import (
    GameState,
    game_has_started,
    get_event_flag,
    get_event_var,
    get_game_state,
    get_game_state_symbol,
)
from modules.player import get_player, get_player_avatar, player_avatar_is_controllable
from modules.pokemon_party import get_party
from modules.profiles import Profile
from modules.roms import load_rom_data
from modules.state_cache import state_cache
from modules.tasks import get_global_script_context, get_tasks
from tests.utility import MockStatsDatabase


class TestLivingDexNewGameIntro(unittest.TestCase):
    def _run(self, controller, emulator, limit):
        for _ in range(limit):
            try:
                next(controller)
            except StopIteration:
                return
            emulator.run_single_frame()
            emulator.set_throttle(False)
            context.frame += 1
        avatar = get_player_avatar()
        script = get_global_script_context()
        self.fail(
            "controller timed out: "
            f"map={get_map_enum(avatar.map_group_and_number).name} "
            f"coords={avatar.local_coordinates} callback={get_game_state_symbol()} "
            f"script={script.script_function_name if script.is_active else 'inactive'} "
            f"tasks={','.join(task.symbol for task in get_tasks())} message={context.message} "
            f"party={','.join(pokemon.species.name for pokemon in get_party())}"
        )

    def _run_with_listeners(self, controller, bot_mode, emulator, limit):
        from modules.modes import FrameInfo, get_bot_listeners

        previous = None
        context.controller_stack.clear()
        context.controller_stack.append(controller)
        context.bot_mode_instance = bot_mode
        context._current_bot_mode = bot_mode.name()
        context.config.logging = context.config.logging.model_copy(update={"log_encounters_to_console": False})
        context.bot_listeners = get_bot_listeners(context.rom)
        for _ in range(limit):
            script = get_global_script_context()
            frame = FrameInfo(
                frame_count=emulator.get_frame_count(),
                game_state=get_game_state(),
                active_tasks=[task.symbol.lower() for task in get_tasks()],
                script_stack=script.stack if script.is_active else [],
                controller_stack=[item.__qualname__ for item in context.controller_stack],
                previous_frame=previous,
            )
            for listener in context.bot_listeners.copy():
                listener.handle_frame(bot_mode, frame)
            try:
                next(context.controller_stack[-1])
            except (StopIteration, GeneratorExit):
                context.controller_stack.pop()
                if not context.controller_stack:
                    return
            emulator.run_single_frame()
            emulator.set_throttle(False)
            context.frame += 1
            previous = frame
            previous.previous_frame = None
        avatar = get_player_avatar()
        script = get_global_script_context()
        self.fail(
            f"controller did not finish within {limit} frames: "
            f"map={get_map_enum(avatar.map_group_and_number).name} "
            f"coords={avatar.local_coordinates} callback={get_game_state_symbol()} "
            f"game_state={get_game_state().name} "
            f"script={script.script_function_name if script.is_active else 'inactive'} "
            f"tasks={','.join(task.symbol for task in get_tasks())} "
            f"controllers={','.join(item.__qualname__ for item in context.controller_stack)} "
            f"party={','.join(pokemon.species.name for pokemon in get_party())}"
        )

    def test_all_five_roms_reach_started_state_with_configured_identity(self):
        root = Path(__file__).parents[1]
        config = load_fleet_config(root / "fleet.yml")
        missing = [item.rom for item in config.instances if not (root / "roms" / item.rom).is_file()]
        if missing:
            self.skipTest("user-supplied ROM assets unavailable")

        for item in config.instances:
            with self.subTest(game=item.game), tempfile.TemporaryDirectory() as directory:
                rom = load_rom_data(root / "roms" / item.rom)
                profile = Profile(rom, Path(directory), datetime.now())
                context.profile = profile
                context.frame = 0
                set_rom(rom)
                state_cache.reset()
                emulator = LibmgbaEmulator(profile, lambda: None, is_test_run=True)
                context.emulator = emulator
                emulator.set_audio_enabled(False)
                emulator.set_video_enabled(False)
                emulator.set_throttle(False)
                intro = run_new_game_intro(config.trainer_name, config.trainer_gender)
                try:
                    self._run(intro, emulator, 30_000)
                    self.assertTrue(game_has_started())
                    self.assertEqual(get_player().name, "Alesjr")
                    self.assertEqual(get_player().gender, "male")
                finally:
                    emulator.shutdown()
                    state_cache.reset()

    def test_rse_fresh_games_reach_starter_bag_with_persistent_evidence(self):
        root = Path(__file__).parents[1]
        config = load_fleet_config(root / "fleet.yml")
        instances = [item for item in config.instances if item.game in {"Ruby", "Sapphire", "Emerald"}]
        if selected_game := os.environ.get("POKEBOT_TEST_GAME"):
            selected_games = {game.strip() for game in selected_game.split(",")}
            instances = [item for item in instances if item.game in selected_games]
        if any(not (root / "roms" / item.rom).is_file() for item in instances):
            self.skipTest("user-supplied ROM assets unavailable")

        from modules.config import Config

        for item in instances:
            with self.subTest(game=item.game), tempfile.TemporaryDirectory() as directory:
                rom = load_rom_data(root / "roms" / item.rom)
                profile = Profile(rom, Path(directory), datetime.now())
                context.profile = profile
                context.config = Config(root / "modules" / "config" / "templates")
                context.stats = MockStatsDatabase()
                gameplay = context.config.living_dex.gameplay.model_copy(update={"starter": item.starter})
                context.config.living_dex = context.config.living_dex.model_copy(update={"gameplay": gameplay})
                context.frame = 0
                set_rom(rom)
                state_cache.reset()
                emulator = LibmgbaEmulator(profile, lambda: None, is_test_run=True)
                context.emulator = emulator
                emulator.set_audio_enabled(False)
                emulator.set_video_enabled(False)
                emulator.set_throttle(False)
                try:
                    self._run(run_new_game_intro(config.trainer_name, config.trainer_gender), emulator, 30_000)
                    clock = run_rse_clock_setup()
                    if item.game == "Emerald":
                        for _ in range(15_000):
                            next(clock)
                            emulator.run_single_frame()
                            context.frame += 1
                            if get_game_state_symbol() == "CB2_WALLCLOCK":
                                break
                        else:
                            self.fail("clock UI was not reached before recovery test")
                        clock.close()
                        self.assertFalse(get_event_flag("SET_WALL_CLOCK"))
                        clock = run_rse_clock_setup()
                    self._run(clock, emulator, 30_000)
                    self.assertTrue(get_event_flag("SET_WALL_CLOCK"))
                    with self.assertRaises(StopIteration):
                        next(run_rse_clock_setup())
                    self._run(run_rse_meet_rival(), emulator, 30_000)
                    self.assertGreaterEqual(get_event_var("LITTLEROOT_RIVAL_STATE"), 3)
                    with self.assertRaises(StopIteration):
                        next(run_rse_meet_rival())
                    self._run(run_rse_reach_starter_bag(), emulator, 30_000)
                    self.assertEqual(get_map_enum(get_player_avatar().map_group_and_number), MapRSE.ROUTE101)
                    self.assertGreaterEqual(get_event_var("ROUTE101_STATE"), 2)
                    candidate_personalities = []
                    attempt_states = []

                    def accept_second_candidate(pokemon):
                        candidate_personalities.append(pokemon.personality_value)
                        return len(candidate_personalities) >= 2

                    def observe_attempt(attempt):
                        attempt_states.append(
                            (
                                attempt,
                                len(get_party()),
                                get_event_flag("SYS_POKEMON_GET"),
                                get_event_flag("RESCUED_BIRCH"),
                            )
                        )

                    self._run(
                        run_rse_choose_starter(
                            qualifies=accept_second_candidate,
                            attempt_observer=observe_attempt,
                        ),
                        emulator,
                        80_000,
                    )
                    self.assertEqual(len(candidate_personalities), 2)
                    self.assertNotEqual(candidate_personalities[0], candidate_personalities[1])
                    self.assertEqual(attempt_states[:2], [(1, 0, False, False), (2, 0, False, False)])
                    self.assertTrue(get_event_flag("SYS_POKEMON_GET"))
                    self.assertTrue(get_event_flag("RESCUED_BIRCH"))
                    self.assertGreaterEqual(get_event_var("BIRCH_LAB_STATE"), 3)
                    self.assertTrue(player_avatar_is_controllable())
                    self.assertFalse(get_global_script_context().is_active)
                    self._run(run_rse_finish_starter_lab(), emulator, 1_000)
                    with self.assertRaises(StopIteration):
                        next(run_rse_choose_starter())
                    self.assertIn(
                        context.config.living_dex.gameplay.starter,
                        {pokemon.species.name for pokemon in get_party()},
                    )
                    from modules.items import get_item_bag, get_item_by_name
                    from modules.modes.living_dex import LivingDexMode

                    mode = LivingDexMode()
                    self._run_with_listeners(
                        run_rse_route103_and_receive_pokedex(
                            set_navigation_encounter_policy=mode._set_navigation_encounter_policy
                        ),
                        mode,
                        emulator,
                        120_000,
                    )
                    self.assertTrue(get_event_flag("DEFEATED_RIVAL_ROUTE103"))
                    self.assertTrue(get_event_flag("SYS_POKEDEX_GET"))
                    self.assertGreater(get_item_bag().quantity_of(get_item_by_name("Poké Ball")), 0)
                    self.assertTrue(player_avatar_is_controllable())
                    self.assertFalse(get_global_script_context().is_active)
                    self._run(run_rse_receive_running_shoes(), emulator, 30_000)
                    self.assertTrue(get_event_flag("RECEIVED_RUNNING_SHOES"))
                    self.assertTrue(player_avatar_is_controllable())
                    self.assertFalse(get_global_script_context().is_active)
                    petalburg_state = "PETALBURG_CITY_STATE" if context.rom.is_emerald else "PETALBURG_STATE"
                    initial_petalburg_state = get_event_var(petalburg_state)
                    self._run_with_listeners(
                        run_rse_meet_norman(
                            set_navigation_encounter_policy=mode._set_navigation_encounter_policy
                        ),
                        mode,
                        emulator,
                        120_000,
                    )
                    self.assertGreater(get_event_var(petalburg_state), initial_petalburg_state)
                    self.assertEqual(
                        get_map_enum(get_player_avatar().map_group_and_number), MapRSE.PETALBURG_CITY_GYM
                    )
                    self.assertTrue(player_avatar_is_controllable())
                    self.assertFalse(get_global_script_context().is_active)
                    state_after_norman = get_event_var(petalburg_state)
                    self._run(run_rse_wally_tutorial(), emulator, 120_000)
                    self.assertGreaterEqual(get_event_var(petalburg_state), state_after_norman)
                    self.assertGreaterEqual(get_event_var(petalburg_state), 3)
                    self.assertEqual(
                        get_map_enum(get_player_avatar().map_group_and_number), MapRSE.PETALBURG_CITY_GYM
                    )
                    self.assertTrue(player_avatar_is_controllable())
                    self.assertFalse(get_global_script_context().is_active)
                    initial_woods_state = get_event_var("PETALBURG_WOODS_STATE")
                    self._run_with_listeners(
                        run_rse_defeat_petalburg_woods_villain(
                            set_navigation_encounter_policy=mode._set_navigation_encounter_policy
                        ),
                        mode,
                        emulator,
                        180_000,
                    )
                    self.assertGreater(get_event_var("PETALBURG_WOODS_STATE"), initial_woods_state)
                    self.assertEqual(
                        get_map_enum(get_player_avatar().map_group_and_number), MapRSE.PETALBURG_WOODS
                    )
                    self.assertTrue(player_avatar_is_controllable())
                    self.assertFalse(get_global_script_context().is_active)
                    self._run_with_listeners(
                        run_rse_reach_rustboro(
                            set_navigation_encounter_policy=mode._set_navigation_encounter_policy
                        ),
                        mode,
                        emulator,
                        180_000,
                    )
                    self.assertTrue(get_event_flag("VISITED_RUSTBORO_CITY"))
                    self.assertEqual(
                        get_map_enum(get_player_avatar().map_group_and_number), MapRSE.RUSTBORO_CITY
                    )
                    self.assertTrue(player_avatar_is_controllable())
                    self.assertFalse(get_global_script_context().is_active)
                    self._run_with_listeners(
                        run_rse_defeat_roxanne(
                            set_navigation_encounter_policy=mode._set_navigation_encounter_policy
                        ),
                        mode,
                        emulator,
                        300_000 if context.rom.is_emerald else 100_000,
                    )
                    self.assertTrue(get_event_flag("BADGE01_GET"))
                    self.assertEqual(
                        get_map_enum(get_player_avatar().map_group_and_number), MapRSE.RUSTBORO_CITY_GYM
                    )
                    self.assertTrue(player_avatar_is_controllable())
                    self.assertFalse(get_global_script_context().is_active)
                    self._run(run_rse_start_devon_goods_case(), emulator, 60_000)
                    self.assertTrue(get_event_flag("DEVON_GOODS_STOLEN"))
                    self.assertTrue(player_avatar_is_controllable())
                    self.assertFalse(get_global_script_context().is_active)
                    self._run_with_listeners(
                        run_rse_recover_devon_goods(
                            set_navigation_encounter_policy=mode._set_navigation_encounter_policy
                        ),
                        mode,
                        emulator,
                        300_000,
                    )
                    self.assertTrue(get_event_flag("RECOVERED_DEVON_GOODS"))
                    self.assertTrue(player_avatar_is_controllable())
                    self.assertFalse(get_global_script_context().is_active)
                    self._run_with_listeners(
                        run_rse_return_devon_goods(
                            set_navigation_encounter_policy=mode._set_navigation_encounter_policy
                        ),
                        mode,
                        emulator,
                        180_000,
                    )
                    self.assertTrue(get_event_flag("RETURNED_DEVON_GOODS"))
                    self.assertTrue(player_avatar_is_controllable())
                    self.assertFalse(get_global_script_context().is_active)
                    self._run(run_rse_receive_pokenav(), emulator, 120_000)
                    self.assertTrue(get_event_flag("SYS_POKENAV_GET"))
                    self.assertTrue(get_event_flag("RECEIVED_POKENAV"))
                    self.assertTrue(player_avatar_is_controllable())
                    self.assertFalse(get_global_script_context().is_active)
                    self._run_with_listeners(
                        run_rse_sail_to_dewford(
                            set_navigation_encounter_policy=mode._set_navigation_encounter_policy
                        ),
                        mode,
                        emulator,
                        300_000,
                    )
                    self.assertTrue(get_event_flag("VISITED_DEWFORD_TOWN"))
                    self._run_with_listeners(
                        run_rse_receive_flash(
                            set_navigation_encounter_policy=mode._set_navigation_encounter_policy
                        ),
                        mode,
                        emulator,
                        180_000,
                    )
                    self.assertGreater(get_item_bag().quantity_of(get_item_by_name("HM05")), 0)
                    if context.rom.is_emerald:
                        self.assertTrue(get_event_flag("RECEIVED_HM_FLASH"))
                    self._run_with_listeners(
                        run_rse_deliver_steven_letter(
                            set_navigation_encounter_policy=mode._set_navigation_encounter_policy
                        ),
                        mode,
                        emulator,
                        300_000,
                    )
                    self.assertTrue(get_event_flag("DELIVERED_STEVEN_LETTER"))
                    self._run_with_listeners(
                        run_rse_defeat_brawly(
                            set_navigation_encounter_policy=mode._set_navigation_encounter_policy
                        ),
                        mode,
                        emulator,
                        300_000,
                    )
                    self.assertTrue(get_event_flag("BADGE02_GET"))
                    self._run_with_listeners(
                        run_rse_sail_to_slateport(
                            set_navigation_encounter_policy=mode._set_navigation_encounter_policy
                        ),
                        mode,
                        emulator,
                        300_000,
                    )
                    self.assertTrue(get_event_flag("VISITED_SLATEPORT_CITY"))
                    self._run(run_rse_talk_to_dock(), emulator, 120_000)
                    self.assertTrue(get_event_flag("DOCK_REJECTED_DEVON_GOODS"))
                    self._run_with_listeners(
                        run_rse_deliver_devon_goods(
                            set_navigation_encounter_policy=mode._set_navigation_encounter_policy
                        ),
                        mode,
                        emulator,
                        300_000,
                    )
                    self.assertTrue(get_event_flag("DELIVERED_DEVON_GOODS"))
                    self._run_with_listeners(
                        run_rse_defeat_route110_rival(
                            set_navigation_encounter_policy=mode._set_navigation_encounter_policy
                        ),
                        mode,
                        emulator,
                        600_000,
                    )
                    self.assertGreater(get_event_var("ROUTE110_STATE"), 0)
                    self._run_with_listeners(
                        run_rse_reach_mauville(
                            set_navigation_encounter_policy=mode._set_navigation_encounter_policy
                        ),
                        mode,
                        emulator,
                        180_000,
                    )
                    self.assertTrue(get_event_flag("VISITED_MAUVILLE_CITY"))
                    self._run_with_listeners(
                        run_rse_defeat_wally(
                            set_navigation_encounter_policy=mode._set_navigation_encounter_policy
                        ),
                        mode,
                        emulator,
                        300_000,
                    )
                    self.assertTrue(get_event_flag("DEFEATED_WALLY_MAUVILLE"))
                    if os.environ.get("POKEBOT_TEST_STOP_AFTER_RSE25") == "1":
                        self.assertTrue(player_avatar_is_controllable())
                        self.assertFalse(get_global_script_context().is_active)
                        continue
                    self._run(run_rse_receive_rock_smash(), emulator, 120_000)
                    self.assertGreater(get_item_bag().quantity_of(get_item_by_name("HM06")), 0)
                    self.assertTrue(
                        get_event_flag(
                            "RECEIVED_HM_ROCK_SMASH" if context.rom.is_emerald else "RECEIVED_HM06"
                        )
                    )
                    self.assertTrue(player_avatar_is_controllable())
                    self.assertFalse(get_global_script_context().is_active)
                    self._run_with_listeners(
                        run_rse_defeat_wattson(
                            set_navigation_encounter_policy=mode._set_navigation_encounter_policy
                        ),
                        mode,
                        emulator,
                        600_000,
                    )
                    self.assertTrue(get_event_flag("BADGE03_GET"))
                    self.assertTrue(player_avatar_is_controllable())
                    self.assertFalse(get_global_script_context().is_active)
                    self._run_with_listeners(
                        run_rse_open_rusturf_tunnel(
                            set_navigation_encounter_policy=mode._set_navigation_encounter_policy
                        ),
                        mode,
                        emulator,
                        600_000,
                    )
                    self.assertTrue(get_event_flag("RUSTURF_TUNNEL_OPENED"))
                    self.assertGreater(get_item_bag().quantity_of(get_item_by_name("HM04")), 0)
                    strength_flag = "RECEIVED_HM04" if context.rom.is_rs else "RECEIVED_HM_STRENGTH"
                    self.assertTrue(get_event_flag(strength_flag))
                    self.assertTrue(player_avatar_is_controllable())
                    self.assertFalse(get_global_script_context().is_active)
                finally:
                    emulator.shutdown()
                    state_cache.reset()


if __name__ == "__main__":
    unittest.main()
