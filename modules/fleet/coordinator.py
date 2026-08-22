from __future__ import annotations

import hmac
from contextlib import suppress
from pathlib import Path

import aiohttp
from aiohttp import web

from modules.fleet.config import FleetConfig
from modules.fleet.database import FleetDatabase, FleetSpecimen, LeaseUnavailable, TargetUnavailable
from modules.living_dex.goals import build_collection_targets, validate_collection_targets
from modules.living_dex.planner import load_acquisition_matrix, validate_acquisition_matrix
from modules.runtime import get_base_path

DATABASE_KEY = web.AppKey("fleet_database", FleetDatabase)


def create_coordinator_app(config: FleetConfig, database_path: Path, internal_token: str) -> web.Application:
    if len(internal_token) < 32:
        raise ValueError("internal token must contain at least 32 characters")
    database = FleetDatabase(database_path)
    database.sync_instances(config.instances)
    collection_targets = build_collection_targets()
    validate_collection_targets(collection_targets)
    database.sync_collection_targets(collection_targets)
    acquisition_options = load_acquisition_matrix()
    validate_acquisition_matrix(collection_targets, acquisition_options)
    database.sync_acquisition_options(acquisition_options)
    app = web.Application()
    app[DATABASE_KEY] = database
    static_root = get_base_path() / "modules" / "web" / "static" / "fleet"
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

    async def fleet_collection(_: web.Request) -> web.Response:
        return web.json_response(database.collection_summary())

    async def fleet_assignments(_: web.Request) -> web.Response:
        return web.json_response({"assignments": database.assignments()})

    async def dashboard(_: web.Request) -> web.FileResponse:
        return web.FileResponse(static_root / "index.html")

    async def fleet_video(request: web.Request) -> web.StreamResponse:
        profile = request.match_info["profile"]
        instance = instances_by_profile.get(profile)
        if instance is None:
            raise web.HTTPNotFound(text="unknown profile")
        hostname = "pokebot-" + "".join(
            character.lower() if character.isalnum() or character in "_-" else "-"
            for character in profile
        ).strip("-")
        session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=None, connect=3))
        upstream = None
        try:
            upstream = await session.get(f"http://{hostname}:8888/dashboard/video.mjpeg")
            if upstream.status != 200:
                raise web.HTTPBadGateway(text=f"video upstream returned {upstream.status}")
            response = web.StreamResponse(
                headers={
                    "Content-Type": "multipart/x-mixed-replace; boundary=frame",
                    "Cache-Control": "no-store",
                    "X-Content-Type-Options": "nosniff",
                }
            )
            await response.prepare(request)
            async for chunk in upstream.content.iter_chunked(64 * 1024):
                await response.write(chunk)
            return response
        except (aiohttp.ClientError, TimeoutError) as error:
            raise web.HTTPBadGateway(text=f"video upstream unavailable: {error}") from error
        finally:
            if upstream is not None:
                upstream.close()
            with suppress(RuntimeError):
                await session.close()

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

    async def reconcile(request: web.Request) -> web.Response:
        require_internal_token(request)
        payload = await request.json()
        profile = payload["profile"]
        if not database.lease_allows(payload["lease_token"], profile):
            raise web.HTTPConflict(text="active profile lease required")
        try:
            database.reconcile_specimens(profile, [FleetSpecimen(**item) for item in payload["specimens"]])
            database.prune_satisfied_assignments()
        except (TypeError, ValueError) as error:
            raise web.HTTPBadRequest(text=str(error)) from error
        return web.Response(status=204)

    async def acquire_target(request: web.Request) -> web.Response:
        require_internal_token(request)
        payload = await request.json()
        profile = payload["profile"]
        if not database.lease_allows(payload["lease_token"], profile):
            raise web.HTTPConflict(text="active profile lease required")
        try:
            assignment = database.acquire_target(
                profile,
                set(payload.get("completed_prerequisites", [])),
                ttl_seconds=payload.get("ttl", 120),
            )
        except TargetUnavailable as error:
            raise web.HTTPConflict(text=str(error)) from error
        except KeyError as error:
            raise web.HTTPNotFound(text="unknown profile") from error
        return web.json_response(assignment, status=201)

    async def release_target(request: web.Request) -> web.Response:
        require_internal_token(request)
        payload = await request.json()
        profile = payload["profile"]
        if not database.lease_allows(payload["lease_token"], profile):
            raise web.HTTPConflict(text="active profile lease required")
        if not database.release_target(payload["assignment_token"], profile):
            raise web.HTTPNotFound(text="assignment not found")
        return web.Response(status=204)

    async def renew_target(request: web.Request) -> web.Response:
        require_internal_token(request)
        payload = await request.json()
        profile = payload["profile"]
        if not database.lease_allows(payload["lease_token"], profile):
            raise web.HTTPConflict(text="active profile lease required")
        try:
            expires_at = database.renew_target(
                payload["assignment_token"],
                profile,
                ttl_seconds=payload.get("ttl", 120),
            )
        except TargetUnavailable as error:
            raise web.HTTPConflict(text=str(error)) from error
        return web.json_response({"expires_at": expires_at.isoformat()})

    app.add_routes(
        [
            web.get("/", dashboard),
            web.get("/fleet/state", fleet_state),
            web.get("/fleet/instances/{profile}", fleet_instance),
            web.get("/fleet/collection", fleet_collection),
            web.get("/fleet/assignments", fleet_assignments),
            web.get("/fleet/video/{profile}", fleet_video),
            web.post("/internal/leases", acquire),
            web.post("/internal/leases/renew", renew),
            web.post("/internal/leases/release", release),
            web.post("/internal/heartbeat", heartbeat),
            web.post("/internal/specimens/reconcile", reconcile),
            web.post("/internal/targets/acquire", acquire_target),
            web.post("/internal/targets/renew", renew_target),
            web.post("/internal/targets/release", release_target),
        ]
    )
    app.router.add_static("/fleet/assets", static_root)
    return app
