"""Read-only Living Dex dashboard.

No emulator-control route is intentionally exposed here. The server is suitable
for a trusted home LAN and therefore has no authentication layer.
"""

from __future__ import annotations

import asyncio
from threading import Thread

from aiohttp import web

from modules.living_dex.dashboard import snapshot_via_main_thread
from modules.runtime import get_base_path


def http_server(host: str, port: int) -> web.AppRunner:
    app = web.Application()
    routes = web.RouteTableDef()
    static_root = get_base_path() / "modules" / "web" / "static" / "dashboard"

    @routes.get("/")
    @routes.get("/dashboard")
    async def dashboard(_: web.Request) -> web.FileResponse:
        return web.FileResponse(static_root / "index.html")

    @routes.get("/dashboard/state")
    async def state(_: web.Request) -> web.Response:
        return web.json_response(await asyncio.to_thread(snapshot_via_main_thread))

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

    Thread(target=run_server, name="living-dex-dashboard", daemon=True).start()
