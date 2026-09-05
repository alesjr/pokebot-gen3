from __future__ import annotations

import hmac
import os
import time
from pathlib import Path

import aiohttp
from aiohttp import web

from modules import exceptions
from modules.fleet.config import FleetConfig
from modules.fleet.database import FleetDatabase, LeaseUnavailable
from modules.profiles import PROFILES_DIRECTORY, create_profile, list_available_profiles
from modules.roms import list_available_roms
from modules.runtime import get_base_path

DATABASE_KEY = web.AppKey("fleet_database", FleetDatabase)


def _game_name(rom) -> str:
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


def create_coordinator_app(config: FleetConfig, database_path: Path, internal_token: str) -> web.Application:
    if len(internal_token) < 32:
        raise ValueError("internal token must contain at least 32 characters")
    database = FleetDatabase(database_path)
    database.sync_instances(config.instances)
    app = web.Application()
    app[DATABASE_KEY] = database
    static_root = get_base_path() / "modules" / "web" / "static" / "fleet"
    sprites_root = get_base_path() / "modules" / "web" / "static" / "sprites"
    instances_by_profile = {item.profile: item for item in config.instances}

    async def close_database(_: web.Application) -> None:
        database.close()

    app.on_cleanup.append(close_database)

    def require_internal_token(request: web.Request) -> None:
        supplied = request.headers.get("Authorization", "").removeprefix("Bearer ")
        if not hmac.compare_digest(supplied, internal_token):
            raise web.HTTPUnauthorized(text="invalid internal token")

    async def fleet_state(_: web.Request) -> web.Response:
        return web.json_response({"instances": database.state()})

    async def fleet_instance(request: web.Request) -> web.Response:
        profile = request.match_info["profile"]
        instance = next((item for item in database.state() if item["profile"] == profile), None)
        if instance is None:
            raise web.HTTPNotFound(text="unknown profile")
        return web.json_response(instance)

    async def dashboard(_: web.Request) -> web.FileResponse:
        return web.FileResponse(static_root / "index.html")

    def instance_url(profile: str, suffix: str) -> str:
        if profile not in instances_by_profile:
            raise web.HTTPNotFound(text="profile has no running instance")
        hostname = "pokebot-" + "".join(
            character.lower() if character.isalnum() or character in "_-" else "-"
            for character in profile
        ).strip("-")
        return f"http://{hostname}:8888/{suffix.lstrip('/')}"

    async def proxy(request: web.Request) -> web.StreamResponse:
        profile = request.match_info["profile"]
        suffix = request.match_info["suffix"]
        url = instance_url(profile, suffix)
        body = await request.read()
        timeout = aiohttp.ClientTimeout(total=8)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.request(
                    request.method,
                    url,
                    params=request.query,
                    data=body or None,
                    headers={"Content-Type": request.content_type} if body else None,
                ) as upstream:
                    payload = await upstream.read()
                    return web.Response(
                        body=payload,
                        status=upstream.status,
                        content_type=upstream.content_type,
                    )
        except (aiohttp.ClientError, TimeoutError) as error:
            raise web.HTTPBadGateway(text=f"instance unavailable: {error}") from error

    async def profiles(_: web.Request) -> web.Response:
        active = {item.profile: item for item in config.instances}
        items = []
        for profile in list_available_profiles():
            fleet = active.get(profile.path.name)
            items.append(
                {
                    "name": profile.path.name,
                    "game": _game_name(profile.rom),
                    "last_played": profile.last_played.isoformat() if profile.last_played else None,
                    "active": fleet is not None,
                }
            )
        return web.json_response({"profiles": items})

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

    async def remove_profile_route(request: web.Request) -> web.Response:
        payload = await request.json()
        name, confirmation = str(payload.get("name", "")), str(payload.get("confirmation", ""))
        if not name or Path(name).name != name or confirmation != name:
            raise web.HTTPBadRequest(text="profile confirmation does not match")
        instance = next((item for item in database.state() if item["profile"] == name), None)
        if instance is not None and (instance["status"] == "running" or instance["lease_owner"] is not None):
            raise web.HTTPConflict(text="stop active instance before removing profile")
        source = PROFILES_DIRECTORY / name
        if not source.is_dir() or source.parent.resolve() != PROFILES_DIRECTORY.resolve():
            raise web.HTTPNotFound(text="profile not found")
        trash = PROFILES_DIRECTORY / "_trash"
        trash.mkdir(exist_ok=True)
        destination = trash / f"{int(time.time())}-{name}"
        os.replace(source, destination)
        return web.json_response({"message": "profile moved to profiles/_trash"})

    async def acquire(request: web.Request) -> web.Response:
        require_internal_token(request)
        payload = await request.json()
        try:
            lease = database.acquire_lease(
                payload["profile"], payload["owner"], payload["purpose"], ttl_seconds=payload.get("ttl", 30)
            )
        except LeaseUnavailable as error:
            raise web.HTTPConflict(text=str(error)) from error
        return web.json_response(
            {
                "profile": lease.profile,
                "owner": lease.owner,
                "purpose": lease.purpose,
                "lease_token": lease.token,
                "expires_at": lease.expires_at.isoformat(),
            },
            status=201,
        )

    async def renew(request: web.Request) -> web.Response:
        require_internal_token(request)
        payload = await request.json()
        try:
            expires_at = database.renew_lease(payload["lease_token"], ttl_seconds=payload.get("ttl", 30))
        except LeaseUnavailable as error:
            raise web.HTTPConflict(text=str(error)) from error
        return web.json_response({"expires_at": expires_at.isoformat()})

    async def release(request: web.Request) -> web.Response:
        require_internal_token(request)
        payload = await request.json()
        if not database.release_lease(payload["lease_token"]):
            raise web.HTTPNotFound(text="lease not found")
        return web.Response(status=204)

    async def heartbeat(request: web.Request) -> web.Response:
        require_internal_token(request)
        payload = await request.json()
        if not database.lease_allows(payload["lease_token"], payload["profile"]):
            raise web.HTTPConflict(text="active profile lease required")
        try:
            database.heartbeat(
                payload["profile"],
                status=payload["status"],
                objective=payload.get("objective"),
                emulator_frame=payload["emulator_frame"],
            )
        except KeyError as error:
            raise web.HTTPNotFound(text="unknown profile") from error
        return web.Response(status=204)

    app.add_routes(
        [
            web.get("/", dashboard),
            web.get("/healthz", fleet_state),
            web.get("/fleet/state", fleet_state),
            web.get("/fleet/instances/{profile}", fleet_instance),
            web.get("/api/profiles", profiles),
            web.get("/api/roms", roms),
            web.post("/api/profiles", create_profile_route),
            web.post("/api/profiles/remove", remove_profile_route),
            web.route("*", "/api/instances/{profile}/{suffix:.*}", proxy),
            web.post("/internal/leases", acquire),
            web.post("/internal/leases/renew", renew),
            web.post("/internal/leases/release", release),
            web.post("/internal/heartbeat", heartbeat),
        ]
    )
    app.router.add_static("/fleet/assets", static_root)
    app.router.add_static("/assets/sprites", sprites_root)
    return app
