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
        'Mission 1 - Obtain the first shiny starter',
        'Starts the game, completes Littleroot events, and obtains the configured shiny starter.',
        'main_story',
        1
    ),
    (
        'mission-002-first-poke-balls',
        'Mission 2 - Receive the first Poké Balls',
        'Defeats the rival on Route 103 and receives the Pokédex and first Poké Balls.',
        'main_story',
        2
    ),
    (
        'mission-003-reach-route102',
        'Mission 3 - Reach the first route',
        'Reaches Route 102, makes the first capture, and forms the initial party.',
        'main_story',
        3
    )
ON CONFLICT(code) DO UPDATE SET
    name = excluded.name,
    description = excluded.description,
    category = excluded.category,
    sequence = excluded.sequence;

WITH mission_game_catalog(
    mission_code, sequence, training_target_level,
    training_map_group, training_map_number, training_tile_x, training_tile_y
) AS (
    VALUES
        ('mission-001-first-starter', 1, NULL, 0, 16, 7, 15),
        ('mission-002-first-poke-balls', 2, 5, 0, 16, 7, 15),
        ('mission-003-reach-route102', 3, 5, 0, 16, 7, 15)
)
INSERT INTO mission_games(
    mission_id, game_id, sequence, training_target_level,
    training_map_group, training_map_number, training_tile_x, training_tile_y
)
SELECT missions.id, games.id, mission_game_catalog.sequence,
       mission_game_catalog.training_target_level,
       mission_game_catalog.training_map_group,
       mission_game_catalog.training_map_number,
       mission_game_catalog.training_tile_x,
       mission_game_catalog.training_tile_y
FROM mission_game_catalog
JOIN missions ON missions.code = mission_game_catalog.mission_code
CROSS JOIN games
WHERE games.code IN ('ruby', 'sapphire', 'emerald')
ON CONFLICT(mission_id, game_id) DO UPDATE SET
    sequence = excluded.sequence,
    training_target_level = excluded.training_target_level,
    training_map_group = excluded.training_map_group,
    training_map_number = excluded.training_map_number,
    training_tile_x = excluded.training_tile_x,
    training_tile_y = excluded.training_tile_y;

WITH rule_catalog(rule_key, value, value_type, description) AS (
    VALUES
        ('shiny.capture_required', 'true', 'boolean', 'Capture every encountered shiny Pokémon.'),
        ('shiny.storage_required', 'true', 'boolean', 'Store shiny Pokémon in the PC.'),
        ('shiny.pc_terminal_tile', '[10,2]', 'json', 'Terminal position in RSE Pokémon Centers.'),
        ('starter.shiny_required', 'true', 'boolean', 'The first starter must be shiny.'),
        ('first_wild.capture_required', 'true', 'boolean', 'Capture the first wild encounter after obtaining Poké Balls.'),
        ('training.before_mission', 'true', 'boolean', 'Train before missions to the required level.'),
        ('training.whiteout_level_increment', '1', 'integer', 'Increase the minimum target by one level after each whiteout.'),
        ('recovery.heal_before_risk', 'true', 'boolean', 'Heal a party below the safe threshold before proceeding.'),
        ('party.target_size', '6', 'integer', 'Capture until the party contains six Pokémon.'),
        ('party.combat_score', 'base_stats_plus_ivs', 'text', 'Compare potential using base stats and IVs.'),
        ('party.combat_level_weight', '0', 'integer', 'Level does not affect potential comparison.'),
        ('party.shiny_combatants', 'false', 'boolean', 'Shiny Pokémon never occupy combatant slots.'),
        ('party.optimize_on_pc_access', 'true', 'boolean', 'Compare party and storage when accessing the PC.'),
        ('party.selection_tiebreak', 'ivs_then_stable_identity', 'text', 'Break ties using IVs and stable identity, never level.'),
        ('hm.slot_policy', 'minimum_required_coverage', 'text', 'Use the smallest HM Slayer set covering the required HMs.'),
        ('hm.preferred_coverage', '4', 'integer', 'Prefer an HM Slayer capable of learning four different HMs.'),
        ('unique.shiny_required', 'true', 'boolean', 'Legendary and unique encounters must be shiny.')
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
        ('mission-001-first-starter', 'new-game', 1, 'Start a new game', NULL,
         'function:modules.campaign.rse:run_new_game_intro', '{"trainer_name":"$profile.trainer_name","trainer_gender":"$profile.trainer_gender"}',
         NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL),
        ('mission-001-first-starter', 'set-bedroom-clock', 2, 'Set the bedroom clock', NULL,
         'function:campaign:_set_bedroom_clock', '{"trainer_gender":"$profile.trainer_gender"}', 1, 1, 'LITTLEROOT_TOWN_BRENDANS_HOUSE_2F', 'Littleroot Town', 5, 2, NULL, NULL),
        ('mission-001-first-starter', 'meet-rival', 3, 'Meet the rival', NULL,
         'function:modules.campaign.rse:run_meet_rival', '{"trainer_gender":"$profile.trainer_gender"}', 1, 3, 'LITTLEROOT_TOWN_MAYS_HOUSE_2F', 'Littleroot Town', 7, 3, 5, 5),
        ('mission-001-first-starter', 'reach-starter-bag', 4, 'Reach Professor Birch''s bag', NULL,
         'function:modules.modes.starters:reach_rse_starter_bag', '{}', 0, 16, 'ROUTE101', NULL, 7, 15, NULL, NULL),
        ('mission-001-first-starter', 'choose-starter', 5, 'Obtain the configured shiny starter', NULL,
         'function:campaign:_choose_starter', '{"starter":"$profile.starter","shiny_required":"$rules.starter.shiny_required"}',
         0, 16, 'ROUTE101', NULL, 7, 15, NULL, NULL),

        ('mission-002-first-poke-balls', 'defeat-route103-rival', 1, 'Defeat the rival on Route 103', NULL,
         'function:modules.campaign.rse:run_defeat_route103_rival', '{}', 0, 18, 'ROUTE103', NULL, 10, 3, 9, 3),
        ('mission-002-first-poke-balls', 'receive-first-poke-balls', 2, 'Receive the Pokédex and first Poké Balls', NULL,
         'function:modules.campaign.rse:run_receive_first_poke_balls', '{}', 1, 4, 'LITTLEROOT_TOWN_PROFESSOR_BIRCHS_LAB', NULL, NULL, NULL, NULL, NULL),

        ('mission-003-reach-route102', 'leave-birch-lab', 1, 'Leave Professor Birch''s lab', NULL,
         'function:modules.campaign.rse:run_leave_birch_lab', '{}', 0, 9, 'LITTLEROOT_TOWN', NULL, 7, 16, NULL, NULL),
        ('mission-003-reach-route102', 'reach-route101', 2, 'Receive Running Shoes and enter Route 101', NULL,
         'function:modules.campaign.engine:navigate_to_catalog_location', '{"map_group":"$step.map_group","map_number":"$step.map_number","tile_x":"$step.tile_x","tile_y":"$step.tile_y"}', 0, 16, 'ROUTE101', NULL, 10, 19, NULL, NULL),
        ('mission-003-reach-route102', 'reach-oldale', 3, 'Cross Route 101 to Oldale', NULL,
         'function:modules.campaign.engine:navigate_to_catalog_location', '{"map_group":"$step.map_group","map_number":"$step.map_number","tile_x":"$step.tile_x","tile_y":"$step.tile_y"}', 0, 10, 'OLDALE_TOWN', NULL, 10, 18, NULL, NULL),
        ('mission-003-reach-route102', 'reach-route102', 4, 'Reach Route 102', NULL,
         'function:modules.campaign.engine:navigate_to_catalog_location', '{"map_group":"$step.map_group","map_number":"$step.map_number","tile_x":"$step.tile_x","tile_y":"$step.tile_y"}', 0, 17, 'ROUTE102', NULL, 49, 10, NULL, NULL),
        ('mission-003-reach-route102', 'reach-route102-grass', 5, 'Enter the grass on Route 102', NULL,
         'function:modules.campaign.engine:navigate_to_catalog_location', '{"map_group":"$step.map_group","map_number":"$step.map_number","tile_x":"$step.tile_x","tile_y":"$step.tile_y"}', 0, 17, 'ROUTE102', NULL, 39, 5, NULL, NULL),
        ('mission-003-reach-route102', 'catch-new-route102-pokemon', 6, 'Capture the first wild Pokémon', NULL,
         'function:campaign:_catch_wild_pokemon', '{"target_source_type":"other","target_source":"owned_non_starter_count","target_count":1,"capture_required":"$rules.first_wild.capture_required"}',
         0, 17, 'ROUTE102', NULL, 39, 5, NULL, NULL),
        ('mission-003-reach-route102', 'heal-captured-pokemon-oldale', 7, 'Heal the party at Oldale Pokémon Center', NULL,
         'function:campaign:_heal_captured_pokemon', '{"map_group":"$step.map_group","map_number":"$step.map_number","tile_x":"$step.tile_x","tile_y":"$step.tile_y"}', 0, 10, 'OLDALE_TOWN', NULL, 6, 16, NULL, NULL),
        ('mission-003-reach-route102', 'deposit-shiny-starter', 8, 'Deposit the shiny starter in the PC', NULL,
         'function:modules.campaign.rse:run_organize_party_at_pc', '{"tile_x":"$step.tile_x","tile_y":"$step.tile_y","storage_required":"$rules.shiny.storage_required","optimize_party":"$rules.party.optimize_on_pc_access","target_size":"$rules.party.target_size","required_hms":[],"temporary_required_species":[]}', 2, 2, 'OLDALE_TOWN_POKEMON_CENTER_1F', NULL, 10, 2, NULL, NULL),
        ('mission-003-reach-route102', 'return-route102-grass', 9, 'Return to the grass on Route 102', NULL,
         'function:modules.campaign.engine:navigate_to_catalog_location', '{"map_group":"$step.map_group","map_number":"$step.map_number","tile_x":"$step.tile_x","tile_y":"$step.tile_y"}', 0, 17, 'ROUTE102', NULL, 39, 5, NULL, NULL),
        ('mission-003-reach-route102', 'fill-party', 10, 'Capture until the party has six combatants', NULL,
         'function:campaign:_catch_wild_pokemon', '{"target_source_type":"party","target_source":"non_shiny_count","target_count":"$rules.party.target_size","deposit_shinies":"$rules.shiny.storage_required"}',
         0, 17, 'ROUTE102', NULL, 39, 5, NULL, NULL),
        ('mission-003-reach-route102', 'ev-train-captured-pokemon', 11, 'Train captured Pokémon to level 20',
         'first_gym_max_level=15; level_margin=5; target_level=20',
         'mode:EV Train:run_until_party_level', '{"constructor":{},"arguments":{"target_level":20,"include_shiny":false}}',
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
