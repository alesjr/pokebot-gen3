from __future__ import annotations

import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds")


@dataclass(frozen=True)
class ProfileLease:
    profile: str
    owner: str
    purpose: str
    token: str
    expires_at: datetime


class LeaseUnavailable(RuntimeError):
    pass


class FleetDatabase:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(path, timeout=5, isolation_level=None)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA foreign_keys=ON")
        self._migrate()

    def close(self) -> None:
        self._connection.close()

    def _migrate(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS fleet_instances (
                profile TEXT PRIMARY KEY,
                game TEXT NOT NULL,
                port INTEGER NOT NULL UNIQUE,
                status TEXT NOT NULL DEFAULT 'offline',
                objective TEXT,
                emulator_frame INTEGER,
                heartbeat_at TEXT
            );
            CREATE TABLE IF NOT EXISTS profile_leases (
                profile TEXT PRIMARY KEY,
                owner TEXT NOT NULL,
                purpose TEXT NOT NULL,
                token TEXT NOT NULL UNIQUE,
                acquired_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY(profile) REFERENCES fleet_instances(profile)
            );
            """
        )

    def sync_instances(self, instances) -> None:
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            for item in instances:
                self._connection.execute(
                    """
                    INSERT INTO fleet_instances(profile, game, port)
                    VALUES (?, ?, ?)
                    ON CONFLICT(profile) DO UPDATE SET game=excluded.game, port=excluded.port
                    """,
                    (item.profile, item.game, item.port),
                )
            self._connection.commit()
        except BaseException:
            self._connection.rollback()
            raise

    def acquire_lease(
        self,
        profile: str,
        owner: str,
        purpose: str,
        *,
        ttl_seconds: int = 30,
        now: datetime | None = None,
    ) -> ProfileLease:
        acquired_at = now or _utc_now()
        expires_at = acquired_at + timedelta(seconds=ttl_seconds)
        token = secrets.token_urlsafe(32)
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            self._connection.execute(
                "DELETE FROM profile_leases WHERE profile = ? AND expires_at <= ?",
                (profile, _timestamp(acquired_at)),
            )
            self._connection.execute(
                "DELETE FROM profile_leases WHERE profile = ? AND owner = ?",
                (profile, owner),
            )
            try:
                self._connection.execute(
                    """
                    INSERT INTO profile_leases(profile, owner, purpose, token, acquired_at, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (profile, owner, purpose, token, _timestamp(acquired_at), _timestamp(expires_at)),
                )
            except sqlite3.IntegrityError as error:
                raise LeaseUnavailable(f"profile already leased: {profile}") from error
            self._connection.commit()
        except BaseException:
            self._connection.rollback()
            raise
        return ProfileLease(profile, owner, purpose, token, expires_at)

    def renew_lease(
        self, token: str, *, ttl_seconds: int = 30, now: datetime | None = None
    ) -> datetime:
        current = now or _utc_now()
        expires_at = current + timedelta(seconds=ttl_seconds)
        cursor = self._connection.execute(
            """
            UPDATE profile_leases SET expires_at = ?
            WHERE token = ? AND expires_at > ?
            """,
            (_timestamp(expires_at), token, _timestamp(current)),
        )
        if cursor.rowcount != 1:
            raise LeaseUnavailable("lease missing or expired")
        return expires_at

    def release_lease(self, token: str) -> bool:
        cursor = self._connection.execute("DELETE FROM profile_leases WHERE token = ?", (token,))
        return cursor.rowcount == 1

    def lease_allows(self, token: str, profile: str, *, now: datetime | None = None) -> bool:
        return self._connection.execute(
            "SELECT 1 FROM profile_leases WHERE token = ? AND profile = ? AND expires_at > ?",
            (token, profile, _timestamp(now or _utc_now())),
        ).fetchone() is not None

    def heartbeat(self, profile: str, *, status: str, objective: str | None, emulator_frame: int) -> None:
        cursor = self._connection.execute(
            """
            UPDATE fleet_instances
            SET status = ?, objective = ?, emulator_frame = ?, heartbeat_at = ?
            WHERE profile = ?
            """,
            (status, objective, emulator_frame, _timestamp(_utc_now()), profile),
        )
        if cursor.rowcount != 1:
            raise KeyError(profile)

    def state(self) -> list[dict]:
        rows = self._connection.execute(
            """
            SELECT instances.*, leases.owner AS lease_owner, leases.purpose AS lease_purpose,
                   leases.expires_at AS lease_expires_at
            FROM fleet_instances AS instances
            LEFT JOIN profile_leases AS leases ON leases.profile = instances.profile
            ORDER BY instances.port
            """
        ).fetchall()
        return [dict(row) for row in rows]
