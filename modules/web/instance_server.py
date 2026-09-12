from __future__ import annotations

import asyncio
import io
import os
import sys
import time
from pathlib import Path
from threading import Event, Thread

from aiohttp import web

from modules import exceptions
from modules.context import context
from modules.main import work_queue
from modules.modes import get_bot_modes
from modules.missions import MissionsDatabase
from modules.profiles import PROFILES_DIRECTORY, clear_profile_data, create_profile, list_available_profiles
from modules.roms import list_available_roms
from modules.runtime import get_base_path
from modules.web.log_buffer import web_log_buffer


ALLOWED_BUTTONS = {"A", "B", "L", "R", "Start", "Select", "Up", "Down", "Left", "Right"}
ALLOWED_SPEEDS = {0, 1, 2, 3, 4, 8, 16, 32}


def _game_name(rom=None) -> str:
    rom = rom or context.rom
    if rom.is_ruby:
        return "Ruby"
    if rom.is_sapphire:
        return "Sapphire"
    if rom.is_emerald:
        return "Emerald"
    if rom.is_fr:
        return "FireRed"
    if rom.is_lg:
        return "LeafGreen"
    raise ValueError("unsupported game")


def _main_thread_call(callback, timeout: float = 3.0):
    completed = Event()
    result = []

    def execute() -> None:
        try:
            result.append((True, callback()))
        except BaseException as error:
            result.append((False, error))
        finally:
            completed.set()

    work_queue.put(execute)
    if not completed.wait(timeout):
        raise TimeoutError("emulator main loop did not answer")
    success, value = result[0]
    if not success:
        raise value
    return value


async def _run_on_main(callback, timeout: float = 3.0):
    return await asyncio.to_thread(_main_thread_call, callback, timeout)


def _schedule_profile_restart(name: str | None, speed: int) -> None:
    def restart() -> None:
        time.sleep(0.5)
        arguments = [
            sys.executable,
            str(get_base_path() / "pokebot.py"),
        ]
        if name is not None:
            arguments.append(name)
        arguments.extend(
            [
                "--bot-mode",
                os.environ.get("POKEBOT_MODE", "Manual"),
                "--headless",
                "--emulation-speed",
                str(speed),
                "--no-audio",
            ]
        )
        os.execv(
            sys.executable,
            arguments,
        )

    Thread(target=restart, name="profile-restart", daemon=True).start()


def _available_modes() -> list[dict]:
    modes = [{"name": "Manual", "selectable": True}]
    for mode in get_bot_modes():
        try:
            selectable = bool(mode.is_selectable())
        except Exception:
            selectable = False
        modes.append({"name": mode.name(), "selectable": selectable})
    return modes


def _recent_encounters() -> list[dict]:
    if context.stats is None:
        return []
    return [
        {
            "id": encounter.encounter_id,
            "species": encounter.species_name,
            "level": encounter.pokemon.level,
            "shiny": encounter.is_shiny,
            "captured": encounter.outcome is not None and encounter.outcome.name == "Caught",
            "time": encounter.encounter_time.isoformat(),
        }
        for encounter in context.stats.get_encounter_log()[:20]
    ]


def _save_states() -> list[str]:
    profile = context.profile.path
    names = ["current_state.ss1"] if (profile / "current_state.ss1").is_file() else []
    states = profile / "states"
    if states.is_dir():
        names.extend(path.name for path in sorted(states.glob("*.ss1"), reverse=True)[:50])
    return names


def _state() -> dict:
    emulator = context.emulator
    campaign = dict(context.campaign_state)
    if context.bot_mode != "Campaign" and not (
        context.bot_mode == "Manual" and campaign.get("pause_reason") is not None
    ):
        campaign = {
            "mission": None,
            "step": None,
            "step_order": None,
            "objective": None,
            "pause_reason": None,
        }
    return {
        "profile": context.profile.path.name,
        "game": _game_name(),
        "mode": context.bot_mode,
        "message": context.message,
        "campaign": campaign,
        "frame": emulator.get_frame_count(),
        "fps": emulator.get_current_fps(),
        "speed": context.emulation_speed,
        "video_enabled": emulator.get_video_enabled(),
        "modes": _available_modes(),
        "encounters": _recent_encounters(),
        "save_states": _save_states(),
    }


def _frame() -> bytes:
    image = context.emulator.get_current_screen_image()
    output = io.BytesIO()
    image.save(output, format="JPEG", quality=80)
    return output.getvalue()


def _load_state(name: str) -> None:
    if not name or Path(name).name != name:
        raise ValueError("invalid save state name")
    profile = context.profile.path
    path = profile / "current_state.ss1" if name == "current_state.ss1" else profile / "states" / name
    if not path.is_file() or path.suffix != ".ss1":
        raise ValueError("save state not found")
    context.emulator.load_save_state(path.read_bytes())
"python", "pokebot.py", "Sapphire", "--bot-mode", "Campaign", "--headless", "--no-video", "--no-audio"

def create_instance_app() -> web.Application:
    app = web.Application(client_max_size=64 * 1024)
    static_root = get_base_path() / "modules" / "web" / "static" / "fleet"
    sprites_root = get_base_path() / "modules" / "web" / "static" / "sprites"

    def require_active_profile(request: web.Request) -> None:
        if context.profile is None or context.emulator is None:
            raise web.HTTPConflict(text="no profile is active")
        profile = request.match_info.get("profile")
        if profile is not None and profile != context.profile.path.name:
            raise web.HTTPConflict(text="profile is not active in this container")

    async def dashboard(_: web.Request) -> web.FileResponse:
        return web.FileResponse(static_root / "index.html")

    async def health(_: web.Request) -> web.Response:
        return web.json_response({"status": "ok"})

    async def fleet_state(_: web.Request) -> web.Response:
        if context.profile is None or context.emulator is None:
            return web.json_response({"instances": []})
        current = await _run_on_main(_state)
        return web.json_response(
            {
                "instances": [
                    {
                        "profile": current["profile"],
                        "game": current["game"],
                        "port": 8888,
                        "status": "running",
                        "objective": current["message"],
                        "emulator_frame": current["frame"],
                    }
                ]
            }
        )

    async def profiles(_: web.Request) -> web.Response:
        current = context.profile.path.name if context.profile is not None else None
        return web.json_response(
            {
                "profiles": [
                    {
                        "name": profile.path.name,
                        "game": _game_name(profile.rom),
                        "last_played": profile.last_played.isoformat() if profile.last_played else None,
                        "active": profile.path.name == current,
                    }
                    for profile in list_available_profiles()
                ]
            }
        )

    async def roms(_: web.Request) -> web.Response:
        return web.json_response(
            {
                "roms": [
                    {"file": rom.file.name, "game": _game_name(rom), "starters": rom.starter_names}
                    for rom in list_available_roms()
                    if rom.is_rse or rom.is_frlg
                ]
            }
        )

    async def create_profile_route(request: web.Request) -> web.Response:
        payload = await request.json()
        name, game = str(payload.get("name", "")).strip(), str(payload.get("game", ""))
        trainer_name = str(payload.get("trainer_name", "")).strip()
        trainer_gender = str(payload.get("trainer_gender", ""))
        starter = str(payload.get("starter", ""))
        if not name or len(name) > 80 or Path(name).name != name:
            raise web.HTTPBadRequest(text="invalid profile name")
        rom = next((item for item in list_available_roms() if _game_name(item) == game), None)
        if rom is None or not (rom.is_rse or rom.is_frlg):
            raise web.HTTPBadRequest(text="selected game has no available ROM")
        if not trainer_name or len(trainer_name) > 7:
            raise web.HTTPBadRequest(text="trainer name must contain 1 to 7 characters")
        if trainer_gender not in {"male", "female"}:
            raise web.HTTPBadRequest(text="invalid trainer gender")
        if starter not in rom.starter_names:
            raise web.HTTPBadRequest(text="starter is not available in selected game")
        try:
            profile = create_profile(
                name,
                rom,
                trainer_name=trainer_name,
                trainer_gender=trainer_gender,
                starter=starter,
            )
        except (exceptions.PrettyValueError, RuntimeError, ValueError) as error:
            raise web.HTTPConflict(text=str(error)) from error
        return web.json_response({"name": profile.path.name, "game": _game_name(profile.rom)}, status=201)

    async def start_profile_route(request: web.Request) -> web.Response:
        payload = await request.json()
        name = str(payload.get("name", ""))
        game = str(payload.get("game", ""))
        if not name or Path(name).name != name:
            raise web.HTTPBadRequest(text="invalid profile name")
        if not game:
            raise web.HTTPBadRequest(text="selected game is required")
        profile = next((item for item in list_available_profiles() if item.path.name == name), None)
        if profile is None:
            raise web.HTTPNotFound(text="profile not found")
        if _game_name(profile.rom) != game:
            raise web.HTTPConflict(text="profile does not belong to selected game")
        if context.profile is not None and name == context.profile.path.name:
            return web.json_response({"message": "profile already running"})

        speed = (
            int(context.emulation_speed)
            if context.emulator is not None
            else int(os.environ.get("POKEBOT_EMULATION_SPEED", "0"))
        )
        if context.emulator is not None:
            await _run_on_main(context.emulator.shutdown)

        _schedule_profile_restart(name, speed)
        return web.json_response({"message": f"starting profile {name}"}, status=202)

    async def stop_profile_route(request: web.Request) -> web.Response:
        name = str((await request.json()).get("name", ""))
        if context.profile is None or context.emulator is None:
            raise web.HTTPConflict(text="no profile is active")
        if name != context.profile.path.name:
            raise web.HTTPConflict(text="profile is not active in this container")

        speed = int(context.emulation_speed)

        def stop() -> None:
            context.set_manual_mode(enable_video_and_slow_down=False)
            context.emulator.reset_held_buttons()
            context.emulator.shutdown()

        await _run_on_main(stop, timeout=15)
        _schedule_profile_restart(None, speed)
        return web.json_response({"message": f"profile {name} stopped"}, status=202)

    async def reset_profile_route(request: web.Request) -> web.Response:
        payload = await request.json()
        name = str(payload.get("name", ""))
        if not name or Path(name).name != name or payload.get("confirmed") is not True:
            raise web.HTTPBadRequest(text="profile reset was not confirmed")
        profile = next((item for item in list_available_profiles() if item.path.name == name), None)
        if profile is None:
            raise web.HTTPNotFound(text="profile not found")
        speed = (
            int(context.emulation_speed)
            if context.emulator is not None
            else int(os.environ.get("POKEBOT_EMULATION_SPEED", "0"))
        )

        def clear() -> None:
            with MissionsDatabase(get_base_path() / "stats" / "missions.db") as database:
                database.clear_profile_progress(name)
            clear_profile_data(profile)

        if context.emulator is None:
            clear()
        else:
            def reset() -> None:
                context.set_manual_mode(enable_video_and_slow_down=False)
                context.emulator.reset_held_buttons()
                context.emulator.shutdown()
                clear()

            await _run_on_main(reset, timeout=15)
        _schedule_profile_restart(name, speed)
        return web.json_response({"message": f"profile {name} reset; starting new save"}, status=202)

    async def remove_profile_route(request: web.Request) -> web.Response:
        payload = await request.json()
        name = str(payload.get("name", ""))
        if not name or Path(name).name != name or payload.get("confirmed") is not True:
            raise web.HTTPBadRequest(text="profile removal was not confirmed")
        if context.profile is not None and name == context.profile.path.name:
            raise web.HTTPConflict(text="active profile cannot be removed")
        source = PROFILES_DIRECTORY / name
        if not source.is_dir() or source.parent.resolve() != PROFILES_DIRECTORY.resolve():
            raise web.HTTPNotFound(text="profile not found")
        trash = PROFILES_DIRECTORY / "_trash"
        trash.mkdir(exist_ok=True)
        os.replace(source, trash / f"{int(time.time())}-{name}")
        return web.json_response({"message": "profile moved to profiles/_trash"})

    async def state(request: web.Request) -> web.Response:
        require_active_profile(request)
        return web.json_response(await _run_on_main(_state))

    async def frame(request: web.Request) -> web.Response:
        require_active_profile(request)
        return web.Response(body=await _run_on_main(_frame), content_type="image/jpeg")

    async def stream(request: web.Request) -> web.StreamResponse:
        require_active_profile(request)
        response = web.StreamResponse(
            headers={
                "Content-Type": "multipart/x-mixed-replace; boundary=frame",
                "Cache-Control": "no-store, no-cache, must-revalidate",
                "Pragma": "no-cache",
                "X-Accel-Buffering": "no",
            }
        )
        await response.prepare(request)
        frame_interval = 1 / 60
        try:
            while True:
                started_at = asyncio.get_running_loop().time()
                image = await _run_on_main(_frame)
                await response.write(
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    + f"Content-Length: {len(image)}\r\n\r\n".encode()
                    + image
                    + b"\r\n"
                )
                elapsed = asyncio.get_running_loop().time() - started_at
                await asyncio.sleep(max(0, frame_interval - elapsed))
        except (asyncio.CancelledError, ConnectionError, RuntimeError):
            pass
        return response

    async def logs(request: web.Request) -> web.Response:
        require_active_profile(request)
        try:
            after = max(0, int(request.query.get("after", "0")))
        except ValueError as error:
            raise web.HTTPBadRequest(text="invalid log cursor") from error
        return web.json_response(web_log_buffer.snapshot(after))

    async def set_mode(request: web.Request) -> web.Response:
        require_active_profile(request)
        payload = await request.json()
        name = str(payload.get("mode", ""))

        def apply() -> dict:
            available = {item["name"]: item for item in _available_modes()}
            if name not in available or not available[name]["selectable"]:
                raise ValueError("bot mode is not selectable")
            if name == "Manual":
                context.set_manual_mode(enable_video_and_slow_down=False)
            else:
                context.bot_mode = name
            return {"mode": context.bot_mode}

        try:
            return web.json_response(await _run_on_main(apply))
        except ValueError as error:
            raise web.HTTPBadRequest(text=str(error)) from error

    async def set_speed(request: web.Request) -> web.Response:
        require_active_profile(request)
        try:
            speed = int((await request.json()).get("speed"))
        except (TypeError, ValueError) as error:
            raise web.HTTPBadRequest(text="invalid emulation speed") from error
        if speed not in ALLOWED_SPEEDS:
            raise web.HTTPBadRequest(text="invalid emulation speed")
        await _run_on_main(lambda: setattr(context, "emulation_speed", speed))
        return web.json_response({"speed": context.emulation_speed})

    async def control(request: web.Request) -> web.Response:
        require_active_profile(request)
        action = str((await request.json()).get("action", ""))

        def apply() -> dict:
            if action == "reset":
                context.emulator.reset()
            elif action == "save_state":
                context.emulator.create_save_state("Web")
            elif action == "toggle_video":
                context.toggle_video()
            elif action == "pause":
                context.set_manual_mode(enable_video_and_slow_down=False)
            else:
                raise ValueError("unknown emulator action")
            return {"message": action}

        try:
            return web.json_response(await _run_on_main(apply))
        except ValueError as error:
            raise web.HTTPBadRequest(text=str(error)) from error

    async def input_button(request: web.Request) -> web.Response:
        require_active_profile(request)
        payload = await request.json()
        button, action = str(payload.get("button", "")), str(payload.get("action", ""))
        if button not in ALLOWED_BUTTONS or action not in {"hold", "release", "press"}:
            raise web.HTTPBadRequest(text="invalid button action")

        def apply() -> None:
            if context.bot_mode != "Manual":
                context.set_manual_mode(enable_video_and_slow_down=False)
            if action == "hold":
                context.emulator.hold_button(button)
            elif action == "release":
                context.emulator.release_button(button)
            else:
                context.emulator.press_button(button)

        await _run_on_main(apply)
        return web.Response(status=204)

    async def load_state(request: web.Request) -> web.Response:
        require_active_profile(request)
        name = str((await request.json()).get("name", ""))
        try:
            await _run_on_main(lambda: _load_state(name))
        except ValueError as error:
            raise web.HTTPBadRequest(text=str(error)) from error
        return web.json_response({"message": "save state loaded"})

    app.add_routes(
        [
            web.get("/", dashboard),
            web.get("/healthz", health),
            web.get("/fleet/state", fleet_state),
            web.get("/api/profiles", profiles),
            web.get("/api/roms", roms),
            web.post("/api/profiles", create_profile_route),
            web.post("/api/profiles/start", start_profile_route),
            web.post("/api/profiles/stop", stop_profile_route),
            web.post("/api/profiles/reset", reset_profile_route),
            web.post("/api/profiles/remove", remove_profile_route),
            web.get("/state", state),
            web.get("/frame.jpg", frame),
            web.get("/stream.mjpeg", stream),
            web.get("/logs", logs),
            web.post("/mode", set_mode),
            web.post("/speed", set_speed),
            web.post("/control", control),
            web.post("/input", input_button),
            web.post("/load-state", load_state),
            web.get("/api/instances/{profile}/state", state),
            web.get("/api/instances/{profile}/frame.jpg", frame),
            web.get("/api/instances/{profile}/stream.mjpeg", stream),
            web.get("/api/instances/{profile}/logs", logs),
            web.post("/api/instances/{profile}/mode", set_mode),
            web.post("/api/instances/{profile}/speed", set_speed),
            web.post("/api/instances/{profile}/control", control),
            web.post("/api/instances/{profile}/input", input_button),
            web.post("/api/instances/{profile}/load-state", load_state),
        ]
    )
    app.router.add_static("/fleet/assets", static_root)
    app.router.add_static("/assets/sprites", sprites_root)
    return app


def start_instance_server(host: str = "0.0.0.0", port: int = 8888) -> None:
    def run() -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        runner = web.AppRunner(create_instance_app())
        loop.run_until_complete(runner.setup())
        loop.run_until_complete(web.TCPSite(runner, host, port).start())
        loop.run_forever()

    Thread(target=run, name="instance-web", daemon=True).start()
