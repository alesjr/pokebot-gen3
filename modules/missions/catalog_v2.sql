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
ON CONFLICT DO UPDATE SET
    code = excluded.code,
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

INSERT INTO missions(code, name, description, category, sequence) VALUES
    ('mission-004-stone-badge', 'Mission 4 - Stone Badge', 'Petalburg, Petalburg Woods, Rustboro, and Stone Badge.', 'main_story', 4),
    ('mission-005-dynamo-badge', 'Mission 5 - Dynamo Badge', 'Devon Goods, Dewford, Slateport, and Dynamo Badge.', 'main_story', 5),
    ('mission-006-balance-badge', 'Mission 6 - Balance Badge', 'Meteor Falls, Mt. Chimney, Lavaridge, and Balance Badge.', 'main_story', 6),
    ('mission-007-feather-badge', 'Mission 7 - Feather Badge', 'Weather Institute, Devon Scope, Fortree, and Feather Badge.', 'main_story', 7),
    ('mission-008-mind-badge', 'Mission 8 - Mind Badge', 'Mt. Pyre, Magma/Aqua bases, Mossdeep, and Mind Badge.', 'main_story', 8),
    ('mission-009-rain-badge', 'Mission 9 - Rain Badge', 'Seafloor Cavern, main legendary, Sootopolis, and Rain Badge.', 'main_story', 9),
    ('mission-010-champion', 'Mission 10 - Champion', 'Victory Road, Elite Four, and Champion.', 'main_story', 10)
ON CONFLICT(code) DO UPDATE SET
    name = excluded.name,
    description = excluded.description,
    category = excluded.category,
    sequence = excluded.sequence;

WITH plans(mission_code, game_code, sequence, target_level) AS (
    VALUES
        ('mission-004-stone-badge', 'ruby', 4, 20),
        ('mission-004-stone-badge', 'sapphire', 4, 20),
        ('mission-004-stone-badge', 'emerald', 4, 20),
        ('mission-005-dynamo-badge', 'ruby', 5, 25),
        ('mission-005-dynamo-badge', 'sapphire', 5, 25),
        ('mission-005-dynamo-badge', 'emerald', 5, 25),
        ('mission-006-balance-badge', 'ruby', 6, 32),
        ('mission-006-balance-badge', 'sapphire', 6, 32),
        ('mission-006-balance-badge', 'emerald', 6, 32),
        ('mission-007-feather-badge', 'ruby', 7, 36),
        ('mission-007-feather-badge', 'sapphire', 7, 36),
        ('mission-007-feather-badge', 'emerald', 7, 36),
        ('mission-008-mind-badge', 'ruby', 8, 43),
        ('mission-008-mind-badge', 'sapphire', 8, 43),
        ('mission-008-mind-badge', 'emerald', 8, 43),
        ('mission-009-rain-badge', 'ruby', 9, 48),
        ('mission-009-rain-badge', 'sapphire', 9, 48),
        ('mission-009-rain-badge', 'emerald', 9, 48),
        ('mission-010-champion', 'ruby', 10, 58),
        ('mission-010-champion', 'sapphire', 10, 58),
        ('mission-010-champion', 'emerald', 10, 58)
)
INSERT INTO mission_games(
    mission_id, game_id, sequence, training_target_level,
    training_map_group, training_map_number, training_tile_x, training_tile_y
)
SELECT missions.id, games.id, plans.sequence, plans.target_level, 0, 17, 39, 5
FROM plans
JOIN missions ON missions.code = plans.mission_code
JOIN games ON games.code = plans.game_code
ON CONFLICT(mission_id, game_id) DO UPDATE SET
    sequence = excluded.sequence,
    training_target_level = excluded.training_target_level,
    training_map_group = excluded.training_map_group,
    training_map_number = excluded.training_map_number,
    training_tile_x = excluded.training_tile_x,
    training_tile_y = excluded.training_tile_y;

WITH steps(
    mission_code, game_code, code, step_order, name, action_params,
    map_group, map_number, map_name, city, tile_x, tile_y
) AS (
    VALUES
        ('mission-004-stone-badge', '*', 'petalburg-introduction', 1, 'Help Wally in Petalburg',
         '{"actions":[{"operation":"navigate","map_group":8,"map_number":1,"tile_x":4,"tile_y":108,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         8, 1, 'PETALBURG_CITY_GYM', 'Petalburg City', 4, 108),
        ('mission-004-stone-badge', '*', 'petalburg-woods-devon', 2, 'Protect the Devon employee in Petalburg Woods',
         '{"actions":[{"operation":"navigate","map_group":24,"map_number":11,"tile_x":26,"tile_y":23,"button":"A"}]}',
         24, 11, 'PETALBURG_WOODS', NULL, 26, 23),
        ('mission-004-stone-badge', '*', 'win-stone-badge', 3, 'Defeat Roxanne',
         '{"actions":[{"operation":"navigate","map_group":11,"map_number":3,"tile_x":5,"tile_y":3,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         11, 3, 'RUSTBORO_CITY_GYM', 'Rustboro City', 5, 3),

        ('mission-005-dynamo-badge', '*', 'recover-devon-goods', 1, 'Recover the Devon Goods',
         '{"actions":[{"operation":"navigate","map_group":24,"map_number":4,"tile_x":14,"tile_y":6,"button":"A"},{"operation":"talk_to_npc","local_object_id":6,"button":"A"}]}',
         24, 4, 'RUSTURF_TUNNEL', NULL, 14, 6),
        ('mission-005-dynamo-badge', '*', 'return-devon-goods', 2, 'Return the Devon Goods',
         '{"actions":[{"operation":"navigate","map_group":0,"map_number":3,"tile_x":13,"tile_y":35,"button":"A"},{"operation":"talk_to_npc","local_object_id":11,"button":"A"}]}',
         0, 3, 'RUSTBORO_CITY', 'Rustboro City', 13, 35),
        ('mission-005-dynamo-badge', '*', 'receive-devon-deliveries', 3, 'Receive the Devon letter and delivery',
         '{"actions":[{"operation":"navigate","map_group":11,"map_number":2,"tile_x":17,"tile_y":6,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         11, 2, 'RUSTBORO_CITY_DEVON_CORP_3F', 'Rustboro City', 17, 6),
        ('mission-005-dynamo-badge', '*', 'receive-flash', 4, 'Travel to Dewford and receive Flash',
         '{"actions":[{"operation":"navigate","map_group":17,"map_number":0,"tile_x":5,"tile_y":4,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"},{"operation":"navigate","map_group":24,"map_number":7,"tile_x":36,"tile_y":10,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         24, 7, 'GRANITE_CAVE_1F', NULL, 36, 10),
        ('mission-005-dynamo-badge', '*', 'deliver-steven-letter', 5, 'Deliver the letter to Steven',
         '{"required_hms":["Flash"],"actions":[{"operation":"navigate","map_group":24,"map_number":10,"tile_x":7,"tile_y":9,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         24, 10, 'GRANITE_CAVE_STEVENS_ROOM', NULL, 7, 9),
        ('mission-005-dynamo-badge', 'emerald', 'win-knuckle-badge', 6, 'Defeat Brawly',
         '{"actions":[{"operation":"navigate","map_group":3,"map_number":3,"tile_x":4,"tile_y":4,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         3, 3, 'DEWFORD_TOWN_GYM', 'Dewford Town', 4, 4),
        ('mission-005-dynamo-badge', 'rs', 'win-knuckle-badge', 6, 'Defeat Brawly',
         '{"actions":[{"operation":"navigate","map_group":3,"map_number":3,"tile_x":14,"tile_y":5,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         3, 3, 'DEWFORD_TOWN_GYM', 'Dewford Town', 14, 5),
        ('mission-005-dynamo-badge', '*', 'deliver-devon-goods', 7, 'Travel to Slateport and deliver the Devon Goods',
         '{"actions":[{"operation":"navigate","map_group":0,"map_number":11,"tile_x":12,"tile_y":10,"button":"A"},{"operation":"talk_to_npc","local_object_id":2,"button":"A"},{"operation":"navigate","map_group":9,"map_number":8,"tile_x":13,"tile_y":7,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         9, 8, 'SLATEPORT_CITY_OCEANIC_MUSEUM_2F', 'Slateport City', 13, 7),
        ('mission-005-dynamo-badge', '*', 'defeat-wally-mauville', 8, 'Defeat Wally in Mauville',
         '{"actions":[{"operation":"navigate","map_group":0,"map_number":2,"tile_x":8,"tile_y":7,"button":"A"},{"operation":"talk_to_npc","local_object_id":6,"button":"A"}]}',
         0, 2, 'MAUVILLE_CITY', 'Mauville City', 8, 7),
        ('mission-005-dynamo-badge', '*', 'receive-rock-smash', 9, 'Receive Rock Smash',
         '{"actions":[{"operation":"navigate","map_group":10,"map_number":2,"tile_x":4,"tile_y":5,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         10, 2, 'MAUVILLE_CITY_HOUSE1', 'Mauville City', 4, 5),
        ('mission-005-dynamo-badge', 'emerald', 'win-dynamo-badge', 10, 'Defeat Wattson',
         '{"actions":[{"operation":"navigate","map_group":10,"map_number":0,"tile_x":5,"tile_y":3,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         10, 0, 'MAUVILLE_CITY_GYM', 'Mauville City', 5, 3),
        ('mission-005-dynamo-badge', 'rs', 'win-dynamo-badge', 10, 'Defeat Wattson',
         '{"actions":[{"operation":"navigate","map_group":10,"map_number":0,"tile_x":4,"tile_y":4,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         10, 0, 'MAUVILLE_CITY_GYM', 'Mauville City', 4, 4),

        ('mission-006-balance-badge', '*', 'meteor-falls-event', 1, 'Complete the Meteor Falls event',
         '{"actions":[{"operation":"navigate","map_group":24,"map_number":0,"tile_x":14,"tile_y":22,"button":"A"}]}',
         24, 0, 'METEOR_FALLS_1F_1R', NULL, 14, 22),
        ('mission-006-balance-badge', 'ruby', 'defeat-mt-chimney-team', 2, 'Defeat Team Magma on Mt. Chimney',
         '{"actions":[{"operation":"navigate","map_group":24,"map_number":12,"tile_x":13,"tile_y":7,"button":"A"},{"operation":"talk_to_npc","local_object_id":2,"button":"A"}]}',
         24, 12, 'MT_CHIMNEY', NULL, 13, 7),
        ('mission-006-balance-badge', 'sapphire', 'defeat-mt-chimney-team', 2, 'Defeat Team Aqua on Mt. Chimney',
         '{"actions":[{"operation":"navigate","map_group":24,"map_number":12,"tile_x":24,"tile_y":20,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         24, 12, 'MT_CHIMNEY', NULL, 24, 20),
        ('mission-006-balance-badge', 'emerald', 'defeat-mt-chimney-team', 2, 'Defeat Team Magma on Mt. Chimney',
         '{"actions":[{"operation":"navigate","map_group":24,"map_number":12,"tile_x":13,"tile_y":7,"button":"A"},{"operation":"talk_to_npc","local_object_id":2,"button":"A"}]}',
         24, 12, 'MT_CHIMNEY', NULL, 13, 7),
        ('mission-006-balance-badge', 'emerald', 'win-heat-badge', 3, 'Defeat Flannery',
         '{"actions":[{"operation":"navigate","map_group":4,"map_number":1,"tile_x":13,"tile_y":10,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         4, 1, 'LAVARIDGE_TOWN_GYM_1F', 'Lavaridge Town', 13, 10),
        ('mission-006-balance-badge', 'rs', 'win-heat-badge', 3, 'Defeat Flannery',
         '{"actions":[{"operation":"navigate","map_group":4,"map_number":1,"tile_x":8,"tile_y":11,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         4, 1, 'LAVARIDGE_TOWN_GYM_1F', 'Lavaridge Town', 8, 11),
        ('mission-006-balance-badge', 'emerald', 'win-balance-badge', 4, 'Defeat Norman',
         '{"actions":[{"operation":"navigate","map_group":8,"map_number":1,"tile_x":4,"tile_y":3,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         8, 1, 'PETALBURG_CITY_GYM', 'Petalburg City', 4, 3),
        ('mission-006-balance-badge', 'rs', 'win-balance-badge', 4, 'Defeat Norman',
         '{"actions":[{"operation":"navigate","map_group":8,"map_number":1,"tile_x":4,"tile_y":4,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         8, 1, 'PETALBURG_CITY_GYM', 'Petalburg City', 4, 4),
        ('mission-006-balance-badge', '*', 'receive-surf', 5, 'Receive Surf',
         '{"actions":[{"operation":"navigate","map_group":8,"map_number":0,"tile_x":3,"tile_y":5,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         8, 0, 'PETALBURG_CITY_WALLYS_HOUSE', 'Petalburg City', 3, 5),

        ('mission-007-feather-badge', 'emerald', 'clear-weather-institute', 1, 'Drive Team Aqua out of the Weather Institute',
         '{"required_hms":["Surf"],"actions":[{"operation":"navigate","map_group":32,"map_number":1,"tile_x":4,"tile_y":7,"button":"A"},{"operation":"talk_to_npc","local_object_id":3,"button":"A"}]}',
         32, 1, 'ROUTE119_WEATHER_INSTITUTE_2F', NULL, 4, 7),
        ('mission-007-feather-badge', 'rs', 'clear-weather-institute', 1, 'Drive the team out of the Weather Institute',
         '{"required_hms":["Surf"],"actions":[{"operation":"navigate","map_group":32,"map_number":1,"tile_x":4,"tile_y":7,"button":"A"},{"operation":"talk_to_npc","local_object_id":3,"button":"A"}]}',
         32, 1, 'ROUTE119_WEATHER_INSTITUTE_2F', NULL, 4, 7),
        ('mission-007-feather-badge', '*', 'receive-fly', 2, 'Defeat the rival and receive Fly',
         '{"required_hms":["Surf"],"actions":[{"operation":"navigate","map_group":0,"map_number":35,"tile_x":13,"tile_y":16,"button":"A"}]}',
         0, 35, 'ROUTE120', NULL, 13, 16),
        ('mission-007-feather-badge', '*', 'receive-devon-scope', 3, 'Receive the Devon Scope',
         '{"required_hms":["Surf","Fly"],"actions":[{"operation":"navigate","map_group":0,"map_number":35,"tile_x":13,"tile_y":16,"button":"A"},{"operation":"talk_to_npc","local_object_id":31,"button":"A"}]}',
         0, 35, 'ROUTE120', NULL, 13, 16),
        ('mission-007-feather-badge', 'emerald', 'win-feather-badge', 4, 'Defeat Winona',
         '{"required_hms":["Surf","Fly"],"actions":[{"operation":"navigate","map_group":12,"map_number":1,"tile_x":15,"tile_y":3,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         12, 1, 'FORTREE_CITY_GYM', 'Fortree City', 15, 3),
        ('mission-007-feather-badge', 'rs', 'win-feather-badge', 4, 'Defeat Winona',
         '{"required_hms":["Surf","Fly"],"actions":[{"operation":"navigate","map_group":12,"map_number":1,"tile_x":4,"tile_y":2,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         12, 1, 'FORTREE_CITY_GYM', 'Fortree City', 4, 2),

        ('mission-008-mind-badge', '*', 'receive-orb-mt-pyre', 1, 'Complete Mt. Pyre and receive the Orb',
         '{"required_hms":["Surf","Fly"],"actions":[{"operation":"navigate","map_group":24,"map_number":22,"tile_x":23,"tile_y":7,"button":"A"},{"operation":"talk_to_npc","local_object_id":3,"button":"A"}]}',
         24, 22, 'MT_PYRE_SUMMIT', NULL, 23, 7),
        ('mission-008-mind-badge', 'emerald', 'awaken-groudon-magma-hideout', 2, 'Complete Magma Hideout',
         '{"required_hms":["Rock Smash","Strength"],"actions":[{"operation":"navigate","map_group":24,"map_number":91,"tile_x":16,"tile_y":22,"button":"A"},{"operation":"talk_to_npc","local_object_id":6,"button":"A"}]}',
         24, 91, 'MAGMA_HIDEOUT_4F', NULL, 16, 22),
        ('mission-008-mind-badge', '*', 'clear-submarine-hideout', 3, 'Prevent the submarine escape at the hideout',
         '{"required_hms":["Surf","Fly"],"actions":[{"operation":"navigate","map_group":9,"map_number":9,"tile_x":6,"tile_y":12,"button":"A"},{"operation":"talk_to_npc","local_object_id":4,"button":"A"},{"operation":"navigate","map_group":24,"map_number":25,"tile_x":23,"tile_y":20,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         24, 25, 'AQUA_HIDEOUT_B2F', 'Lilycove City', 23, 20),
        ('mission-008-mind-badge', 'emerald', 'win-mind-badge', 4, 'Defeat Tate and Liza',
         '{"required_hms":["Surf","Fly"],"actions":[{"operation":"navigate","map_group":14,"map_number":0,"tile_x":23,"tile_y":8,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         14, 0, 'MOSSDEEP_CITY_GYM', 'Mossdeep City', 23, 8),
        ('mission-008-mind-badge', 'rs', 'win-mind-badge', 4, 'Defeat Tate and Liza',
         '{"required_hms":["Surf","Fly"],"actions":[{"operation":"navigate","map_group":14,"map_number":0,"tile_x":8,"tile_y":4,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         14, 0, 'MOSSDEEP_CITY_GYM', 'Mossdeep City', 8, 4),
        ('mission-008-mind-badge', 'emerald', 'defend-space-center', 5, 'Defeat Team Magma at the Space Center',
         '{"actions":[{"operation":"navigate","map_group":14,"map_number":10,"tile_x":1,"tile_y":9,"button":"A"},{"operation":"talk_to_npc","local_object_id":4,"button":"A"}]}',
         14, 10, 'MOSSDEEP_CITY_SPACE_CENTER_2F', 'Mossdeep City', 1, 9),
        ('mission-008-mind-badge', '*', 'receive-dive', 6, 'Receive Dive',
         '{"required_hms":["Surf"],"actions":[{"operation":"navigate","map_group":14,"map_number":7,"tile_x":9,"tile_y":7,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         14, 7, 'MOSSDEEP_CITY_STEVENS_HOUSE', 'Mossdeep City', 9, 7),

        ('mission-009-rain-badge', 'ruby', 'release-main-legend', 1, 'Complete Seafloor Cavern',
         '{"required_hms":["Surf","Dive","Rock Smash","Strength"],"actions":[{"operation":"navigate","map_group":24,"map_number":27,"tile_x":10,"tile_y":2,"button":"A"},{"operation":"puzzle_solver"},{"operation":"navigate","map_group":24,"map_number":36,"tile_x":16,"tile_y":38,"button":"A"}]}',
         24, 36, 'SEAFLOOR_CAVERN_ROOM9', NULL, 16, 38),
        ('mission-009-rain-badge', 'sapphire', 'release-main-legend', 1, 'Complete Seafloor Cavern',
         '{"required_hms":["Surf","Dive","Rock Smash","Strength"],"actions":[{"operation":"navigate","map_group":24,"map_number":27,"tile_x":10,"tile_y":2,"button":"A"},{"operation":"puzzle_solver"},{"operation":"navigate","map_group":24,"map_number":36,"tile_x":16,"tile_y":38,"button":"A"}]}',
         24, 36, 'SEAFLOOR_CAVERN_ROOM9', NULL, 16, 38),
        ('mission-009-rain-badge', 'emerald', 'release-main-legend', 1, 'Complete Seafloor Cavern',
         '{"required_hms":["Surf","Dive","Rock Smash","Strength"],"actions":[{"operation":"navigate","map_group":24,"map_number":27,"tile_x":10,"tile_y":2,"button":"A"},{"operation":"puzzle_solver"},{"operation":"navigate","map_group":24,"map_number":36,"tile_x":16,"tile_y":38,"button":"A"}]}',
         24, 36, 'SEAFLOOR_CAVERN_ROOM9', NULL, 16, 38),
        ('mission-009-rain-badge', 'emerald', 'open-sky-pillar', 2, 'Open Sky Pillar',
         '{"required_hms":["Surf","Dive"],"actions":[{"operation":"navigate","map_group":24,"map_number":42,"tile_x":9,"tile_y":14,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         24, 42, 'CAVE_OF_ORIGIN_B1F', 'Sootopolis City', 9, 14),
        ('mission-009-rain-badge', 'ruby', 'capture-main-legend-shiny', 2, 'Capture shiny Groudon',
         '{"constructor":{},"arguments":{"shiny_only":true,"stop_when_caught":true,"target_name":"Groudon","encounter_type":"static","shiny_locked":false}}',
         24, 42, 'CAVE_OF_ORIGIN_B1F', 'Sootopolis City', 9, 14),
        ('mission-009-rain-badge', 'sapphire', 'capture-main-legend-shiny', 2, 'Capture shiny Kyogre',
         '{"constructor":{},"arguments":{"shiny_only":true,"stop_when_caught":true,"target_name":"Kyogre","encounter_type":"static","shiny_locked":false}}',
         24, 42, 'CAVE_OF_ORIGIN_B1F', 'Sootopolis City', 9, 14),
        ('mission-009-rain-badge', 'emerald', 'capture-main-legend-shiny', 3, 'Solve Sky Pillar and capture shiny Rayquaza',
         '{"constructor":{},"arguments":{"shiny_only":true,"stop_when_caught":true,"target_name":"Rayquaza","encounter_type":"static","shiny_locked":false,"solve_puzzle":true}}',
         24, 85, 'SKY_PILLAR_TOP', NULL, 14, 7),
        ('mission-009-rain-badge', 'rs', 'receive-waterfall', 3, 'Obtain Waterfall in the Cave of Origin',
         '{"required_hms":["Surf","Dive"],"actions":[{"operation":"navigate","map_group":24,"map_number":40,"tile_x":6,"tile_y":6,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         24, 40, 'CAVE_OF_ORIGIN_B3F', 'Sootopolis City', 6, 6),
        ('mission-009-rain-badge', 'emerald', 'receive-waterfall', 4, 'Receive Waterfall from Wallace',
         '{"required_hms":["Surf","Dive"],"actions":[{"operation":"navigate","map_group":0,"map_number":7,"tile_x":31,"tile_y":19,"button":"A"},{"operation":"talk_to_npc","local_object_id":18,"button":"A"}]}',
         0, 7, 'SOOTOPOLIS_CITY', 'Sootopolis City', 31, 19),
        ('mission-009-rain-badge', '*', 'win-rain-badge', 5, 'Defeat the Sootopolis Gym Leader',
         '{"required_hms":["Surf","Dive"],"actions":[{"operation":"navigate","map_group":15,"map_number":0,"tile_x":8,"tile_y":3,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         15, 0, 'SOOTOPOLIS_CITY_GYM_1F', 'Sootopolis City', 8, 3),

        ('mission-010-champion', '*', 'defeat-wally-victory-road', 1, 'Defeat Wally on Victory Road',
         '{"required_hms":["Surf","Strength","Rock Smash","Waterfall"],"actions":[{"operation":"navigate","map_group":24,"map_number":43,"tile_x":31,"tile_y":10,"button":"A"},{"operation":"talk_to_npc","local_object_id":7,"button":"A"}]}',
         24, 43, 'VICTORY_ROAD_1F', NULL, 31, 10),
        ('mission-010-champion', '*', 'defeat-elite-sidney', 2, 'Defeat Sidney',
         '{"required_hms":["Surf","Strength","Rock Smash","Waterfall"],"actions":[{"operation":"navigate","map_group":16,"map_number":0,"tile_x":6,"tile_y":6,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         16, 0, 'EVER_GRANDE_CITY_SIDNEYS_ROOM', 'Ever Grande City', 6, 6),
        ('mission-010-champion', '*', 'defeat-elite-phoebe', 3, 'Defeat Phoebe',
         '{"actions":[{"operation":"navigate","map_group":16,"map_number":1,"tile_x":6,"tile_y":6,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         16, 1, 'EVER_GRANDE_CITY_PHOEBES_ROOM', 'Ever Grande City', 6, 6),
        ('mission-010-champion', '*', 'defeat-elite-glacia', 4, 'Defeat Glacia',
         '{"actions":[{"operation":"navigate","map_group":16,"map_number":2,"tile_x":6,"tile_y":6,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         16, 2, 'EVER_GRANDE_CITY_GLACIAS_ROOM', 'Ever Grande City', 6, 6),
        ('mission-010-champion', '*', 'defeat-elite-drake', 5, 'Defeat Drake',
         '{"actions":[{"operation":"navigate","map_group":16,"map_number":3,"tile_x":6,"tile_y":6,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         16, 3, 'EVER_GRANDE_CITY_DRAKES_ROOM', 'Ever Grande City', 6, 6),
        ('mission-010-champion', '*', 'become-champion', 6, 'Defeat the Champion',
         '{"actions":[{"operation":"navigate","map_group":16,"map_number":4,"tile_x":6,"tile_y":6,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         16, 4, 'EVER_GRANDE_CITY_CHAMPIONS_ROOM', 'Ever Grande City', 6, 6)
)
INSERT INTO mission_steps(
    mission_game_id, code, step_order, name, description, action, action_params,
    recovery_action, recovery_params, map_group, map_number, map_name, city, tile_x, tile_y
)
SELECT mission_games.id, steps.code, steps.step_order, steps.name, NULL,
       CASE WHEN steps.code = 'capture-main-legend-shiny'
            THEN 'mode:Static Soft Resets:run'
            ELSE 'function:modules.campaign.actions:run_catalog_actions' END,
       steps.action_params, NULL, '{}', steps.map_group, steps.map_number,
       steps.map_name, steps.city, steps.tile_x, steps.tile_y
FROM steps
JOIN missions ON missions.code = steps.mission_code
JOIN mission_games ON mission_games.mission_id = missions.id
JOIN games ON games.id = mission_games.game_id
WHERE steps.game_code = '*'
   OR steps.game_code = games.code
   OR (steps.game_code = 'rs' AND games.code IN ('ruby', 'sapphire'))
ON CONFLICT DO UPDATE SET
    code = excluded.code,
    step_order = excluded.step_order,
    name = excluded.name,
    action = excluded.action,
    action_params = excluded.action_params,
    map_group = excluded.map_group,
    map_number = excluded.map_number,
    map_name = excluded.map_name,
    city = excluded.city,
    tile_x = excluded.tile_x,
    tile_y = excluded.tile_y;


WITH conditions(mission_code, game_code, step_code, source_type, source_key, operator, expected_value, value_type) AS (
    VALUES
        ('mission-004-stone-badge', '*', 'petalburg-introduction', 'var', 'PETALBURG_GYM_STATE', '>=', '2', 'integer'),
        ('mission-004-stone-badge', '*', 'petalburg-woods-devon', 'var', 'PETALBURG_WOODS_STATE', '>=', '1', 'integer'),
        ('mission-004-stone-badge', '*', 'win-stone-badge', 'flag', 'BADGE01_GET', 'set', 'true', 'boolean'),
        ('mission-005-dynamo-badge', '*', 'recover-devon-goods', 'flag', 'RECOVERED_DEVON_GOODS', 'set', 'true', 'boolean'),
        ('mission-005-dynamo-badge', '*', 'return-devon-goods', 'flag', 'RETURNED_DEVON_GOODS', 'set', 'true', 'boolean'),
        ('mission-005-dynamo-badge', '*', 'receive-devon-deliveries', 'item', 'Letter', '>=', '1', 'integer'),
        ('mission-005-dynamo-badge', 'rs', 'receive-flash', 'flag', 'RECEIVED_HM05', 'set', 'true', 'boolean'),
        ('mission-005-dynamo-badge', 'emerald', 'receive-flash', 'flag', 'RECEIVED_HM_FLASH', 'set', 'true', 'boolean'),
        ('mission-005-dynamo-badge', '*', 'deliver-steven-letter', 'flag', 'DELIVERED_STEVEN_LETTER', 'set', 'true', 'boolean'),
        ('mission-005-dynamo-badge', '*', 'win-knuckle-badge', 'flag', 'BADGE02_GET', 'set', 'true', 'boolean'),
        ('mission-005-dynamo-badge', '*', 'deliver-devon-goods', 'flag', 'DELIVERED_DEVON_GOODS', 'set', 'true', 'boolean'),
        ('mission-005-dynamo-badge', '*', 'defeat-wally-mauville', 'flag', 'DEFEATED_WALLY_MAUVILLE', 'set', 'true', 'boolean'),
        ('mission-005-dynamo-badge', 'rs', 'receive-rock-smash', 'flag', 'RECEIVED_HM06', 'set', 'true', 'boolean'),
        ('mission-005-dynamo-badge', 'emerald', 'receive-rock-smash', 'flag', 'RECEIVED_HM_ROCK_SMASH', 'set', 'true', 'boolean'),
        ('mission-005-dynamo-badge', '*', 'win-dynamo-badge', 'flag', 'BADGE03_GET', 'set', 'true', 'boolean'),
        ('mission-006-balance-badge', '*', 'meteor-falls-event', 'var', 'METEOR_FALLS_STATE', '>=', '1', 'integer'),
        ('mission-006-balance-badge', '*', 'defeat-mt-chimney-team', 'flag', 'DEFEATED_EVIL_TEAM_MT_CHIMNEY', 'set', 'true', 'boolean'),
        ('mission-006-balance-badge', '*', 'win-heat-badge', 'flag', 'BADGE04_GET', 'set', 'true', 'boolean'),
        ('mission-006-balance-badge', '*', 'win-balance-badge', 'flag', 'BADGE05_GET', 'set', 'true', 'boolean'),
        ('mission-006-balance-badge', 'rs', 'receive-surf', 'flag', 'RECEIVED_HM03', 'set', 'true', 'boolean'),
        ('mission-006-balance-badge', 'emerald', 'receive-surf', 'flag', 'RECEIVED_HM_SURF', 'set', 'true', 'boolean'),
        ('mission-007-feather-badge', 'rs', 'clear-weather-institute', 'flag', 'HIDE_EVIL_TEAM_WEATHER_INSTITUTE', 'set', 'true', 'boolean'),
        ('mission-007-feather-badge', 'emerald', 'clear-weather-institute', 'flag', 'HIDE_ROUTE_119_TEAM_AQUA', 'set', 'true', 'boolean'),
        ('mission-007-feather-badge', 'rs', 'receive-fly', 'flag', 'RECEIVED_HM02', 'set', 'true', 'boolean'),
        ('mission-007-feather-badge', 'emerald', 'receive-fly', 'flag', 'RECEIVED_HM_FLY', 'set', 'true', 'boolean'),
        ('mission-007-feather-badge', '*', 'receive-devon-scope', 'flag', 'RECEIVED_DEVON_SCOPE', 'set', 'true', 'boolean'),
        ('mission-007-feather-badge', '*', 'win-feather-badge', 'flag', 'BADGE06_GET', 'set', 'true', 'boolean'),
        ('mission-008-mind-badge', '*', 'receive-orb-mt-pyre', 'flag', 'RECEIVED_RED_OR_BLUE_ORB', 'set', 'true', 'boolean'),
        ('mission-008-mind-badge', 'emerald', 'awaken-groudon-magma-hideout', 'flag', 'GROUDON_AWAKENED_MAGMA_HIDEOUT', 'set', 'true', 'boolean'),
        ('mission-008-mind-badge', 'rs', 'clear-submarine-hideout', 'flag', 'EVIL_TEAM_ESCAPED_IN_SUBMARINE', 'set', 'true', 'boolean'),
        ('mission-008-mind-badge', 'emerald', 'clear-submarine-hideout', 'flag', 'TEAM_AQUA_ESCAPED_IN_SUBMARINE', 'set', 'true', 'boolean'),
        ('mission-008-mind-badge', '*', 'win-mind-badge', 'flag', 'BADGE07_GET', 'set', 'true', 'boolean'),
        ('mission-008-mind-badge', 'emerald', 'defend-space-center', 'flag', 'DEFEATED_MAGMA_SPACE_CENTER', 'set', 'true', 'boolean'),
        ('mission-008-mind-badge', 'rs', 'receive-dive', 'flag', 'RECEIVED_HM08', 'set', 'true', 'boolean'),
        ('mission-008-mind-badge', 'emerald', 'receive-dive', 'flag', 'RECEIVED_HM_DIVE', 'set', 'true', 'boolean'),
        ('mission-009-rain-badge', 'rs', 'release-main-legend', 'flag', 'LEGEND_ESCAPED_SEAFLOOR_CAVERN', 'set', 'true', 'boolean'),
        ('mission-009-rain-badge', 'emerald', 'release-main-legend', 'flag', 'KYOGRE_ESCAPED_SEAFLOOR_CAVERN', 'set', 'true', 'boolean'),
        ('mission-009-rain-badge', 'emerald', 'open-sky-pillar', 'flag', 'WALLACE_GOES_TO_SKY_PILLAR', 'set', 'true', 'boolean'),
        ('mission-009-rain-badge', 'ruby', 'capture-main-legend-shiny', 'other', 'owns_shiny_species:Groudon', '=', 'true', 'boolean'),
        ('mission-009-rain-badge', 'sapphire', 'capture-main-legend-shiny', 'other', 'owns_shiny_species:Kyogre', '=', 'true', 'boolean'),
        ('mission-009-rain-badge', 'emerald', 'capture-main-legend-shiny', 'other', 'owns_shiny_species:Rayquaza', '=', 'true', 'boolean'),
        ('mission-009-rain-badge', 'rs', 'receive-waterfall', 'item', 'HM07', '>=', '1', 'integer'),
        ('mission-009-rain-badge', 'emerald', 'receive-waterfall', 'flag', 'RECEIVED_HM_WATERFALL', 'set', 'true', 'boolean'),
        ('mission-009-rain-badge', '*', 'win-rain-badge', 'flag', 'BADGE08_GET', 'set', 'true', 'boolean'),
        ('mission-010-champion', '*', 'defeat-wally-victory-road', 'flag', 'DEFEATED_WALLY_VICTORY_ROAD', 'set', 'true', 'boolean'),
        ('mission-010-champion', 'rs', 'defeat-elite-sidney', 'flag', 'DEFEATED_ELITE_4_SYDNEY', 'set', 'true', 'boolean'),
        ('mission-010-champion', 'emerald', 'defeat-elite-sidney', 'flag', 'DEFEATED_ELITE_4_SIDNEY', 'set', 'true', 'boolean'),
        ('mission-010-champion', '*', 'defeat-elite-phoebe', 'flag', 'DEFEATED_ELITE_4_PHOEBE', 'set', 'true', 'boolean'),
        ('mission-010-champion', '*', 'defeat-elite-glacia', 'flag', 'DEFEATED_ELITE_4_GLACIA', 'set', 'true', 'boolean'),
        ('mission-010-champion', '*', 'defeat-elite-drake', 'flag', 'DEFEATED_ELITE_4_DRAKE', 'set', 'true', 'boolean'),
        ('mission-010-champion', 'rs', 'become-champion', 'flag', 'SYS_GAME_CLEAR', 'set', 'true', 'boolean'),
        ('mission-010-champion', 'emerald', 'become-champion', 'flag', 'IS_CHAMPION', 'set', 'true', 'boolean')
)
INSERT INTO step_conditions(
    step_id, purpose, condition_group, source_type, source_key,
    operator, expected_value, value_type
)
SELECT mission_steps.id, 'complete', 1, conditions.source_type,
       conditions.source_key, conditions.operator, conditions.expected_value,
       conditions.value_type
FROM conditions
JOIN missions ON missions.code = conditions.mission_code
JOIN mission_games ON mission_games.mission_id = missions.id
JOIN games ON games.id = mission_games.game_id
JOIN mission_steps ON mission_steps.mission_game_id = mission_games.id
                  AND mission_steps.code = conditions.step_code
WHERE conditions.game_code = '*'
   OR conditions.game_code = games.code
   OR (conditions.game_code = 'rs' AND games.code IN ('ruby', 'sapphire'))
ON CONFLICT(
    step_id, purpose, condition_group, source_type,
    source_key, operator, expected_value
) DO UPDATE SET value_type = excluded.value_type;

WITH unlocks(mission_code, game_code, step_code, source_type, source_key, operator, expected_value, value_type) AS (
    VALUES
        ('mission-004-stone-badge', '*', 'petalburg-introduction', 'other', 'shiny_starter_in_storage', '=', 'true', 'boolean'),
        ('mission-005-dynamo-badge', '*', 'recover-devon-goods', 'flag', 'BADGE01_GET', 'set', 'true', 'boolean'),
        ('mission-006-balance-badge', '*', 'meteor-falls-event', 'flag', 'BADGE03_GET', 'set', 'true', 'boolean'),
        ('mission-007-feather-badge', '*', 'clear-weather-institute', 'flag', 'BADGE05_GET', 'set', 'true', 'boolean'),
        ('mission-008-mind-badge', '*', 'receive-orb-mt-pyre', 'flag', 'BADGE06_GET', 'set', 'true', 'boolean'),
        ('mission-009-rain-badge', 'rs', 'release-main-legend', 'flag', 'RECEIVED_HM08', 'set', 'true', 'boolean'),
        ('mission-009-rain-badge', 'emerald', 'release-main-legend', 'flag', 'RECEIVED_HM_DIVE', 'set', 'true', 'boolean'),
        ('mission-010-champion', '*', 'defeat-wally-victory-road', 'flag', 'BADGE08_GET', 'set', 'true', 'boolean')
)
INSERT INTO step_conditions(
    step_id, purpose, condition_group, source_type, source_key,
    operator, expected_value, value_type
)
SELECT mission_steps.id, 'unlock', 1, unlocks.source_type,
       unlocks.source_key, unlocks.operator, unlocks.expected_value,
       unlocks.value_type
FROM unlocks
JOIN missions ON missions.code = unlocks.mission_code
JOIN mission_games ON mission_games.mission_id = missions.id
JOIN games ON games.id = mission_games.game_id
JOIN mission_steps ON mission_steps.mission_game_id = mission_games.id
                  AND mission_steps.code = unlocks.step_code
WHERE unlocks.game_code = '*'
   OR unlocks.game_code = games.code
   OR (unlocks.game_code = 'rs' AND games.code IN ('ruby', 'sapphire'))
ON CONFLICT(
    step_id, purpose, condition_group, source_type,
    source_key, operator, expected_value
) DO UPDATE SET value_type = excluded.value_type;

COMMIT;
