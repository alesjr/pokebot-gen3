"""Read-only Living Dex dashboard.

No emulator-control route is intentionally exposed here. The server is suitable
for a trusted home LAN and therefore has no authentication layer.
"""

from __future__ import annotations

import asyncio
from contextlib import suppress
from threading import Thread

from aiohttp import web

from modules.context import context
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

    @routes.get("/dashboard/video.mjpeg")
    async def video(request: web.Request) -> web.StreamResponse:
        stream = context.video_stream
        if stream is None:
            raise web.HTTPServiceUnavailable(text="video stream unavailable")

        response = web.StreamResponse(
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate",
                "Content-Type": "multipart/x-mixed-replace; boundary=frame",
                "X-Content-Type-Options": "nosniff",
            }
        )
        await response.prepare(request)
        sequence = 0
        try:
            with stream.subscribe():
                while True:
                    sequence, jpeg = await asyncio.to_thread(stream.wait_for_jpeg, sequence)
                    if jpeg is None:
                        continue
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

    Thread(target=run_server, name="living-dex-dashboard", daemon=True).start()
