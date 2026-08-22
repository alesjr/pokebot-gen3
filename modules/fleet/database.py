from __future__ import annotations

import secrets
import sqlite3
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from modules.living_dex.goals import CollectionTarget
from modules.living_dex.planner import AcquisitionOption


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


class TargetUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class FleetSpecimen:
    personality_value: int
    species: str
    national_dex_number: int
    ot_name: str
    trainer_id: int
    secret_id: int
    profile: str
    gender: str
    form: str
    shiny: bool
    official_event: bool = False


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
            CREATE TABLE IF NOT EXISTS collection_targets (
                national_dex_number INTEGER NOT NULL,
                species TEXT NOT NULL,
                variant TEXT NOT NULL,
                shiny_required INTEGER NOT NULL,
                official_event_required INTEGER NOT NULL,
                PRIMARY KEY(national_dex_number, variant)
            );
            CREATE TABLE IF NOT EXISTS fleet_specimens (
                personality_value INTEGER NOT NULL,
                species TEXT NOT NULL,
                national_dex_number INTEGER NOT NULL,
                ot_name TEXT NOT NULL,
                trainer_id INTEGER NOT NULL,
                secret_id INTEGER NOT NULL,
                profile TEXT NOT NULL,
                gender TEXT NOT NULL,
                form TEXT NOT NULL,
                shiny INTEGER NOT NULL,
                official_event INTEGER NOT NULL DEFAULT 0,
                observed_at TEXT NOT NULL,
                PRIMARY KEY(personality_value, ot_name, trainer_id, secret_id)
            );
            CREATE TABLE IF NOT EXISTS acquisition_options (
                id INTEGER PRIMARY KEY,
                game TEXT NOT NULL,
                species TEXT NOT NULL,
                variant TEXT NOT NULL,
                method TEXT NOT NULL,
                location TEXT NOT NULL,
                cost INTEGER NOT NULL,
                prerequisites TEXT NOT NULL,
                UNIQUE(game, species, variant, method, location, prerequisites)
            );
            CREATE TABLE IF NOT EXISTS target_assignments (
                national_dex_number INTEGER NOT NULL,
                variant TEXT NOT NULL,
                profile TEXT NOT NULL,
                option_id INTEGER NOT NULL,
                token TEXT NOT NULL UNIQUE,
                assigned_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                PRIMARY KEY(national_dex_number, variant),
                FOREIGN KEY(profile) REFERENCES fleet_instances(profile),
                FOREIGN KEY(option_id) REFERENCES acquisition_options(id)
            );
            """
        )

    def sync_acquisition_options(self, options: tuple[AcquisitionOption, ...]) -> None:
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            self._connection.executemany(
                """
                INSERT INTO acquisition_options(
                    game, species, variant, method, location, cost, prerequisites
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(game, species, variant, method, location, prerequisites)
                DO UPDATE SET cost=excluded.cost
                """,
                [
                    (
                        option.game,
                        option.species,
                        option.variant,
                        option.method,
                        option.location,
                        option.cost,
                        json.dumps(option.prerequisites),
                    )
                    for option in options
                ],
            )
            self._connection.commit()
        except BaseException:
            self._connection.rollback()
            raise

    def sync_collection_targets(self, targets: tuple[CollectionTarget, ...]) -> None:
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            self._connection.executemany(
                """
                INSERT INTO collection_targets(
                    national_dex_number, species, variant, shiny_required, official_event_required
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(national_dex_number, variant) DO UPDATE SET
                    species=excluded.species,
                    shiny_required=excluded.shiny_required,
                    official_event_required=excluded.official_event_required
                """,
                [
                    (
                        target.national_dex_number,
                        target.species,
                        target.variant,
                        int(target.shiny_required),
                        int(target.official_event_required),
                    )
                    for target in targets
                ],
            )
            self._connection.commit()
        except BaseException:
            self._connection.rollback()
            raise

    def register_specimen(self, specimen: FleetSpecimen) -> bool:
        cursor = self._connection.execute(
            """
            INSERT INTO fleet_specimens(
                personality_value, species, national_dex_number, ot_name, trainer_id, secret_id,
                profile, gender, form, shiny, official_event, observed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(personality_value, ot_name, trainer_id, secret_id) DO UPDATE SET
                profile=excluded.profile, gender=excluded.gender, form=excluded.form,
                shiny=excluded.shiny, official_event=excluded.official_event,
                observed_at=excluded.observed_at
            """,
            (
                specimen.personality_value,
                specimen.species,
                specimen.national_dex_number,
                specimen.ot_name,
                specimen.trainer_id,
                specimen.secret_id,
                specimen.profile,
                specimen.gender,
                specimen.form,
                int(specimen.shiny),
                int(specimen.official_event),
                _timestamp(_utc_now()),
            ),
        )
        return cursor.rowcount == 1

    def reconcile_specimens(self, profile: str, specimens: list[FleetSpecimen]) -> None:
        if any(specimen.profile != profile for specimen in specimens):
            raise ValueError("all specimens must belong to reconciled profile")
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            self._connection.execute("DELETE FROM fleet_specimens WHERE profile = ?", (profile,))
            for specimen in specimens:
                self.register_specimen(specimen)
            self._connection.commit()
        except BaseException:
            self._connection.rollback()
            raise

    def collection_summary(self) -> dict:
        targets = self._connection.execute(
            "SELECT * FROM collection_targets ORDER BY national_dex_number, variant"
        ).fetchall()
        specimens = self._connection.execute("SELECT * FROM fleet_specimens").fetchall()

        def satisfied(target: sqlite3.Row) -> bool:
            for specimen in specimens:
                if specimen["national_dex_number"] != target["national_dex_number"]:
                    continue
                if target["shiny_required"] and not specimen["shiny"]:
                    continue
                if target["official_event_required"] and not specimen["official_event"]:
                    continue
                if target["variant"] != "any" and target["variant"] not in (
                    specimen["gender"], specimen["form"]
                ):
                    continue
                return True
            return False

        missing = [dict(target) for target in targets if not satisfied(target)]
        return {
            "targets": len(targets),
            "satisfied": len(targets) - len(missing),
            "missing": missing,
            "specimens": len(specimens),
        }

    def acquire_target(
        self,
        profile: str,
        completed_prerequisites: set[str],
        *,
        ttl_seconds: int = 120,
        now: datetime | None = None,
    ) -> dict:
        current = now or _utc_now()
        expires_at = current + timedelta(seconds=ttl_seconds)
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            self._connection.execute(
                "DELETE FROM target_assignments WHERE expires_at <= ?", (_timestamp(current),)
            )
            game_row = self._connection.execute(
                "SELECT game FROM fleet_instances WHERE profile = ?", (profile,)
            ).fetchone()
            if game_row is None:
                raise KeyError(profile)
            missing = self.collection_summary()["missing"]
            assigned = {
                (row["national_dex_number"], row["variant"])
                for row in self._connection.execute(
                    "SELECT national_dex_number, variant FROM target_assignments"
                )
            }
            candidates = []
            for target in missing:
                identity = (target["national_dex_number"], target["variant"])
                if identity in assigned:
                    continue
                rows = self._connection.execute(
                    """
                    SELECT * FROM acquisition_options
                    WHERE game = ? AND species = ? AND (variant = ? OR variant = 'any')
                    ORDER BY cost, location, id
                    """,
                    (game_row["game"], target["species"], target["variant"]),
                ).fetchall()
                option = next(
                    (
                        row
                        for row in rows
                        if set(json.loads(row["prerequisites"])).issubset(completed_prerequisites)
                    ),
                    None,
                )
                if option is not None:
                    candidates.append((option["cost"], identity, target, option))
            if not candidates:
                raise TargetUnavailable(f"no eligible target for profile: {profile}")
            _, identity, target, option = min(candidates, key=lambda item: (item[0], item[1]))
            token = secrets.token_urlsafe(32)
            self._connection.execute(
                """
                INSERT INTO target_assignments(
                    national_dex_number, variant, profile, option_id, token, assigned_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (*identity, profile, option["id"], token, _timestamp(current), _timestamp(expires_at)),
            )
            self._connection.commit()
        except BaseException:
            self._connection.rollback()
            raise
        return {
            "national_dex_number": target["national_dex_number"],
            "species": target["species"],
            "variant": target["variant"],
            "profile": profile,
            "method": option["method"],
            "location": option["location"],
            "prerequisites": json.loads(option["prerequisites"]),
            "assignment_token": token,
            "expires_at": expires_at.isoformat(),
        }

    def release_target(self, token: str, profile: str) -> bool:
        cursor = self._connection.execute(
            "DELETE FROM target_assignments WHERE token = ? AND profile = ?", (token, profile)
        )
        return cursor.rowcount == 1

    def renew_target(
        self,
        token: str,
        profile: str,
        *,
        ttl_seconds: int = 120,
        now: datetime | None = None,
    ) -> datetime:
        current = now or _utc_now()
        expires_at = current + timedelta(seconds=ttl_seconds)
        cursor = self._connection.execute(
            """
            UPDATE target_assignments SET expires_at = ?
            WHERE token = ? AND profile = ? AND expires_at > ?
            """,
            (_timestamp(expires_at), token, profile, _timestamp(current)),
        )
        if cursor.rowcount != 1:
            raise TargetUnavailable("target assignment missing or expired")
        return expires_at

    def prune_satisfied_assignments(self) -> int:
        missing = {
            (item["national_dex_number"], item["variant"])
            for item in self.collection_summary()["missing"]
        }
        rows = self._connection.execute(
            "SELECT national_dex_number, variant FROM target_assignments"
        ).fetchall()
        satisfied = [
            (row["national_dex_number"], row["variant"])
            for row in rows
            if (row["national_dex_number"], row["variant"]) not in missing
        ]
        self._connection.executemany(
            "DELETE FROM target_assignments WHERE national_dex_number = ? AND variant = ?",
            satisfied,
        )
        return len(satisfied)

    def assignments(self, *, now: datetime | None = None) -> list[dict]:
        current = now or _utc_now()
        rows = self._connection.execute(
            """
            SELECT assignments.national_dex_number, targets.species, assignments.variant,
                   assignments.profile, options.method, options.location,
                   assignments.assigned_at, assignments.expires_at
            FROM target_assignments AS assignments
            JOIN collection_targets AS targets USING(national_dex_number, variant)
            JOIN acquisition_options AS options ON options.id = assignments.option_id
            WHERE assignments.expires_at > ?
            ORDER BY assignments.national_dex_number, assignments.variant
            """,
            (_timestamp(current),),
        ).fetchall()
        return [dict(row) for row in rows]

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
