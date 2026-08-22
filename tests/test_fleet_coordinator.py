import tempfile
import asyncio
from pathlib import Path

from aiohttp.test_utils import AioHTTPTestCase

from modules.fleet.config import load_fleet_config
from modules.fleet.coordinator import create_coordinator_app
from modules.fleet.client import FleetClient


class TestFleetCoordinator(AioHTTPTestCase):
    async def get_application(self):
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(__file__).parents[1]
        config = load_fleet_config(root / "fleet.yml")
        return create_coordinator_app(
            config,
            Path(self.temporary.name) / "fleet.db",
            "test-token-with-at-least-32-characters",
        )

    async def asyncTearDown(self):
        await super().asyncTearDown()
        self.temporary.cleanup()

    async def test_public_routes_are_read_only_snapshots(self):
        response = await self.client.get("/")
        self.assertEqual(response.status, 200)
        self.assertIn("Living Dex Gen III", await response.text())

        response = await self.client.get("/fleet/state")
        self.assertEqual(response.status, 200)
        payload = await response.json()
        self.assertEqual(len(payload["instances"]), 5)

        response = await self.client.get("/fleet/collection")
        self.assertEqual(response.status, 200)
        collection = await response.json()
        self.assertGreater(collection["targets"], 386)
        self.assertEqual(collection["satisfied"], 0)

        response = await self.client.get("/fleet/instances/LivingDex-Ruby")
        self.assertEqual(response.status, 200)
        self.assertEqual((await response.json())["game"], "Ruby")

        response = await self.client.get("/fleet/video/unknown")
        self.assertEqual(response.status, 404)

    async def test_internal_write_requires_token(self):
        payload = {"profile": "LivingDex-Ruby", "owner": "bot", "purpose": "bot"}
        response = await self.client.post("/internal/leases", json=payload)
        self.assertEqual(response.status, 401)

        response = await self.client.post(
            "/internal/leases",
            json=payload,
            headers={"Authorization": "Bearer test-token-with-at-least-32-characters"},
        )
        self.assertEqual(response.status, 201)
        self.assertIn("lease_token", await response.json())

    async def test_bot_client_acquires_heartbeats_and_releases(self):
        client = FleetClient(
            str(self.server.make_url("/")),
            "test-token-with-at-least-32-characters",
            "LivingDex-Emerald",
            heartbeat_interval=0,
        )
        await asyncio.to_thread(client.acquire, "bot:emerald")
        self.assertTrue(
            await asyncio.to_thread(
                client.heartbeat_if_due,
                status="running",
                objective="starter hunt",
                emulator_frame=123,
            )
        )
        response = await self.client.get("/fleet/instances/LivingDex-Emerald")
        state = await response.json()
        self.assertEqual(state["lease_owner"], "bot:emerald")
        self.assertEqual(state["emulator_frame"], 123)
        await asyncio.to_thread(
            client.reconcile_specimens,
            [
                {
                    "personality_value": 25,
                    "species": "Pikachu",
                    "national_dex_number": 25,
                    "ot_name": "Alesjr",
                    "trainer_id": 1,
                    "secret_id": 2,
                    "profile": "LivingDex-Emerald",
                    "gender": "female",
                    "form": "any",
                    "shiny": True,
                    "official_event": False,
                }
            ],
        )
        response = await self.client.get("/fleet/collection")
        self.assertEqual((await response.json())["specimens"], 1)
        assignment = await asyncio.to_thread(client.acquire_target, set())
        self.assertEqual(assignment["profile"], "LivingDex-Emerald")
        response = await self.client.get("/fleet/assignments")
        self.assertEqual(len((await response.json())["assignments"]), 1)
        await asyncio.to_thread(client.release_target, assignment["assignment_token"])
        await asyncio.to_thread(client.release)
