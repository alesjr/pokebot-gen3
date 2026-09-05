from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


SCHEMA_VERSION = 6


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
    steps: tuple[MissionStep, ...]


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


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
        if existing is not None and existing[0] not in {1, 2, 3, 4, 5, SCHEMA_VERSION}:
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
                FOREIGN KEY(mission_id) REFERENCES missions(id) ON DELETE CASCADE,
                FOREIGN KEY(game_id) REFERENCES games(id) ON DELETE RESTRICT,
                UNIQUE(mission_id, game_id),
                UNIQUE(game_id, sequence)
            );

            CREATE TABLE IF NOT EXISTS mission_steps (
                id INTEGER PRIMARY KEY,
                mission_game_id INTEGER NOT NULL,
                code TEXT NOT NULL,
                step_order INTEGER NOT NULL CHECK(step_order > 0),
                name TEXT NOT NULL,
                description TEXT,
                action TEXT,
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

            CREATE INDEX IF NOT EXISTS idx_mission_games_game
                ON mission_games(game_id, sequence);
            CREATE INDEX IF NOT EXISTS idx_mission_steps_order
                ON mission_steps(mission_game_id, step_order);
            CREATE INDEX IF NOT EXISTS idx_step_conditions_source
                ON step_conditions(source_type, source_key);
            CREATE INDEX IF NOT EXISTS idx_mission_progress_profile_status
                ON mission_progress(profile, status);

            INSERT INTO schema_version(version)
            SELECT 3 WHERE NOT EXISTS (SELECT 1 FROM schema_version);

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
        """Insert missing built-in catalogue rows without overwriting database edits."""
        games = (
            ("ruby", "Ruby", "AXV", 2),
            ("sapphire", "Sapphire", "AXP", 2),
            ("emerald", "Emerald", "BPE", 0),
            ("firered", "FireRed", "BPR", 1),
            ("leafgreen", "LeafGreen", "BPG", 1),
        )
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            self._connection.executemany(
                """
                INSERT INTO games(code, name, game_code, revision) VALUES (?, ?, ?, ?)
                ON CONFLICT(code) DO NOTHING
                """,
                games,
            )
            self._connection.execute(
                """
                INSERT INTO missions(code, name, description, category, sequence)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(code) DO NOTHING
                """,
                (
                    "mission-001-first-starter",
                    "Missão 1 - Obter o primeiro starter shiny",
                    "Inicia o jogo, conclui eventos de Littleroot e obtém o starter shiny configurado.",
                    "main_story",
                    1,
                ),
            )
            self._connection.execute(
                """
                UPDATE missions
                SET name = 'Missão 1 - Obter o primeiro starter shiny',
                    description = 'Inicia o jogo, conclui eventos de Littleroot e obtém o starter shiny configurado.'
                WHERE code = 'mission-001-first-starter'
                  AND name = 'Missão 1 - Obter o primeiro starter'
                """
            )
            mission_id = self._connection.execute(
                "SELECT id FROM missions WHERE code = 'mission-001-first-starter'"
            ).fetchone()[0]

            for game_code, *_ in games[:3]:
                game_id = self._connection.execute(
                    "SELECT id FROM games WHERE code = ?", (game_code,)
                ).fetchone()[0]
                self._connection.execute(
                    """
                    INSERT INTO mission_games(mission_id, game_id, sequence) VALUES (?, ?, 1)
                    ON CONFLICT(mission_id, game_id) DO NOTHING
                    """,
                    (mission_id, game_id),
                )
                mission_game_id = self._connection.execute(
                    "SELECT id FROM mission_games WHERE mission_id = ? AND game_id = ?",
                    (mission_id, game_id),
                ).fetchone()[0]
                self._seed_first_starter_steps(mission_game_id, game_code)

            self._connection.execute(
                """
                INSERT INTO missions(code, name, description, category, sequence)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(code) DO NOTHING
                """,
                (
                    "mission-002-first-poke-balls",
                    "Missão 2 - Receber as primeiras Poké Balls",
                    "Derrota o rival na Route 103 e recebe a Pokédex e as primeiras Poké Balls.",
                    "main_story",
                    2,
                ),
            )
            second_mission_id = self._connection.execute(
                "SELECT id FROM missions WHERE code = 'mission-002-first-poke-balls'"
            ).fetchone()[0]
            for game_code, *_ in games[:3]:
                game_id = self._connection.execute(
                    "SELECT id FROM games WHERE code = ?", (game_code,)
                ).fetchone()[0]
                self._connection.execute(
                    """
                    INSERT INTO mission_games(mission_id, game_id, sequence) VALUES (?, ?, 2)
                    ON CONFLICT(mission_id, game_id) DO NOTHING
                    """,
                    (second_mission_id, game_id),
                )
                mission_game_id = self._connection.execute(
                    "SELECT id FROM mission_games WHERE mission_id = ? AND game_id = ?",
                    (second_mission_id, game_id),
                ).fetchone()[0]
                self._seed_first_poke_balls_steps(mission_game_id, game_code)

            self._connection.execute(
                """
                INSERT INTO missions(code, name, description, category, sequence)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(code) DO NOTHING
                """,
                (
                    "mission-003-reach-route102",
                    "Missão 3 - Chegar à primeira rota",
                    "Sai de Littleroot, recebe os Running Shoes e chega à Route 102.",
                    "main_story",
                    3,
                ),
            )
            third_mission_id = self._connection.execute(
                "SELECT id FROM missions WHERE code = 'mission-003-reach-route102'"
            ).fetchone()[0]
            self._connection.execute(
                """
                UPDATE missions
                SET description = 'Chega à Route 102 e usa as primeiras Poké Balls para capturar novas espécies.'
                WHERE id = ?
                  AND description = 'Sai de Littleroot, recebe os Running Shoes e chega à Route 102.'
                """,
                (third_mission_id,),
            )
            for game_code, *_ in games[:3]:
                game_id = self._connection.execute(
                    "SELECT id FROM games WHERE code = ?", (game_code,)
                ).fetchone()[0]
                self._connection.execute(
                    """
                    INSERT INTO mission_games(mission_id, game_id, sequence) VALUES (?, ?, 3)
                    ON CONFLICT(mission_id, game_id) DO NOTHING
                    """,
                    (third_mission_id, game_id),
                )
                mission_game_id = self._connection.execute(
                    "SELECT id FROM mission_games WHERE mission_id = ? AND game_id = ?",
                    (third_mission_id, game_id),
                ).fetchone()[0]
                self._seed_reach_route102_steps(mission_game_id, game_code)
            self._connection.commit()
        except BaseException:
            self._connection.rollback()
            raise

    def _seed_first_starter_steps(self, mission_game_id: int, game_code: str) -> None:
        rival_tile = (5, 5) if game_code == "emerald" else (7, 3)
        steps = (
            ("new-game", 1, "Iniciar novo jogo", "new_game_intro", None, None, None, None, None, None),
            (
                "set-bedroom-clock",
                2,
                "Ajustar relógio do quarto",
                "set_bedroom_clock",
                1,
                1,
                "LITTLEROOT_TOWN_BRENDANS_HOUSE_2F",
                "Littleroot Town",
                5,
                2,
            ),
            (
                "meet-rival",
                3,
                "Encontrar rival",
                "meet_rival",
                1,
                3,
                "LITTLEROOT_TOWN_MAYS_HOUSE_2F",
                "Littleroot Town",
                rival_tile[0],
                rival_tile[1],
            ),
            (
                "reach-starter-bag",
                4,
                "Chegar à bolsa do Professor Birch",
                "reach_starter_bag",
                0,
                16,
                "ROUTE101",
                None,
                7,
                15,
            ),
            (
                "choose-starter",
                5,
                "Obter starter shiny configurado",
                "choose_starter",
                0,
                16,
                "ROUTE101",
                None,
                7,
                15,
            ),
        )
        for code, order, name, action, map_group, map_number, map_name, city, tile_x, tile_y in steps:
            self._connection.execute(
                """
                INSERT INTO mission_steps(
                    mission_game_id, code, step_order, name, action,
                    map_group, map_number, map_name, city, tile_x, tile_y
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(mission_game_id, code) DO NOTHING
                """,
                (
                    mission_game_id,
                    code,
                    order,
                    name,
                    action,
                    map_group,
                    map_number,
                    map_name,
                    city,
                    tile_x,
                    tile_y,
                ),
            )

        self._connection.execute(
            """
            UPDATE mission_steps
            SET name = 'Obter starter shiny configurado'
            WHERE mission_game_id = ?
              AND code = 'choose-starter'
              AND name = 'Obter starter configurado'
            """,
            (mission_game_id,),
        )
        conditions = {
            "new-game": (("other", "game_started", "=", "true", "boolean"),),
            "set-bedroom-clock": (("flag", "SET_WALL_CLOCK", "set", "true", "boolean"),),
            "meet-rival": (("var", "LITTLEROOT_RIVAL_STATE", ">=", "3", "integer"),),
            "reach-starter-bag": (("var", "ROUTE101_STATE", ">=", "2", "integer"),),
            "choose-starter": (
                ("flag", "SYS_POKEMON_GET", "set", "true", "boolean"),
                ("flag", "RESCUED_BIRCH", "set", "true", "boolean"),
                ("var", "BIRCH_LAB_STATE", ">=", "3", "integer"),
                ("other", "owns_configured_shiny_starter", "=", "true", "boolean"),
            ),
        }
        for step_code, entries in conditions.items():
            step_id = self._connection.execute(
                "SELECT id FROM mission_steps WHERE mission_game_id = ? AND code = ?",
                (mission_game_id, step_code),
            ).fetchone()[0]
            for source_type, source_key, operator, expected_value, value_type in entries:
                self._connection.execute(
                    """
                    INSERT INTO step_conditions(
                        step_id, purpose, condition_group, source_type, source_key,
                        operator, expected_value, value_type
                    ) VALUES (?, 'complete', 1, ?, ?, ?, ?, ?)
                    ON CONFLICT(
                        step_id, purpose, condition_group, source_type,
                        source_key, operator, expected_value
                    ) DO NOTHING
                    """,
                    (step_id, source_type, source_key, operator, expected_value, value_type),
                )

    def _seed_first_poke_balls_steps(self, mission_game_id: int, game_code: str) -> None:
        rival_tile = (9, 3) if game_code == "emerald" else (10, 3)
        steps = (
            (
                "defeat-route103-rival",
                1,
                "Derrotar rival na Route 103",
                "defeat_route103_rival",
                0,
                18,
                "ROUTE103",
                rival_tile[0],
                rival_tile[1],
            ),
            (
                "receive-first-poke-balls",
                2,
                "Receber Pokédex e primeiras Poké Balls",
                "receive_first_poke_balls",
                1,
                4,
                "LITTLEROOT_TOWN_PROFESSOR_BIRCHS_LAB",
                None,
                None,
            ),
        )
        for code, order, name, action, map_group, map_number, map_name, tile_x, tile_y in steps:
            self._connection.execute(
                """
                INSERT INTO mission_steps(
                    mission_game_id, code, step_order, name, action,
                    map_group, map_number, map_name, tile_x, tile_y
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(mission_game_id, code) DO NOTHING
                """,
                (
                    mission_game_id,
                    code,
                    order,
                    name,
                    action,
                    map_group,
                    map_number,
                    map_name,
                    tile_x,
                    tile_y,
                ),
            )

        conditions = {
            "defeat-route103-rival": (
                ("unlock", "flag", "SYS_POKEMON_GET", "set", "true", "boolean"),
                ("unlock", "flag", "RESCUED_BIRCH", "set", "true", "boolean"),
                ("unlock", "var", "BIRCH_LAB_STATE", ">=", "3", "integer"),
                (
                    "unlock",
                    "other",
                    "owns_configured_shiny_starter",
                    "=",
                    "true",
                    "boolean",
                ),
                ("complete", "flag", "DEFEATED_RIVAL_ROUTE103", "set", "true", "boolean"),
            ),
            "receive-first-poke-balls": (
                ("unlock", "flag", "DEFEATED_RIVAL_ROUTE103", "set", "true", "boolean"),
                ("complete", "flag", "SYS_POKEDEX_GET", "set", "true", "boolean"),
                ("complete", "var", "BIRCH_LAB_STATE", ">=", "5", "integer"),
            ),
        }
        for step_code, entries in conditions.items():
            step_id = self._connection.execute(
                "SELECT id FROM mission_steps WHERE mission_game_id = ? AND code = ?",
                (mission_game_id, step_code),
            ).fetchone()[0]
            for purpose, source_type, source_key, operator, expected_value, value_type in entries:
                self._connection.execute(
                    """
                    INSERT INTO step_conditions(
                        step_id, purpose, condition_group, source_type, source_key,
                        operator, expected_value, value_type
                    ) VALUES (?, ?, 1, ?, ?, ?, ?, ?)
                    ON CONFLICT(
                        step_id, purpose, condition_group, source_type,
                        source_key, operator, expected_value
                    ) DO NOTHING
                    """,
                    (
                        step_id,
                        purpose,
                        source_type,
                        source_key,
                        operator,
                        expected_value,
                        value_type,
                    ),
                )

        receive_step_id = self._connection.execute(
            """
            SELECT id FROM mission_steps
            WHERE mission_game_id = ? AND code = 'receive-first-poke-balls'
            """,
            (mission_game_id,),
        ).fetchone()[0]
        self._connection.execute(
            """
            DELETE FROM step_conditions
            WHERE step_id = ? AND purpose = 'complete'
              AND source_type = 'item' AND source_key = 'Poké Ball'
              AND operator = '>=' AND expected_value = '1'
            """,
            (receive_step_id,),
        )

    def _seed_reach_route102_steps(self, mission_game_id: int, game_code: str) -> None:
        first_gym_max_level = {"ruby": 15, "sapphire": 15, "emerald": 15}[game_code]
        training_level_margin = 5
        training_target_level = first_gym_max_level + training_level_margin
        legacy_step = self._connection.execute(
            """
            SELECT id FROM mission_steps
            WHERE mission_game_id = ? AND code = 'reach-route102'
              AND action = 'reach_route102' AND step_order = 1
            """,
            (mission_game_id,),
        ).fetchone()
        if legacy_step is not None:
            self._connection.execute(
                "UPDATE mission_progress SET current_step_id = NULL WHERE current_step_id = ?",
                (legacy_step[0],),
            )
            self._connection.execute("DELETE FROM mission_steps WHERE id = ?", (legacy_step[0],))

        steps = (
            (
                "leave-birch-lab",
                1,
                "Sair do laboratório do Professor Birch",
                "leave_birch_lab",
                0,
                9,
                "LITTLEROOT_TOWN",
                7,
                16,
            ),
            (
                "reach-route101",
                2,
                "Receber Running Shoes e entrar na Route 101",
                "navigate_to_catalog_location",
                0,
                16,
                "ROUTE101",
                10,
                19,
            ),
            (
                "reach-oldale",
                3,
                "Atravessar a Route 101 até Oldale",
                "navigate_to_catalog_location",
                0,
                10,
                "OLDALE_TOWN",
                10,
                18,
            ),
            (
                "reach-route102",
                4,
                "Chegar à Route 102",
                "reach_route102",
                0,
                17,
                "ROUTE102",
                49,
                10,
            ),
            (
                "reach-route102-grass",
                5,
                "Entrar na grama da Route 102",
                "navigate_to_catalog_location",
                0,
                17,
                "ROUTE102",
                39,
                5,
            ),
            (
                "catch-new-route102-pokemon",
                6,
                "Gastar as primeiras Poké Balls capturando novas espécies",
                "catch_new_route102_pokemon",
                0,
                17,
                "ROUTE102",
                39,
                5,
            ),
            (
                "heal-captured-pokemon-oldale",
                7,
                "Curar equipe no Centro Pokémon de Oldale",
                "heal_captured_pokemon_oldale",
                0,
                10,
                "OLDALE_TOWN",
                6,
                16,
            ),
            (
                "deposit-shiny-starter",
                8,
                "Depositar starter shiny no PC",
                "deposit_shiny_starter",
                2,
                2,
                "OLDALE_TOWN_POKEMON_CENTER_1F",
                10,
                2,
            ),
            (
                "return-route102-grass",
                9,
                "Voltar para a grama da Route 102",
                "navigate_to_catalog_location",
                0,
                17,
                "ROUTE102",
                39,
                5,
            ),
            (
                "ev-train-captured-pokemon",
                10,
                f"Treinar capturados até o nível {training_target_level}",
                "ev_train_captured_pokemon",
                0,
                17,
                "ROUTE102",
                39,
                5,
            ),
        )
        for code, order, name, action, map_group, map_number, map_name, tile_x, tile_y in steps:
            self._connection.execute(
                """
                INSERT INTO mission_steps(
                    mission_game_id, code, step_order, name, action,
                    map_group, map_number, map_name, tile_x, tile_y
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(mission_game_id, code) DO NOTHING
                """,
                (
                    mission_game_id,
                    code,
                    order,
                    name,
                    action,
                    map_group,
                    map_number,
                    map_name,
                    tile_x,
                    tile_y,
                ),
            )

        self._connection.execute(
            """
            UPDATE mission_steps
            SET tile_x = 49, tile_y = 10
            WHERE mission_game_id = ? AND code = 'reach-route102'
              AND action = 'reach_route102' AND tile_x = 40 AND tile_y = 9
            """,
            (mission_game_id,),
        )
        self._connection.execute(
            """
            UPDATE mission_steps
            SET tile_x = 39, tile_y = 5
            WHERE mission_game_id = ?
              AND code IN ('reach-route102-grass', 'catch-new-route102-pokemon')
              AND tile_x = 36 AND tile_y IN (4, 5)
            """,
            (mission_game_id,),
        )
        self._connection.execute(
            """
            UPDATE mission_steps
            SET tile_x = 10, tile_y = 2
            WHERE mission_game_id = ? AND code = 'deposit-shiny-starter'
              AND (
                  (tile_x IN (9, 10, 11) AND tile_y IN (3, 4))
                  OR (tile_x IN (9, 11) AND tile_y = 2)
              )
            """,
            (mission_game_id,),
        )
        self._connection.execute(
            """
            UPDATE step_conditions
            SET expected_value = '39:5'
            WHERE source_type = 'tile' AND source_key = 'current'
              AND expected_value IN ('36:4', '36:5')
              AND step_id IN (
                  SELECT id FROM mission_steps
                  WHERE mission_game_id = ? AND code = 'reach-route102-grass'
              )
            """,
            (mission_game_id,),
        )
        self._connection.execute(
            """
            UPDATE mission_steps
            SET description = ?
            WHERE mission_game_id = ? AND code = 'ev-train-captured-pokemon'
              AND description IS NULL
            """,
            (
                f"first_gym_max_level={first_gym_max_level}; "
                f"level_margin={training_level_margin}; "
                f"target_level={training_target_level}",
                mission_game_id,
            ),
        )

        capture_step_id = self._connection.execute(
            """
            SELECT id FROM mission_steps
            WHERE mission_game_id = ? AND code = 'catch-new-route102-pokemon'
            """,
            (mission_game_id,),
        ).fetchone()[0]
        self._connection.execute(
            """
            DELETE FROM step_conditions
            WHERE step_id = ? AND purpose = 'complete'
              AND source_type = 'other' AND source_key = 'pokedex_owned_count'
            """,
            (capture_step_id,),
        )
        self._connection.execute(
            """
            DELETE FROM step_conditions
            WHERE source_type = 'other' AND source_key = 'owned_non_starter_count'
              AND step_id IN (
                  SELECT id FROM mission_steps WHERE mission_game_id = ?
              )
            """,
            (mission_game_id,),
        )
        reach_route_step_id = self._connection.execute(
            """
            SELECT id FROM mission_steps
            WHERE mission_game_id = ? AND code = 'reach-route102'
            """,
            (mission_game_id,),
        ).fetchone()[0]
        self._connection.execute(
            """
            DELETE FROM step_conditions
            WHERE step_id = ? AND purpose = 'complete'
              AND source_type = 'item' AND source_key = 'Poké Ball'
            """,
            (reach_route_step_id,),
        )

        conditions = {
            "leave-birch-lab": (
                (1, "unlock", "flag", "SYS_POKEDEX_GET", "set", "true", "boolean"),
                (1, "unlock", "var", "BIRCH_LAB_STATE", ">=", "5", "integer"),
                (1, "unlock", "item", "Poké Ball", ">=", "1", "integer"),
                (1, "complete", "map", "current", "=", "0:9", "text"),
                (2, "complete", "map", "current", "=", "0:16", "text"),
                (3, "complete", "map", "current", "=", "0:10", "text"),
                (4, "complete", "map", "current", "=", "0:17", "text"),
                (5, "complete", "party", "non_starter_count", ">=", "2", "integer"),
            ),
            "reach-route101": (
                (1, "complete", "flag", "RECEIVED_RUNNING_SHOES", "set", "true", "boolean"),
                (1, "complete", "map", "current", "=", "0:16", "text"),
                (2, "complete", "flag", "RECEIVED_RUNNING_SHOES", "set", "true", "boolean"),
                (2, "complete", "map", "current", "=", "0:10", "text"),
                (3, "complete", "flag", "RECEIVED_RUNNING_SHOES", "set", "true", "boolean"),
                (3, "complete", "map", "current", "=", "0:17", "text"),
                (4, "complete", "party", "non_starter_count", ">=", "2", "integer"),
            ),
            "reach-oldale": (
                (1, "complete", "map", "current", "=", "0:10", "text"),
                (2, "complete", "map", "current", "=", "0:17", "text"),
                (3, "complete", "party", "non_starter_count", ">=", "2", "integer"),
            ),
            "reach-route102": (
                (1, "complete", "map", "current", "=", "0:17", "text"),
                (2, "complete", "party", "non_starter_count", ">=", "2", "integer"),
            ),
            "reach-route102-grass": (
                (1, "complete", "map", "current", "=", "0:17", "text"),
                (1, "complete", "tile", "current", "=", "39:5", "text"),
                (2, "complete", "party", "non_starter_count", ">=", "2", "integer"),
            ),
            "catch-new-route102-pokemon": (
                (1, "unlock", "map", "current", "=", "0:17", "text"),
                (1, "unlock", "item", "Poké Ball", ">=", "1", "integer"),
                (1, "complete", "item", "Poké Ball", "=", "0", "integer"),
                (1, "complete", "party", "non_starter_count", ">=", "2", "integer"),
            ),
            "heal-captured-pokemon-oldale": (
                (1, "unlock", "party", "non_starter_count", ">=", "2", "integer"),
                (1, "complete", "party", "all_healthy", "=", "true", "boolean"),
                (1, "complete", "map", "current", "=", "0:10", "text"),
                (2, "complete", "party", "all_healthy", "=", "true", "boolean"),
                (2, "complete", "map", "current", "=", "2:2", "text"),
            ),
            "deposit-shiny-starter": (
                (1, "unlock", "party", "non_starter_count", ">=", "2", "integer"),
                (1, "complete", "other", "shiny_starter_in_storage", "=", "true", "boolean"),
                (1, "complete", "party", "configured_starter_count", "=", "0", "integer"),
                (1, "complete", "party", "count", ">=", "2", "integer"),
            ),
            "return-route102-grass": (
                (1, "complete", "map", "current", "=", "0:17", "text"),
                (1, "complete", "tile", "current", "=", "39:5", "text"),
            ),
            "ev-train-captured-pokemon": (
                (1, "unlock", "other", "shiny_starter_in_storage", "=", "true", "boolean"),
                (1, "unlock", "party", "count", ">=", "2", "integer"),
                (1, "complete", "party", "minimum_level", ">=", str(training_target_level), "integer"),
                (1, "complete", "party", "count", ">=", "2", "integer"),
                (1, "complete", "other", "shiny_starter_in_storage", "=", "true", "boolean"),
            ),
        }
        for step_code, entries in conditions.items():
            step_id = self._connection.execute(
                "SELECT id FROM mission_steps WHERE mission_game_id = ? AND code = ?",
                (mission_game_id, step_code),
            ).fetchone()[0]
            for group, purpose, source_type, source_key, operator, expected_value, value_type in entries:
                self._connection.execute(
                    """
                    INSERT INTO step_conditions(
                        step_id, purpose, condition_group, source_type, source_key,
                        operator, expected_value, value_type
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(
                        step_id, purpose, condition_group, source_type,
                        source_key, operator, expected_value
                    ) DO NOTHING
                    """,
                    (
                        step_id,
                        purpose,
                        group,
                        source_type,
                        source_key,
                        operator,
                        expected_value,
                        value_type,
                    ),
                )

    def mission_plan(self, game_code: str, mission_code: str) -> MissionPlan | None:
        mission = self._connection.execute(
            """
            SELECT m.id, mg.id AS mission_game_id, m.code, m.name, g.code AS game_code
            FROM missions AS m
            JOIN mission_games AS mg ON mg.mission_id = m.id
            JOIN games AS g ON g.id = mg.game_id
            WHERE g.code = ? AND m.code = ?
            """,
            (game_code, mission_code),
        ).fetchone()
        if mission is None:
            return None
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
