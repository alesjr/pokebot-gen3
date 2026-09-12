BEGIN IMMEDIATE;

INSERT INTO missions(code, name, description, category, sequence) VALUES
    ('mission-004-stone-badge', 'Missão 4 - Stone Badge', 'Petalburg, Petalburg Woods, Rustboro e Stone Badge.', 'main_story', 4),
    ('mission-005-dynamo-badge', 'Missão 5 - Dynamo Badge', 'Devon Goods, Dewford, Slateport e Dynamo Badge.', 'main_story', 5),
    ('mission-006-balance-badge', 'Missão 6 - Balance Badge', 'Meteor Falls, Mt. Chimney, Lavaridge e Balance Badge.', 'main_story', 6),
    ('mission-007-feather-badge', 'Missão 7 - Feather Badge', 'Weather Institute, Devon Scope, Fortree e Feather Badge.', 'main_story', 7),
    ('mission-008-mind-badge', 'Missão 8 - Mind Badge', 'Mt. Pyre, bases Magma/Aqua, Mossdeep e Mind Badge.', 'main_story', 8),
    ('mission-009-rain-badge', 'Missão 9 - Rain Badge', 'Seafloor Cavern, lendário principal, Sootopolis e Rain Badge.', 'main_story', 9),
    ('mission-010-champion', 'Missão 10 - Champion', 'Victory Road, Elite Four e Champion.', 'main_story', 10)
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
        ('mission-004-stone-badge', '*', 'petalburg-introduction', 1, 'Ajudar Wally em Petalburg',
         '{"actions":[{"operation":"navigate","map_group":8,"map_number":1,"tile_x":4,"tile_y":108,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         8, 1, 'PETALBURG_CITY_GYM', 'Petalburg City', 4, 108),
        ('mission-004-stone-badge', '*', 'petalburg-woods-devon', 2, 'Proteger funcionário Devon em Petalburg Woods',
         '{"actions":[{"operation":"navigate","map_group":24,"map_number":11,"tile_x":26,"tile_y":23,"button":"A"}]}',
         24, 11, 'PETALBURG_WOODS', NULL, 26, 23),
        ('mission-004-stone-badge', '*', 'win-stone-badge', 3, 'Derrotar Roxanne',
         '{"actions":[{"operation":"navigate","map_group":11,"map_number":3,"tile_x":5,"tile_y":3,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         11, 3, 'RUSTBORO_CITY_GYM', 'Rustboro City', 5, 3),

        ('mission-005-dynamo-badge', '*', 'recover-devon-goods', 1, 'Recuperar Devon Goods',
         '{"actions":[{"operation":"navigate","map_group":24,"map_number":4,"tile_x":14,"tile_y":6,"button":"A"},{"operation":"talk_to_npc","local_object_id":6,"button":"A"}]}',
         24, 4, 'RUSTURF_TUNNEL', NULL, 14, 6),
        ('mission-005-dynamo-badge', '*', 'return-devon-goods', 2, 'Devolver Devon Goods',
         '{"actions":[{"operation":"navigate","map_group":0,"map_number":3,"tile_x":13,"tile_y":35,"button":"A"},{"operation":"talk_to_npc","local_object_id":11,"button":"A"}]}',
         0, 3, 'RUSTBORO_CITY', 'Rustboro City', 13, 35),
        ('mission-005-dynamo-badge', '*', 'receive-devon-deliveries', 3, 'Receber carta e entrega Devon',
         '{"actions":[{"operation":"navigate","map_group":11,"map_number":2,"tile_x":17,"tile_y":6,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         11, 2, 'RUSTBORO_CITY_DEVON_CORP_3F', 'Rustboro City', 17, 6),
        ('mission-005-dynamo-badge', '*', 'receive-flash', 4, 'Viajar para Dewford e receber Flash',
         '{"actions":[{"operation":"navigate","map_group":17,"map_number":0,"tile_x":5,"tile_y":4,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"},{"operation":"navigate","map_group":24,"map_number":7,"tile_x":36,"tile_y":10,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         24, 7, 'GRANITE_CAVE_1F', NULL, 36, 10),
        ('mission-005-dynamo-badge', '*', 'deliver-steven-letter', 5, 'Entregar carta a Steven',
         '{"required_hms":["Flash"],"actions":[{"operation":"navigate","map_group":24,"map_number":10,"tile_x":7,"tile_y":9,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         24, 10, 'GRANITE_CAVE_STEVENS_ROOM', NULL, 7, 9),
        ('mission-005-dynamo-badge', 'emerald', 'win-knuckle-badge', 6, 'Derrotar Brawly',
         '{"actions":[{"operation":"navigate","map_group":3,"map_number":3,"tile_x":4,"tile_y":4,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         3, 3, 'DEWFORD_TOWN_GYM', 'Dewford Town', 4, 4),
        ('mission-005-dynamo-badge', 'rs', 'win-knuckle-badge', 6, 'Derrotar Brawly',
         '{"actions":[{"operation":"navigate","map_group":3,"map_number":3,"tile_x":14,"tile_y":5,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         3, 3, 'DEWFORD_TOWN_GYM', 'Dewford Town', 14, 5),
        ('mission-005-dynamo-badge', '*', 'deliver-devon-goods', 7, 'Viajar para Slateport e entregar Devon Goods',
         '{"actions":[{"operation":"navigate","map_group":0,"map_number":11,"tile_x":12,"tile_y":10,"button":"A"},{"operation":"talk_to_npc","local_object_id":2,"button":"A"},{"operation":"navigate","map_group":9,"map_number":8,"tile_x":13,"tile_y":7,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         9, 8, 'SLATEPORT_CITY_OCEANIC_MUSEUM_2F', 'Slateport City', 13, 7),
        ('mission-005-dynamo-badge', '*', 'defeat-wally-mauville', 8, 'Derrotar Wally em Mauville',
         '{"actions":[{"operation":"navigate","map_group":0,"map_number":2,"tile_x":8,"tile_y":7,"button":"A"},{"operation":"talk_to_npc","local_object_id":6,"button":"A"}]}',
         0, 2, 'MAUVILLE_CITY', 'Mauville City', 8, 7),
        ('mission-005-dynamo-badge', '*', 'receive-rock-smash', 9, 'Receber Rock Smash',
         '{"actions":[{"operation":"navigate","map_group":10,"map_number":2,"tile_x":4,"tile_y":5,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         10, 2, 'MAUVILLE_CITY_HOUSE1', 'Mauville City', 4, 5),
        ('mission-005-dynamo-badge', 'emerald', 'win-dynamo-badge', 10, 'Derrotar Wattson',
         '{"actions":[{"operation":"navigate","map_group":10,"map_number":0,"tile_x":5,"tile_y":3,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         10, 0, 'MAUVILLE_CITY_GYM', 'Mauville City', 5, 3),
        ('mission-005-dynamo-badge', 'rs', 'win-dynamo-badge', 10, 'Derrotar Wattson',
         '{"actions":[{"operation":"navigate","map_group":10,"map_number":0,"tile_x":4,"tile_y":4,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         10, 0, 'MAUVILLE_CITY_GYM', 'Mauville City', 4, 4),

        ('mission-006-balance-badge', '*', 'meteor-falls-event', 1, 'Concluir evento de Meteor Falls',
         '{"actions":[{"operation":"navigate","map_group":24,"map_number":0,"tile_x":14,"tile_y":22,"button":"A"}]}',
         24, 0, 'METEOR_FALLS_1F_1R', NULL, 14, 22),
        ('mission-006-balance-badge', 'ruby', 'defeat-mt-chimney-team', 2, 'Derrotar Team Magma no Mt. Chimney',
         '{"actions":[{"operation":"navigate","map_group":24,"map_number":12,"tile_x":13,"tile_y":7,"button":"A"},{"operation":"talk_to_npc","local_object_id":2,"button":"A"}]}',
         24, 12, 'MT_CHIMNEY', NULL, 13, 7),
        ('mission-006-balance-badge', 'sapphire', 'defeat-mt-chimney-team', 2, 'Derrotar Team Aqua no Mt. Chimney',
         '{"actions":[{"operation":"navigate","map_group":24,"map_number":12,"tile_x":24,"tile_y":20,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         24, 12, 'MT_CHIMNEY', NULL, 24, 20),
        ('mission-006-balance-badge', 'emerald', 'defeat-mt-chimney-team', 2, 'Derrotar Team Magma no Mt. Chimney',
         '{"actions":[{"operation":"navigate","map_group":24,"map_number":12,"tile_x":13,"tile_y":7,"button":"A"},{"operation":"talk_to_npc","local_object_id":2,"button":"A"}]}',
         24, 12, 'MT_CHIMNEY', NULL, 13, 7),
        ('mission-006-balance-badge', 'emerald', 'win-heat-badge', 3, 'Derrotar Flannery',
         '{"actions":[{"operation":"navigate","map_group":4,"map_number":1,"tile_x":13,"tile_y":10,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         4, 1, 'LAVARIDGE_TOWN_GYM_1F', 'Lavaridge Town', 13, 10),
        ('mission-006-balance-badge', 'rs', 'win-heat-badge', 3, 'Derrotar Flannery',
         '{"actions":[{"operation":"navigate","map_group":4,"map_number":1,"tile_x":8,"tile_y":11,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         4, 1, 'LAVARIDGE_TOWN_GYM_1F', 'Lavaridge Town', 8, 11),
        ('mission-006-balance-badge', 'emerald', 'win-balance-badge', 4, 'Derrotar Norman',
         '{"actions":[{"operation":"navigate","map_group":8,"map_number":1,"tile_x":4,"tile_y":3,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         8, 1, 'PETALBURG_CITY_GYM', 'Petalburg City', 4, 3),
        ('mission-006-balance-badge', 'rs', 'win-balance-badge', 4, 'Derrotar Norman',
         '{"actions":[{"operation":"navigate","map_group":8,"map_number":1,"tile_x":4,"tile_y":4,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         8, 1, 'PETALBURG_CITY_GYM', 'Petalburg City', 4, 4),
        ('mission-006-balance-badge', '*', 'receive-surf', 5, 'Receber Surf',
         '{"actions":[{"operation":"navigate","map_group":8,"map_number":0,"tile_x":3,"tile_y":5,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         8, 0, 'PETALBURG_CITY_WALLYS_HOUSE', 'Petalburg City', 3, 5),

        ('mission-007-feather-badge', 'emerald', 'clear-weather-institute', 1, 'Expulsar Team Aqua do Weather Institute',
         '{"required_hms":["Surf"],"actions":[{"operation":"navigate","map_group":32,"map_number":1,"tile_x":4,"tile_y":7,"button":"A"},{"operation":"talk_to_npc","local_object_id":3,"button":"A"}]}',
         32, 1, 'ROUTE119_WEATHER_INSTITUTE_2F', NULL, 4, 7),
        ('mission-007-feather-badge', 'rs', 'clear-weather-institute', 1, 'Expulsar equipe do Weather Institute',
         '{"required_hms":["Surf"],"actions":[{"operation":"navigate","map_group":32,"map_number":1,"tile_x":4,"tile_y":7,"button":"A"},{"operation":"talk_to_npc","local_object_id":3,"button":"A"}]}',
         32, 1, 'ROUTE119_WEATHER_INSTITUTE_2F', NULL, 4, 7),
        ('mission-007-feather-badge', '*', 'receive-fly', 2, 'Derrotar rival e receber Fly',
         '{"required_hms":["Surf"],"actions":[{"operation":"navigate","map_group":0,"map_number":35,"tile_x":13,"tile_y":16,"button":"A"}]}',
         0, 35, 'ROUTE120', NULL, 13, 16),
        ('mission-007-feather-badge', '*', 'receive-devon-scope', 3, 'Receber Devon Scope',
         '{"required_hms":["Surf","Fly"],"actions":[{"operation":"navigate","map_group":0,"map_number":35,"tile_x":13,"tile_y":16,"button":"A"},{"operation":"talk_to_npc","local_object_id":31,"button":"A"}]}',
         0, 35, 'ROUTE120', NULL, 13, 16),
        ('mission-007-feather-badge', 'emerald', 'win-feather-badge', 4, 'Derrotar Winona',
         '{"required_hms":["Surf","Fly"],"actions":[{"operation":"navigate","map_group":12,"map_number":1,"tile_x":15,"tile_y":3,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         12, 1, 'FORTREE_CITY_GYM', 'Fortree City', 15, 3),
        ('mission-007-feather-badge', 'rs', 'win-feather-badge', 4, 'Derrotar Winona',
         '{"required_hms":["Surf","Fly"],"actions":[{"operation":"navigate","map_group":12,"map_number":1,"tile_x":4,"tile_y":2,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         12, 1, 'FORTREE_CITY_GYM', 'Fortree City', 4, 2),

        ('mission-008-mind-badge', '*', 'receive-orb-mt-pyre', 1, 'Concluir Mt. Pyre e receber o Orb',
         '{"required_hms":["Surf","Fly"],"actions":[{"operation":"navigate","map_group":24,"map_number":22,"tile_x":23,"tile_y":7,"button":"A"},{"operation":"talk_to_npc","local_object_id":3,"button":"A"}]}',
         24, 22, 'MT_PYRE_SUMMIT', NULL, 23, 7),
        ('mission-008-mind-badge', 'emerald', 'awaken-groudon-magma-hideout', 2, 'Concluir Magma Hideout',
         '{"required_hms":["Rock Smash","Strength"],"actions":[{"operation":"navigate","map_group":24,"map_number":91,"tile_x":16,"tile_y":22,"button":"A"},{"operation":"talk_to_npc","local_object_id":6,"button":"A"}]}',
         24, 91, 'MAGMA_HIDEOUT_4F', NULL, 16, 22),
        ('mission-008-mind-badge', '*', 'clear-submarine-hideout', 3, 'Impedir fuga do submarino na base',
         '{"required_hms":["Surf","Fly"],"actions":[{"operation":"navigate","map_group":9,"map_number":9,"tile_x":6,"tile_y":12,"button":"A"},{"operation":"talk_to_npc","local_object_id":4,"button":"A"},{"operation":"navigate","map_group":24,"map_number":25,"tile_x":23,"tile_y":20,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         24, 25, 'AQUA_HIDEOUT_B2F', 'Lilycove City', 23, 20),
        ('mission-008-mind-badge', 'emerald', 'win-mind-badge', 4, 'Derrotar Tate e Liza',
         '{"required_hms":["Surf","Fly"],"actions":[{"operation":"navigate","map_group":14,"map_number":0,"tile_x":23,"tile_y":8,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         14, 0, 'MOSSDEEP_CITY_GYM', 'Mossdeep City', 23, 8),
        ('mission-008-mind-badge', 'rs', 'win-mind-badge', 4, 'Derrotar Tate e Liza',
         '{"required_hms":["Surf","Fly"],"actions":[{"operation":"navigate","map_group":14,"map_number":0,"tile_x":8,"tile_y":4,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         14, 0, 'MOSSDEEP_CITY_GYM', 'Mossdeep City', 8, 4),
        ('mission-008-mind-badge', 'emerald', 'defend-space-center', 5, 'Derrotar Team Magma no Space Center',
         '{"actions":[{"operation":"navigate","map_group":14,"map_number":10,"tile_x":1,"tile_y":9,"button":"A"},{"operation":"talk_to_npc","local_object_id":4,"button":"A"}]}',
         14, 10, 'MOSSDEEP_CITY_SPACE_CENTER_2F', 'Mossdeep City', 1, 9),
        ('mission-008-mind-badge', '*', 'receive-dive', 6, 'Receber Dive',
         '{"required_hms":["Surf"],"actions":[{"operation":"navigate","map_group":14,"map_number":7,"tile_x":9,"tile_y":7,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         14, 7, 'MOSSDEEP_CITY_STEVENS_HOUSE', 'Mossdeep City', 9, 7),

        ('mission-009-rain-badge', 'ruby', 'release-main-legend', 1, 'Concluir Seafloor Cavern',
         '{"required_hms":["Surf","Dive","Rock Smash","Strength"],"actions":[{"operation":"navigate","map_group":24,"map_number":27,"tile_x":10,"tile_y":2,"button":"A"},{"operation":"puzzle_solver"},{"operation":"navigate","map_group":24,"map_number":36,"tile_x":16,"tile_y":38,"button":"A"}]}',
         24, 36, 'SEAFLOOR_CAVERN_ROOM9', NULL, 16, 38),
        ('mission-009-rain-badge', 'sapphire', 'release-main-legend', 1, 'Concluir Seafloor Cavern',
         '{"required_hms":["Surf","Dive","Rock Smash","Strength"],"actions":[{"operation":"navigate","map_group":24,"map_number":27,"tile_x":10,"tile_y":2,"button":"A"},{"operation":"puzzle_solver"},{"operation":"navigate","map_group":24,"map_number":36,"tile_x":16,"tile_y":38,"button":"A"}]}',
         24, 36, 'SEAFLOOR_CAVERN_ROOM9', NULL, 16, 38),
        ('mission-009-rain-badge', 'emerald', 'release-main-legend', 1, 'Concluir Seafloor Cavern',
         '{"required_hms":["Surf","Dive","Rock Smash","Strength"],"actions":[{"operation":"navigate","map_group":24,"map_number":27,"tile_x":10,"tile_y":2,"button":"A"},{"operation":"puzzle_solver"},{"operation":"navigate","map_group":24,"map_number":36,"tile_x":16,"tile_y":38,"button":"A"}]}',
         24, 36, 'SEAFLOOR_CAVERN_ROOM9', NULL, 16, 38),
        ('mission-009-rain-badge', 'emerald', 'open-sky-pillar', 2, 'Abrir Sky Pillar',
         '{"required_hms":["Surf","Dive"],"actions":[{"operation":"navigate","map_group":24,"map_number":42,"tile_x":9,"tile_y":14,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         24, 42, 'CAVE_OF_ORIGIN_B1F', 'Sootopolis City', 9, 14),
        ('mission-009-rain-badge', 'ruby', 'capture-main-legend-shiny', 2, 'Capturar Groudon shiny',
         '{"constructor":{},"arguments":{"shiny_only":true,"stop_when_caught":true,"target_name":"Groudon","encounter_type":"static","shiny_locked":false}}',
         24, 42, 'CAVE_OF_ORIGIN_B1F', 'Sootopolis City', 9, 14),
        ('mission-009-rain-badge', 'sapphire', 'capture-main-legend-shiny', 2, 'Capturar Kyogre shiny',
         '{"constructor":{},"arguments":{"shiny_only":true,"stop_when_caught":true,"target_name":"Kyogre","encounter_type":"static","shiny_locked":false}}',
         24, 42, 'CAVE_OF_ORIGIN_B1F', 'Sootopolis City', 9, 14),
        ('mission-009-rain-badge', 'emerald', 'capture-main-legend-shiny', 3, 'Resolver Sky Pillar e capturar Rayquaza shiny',
         '{"constructor":{},"arguments":{"shiny_only":true,"stop_when_caught":true,"target_name":"Rayquaza","encounter_type":"static","shiny_locked":false,"solve_puzzle":true}}',
         24, 85, 'SKY_PILLAR_TOP', NULL, 14, 7),
        ('mission-009-rain-badge', 'rs', 'receive-waterfall', 3, 'Obter Waterfall na Cave of Origin',
         '{"required_hms":["Surf","Dive"],"actions":[{"operation":"navigate","map_group":24,"map_number":40,"tile_x":6,"tile_y":6,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         24, 40, 'CAVE_OF_ORIGIN_B3F', 'Sootopolis City', 6, 6),
        ('mission-009-rain-badge', 'emerald', 'receive-waterfall', 4, 'Receber Waterfall de Wallace',
         '{"required_hms":["Surf","Dive"],"actions":[{"operation":"navigate","map_group":0,"map_number":7,"tile_x":31,"tile_y":19,"button":"A"},{"operation":"talk_to_npc","local_object_id":18,"button":"A"}]}',
         0, 7, 'SOOTOPOLIS_CITY', 'Sootopolis City', 31, 19),
        ('mission-009-rain-badge', '*', 'win-rain-badge', 5, 'Derrotar líder de Sootopolis',
         '{"required_hms":["Surf","Dive"],"actions":[{"operation":"navigate","map_group":15,"map_number":0,"tile_x":8,"tile_y":3,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         15, 0, 'SOOTOPOLIS_CITY_GYM_1F', 'Sootopolis City', 8, 3),

        ('mission-010-champion', '*', 'defeat-wally-victory-road', 1, 'Derrotar Wally em Victory Road',
         '{"required_hms":["Surf","Strength","Rock Smash","Waterfall"],"actions":[{"operation":"navigate","map_group":24,"map_number":43,"tile_x":31,"tile_y":10,"button":"A"},{"operation":"talk_to_npc","local_object_id":7,"button":"A"}]}',
         24, 43, 'VICTORY_ROAD_1F', NULL, 31, 10),
        ('mission-010-champion', '*', 'defeat-elite-sidney', 2, 'Derrotar Sidney',
         '{"required_hms":["Surf","Strength","Rock Smash","Waterfall"],"actions":[{"operation":"navigate","map_group":16,"map_number":0,"tile_x":6,"tile_y":6,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         16, 0, 'EVER_GRANDE_CITY_SIDNEYS_ROOM', 'Ever Grande City', 6, 6),
        ('mission-010-champion', '*', 'defeat-elite-phoebe', 3, 'Derrotar Phoebe',
         '{"actions":[{"operation":"navigate","map_group":16,"map_number":1,"tile_x":6,"tile_y":6,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         16, 1, 'EVER_GRANDE_CITY_PHOEBES_ROOM', 'Ever Grande City', 6, 6),
        ('mission-010-champion', '*', 'defeat-elite-glacia', 4, 'Derrotar Glacia',
         '{"actions":[{"operation":"navigate","map_group":16,"map_number":2,"tile_x":6,"tile_y":6,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         16, 2, 'EVER_GRANDE_CITY_GLACIAS_ROOM', 'Ever Grande City', 6, 6),
        ('mission-010-champion', '*', 'defeat-elite-drake', 5, 'Derrotar Drake',
         '{"actions":[{"operation":"navigate","map_group":16,"map_number":3,"tile_x":6,"tile_y":6,"button":"A"},{"operation":"talk_to_npc","local_object_id":1,"button":"A"}]}',
         16, 3, 'EVER_GRANDE_CITY_DRAKES_ROOM', 'Ever Grande City', 6, 6),
        ('mission-010-champion', '*', 'become-champion', 6, 'Derrotar Champion',
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
ON CONFLICT(mission_game_id, code) DO UPDATE SET
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

DELETE FROM step_conditions
WHERE step_id IN (
    SELECT mission_steps.id
    FROM mission_steps
    JOIN mission_games ON mission_games.id = mission_steps.mission_game_id
    JOIN missions ON missions.id = mission_games.mission_id
    WHERE missions.sequence BETWEEN 4 AND 10
);

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
   OR (conditions.game_code = 'rs' AND games.code IN ('ruby', 'sapphire'));

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
   OR (unlocks.game_code = 'rs' AND games.code IN ('ruby', 'sapphire'));

COMMIT;
