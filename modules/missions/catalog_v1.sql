BEGIN IMMEDIATE;

INSERT INTO games(code, name, game_code, revision) VALUES
    ('ruby', 'Ruby', 'AXV', 2),
    ('sapphire', 'Sapphire', 'AXP', 2),
    ('emerald', 'Emerald', 'BPE', 0),
    ('firered', 'FireRed', 'BPR', 1),
    ('leafgreen', 'LeafGreen', 'BPG', 1)
ON CONFLICT(code) DO UPDATE SET
    name = excluded.name,
    game_code = excluded.game_code,
    revision = excluded.revision;

INSERT INTO missions(code, name, description, category, sequence) VALUES
    (
        'mission-001-first-starter',
        'Missão 1 - Obter o primeiro starter shiny',
        'Inicia o jogo, conclui eventos de Littleroot e obtém o starter shiny configurado.',
        'main_story',
        1
    ),
    (
        'mission-002-first-poke-balls',
        'Missão 2 - Receber as primeiras Poké Balls',
        'Derrota o rival na Route 103 e recebe a Pokédex e as primeiras Poké Balls.',
        'main_story',
        2
    ),
    (
        'mission-003-reach-route102',
        'Missão 3 - Chegar à primeira rota',
        'Chega à Route 102, faz a primeira captura e forma a equipe inicial.',
        'main_story',
        3
    )
ON CONFLICT(code) DO UPDATE SET
    name = excluded.name,
    description = excluded.description,
    category = excluded.category,
    sequence = excluded.sequence;

INSERT INTO mission_games(mission_id, game_id, sequence)
SELECT missions.id, games.id, missions.sequence
FROM missions
CROSS JOIN games
WHERE missions.code IN (
    'mission-001-first-starter',
    'mission-002-first-poke-balls',
    'mission-003-reach-route102'
)
AND games.code IN ('ruby', 'sapphire', 'emerald')
ON CONFLICT(mission_id, game_id) DO UPDATE SET sequence = excluded.sequence;

WITH rule_catalog(rule_key, value, value_type, description) AS (
    VALUES
        ('shiny.capture_required', 'true', 'boolean', 'Capturar todo Pokémon shiny encontrado.'),
        ('shiny.storage_required', 'true', 'boolean', 'Armazenar Pokémon shiny no PC.'),
        ('shiny.pc_terminal_tile', '[10,2]', 'json', 'Posição do terminal nos Centros Pokémon RSE.'),
        ('starter.shiny_required', 'true', 'boolean', 'O primeiro starter deve ser shiny.'),
        ('first_wild.capture_required', 'true', 'boolean', 'Capturar o primeiro encontro selvagem após obter Poké Balls.'),
        ('training.before_mission', 'true', 'boolean', 'Treinar antes das missões até o nível requerido.'),
        ('party.target_size', '6', 'integer', 'Capturar até formar equipe com seis Pokémon.'),
        ('party.combat_score', 'base_stats_plus_ivs', 'text', 'Comparar potencial por status base e IVs.'),
        ('party.combat_level_weight', '0', 'integer', 'Nível não participa da comparação de potencial.'),
        ('party.shiny_combatants', 'false', 'boolean', 'Shiny nunca ocupa vaga de combatente.'),
        ('party.optimize_on_pc_access', 'true', 'boolean', 'Comparar time e armazenamento ao acessar o PC.'),
        ('party.selection_tiebreak', 'ivs_then_stable_identity', 'text', 'Desempatar por IVs e identidade estável, nunca por nível.'),
        ('hm.slot_policy', 'minimum_required_coverage', 'text', 'Usar o menor conjunto de HM Slayers que cubra os HMs requeridos.'),
        ('hm.preferred_coverage', '4', 'integer', 'Preferir HM Slayer capaz de aprender quatro HMs diferentes.'),
        ('unique.shiny_required', 'true', 'boolean', 'Lendários e encontros únicos devem ser shiny.')
)
INSERT INTO campaign_rules(game_id, rule_key, value, value_type, description)
SELECT games.id, rule_catalog.rule_key, rule_catalog.value,
       rule_catalog.value_type, rule_catalog.description
FROM games
CROSS JOIN rule_catalog
WHERE games.code IN ('ruby', 'sapphire', 'emerald')
ON CONFLICT(game_id, rule_key) DO UPDATE SET
    value = excluded.value,
    value_type = excluded.value_type,
    description = excluded.description;

WITH step_catalog(
    mission_code, code, step_order, name, description, action, action_params,
    map_group, map_number, map_name, city, tile_x, tile_y,
    emerald_tile_x, emerald_tile_y
) AS (
    VALUES
        ('mission-001-first-starter', 'new-game', 1, 'Iniciar novo jogo', NULL,
         'function:modules.campaign.rse:run_new_game_intro', '{"trainer_name":"$profile.trainer_name","trainer_gender":"$profile.trainer_gender"}',
         NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL),
        ('mission-001-first-starter', 'set-bedroom-clock', 2, 'Ajustar relógio do quarto', NULL,
         'function:campaign:_set_bedroom_clock', '{"trainer_gender":"$profile.trainer_gender"}', 1, 1, 'LITTLEROOT_TOWN_BRENDANS_HOUSE_2F', 'Littleroot Town', 5, 2, NULL, NULL),
        ('mission-001-first-starter', 'meet-rival', 3, 'Encontrar rival', NULL,
         'function:modules.campaign.rse:run_meet_rival', '{"trainer_gender":"$profile.trainer_gender"}', 1, 3, 'LITTLEROOT_TOWN_MAYS_HOUSE_2F', 'Littleroot Town', 7, 3, 5, 5),
        ('mission-001-first-starter', 'reach-starter-bag', 4, 'Chegar à bolsa do Professor Birch', NULL,
         'function:modules.modes.starters:reach_rse_starter_bag', '{}', 0, 16, 'ROUTE101', NULL, 7, 15, NULL, NULL),
        ('mission-001-first-starter', 'choose-starter', 5, 'Obter starter shiny configurado', NULL,
         'function:campaign:_choose_starter', '{"starter":"$profile.starter","shiny_required":"$rules.starter.shiny_required"}',
         0, 16, 'ROUTE101', NULL, 7, 15, NULL, NULL),

        ('mission-002-first-poke-balls', 'defeat-route103-rival', 1, 'Derrotar rival na Route 103', NULL,
         'function:modules.campaign.rse:run_defeat_route103_rival', '{}', 0, 18, 'ROUTE103', NULL, 10, 3, 9, 3),
        ('mission-002-first-poke-balls', 'receive-first-poke-balls', 2, 'Receber Pokédex e primeiras Poké Balls', NULL,
         'function:modules.campaign.rse:run_receive_first_poke_balls', '{}', 1, 4, 'LITTLEROOT_TOWN_PROFESSOR_BIRCHS_LAB', NULL, NULL, NULL, NULL, NULL),

        ('mission-003-reach-route102', 'leave-birch-lab', 1, 'Sair do laboratório do Professor Birch', NULL,
         'function:modules.campaign.rse:run_leave_birch_lab', '{}', 0, 9, 'LITTLEROOT_TOWN', NULL, 7, 16, NULL, NULL),
        ('mission-003-reach-route102', 'reach-route101', 2, 'Receber Running Shoes e entrar na Route 101', NULL,
         'function:modules.campaign.engine:navigate_to_catalog_location', '{"map_group":"$step.map_group","map_number":"$step.map_number","tile_x":"$step.tile_x","tile_y":"$step.tile_y"}', 0, 16, 'ROUTE101', NULL, 10, 19, NULL, NULL),
        ('mission-003-reach-route102', 'reach-oldale', 3, 'Atravessar a Route 101 até Oldale', NULL,
         'function:modules.campaign.engine:navigate_to_catalog_location', '{"map_group":"$step.map_group","map_number":"$step.map_number","tile_x":"$step.tile_x","tile_y":"$step.tile_y"}', 0, 10, 'OLDALE_TOWN', NULL, 10, 18, NULL, NULL),
        ('mission-003-reach-route102', 'reach-route102', 4, 'Chegar à Route 102', NULL,
         'function:campaign:_reach_route102', '{"map_group":"$step.map_group","map_number":"$step.map_number","tile_x":"$step.tile_x","tile_y":"$step.tile_y"}', 0, 17, 'ROUTE102', NULL, 49, 10, NULL, NULL),
        ('mission-003-reach-route102', 'reach-route102-grass', 5, 'Entrar na grama da Route 102', NULL,
         'function:modules.campaign.engine:navigate_to_catalog_location', '{"map_group":"$step.map_group","map_number":"$step.map_number","tile_x":"$step.tile_x","tile_y":"$step.tile_y"}', 0, 17, 'ROUTE102', NULL, 39, 5, NULL, NULL),
        ('mission-003-reach-route102', 'catch-new-route102-pokemon', 6, 'Capturar o primeiro Pokémon selvagem', NULL,
         'function:campaign:_catch_wild_pokemon', '{"target_source_type":"other","target_source":"owned_non_starter_count","target_count":1,"capture_required":"$rules.first_wild.capture_required"}',
         0, 17, 'ROUTE102', NULL, 39, 5, NULL, NULL),
        ('mission-003-reach-route102', 'heal-captured-pokemon-oldale', 7, 'Curar equipe no Centro Pokémon de Oldale', NULL,
         'function:campaign:_heal_captured_pokemon', '{"map_group":"$step.map_group","map_number":"$step.map_number","tile_x":"$step.tile_x","tile_y":"$step.tile_y"}', 0, 10, 'OLDALE_TOWN', NULL, 6, 16, NULL, NULL),
        ('mission-003-reach-route102', 'deposit-shiny-starter', 8, 'Depositar starter shiny no PC', NULL,
         'function:modules.campaign.rse:run_deposit_party_shinies', '{"tile_x":"$step.tile_x","tile_y":"$step.tile_y","storage_required":"$rules.shiny.storage_required"}', 2, 2, 'OLDALE_TOWN_POKEMON_CENTER_1F', NULL, 10, 2, NULL, NULL),
        ('mission-003-reach-route102', 'return-route102-grass', 9, 'Voltar para a grama da Route 102', NULL,
         'function:modules.campaign.engine:navigate_to_catalog_location', '{"map_group":"$step.map_group","map_number":"$step.map_number","tile_x":"$step.tile_x","tile_y":"$step.tile_y"}', 0, 17, 'ROUTE102', NULL, 39, 5, NULL, NULL),
        ('mission-003-reach-route102', 'fill-party', 10, 'Capturar até formar equipe com seis combatentes', NULL,
         'function:campaign:_catch_wild_pokemon', '{"target_source_type":"party","target_source":"non_shiny_count","target_count":"$rules.party.target_size","deposit_shinies":"$rules.shiny.storage_required"}',
         0, 17, 'ROUTE102', NULL, 39, 5, NULL, NULL),
        ('mission-003-reach-route102', 'ev-train-captured-pokemon', 11, 'Treinar capturados até o nível 20',
         'first_gym_max_level=15; level_margin=5; target_level=20',
         'function:campaign:_ev_train_captured_pokemon', '{"target_level":20}',
         0, 17, 'ROUTE102', NULL, 39, 5, NULL, NULL)
)
INSERT INTO mission_steps(
    mission_game_id, code, step_order, name, description, action, action_params,
    recovery_action, recovery_params, map_group, map_number, map_name, city, tile_x, tile_y
)
SELECT mission_games.id, step_catalog.code, step_catalog.step_order, step_catalog.name,
       step_catalog.description, step_catalog.action, step_catalog.action_params,
       NULL, '{}', step_catalog.map_group, step_catalog.map_number, step_catalog.map_name,
       step_catalog.city,
       CASE WHEN games.code = 'emerald' AND step_catalog.emerald_tile_x IS NOT NULL
            THEN step_catalog.emerald_tile_x ELSE step_catalog.tile_x END,
       CASE WHEN games.code = 'emerald' AND step_catalog.emerald_tile_y IS NOT NULL
            THEN step_catalog.emerald_tile_y ELSE step_catalog.tile_y END
FROM step_catalog
JOIN missions ON missions.code = step_catalog.mission_code
JOIN mission_games ON mission_games.mission_id = missions.id
JOIN games ON games.id = mission_games.game_id
WHERE games.code IN ('ruby', 'sapphire', 'emerald')
ORDER BY step_catalog.mission_code,
         CASE WHEN step_catalog.code = 'reach-route102' THEN 0 ELSE step_catalog.step_order END
ON CONFLICT(mission_game_id, code) DO UPDATE SET
    step_order = excluded.step_order,
    name = excluded.name,
    description = excluded.description,
    action = excluded.action,
    action_params = excluded.action_params,
    recovery_action = excluded.recovery_action,
    recovery_params = excluded.recovery_params,
    map_group = excluded.map_group,
    map_number = excluded.map_number,
    map_name = excluded.map_name,
    city = excluded.city,
    tile_x = excluded.tile_x,
    tile_y = excluded.tile_y;

DELETE FROM step_conditions
WHERE step_id IN (
    SELECT old_steps.id
    FROM mission_steps AS old_steps
    JOIN mission_games ON mission_games.id = old_steps.mission_game_id
    JOIN missions ON missions.id = mission_games.mission_id
    JOIN games ON games.id = mission_games.game_id
    WHERE missions.code = 'mission-003-reach-route102'
      AND games.code IN ('ruby', 'sapphire', 'emerald')
)
AND (
    (
        source_type = 'party'
        AND source_key = 'non_starter_count'
        AND operator = '>='
        AND expected_value = '2'
        AND step_id IN (
            SELECT mission_steps.id
            FROM mission_steps
            JOIN mission_games ON mission_games.id = mission_steps.mission_game_id
            JOIN missions ON missions.id = mission_games.mission_id
            WHERE missions.code = 'mission-003-reach-route102'
              AND mission_steps.code IN (
                  'leave-birch-lab',
                  'reach-route101',
                  'reach-oldale',
                  'reach-route102',
                  'reach-route102-grass',
                  'catch-new-route102-pokemon',
                  'heal-captured-pokemon-oldale',
                  'deposit-shiny-starter'
              )
        )
    )
    OR (
        source_type = 'item'
        AND source_key = 'Poké Ball'
        AND operator = '='
        AND expected_value = '0'
        AND step_id IN (
            SELECT mission_steps.id
            FROM mission_steps
            WHERE mission_steps.code = 'catch-new-route102-pokemon'
        )
    )
    OR (
        source_type = 'party'
        AND source_key = 'count'
        AND operator = '>='
        AND expected_value = '2'
        AND step_id IN (
            SELECT mission_steps.id
            FROM mission_steps
            WHERE mission_steps.code IN (
                'deposit-shiny-starter',
                'ev-train-captured-pokemon'
            )
        )
    )
);

WITH condition_catalog(
    mission_code, step_code, purpose, condition_group, source_type,
    source_key, operator, expected_value, value_type
) AS (
    VALUES
        ('mission-001-first-starter', 'new-game', 'complete', 1, 'other', 'game_started', '=', 'true', 'boolean'),
        ('mission-001-first-starter', 'set-bedroom-clock', 'complete', 1, 'flag', 'SET_WALL_CLOCK', 'set', 'true', 'boolean'),
        ('mission-001-first-starter', 'meet-rival', 'complete', 1, 'var', 'LITTLEROOT_RIVAL_STATE', '>=', '3', 'integer'),
        ('mission-001-first-starter', 'reach-starter-bag', 'complete', 1, 'var', 'ROUTE101_STATE', '>=', '2', 'integer'),
        ('mission-001-first-starter', 'choose-starter', 'complete', 1, 'flag', 'SYS_POKEMON_GET', 'set', 'true', 'boolean'),
        ('mission-001-first-starter', 'choose-starter', 'complete', 1, 'flag', 'RESCUED_BIRCH', 'set', 'true', 'boolean'),
        ('mission-001-first-starter', 'choose-starter', 'complete', 1, 'var', 'BIRCH_LAB_STATE', '>=', '3', 'integer'),
        ('mission-001-first-starter', 'choose-starter', 'complete', 1, 'other', 'owns_configured_shiny_starter', '=', 'true', 'boolean'),

        ('mission-002-first-poke-balls', 'defeat-route103-rival', 'unlock', 1, 'flag', 'SYS_POKEMON_GET', 'set', 'true', 'boolean'),
        ('mission-002-first-poke-balls', 'defeat-route103-rival', 'unlock', 1, 'flag', 'RESCUED_BIRCH', 'set', 'true', 'boolean'),
        ('mission-002-first-poke-balls', 'defeat-route103-rival', 'unlock', 1, 'var', 'BIRCH_LAB_STATE', '>=', '3', 'integer'),
        ('mission-002-first-poke-balls', 'defeat-route103-rival', 'unlock', 1, 'other', 'owns_configured_shiny_starter', '=', 'true', 'boolean'),
        ('mission-002-first-poke-balls', 'defeat-route103-rival', 'complete', 1, 'flag', 'DEFEATED_RIVAL_ROUTE103', 'set', 'true', 'boolean'),
        ('mission-002-first-poke-balls', 'receive-first-poke-balls', 'unlock', 1, 'flag', 'DEFEATED_RIVAL_ROUTE103', 'set', 'true', 'boolean'),
        ('mission-002-first-poke-balls', 'receive-first-poke-balls', 'complete', 1, 'flag', 'SYS_POKEDEX_GET', 'set', 'true', 'boolean'),
        ('mission-002-first-poke-balls', 'receive-first-poke-balls', 'complete', 1, 'var', 'BIRCH_LAB_STATE', '>=', '5', 'integer'),

        ('mission-003-reach-route102', 'leave-birch-lab', 'unlock', 1, 'flag', 'SYS_POKEDEX_GET', 'set', 'true', 'boolean'),
        ('mission-003-reach-route102', 'leave-birch-lab', 'unlock', 1, 'var', 'BIRCH_LAB_STATE', '>=', '5', 'integer'),
        ('mission-003-reach-route102', 'leave-birch-lab', 'unlock', 1, 'item', 'Poké Ball', '>=', '1', 'integer'),
        ('mission-003-reach-route102', 'leave-birch-lab', 'complete', 1, 'map', 'current', '=', '0:9', 'text'),
        ('mission-003-reach-route102', 'leave-birch-lab', 'complete', 2, 'map', 'current', '=', '0:16', 'text'),
        ('mission-003-reach-route102', 'leave-birch-lab', 'complete', 3, 'map', 'current', '=', '0:10', 'text'),
        ('mission-003-reach-route102', 'leave-birch-lab', 'complete', 4, 'map', 'current', '=', '0:17', 'text'),
        ('mission-003-reach-route102', 'leave-birch-lab', 'complete', 5, 'party', 'non_starter_count', '>=', '1', 'integer'),
        ('mission-003-reach-route102', 'reach-route101', 'complete', 1, 'flag', 'RECEIVED_RUNNING_SHOES', 'set', 'true', 'boolean'),
        ('mission-003-reach-route102', 'reach-route101', 'complete', 1, 'map', 'current', '=', '0:16', 'text'),
        ('mission-003-reach-route102', 'reach-route101', 'complete', 2, 'flag', 'RECEIVED_RUNNING_SHOES', 'set', 'true', 'boolean'),
        ('mission-003-reach-route102', 'reach-route101', 'complete', 2, 'map', 'current', '=', '0:10', 'text'),
        ('mission-003-reach-route102', 'reach-route101', 'complete', 3, 'flag', 'RECEIVED_RUNNING_SHOES', 'set', 'true', 'boolean'),
        ('mission-003-reach-route102', 'reach-route101', 'complete', 3, 'map', 'current', '=', '0:17', 'text'),
        ('mission-003-reach-route102', 'reach-route101', 'complete', 4, 'party', 'non_starter_count', '>=', '1', 'integer'),
        ('mission-003-reach-route102', 'reach-oldale', 'complete', 1, 'map', 'current', '=', '0:10', 'text'),
        ('mission-003-reach-route102', 'reach-oldale', 'complete', 2, 'map', 'current', '=', '0:17', 'text'),
        ('mission-003-reach-route102', 'reach-oldale', 'complete', 3, 'party', 'non_starter_count', '>=', '1', 'integer'),
        ('mission-003-reach-route102', 'reach-route102', 'complete', 1, 'map', 'current', '=', '0:17', 'text'),
        ('mission-003-reach-route102', 'reach-route102', 'complete', 2, 'party', 'non_starter_count', '>=', '1', 'integer'),
        ('mission-003-reach-route102', 'reach-route102-grass', 'complete', 1, 'map', 'current', '=', '0:17', 'text'),
        ('mission-003-reach-route102', 'reach-route102-grass', 'complete', 1, 'tile', 'current', '=', '39:5', 'text'),
        ('mission-003-reach-route102', 'reach-route102-grass', 'complete', 2, 'party', 'non_starter_count', '>=', '1', 'integer'),
        ('mission-003-reach-route102', 'catch-new-route102-pokemon', 'unlock', 1, 'map', 'current', '=', '0:17', 'text'),
        ('mission-003-reach-route102', 'catch-new-route102-pokemon', 'unlock', 1, 'item', 'Poké Ball', '>=', '1', 'integer'),
        ('mission-003-reach-route102', 'catch-new-route102-pokemon', 'complete', 1, 'other', 'owned_non_starter_count', '>=', '1', 'integer'),
        ('mission-003-reach-route102', 'heal-captured-pokemon-oldale', 'unlock', 1, 'other', 'owned_non_starter_count', '>=', '1', 'integer'),
        ('mission-003-reach-route102', 'heal-captured-pokemon-oldale', 'complete', 1, 'party', 'all_healthy', '=', 'true', 'boolean'),
        ('mission-003-reach-route102', 'heal-captured-pokemon-oldale', 'complete', 1, 'map', 'current', '=', '0:10', 'text'),
        ('mission-003-reach-route102', 'heal-captured-pokemon-oldale', 'complete', 2, 'party', 'all_healthy', '=', 'true', 'boolean'),
        ('mission-003-reach-route102', 'heal-captured-pokemon-oldale', 'complete', 2, 'map', 'current', '=', '2:2', 'text'),
        ('mission-003-reach-route102', 'deposit-shiny-starter', 'unlock', 1, 'other', 'owned_non_starter_count', '>=', '1', 'integer'),
        ('mission-003-reach-route102', 'deposit-shiny-starter', 'complete', 1, 'other', 'shiny_starter_in_storage', '=', 'true', 'boolean'),
        ('mission-003-reach-route102', 'deposit-shiny-starter', 'complete', 1, 'party', 'configured_starter_count', '=', '0', 'integer'),
        ('mission-003-reach-route102', 'return-route102-grass', 'complete', 1, 'map', 'current', '=', '0:17', 'text'),
        ('mission-003-reach-route102', 'return-route102-grass', 'complete', 1, 'tile', 'current', '=', '39:5', 'text'),
        ('mission-003-reach-route102', 'fill-party', 'unlock', 1, 'other', 'shiny_starter_in_storage', '=', 'true', 'boolean'),
        ('mission-003-reach-route102', 'fill-party', 'unlock', 1, 'item', 'Poké Ball', '>=', '1', 'integer'),
        ('mission-003-reach-route102', 'fill-party', 'complete', 1, 'party', 'non_shiny_count', '>=', '6', 'integer'),
        ('mission-003-reach-route102', 'fill-party', 'complete', 1, 'party', 'shiny_count', '=', '0', 'integer'),
        ('mission-003-reach-route102', 'ev-train-captured-pokemon', 'unlock', 1, 'other', 'shiny_starter_in_storage', '=', 'true', 'boolean'),
        ('mission-003-reach-route102', 'ev-train-captured-pokemon', 'unlock', 1, 'party', 'non_shiny_count', '>=', '6', 'integer'),
        ('mission-003-reach-route102', 'ev-train-captured-pokemon', 'complete', 1, 'party', 'minimum_level', '>=', '20', 'integer'),
        ('mission-003-reach-route102', 'ev-train-captured-pokemon', 'complete', 1, 'party', 'non_shiny_count', '>=', '6', 'integer'),
        ('mission-003-reach-route102', 'ev-train-captured-pokemon', 'complete', 1, 'other', 'shiny_starter_in_storage', '=', 'true', 'boolean')
)
INSERT INTO step_conditions(
    step_id, purpose, condition_group, source_type, source_key,
    operator, expected_value, value_type
)
SELECT mission_steps.id, condition_catalog.purpose, condition_catalog.condition_group,
       condition_catalog.source_type, condition_catalog.source_key,
       condition_catalog.operator, condition_catalog.expected_value,
       condition_catalog.value_type
FROM condition_catalog
JOIN missions ON missions.code = condition_catalog.mission_code
JOIN mission_games ON mission_games.mission_id = missions.id
JOIN games ON games.id = mission_games.game_id
JOIN mission_steps ON mission_steps.mission_game_id = mission_games.id
                  AND mission_steps.code = condition_catalog.step_code
WHERE games.code IN ('ruby', 'sapphire', 'emerald')
ON CONFLICT(
    step_id, purpose, condition_group, source_type,
    source_key, operator, expected_value
) DO UPDATE SET value_type = excluded.value_type;

COMMIT;
