"""Authenticated remote emulator dashboard."""

from __future__ import annotations

import asyncio
import html
import os
from contextlib import suppress
from threading import Thread

from aiohttp import web
from pydantic import ValidationError

from modules.context import context
from modules.living_dex.dashboard import snapshot_via_main_thread
from modules.runtime import get_base_path
from modules.runtime_log import runtime_log
from modules.web.control import (
    emulator_action,
    list_profile_files,
    list_profiles,
    load_profile_file,
    read_living_dex_config,
    send_button,
    update_living_dex_config,
    reset_profile,
)
from modules.web.security import DashboardSecurity, SESSION_COOKIE, secure_headers


def http_server(host: str, port: int, security: DashboardSecurity | None = None) -> web.AppRunner:
    security = security or DashboardSecurity.from_environment()
    static_root = get_base_path() / "modules" / "web" / "static" / "dashboard"

    @web.middleware
    async def security_middleware(request: web.Request, handler):
        public = request.path in {"/login", "/login.css", "/healthz"}
        if not public and security.session(request) is None:
            if request.path.startswith(("/api/", "/dashboard/")):
                raise web.HTTPUnauthorized(text="Autenticação necessária.")
            raise web.HTTPFound("/login")
        response = await handler(request)
        secure_headers(response)
        return response

    app = web.Application(middlewares=[security_middleware], client_max_size=64 * 1024)
    routes = web.RouteTableDef()

    @routes.get("/login")
    async def login_page(_: web.Request) -> web.Response:
        template = (static_root / "login.html").read_text()
        return web.Response(text=template.replace("{{ERROR}}", ""), content_type="text/html")

    @routes.get("/login.css")
    async def login_css(_: web.Request) -> web.FileResponse:
        return web.FileResponse(static_root / "login.css")

    @routes.get("/healthz")
    async def health(_: web.Request) -> web.Response:
        return web.json_response({"status": "ok"})

    @routes.post("/login")
    async def login(request: web.Request) -> web.Response:
        data = await request.post()
        username, password = str(data.get("username", ""))[:64], str(data.get("password", ""))[:256]
        authenticated = await asyncio.to_thread(security.authenticate, username, password, request.remote or "unknown")
        if authenticated is None:
            template = (static_root / "login.html").read_text()
            return web.Response(
                text=template.replace("{{ERROR}}", html.escape("Usuário ou senha inválidos.")),
                content_type="text/html",
                status=401,
            )
        token, _ = authenticated
        response = web.HTTPFound("/")
        response.set_cookie(
            SESSION_COOKIE,
            token,
            httponly=True,
            secure=os.environ.get("POKEBOT_COOKIE_SECURE", "1") != "0",
            samesite="Strict",
            max_age=12 * 60 * 60,
            path="/",
        )
        return response

    @routes.post("/logout")
    async def logout(request: web.Request) -> web.Response:
        security.require_csrf(request)
        security.logout(request)
        response = web.json_response({"message": "Sessão encerrada."})
        response.del_cookie(SESSION_COOKIE, path="/")
        return response

    @routes.get("/")
    @routes.get("/dashboard")
    async def dashboard(_: web.Request) -> web.FileResponse:
        return web.FileResponse(static_root / "index.html")

    @routes.get("/api/session")
    async def session(request: web.Request) -> web.Response:
        return web.json_response({"csrf_token": security.session(request).csrf_token})

    @routes.get("/dashboard/state")
    async def state(_: web.Request) -> web.Response:
        return web.json_response(await asyncio.to_thread(snapshot_via_main_thread))

    @routes.get("/api/config")
    async def config(_: web.Request) -> web.Response:
        return web.json_response(await asyncio.to_thread(read_living_dex_config))

    @routes.get("/api/logs")
    async def logs(request: web.Request) -> web.Response:
        try:
            after = max(0, int(request.query.get("after", "0")))
        except ValueError as error:
            raise web.HTTPBadRequest(text="Cursor de log inválido.") from error
        return web.json_response(runtime_log.snapshot(after))

    @routes.get("/api/files")
    async def files(_: web.Request) -> web.Response:
        return web.json_response(await asyncio.to_thread(list_profile_files))

    @routes.post("/api/load")
    async def load_file(request: web.Request) -> web.Response:
        security.require_csrf(request)
        payload = await request.json()
        try:
            result = await asyncio.to_thread(load_profile_file, payload.get("kind"), payload.get("name"))
        except (AttributeError, ValueError, TimeoutError) as error:
            raise web.HTTPBadRequest(text=str(error)) from error
        return web.json_response(result)

    @routes.get("/api/profiles")
    async def profiles(_: web.Request) -> web.Response:
        return web.json_response(await asyncio.to_thread(list_profiles))

    @routes.post("/api/profiles/reset")
    async def clear_profile(request: web.Request) -> web.Response:
        security.require_csrf(request)
        payload = await request.json()
        try:
            result = await asyncio.to_thread(
                reset_profile,
                payload.get("profile"),
                payload.get("confirmation"),
            )
        except (AttributeError, ValueError, TimeoutError) as error:
            raise web.HTTPBadRequest(text=str(error)) from error
        return web.json_response(result)

    @routes.put("/api/config")
    async def save_config(request: web.Request) -> web.Response:
        security.require_csrf(request)
        try:
            payload = await request.json()
            if not isinstance(payload, dict):
                raise ValueError("Configuração deve ser objeto JSON.")
            result = await asyncio.to_thread(update_living_dex_config, payload)
        except (ValidationError, ValueError) as error:
            raise web.HTTPBadRequest(text=str(error)) from error
        return web.json_response({"message": "Configuração salva e recarregada.", "config": result})

    @routes.post("/api/control")
    async def control(request: web.Request) -> web.Response:
        security.require_csrf(request)
        payload = await request.json()
        try:
            result = await asyncio.to_thread(emulator_action, payload.get("action"), payload.get("speed"))
        except (AttributeError, ValueError, TimeoutError) as error:
            raise web.HTTPBadRequest(text=str(error)) from error
        return web.json_response(result)

    @routes.post("/api/input")
    async def input_command(request: web.Request) -> web.Response:
        security.require_csrf(request)
        payload = await request.json()
        try:
            await asyncio.to_thread(send_button, payload.get("button"), payload.get("action"))
        except (AttributeError, ValueError, TimeoutError) as error:
            raise web.HTTPBadRequest(text=str(error)) from error
        return web.json_response({"ok": True})

    @routes.get("/dashboard/video.mjpeg")
    async def video(request: web.Request) -> web.StreamResponse:
        stream = context.video_stream
        if stream is None:
            raise web.HTTPServiceUnavailable(text="video stream unavailable")
        response = web.StreamResponse(headers={"Content-Type": "multipart/x-mixed-replace; boundary=frame"})
        secure_headers(response)
        await response.prepare(request)
        sequence = 0
        try:
            with stream.subscribe():
                while True:
                    sequence, jpeg = await asyncio.to_thread(stream.wait_for_jpeg, sequence)
                    if jpeg is not None:
                        await response.write(
                            b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                            + str(len(jpeg)).encode("ascii")
                            + b"\r\n\r\n"
                            + jpeg
                            + b"\r\n"
                        )
        except (ConnectionError, asyncio.CancelledError):
            pass
        finally:
            with suppress(ConnectionError, RuntimeError):
                await response.write_eof()
        return response

    routes.static("/dashboard/assets", static_root)
    app.add_routes(routes)
    return web.AppRunner(app)


def start_http_server(host: str, port: int) -> None:
    runner = http_server(host, port)

    def run_server() -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(runner.setup())
        loop.run_until_complete(web.TCPSite(runner, host, port).start())
        loop.run_forever()

    Thread(target=run_server, name="pokebot-dashboard", daemon=True).start()
