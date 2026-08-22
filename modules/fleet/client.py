from __future__ import annotations

import json
import time
import urllib.error
import urllib.request


class FleetClient:
    def __init__(self, base_url: str, internal_token: str, profile: str, *, heartbeat_interval: float = 5.0):
        self._base_url = base_url.rstrip("/")
        self._internal_token = internal_token
        self._profile = profile
        self._heartbeat_interval = heartbeat_interval
        self._next_heartbeat = 0.0
        self._lease_token: str | None = None

    def acquire(self, owner: str, purpose: str = "bot") -> None:
        response = self._request(
            "/internal/leases",
            {"profile": self._profile, "owner": owner, "purpose": purpose, "ttl": 30},
        )
        self._lease_token = response["lease_token"]

    def heartbeat_if_due(self, *, status: str, objective: str | None, emulator_frame: int) -> bool:
        now = time.monotonic()
        if now < self._next_heartbeat:
            return False
        if self._lease_token is None:
            raise RuntimeError("fleet lease not acquired")
        self._request("/internal/leases/renew", {"lease_token": self._lease_token, "ttl": 30})
        self._request(
            "/internal/heartbeat",
            {
                "profile": self._profile,
                "lease_token": self._lease_token,
                "status": status,
                "objective": objective,
                "emulator_frame": emulator_frame,
            },
        )
        self._next_heartbeat = now + self._heartbeat_interval
        return True

    def reconcile_specimens(self, specimens: list[dict]) -> None:
        if self._lease_token is None:
            raise RuntimeError("fleet lease not acquired")
        self._request(
            "/internal/specimens/reconcile",
            {"profile": self._profile, "lease_token": self._lease_token, "specimens": specimens},
        )

    def acquire_target(self, completed_prerequisites: set[str], *, ttl: int = 120) -> dict:
        if self._lease_token is None:
            raise RuntimeError("fleet lease not acquired")
        return self._request(
            "/internal/targets/acquire",
            {
                "profile": self._profile,
                "lease_token": self._lease_token,
                "completed_prerequisites": sorted(completed_prerequisites),
                "ttl": ttl,
            },
        )

    def release_target(self, assignment_token: str) -> None:
        if self._lease_token is None:
            raise RuntimeError("fleet lease not acquired")
        self._request(
            "/internal/targets/release",
            {
                "profile": self._profile,
                "lease_token": self._lease_token,
                "assignment_token": assignment_token,
            },
        )

    def renew_target(self, assignment_token: str, *, ttl: int = 120) -> str:
        if self._lease_token is None:
            raise RuntimeError("fleet lease not acquired")
        response = self._request(
            "/internal/targets/renew",
            {
                "profile": self._profile,
                "lease_token": self._lease_token,
                "assignment_token": assignment_token,
                "ttl": ttl,
            },
        )
        return response["expires_at"]

    def release(self) -> None:
        if self._lease_token is None:
            return
        token, self._lease_token = self._lease_token, None
        try:
            self._request("/internal/leases/release", {"lease_token": token})
        except (OSError, RuntimeError):
            pass

    def _request(self, path: str, payload: dict) -> dict:
        request = urllib.request.Request(
            self._base_url + path,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._internal_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=3) as response:
                body = response.read()
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"fleet coordinator rejected request: {error.code}: {detail}") from error
        return json.loads(body) if body else {}
