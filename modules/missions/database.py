from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


SCHEMA_VERSION = 8
CATALOG_VERSION = 1


@dataclass(frozen=True)
class StepCondition:
    id: int
    purpose: str
    condition_group: int
    source_type: str
    source_key: str
    operator: str
    expected_value: str
    value_type: str


@dataclass(frozen=True)
class MissionStep:
    id: int
    mission_game_id: int
    code: str
    step_order: int
    name: str
    action: str
    action_params: dict[str, object]
    recovery_action: str | None
    recovery_params: dict[str, object]
    map_group: int | None
    map_number: int | None
    map_name: str | None
    city: str | None
    tile_x: int | None
    tile_y: int | None
    conditions: tuple[StepCondition, ...]


@dataclass(frozen=True)
class MissionPlan:
    id: int
    mission_game_id: int
    code: str
    name: str
    game_code: str
    training_target_level: int | None
    training_map_group: int | None
    training_map_number: int | None
    training_tile_x: int | None
    training_tile_y: int | None
    rules: dict[str, object]
    steps: tuple[MissionStep, ...]


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _decode_mapping(value: str, field: str) -> dict[str, object]:
    decoded = json.loads(value)
    if not isinstance(decoded, dict):
        raise RuntimeError(f"{field} must contain a JSON object")
    return decoded


def _decode_rule_value(value: str, value_type: str) -> object:
    if value_type == "integer":
        return int(value)
    if value_type == "boolean":
        return value.lower() == "true"
    if value_type == "json":
        return json.loads(value)
    return value


class MissionsDatabase:
    """SQLite schema for game-specific mission definitions and detected progress."""

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(path, timeout=5, isolation_level=None)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA foreign_keys=ON")
        self._migrate()

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> MissionsDatabase:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _migrate(self) -> None:
        self._connection.execute(
            "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL CHECK(version > 0))"
        )
        existing = self._connection.execute("SELECT version FROM schema_version").fetchone()
        if existing is not None and existing[0] not in {1, 2, 3, 4, 5, 6, 7, SCHEMA_VERSION}:
            raise RuntimeError(
                f"missions database schema version {existing[0]} is not supported; "
                f"expected {SCHEMA_VERSION}"
            )

        self._connection.executescript(
            """
            BEGIN IMMEDIATE;

            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER NOT NULL CHECK(version > 0)
            );

            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY,
                code TEXT NOT NULL UNIQUE CHECK(code IN (
                    'ruby', 'sapphire', 'emerald', 'firered', 'leafgreen'
                )),
                name TEXT NOT NULL UNIQUE,
                game_code TEXT NOT NULL,
                revision INTEGER NOT NULL CHECK(revision >= 0),
                UNIQUE(game_code, revision)
            );

            CREATE TABLE IF NOT EXISTS missions (
                id INTEGER PRIMARY KEY,
                code TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                description TEXT,
                category TEXT,
                sequence INTEGER NOT NULL CHECK(sequence >= 0)
            );

            CREATE TABLE IF NOT EXISTS mission_games (
                id INTEGER PRIMARY KEY,
                mission_id INTEGER NOT NULL,
                game_id INTEGER NOT NULL,
                sequence INTEGER NOT NULL CHECK(sequence >= 0),
                training_target_level INTEGER CHECK(training_target_level > 0),
                training_map_group INTEGER CHECK(training_map_group >= 0),
                training_map_number INTEGER CHECK(training_map_number >= 0),
                training_tile_x INTEGER,
                training_tile_y INTEGER,
                FOREIGN KEY(mission_id) REFERENCES missions(id) ON DELETE CASCADE,
                FOREIGN KEY(game_id) REFERENCES games(id) ON DELETE RESTRICT,
                UNIQUE(mission_id, game_id),
                UNIQUE(game_id, sequence),
                CHECK(
                    (training_map_group IS NULL AND training_map_number IS NULL
                     AND training_tile_x IS NULL AND training_tile_y IS NULL)
                    OR
                    (training_map_group IS NOT NULL AND training_map_number IS NOT NULL
                     AND training_tile_x IS NOT NULL AND training_tile_y IS NOT NULL)
                )
            );

            CREATE TABLE IF NOT EXISTS mission_steps (
                id INTEGER PRIMARY KEY,
                mission_game_id INTEGER NOT NULL,
                code TEXT NOT NULL,
                step_order INTEGER NOT NULL CHECK(step_order > 0),
                name TEXT NOT NULL,
                description TEXT,
                action TEXT NOT NULL,
                action_params TEXT NOT NULL DEFAULT '{}',
                recovery_action TEXT,
                recovery_params TEXT NOT NULL DEFAULT '{}',
                map_group INTEGER CHECK(map_group >= 0),
                map_number INTEGER CHECK(map_number >= 0),
                map_name TEXT,
                city TEXT,
                tile_x INTEGER,
                tile_y INTEGER,
                FOREIGN KEY(mission_game_id) REFERENCES mission_games(id) ON DELETE CASCADE,
                UNIQUE(mission_game_id, code),
                UNIQUE(mission_game_id, step_order),
                UNIQUE(id, mission_game_id),
                CHECK((tile_x IS NULL AND tile_y IS NULL) OR (tile_x IS NOT NULL AND tile_y IS NOT NULL)),
                CHECK((map_group IS NULL AND map_number IS NULL) OR (map_group IS NOT NULL AND map_number IS NOT NULL))
            );

            CREATE TABLE IF NOT EXISTS step_conditions (
                id INTEGER PRIMARY KEY,
                step_id INTEGER NOT NULL,
                purpose TEXT NOT NULL CHECK(purpose IN ('unlock', 'start', 'complete')),
                condition_group INTEGER NOT NULL DEFAULT 1 CHECK(condition_group > 0),
                source_type TEXT NOT NULL CHECK(source_type IN (
                    'flag', 'var', 'map', 'tile', 'item', 'badge', 'party', 'script', 'other'
                )),
                source_key TEXT NOT NULL,
                operator TEXT NOT NULL CHECK(operator IN (
                    '=', '!=', '>', '>=', '<', '<=', 'set', 'unset', 'contains', 'not_contains'
                )),
                expected_value TEXT NOT NULL,
                value_type TEXT NOT NULL DEFAULT 'integer' CHECK(value_type IN (
                    'integer', 'boolean', 'text', 'hex'
                )),
                description TEXT,
                FOREIGN KEY(step_id) REFERENCES mission_steps(id) ON DELETE CASCADE,
                UNIQUE(step_id, purpose, condition_group, source_type, source_key, operator, expected_value)
            );

            CREATE TABLE IF NOT EXISTS mission_progress (
                id INTEGER PRIMARY KEY,
                profile TEXT NOT NULL,
                mission_game_id INTEGER NOT NULL,
                current_step_id INTEGER,
                status TEXT NOT NULL CHECK(status IN ('locked', 'available', 'in_progress')),
                first_started_at TEXT,
                last_evaluated_at TEXT NOT NULL,
                FOREIGN KEY(mission_game_id) REFERENCES mission_games(id) ON DELETE CASCADE,
                FOREIGN KEY(current_step_id, mission_game_id)
                    REFERENCES mission_steps(id, mission_game_id) ON DELETE RESTRICT,
                UNIQUE(profile, mission_game_id)
            );

            CREATE TABLE IF NOT EXISTS mission_progress_observations (
                id INTEGER PRIMARY KEY,
                mission_progress_id INTEGER NOT NULL,
                step_condition_id INTEGER NOT NULL,
                observed_value TEXT NOT NULL,
                matched INTEGER NOT NULL CHECK(matched IN (0, 1)),
                observed_at TEXT NOT NULL,
                FOREIGN KEY(mission_progress_id) REFERENCES mission_progress(id) ON DELETE CASCADE,
                FOREIGN KEY(step_condition_id) REFERENCES step_conditions(id) ON DELETE CASCADE,
                UNIQUE(mission_progress_id, step_condition_id)
            );

            CREATE TABLE IF NOT EXISTS campaign_rules (
                id INTEGER PRIMARY KEY,
                game_id INTEGER NOT NULL,
                rule_key TEXT NOT NULL,
                value TEXT NOT NULL,
                value_type TEXT NOT NULL DEFAULT 'text' CHECK(value_type IN (
                    'integer', 'boolean', 'text', 'json'
                )),
                description TEXT,
                FOREIGN KEY(game_id) REFERENCES games(id) ON DELETE CASCADE,
                UNIQUE(game_id, rule_key)
            );

            CREATE INDEX IF NOT EXISTS idx_mission_games_game
                ON mission_games(game_id, sequence);
            CREATE INDEX IF NOT EXISTS idx_mission_steps_order
                ON mission_steps(mission_game_id, step_order);
            CREATE INDEX IF NOT EXISTS idx_step_conditions_source
                ON step_conditions(source_type, source_key);
            CREATE INDEX IF NOT EXISTS idx_mission_progress_profile_status
                ON mission_progress(profile, status);
            CREATE INDEX IF NOT EXISTS idx_campaign_rules_game
                ON campaign_rules(game_id, rule_key);

            INSERT INTO schema_version(version)
            SELECT 8 WHERE NOT EXISTS (SELECT 1 FROM schema_version);

            COMMIT;
            """
        )

        version = self._connection.execute("SELECT version FROM schema_version").fetchone()[0]
        if version == 1:
            self._migrate_games_to_v2()
            version = 2
        if version == 2:
            self._migrate_progress_to_v3()
            version = 3
        if version in {3, 4, 5}:
            self._remove_battle_policies_to_v6()
            version = 6
        if version == 6:
            self._migrate_catalog_to_v7()
            version = 7
        if version == 7:
            self._migrate_training_targets_to_v8()
            version = 8
        if version != SCHEMA_VERSION:
            raise RuntimeError(
                f"missions database schema version {version} is not supported; expected {SCHEMA_VERSION}"
            )

    def _remove_battle_policies_to_v6(self) -> None:
        self._connection.executescript(
            """
            BEGIN IMMEDIATE;
            DROP TABLE IF EXISTS mission_battle_policies;
            UPDATE schema_version SET version = 6;
            COMMIT;
            """
        )

    def _migrate_catalog_to_v7(self) -> None:
        self._connection.executescript(
            """
            BEGIN IMMEDIATE;
            ALTER TABLE mission_steps
                ADD COLUMN action_params TEXT NOT NULL DEFAULT '{}';
            ALTER TABLE mission_steps
                ADD COLUMN recovery_action TEXT;
            ALTER TABLE mission_steps
                ADD COLUMN recovery_params TEXT NOT NULL DEFAULT '{}';
            CREATE TABLE IF NOT EXISTS campaign_rules (
                id INTEGER PRIMARY KEY,
                game_id INTEGER NOT NULL,
                rule_key TEXT NOT NULL,
                value TEXT NOT NULL,
                value_type TEXT NOT NULL DEFAULT 'text' CHECK(value_type IN (
                    'integer', 'boolean', 'text', 'json'
                )),
                description TEXT,
                FOREIGN KEY(game_id) REFERENCES games(id) ON DELETE CASCADE,
                UNIQUE(game_id, rule_key)
            );
            CREATE INDEX IF NOT EXISTS idx_campaign_rules_game
                ON campaign_rules(game_id, rule_key);
            UPDATE schema_version SET version = 7;
            COMMIT;
            """
        )

    def _migrate_training_targets_to_v8(self) -> None:
        self._connection.executescript(
            """
            BEGIN IMMEDIATE;
            ALTER TABLE mission_games ADD COLUMN training_target_level INTEGER;
            ALTER TABLE mission_games ADD COLUMN training_map_group INTEGER;
            ALTER TABLE mission_games ADD COLUMN training_map_number INTEGER;
            ALTER TABLE mission_games ADD COLUMN training_tile_x INTEGER;
            ALTER TABLE mission_games ADD COLUMN training_tile_y INTEGER;
            UPDATE schema_version SET version = 8;
            COMMIT;
            """
        )

    def _migrate_progress_to_v3(self) -> None:
        self._connection.execute("PRAGMA foreign_keys=OFF")
        try:
            self._connection.executescript(
                """
                BEGIN IMMEDIATE;
                DROP INDEX IF EXISTS idx_mission_progress_profile_status;
                CREATE TABLE mission_progress_v3 (
                    id INTEGER PRIMARY KEY,
                    profile TEXT NOT NULL,
                    mission_game_id INTEGER NOT NULL,
                    current_step_id INTEGER,
                    status TEXT NOT NULL CHECK(status IN ('locked', 'available', 'in_progress')),
                    first_started_at TEXT,
                    last_evaluated_at TEXT NOT NULL,
                    FOREIGN KEY(mission_game_id) REFERENCES mission_games(id) ON DELETE CASCADE,
                    FOREIGN KEY(current_step_id, mission_game_id)
                        REFERENCES mission_steps(id, mission_game_id) ON DELETE RESTRICT,
                    UNIQUE(profile, mission_game_id)
                );
                INSERT INTO mission_progress_v3(
                    id, profile, mission_game_id, current_step_id, status,
                    first_started_at, last_evaluated_at
                )
                SELECT
                    id, profile, mission_game_id, current_step_id,
                    CASE WHEN status = 'completed' THEN 'available' ELSE status END,
                    first_started_at, last_evaluated_at
                FROM mission_progress;
                DROP TABLE mission_progress;
                ALTER TABLE mission_progress_v3 RENAME TO mission_progress;
                CREATE INDEX idx_mission_progress_profile_status
                    ON mission_progress(profile, status);
                UPDATE schema_version SET version = 3;
                COMMIT;
                """
            )
        finally:
            self._connection.execute("PRAGMA foreign_keys=ON")
        violation = self._connection.execute("PRAGMA foreign_key_check").fetchone()
        if violation is not None:
            raise RuntimeError(f"missions database foreign key violation: {tuple(violation)}")

    def _migrate_games_to_v2(self) -> None:
        self._connection.execute("PRAGMA foreign_keys=OFF")
        try:
            self._connection.executescript(
                """
                BEGIN IMMEDIATE;
                CREATE TABLE games_v2 (
                    id INTEGER PRIMARY KEY,
                    code TEXT NOT NULL UNIQUE CHECK(code IN (
                        'ruby', 'sapphire', 'emerald', 'firered', 'leafgreen'
                    )),
                    name TEXT NOT NULL UNIQUE,
                    game_code TEXT NOT NULL,
                    revision INTEGER NOT NULL CHECK(revision >= 0),
                    UNIQUE(game_code, revision)
                );
                INSERT INTO games_v2 SELECT * FROM games;
                DROP TABLE games;
                ALTER TABLE games_v2 RENAME TO games;
                UPDATE schema_version SET version = 2;
                COMMIT;
                """
            )
        finally:
            self._connection.execute("PRAGMA foreign_keys=ON")
        violation = self._connection.execute("PRAGMA foreign_key_check").fetchone()
        if violation is not None:
            raise RuntimeError(f"missions database foreign key violation: {tuple(violation)}")

    def initialize_builtin_catalog(self) -> None:
        """Load the versioned built-in mission catalogue."""
        catalog_path = Path(__file__).with_name(f"catalog_v{CATALOG_VERSION}.sql")
        self._connection.executescript(catalog_path.read_text(encoding="utf-8"))
        story_catalog_path = Path(__file__).with_name("catalog_rse_story_v1.sql")
        self._connection.executescript(story_catalog_path.read_text(encoding="utf-8"))

    def mission_plan(self, game_code: str, mission_code: str) -> MissionPlan | None:
        mission = self._connection.execute(
            """
            SELECT m.id, mg.id AS mission_game_id, m.code, m.name,
                   g.code AS game_code, mg.training_target_level,
                   mg.training_map_group, mg.training_map_number,
                   mg.training_tile_x, mg.training_tile_y
            FROM missions AS m
            JOIN mission_games AS mg ON mg.mission_id = m.id
            JOIN games AS g ON g.id = mg.game_id
            WHERE g.code = ? AND m.code = ?
            """,
            (game_code, mission_code),
        ).fetchone()
        if mission is None:
            return None
        rule_rows = self._connection.execute(
            """
            SELECT rule_key, value, value_type
            FROM campaign_rules
            JOIN games ON games.id = campaign_rules.game_id
            WHERE games.code = ?
            ORDER BY rule_key
            """,
            (game_code,),
        ).fetchall()
        rules = {
            row["rule_key"]: _decode_rule_value(row["value"], row["value_type"])
            for row in rule_rows
        }
        step_rows = self._connection.execute(
            "SELECT * FROM mission_steps WHERE mission_game_id = ? ORDER BY step_order",
            (mission["mission_game_id"],),
        ).fetchall()
        steps = []
        for row in step_rows:
            condition_rows = self._connection.execute(
                "SELECT * FROM step_conditions WHERE step_id = ? ORDER BY condition_group, id",
                (row["id"],),
            ).fetchall()
            steps.append(
                MissionStep(
                    id=row["id"],
                    mission_game_id=row["mission_game_id"],
                    code=row["code"],
                    step_order=row["step_order"],
                    name=row["name"],
                    action=row["action"],
                    action_params=_decode_mapping(row["action_params"], "action_params"),
                    recovery_action=row["recovery_action"],
                    recovery_params=_decode_mapping(row["recovery_params"], "recovery_params"),
                    map_group=row["map_group"],
                    map_number=row["map_number"],
                    map_name=row["map_name"],
                    city=row["city"],
                    tile_x=row["tile_x"],
                    tile_y=row["tile_y"],
                    conditions=tuple(
                        StepCondition(
                            id=item["id"],
                            purpose=item["purpose"],
                            condition_group=item["condition_group"],
                            source_type=item["source_type"],
                            source_key=item["source_key"],
                            operator=item["operator"],
                            expected_value=item["expected_value"],
                            value_type=item["value_type"],
                        )
                        for item in condition_rows
                    ),
                )
            )
        return MissionPlan(
            id=mission["id"],
            mission_game_id=mission["mission_game_id"],
            code=mission["code"],
            name=mission["name"],
            game_code=mission["game_code"],
            training_target_level=mission["training_target_level"],
            training_map_group=mission["training_map_group"],
            training_map_number=mission["training_map_number"],
            training_tile_x=mission["training_tile_x"],
            training_tile_y=mission["training_tile_y"],
            rules=rules,
            steps=tuple(steps),
        )

    def mission_plans(self, game_code: str) -> tuple[MissionPlan, ...]:
        rows = self._connection.execute(
            """
            SELECT missions.code
            FROM mission_games
            JOIN missions ON missions.id = mission_games.mission_id
            JOIN games ON games.id = mission_games.game_id
            WHERE games.code = ?
            ORDER BY mission_games.sequence, missions.sequence
            """,
            (game_code,),
        ).fetchall()
        return tuple(
            plan
            for row in rows
            if (plan := self.mission_plan(game_code, row["code"])) is not None
        )

    def update_progress(
        self,
        profile: str,
        mission_game_id: int,
        *,
        status: str,
        current_step_id: int | None,
    ) -> None:
        if status not in {"locked", "available", "in_progress"}:
            raise ValueError(f"invalid operational mission status: {status}")
        now = _timestamp()
        started_at = now if status == "in_progress" else None
        self._connection.execute(
            """
            INSERT INTO mission_progress(
                profile, mission_game_id, current_step_id, status,
                first_started_at, last_evaluated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(profile, mission_game_id) DO UPDATE SET
                current_step_id=excluded.current_step_id,
                status=excluded.status,
                first_started_at=COALESCE(mission_progress.first_started_at, excluded.first_started_at),
                last_evaluated_at=excluded.last_evaluated_at
            """,
            (profile, mission_game_id, current_step_id, status, started_at, now),
        )

    def record_observations(
        self,
        profile: str,
        mission_game_id: int,
        observations: tuple[tuple[StepCondition, object, bool], ...],
    ) -> None:
        progress = self._connection.execute(
            "SELECT id FROM mission_progress WHERE profile = ? AND mission_game_id = ?",
            (profile, mission_game_id),
        ).fetchone()
        if progress is None:
            raise RuntimeError("mission progress must exist before recording observations")
        observed_at = _timestamp()
        self._connection.executemany(
            """
            INSERT INTO mission_progress_observations(
                mission_progress_id, step_condition_id, observed_value, matched, observed_at
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(mission_progress_id, step_condition_id) DO UPDATE SET
                observed_value=excluded.observed_value,
                matched=excluded.matched,
                observed_at=excluded.observed_at
            """,
            (
                (progress["id"], condition.id, str(value), int(matched), observed_at)
                for condition, value, matched in observations
            ),
        )

    def clear_profile_progress(self, profile: str) -> None:
        self._connection.execute("DELETE FROM mission_progress WHERE profile = ?", (profile,))
