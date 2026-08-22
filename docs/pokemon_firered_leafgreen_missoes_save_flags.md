# Pokémon FireRed / LeafGreen — Catálogo de objetivos para detecção de progresso por save

> **Fonte técnica principal:** decompilação `pret/pokefirered`.
>
> **Importante:** FireRed e LeafGreen compartilham praticamente toda a estrutura de roteiro e flags. As diferenças de versão afetam principalmente Pokémon disponíveis, encounters e alguns detalhes de conteúdo, e não o grafo principal de missões.

---

# 1. Convenções

## Jogos

```text
FR   = Pokémon FireRed
LG   = Pokémon LeafGreen
FRLG = ambos
```

## Categorias

```text
MAIN      = objetivo necessário para concluir a campanha
SIDE      = objetivo opcional / secundário
SEVII     = arco das Sevii Islands
POSTGAME  = objetivo liberado depois da primeira Liga
EVENT     = conteúdo de distribuição/evento
UTILITY   = item/HM/feature importante para progressão
```

## Status sugeridos

```text
LOCKED
AVAILABLE
IN_PROGRESS
COMPLETED
SKIPPED
UNKNOWN
```

## Confiança sugerida

```text
VERY_HIGH = flag específica e inequívoca
HIGH      = badge/item/event flag diretamente ligado ao objetivo
MEDIUM    = combinação de scene var/trainer flag/map state
LOW       = inferência indireta por localização/item atual
```

---

# 2. Regra fundamental para seu parser

Nunca derive progresso apenas por:

```text
mapa atual
posição atual
nível dos Pokémon
tempo de jogo
quantidade de badges isoladamente
```

Use prioridade:

```text
1. event flag específica
2. system flag específica
3. trainer flag específica
4. map-scene/story var
5. key item/HM recebido
6. badge
7. world-map visited flag
8. localização atual
```

Exemplo correto:

```text
FLAG_GOT_SS_TICKET == true
AND FLAG_HELPED_BILL_IN_SEA_COTTAGE == true
```

é uma evidência melhor de que o arco de Bill foi concluído do que simplesmente detectar o jogador em Vermilion.

---

# 3. Espaço de flags de FireRed / LeafGreen

O decomp define:

```text
TRAINER_FLAGS_START = 0x500
TRAINER_FLAGS_END   = 0x7FF
SYS_FLAGS           = 0x800
```

Portanto:

```text
0x000-0x4FF = event/object/story flags
0x500-0x7FF = trainer flags
0x800-0x8FF = system/world-map flags
```

> IDs de flag são identificadores lógicos. Não os trate como offsets absolutos no arquivo `.sav`.

---

# 4. System flags fundamentais

```text
FLAG_BADGE01_GET         = 0x820
FLAG_BADGE02_GET         = 0x821
FLAG_BADGE03_GET         = 0x822
FLAG_BADGE04_GET         = 0x823
FLAG_BADGE05_GET         = 0x824
FLAG_BADGE06_GET         = 0x825
FLAG_BADGE07_GET         = 0x826
FLAG_BADGE08_GET         = 0x827

FLAG_SYS_POKEMON_GET     = 0x828
FLAG_SYS_POKEDEX_GET     = 0x829
FLAG_SYS_GAME_CLEAR      = 0x82C

FLAG_SYS_B_DASH          = 0x82F

FLAG_SYS_NATIONAL_DEX    = 0x840
FLAG_SYS_CAN_LINK_WITH_RS = 0x844
FLAG_SYS_SEVII_MAP_123   = 0x845
FLAG_SYS_SEVII_MAP_4567  = 0x846
FLAG_SYS_GOT_BERRY_POUCH = 0x847
FLAG_SYS_DEOXYS_AWAKENED = 0x848
FLAG_SYS_UNLOCKED_TANOBY_RUINS = 0x849
FLAG_ENABLE_SHIP_NAVEL_ROCK    = 0x84A
FLAG_ENABLE_SHIP_BIRTH_ISLAND  = 0x84B
```

---

# 5. Badges

| Nº | Badge | Líder | Flag |
|---:|---|---|---|
| 1 | Boulder Badge | Brock | `FLAG_BADGE01_GET = 0x820` |
| 2 | Cascade Badge | Misty | `FLAG_BADGE02_GET = 0x821` |
| 3 | Thunder Badge | Lt. Surge | `FLAG_BADGE03_GET = 0x822` |
| 4 | Rainbow Badge | Erika | `FLAG_BADGE04_GET = 0x823` |
| 5 | Soul Badge | Koga | `FLAG_BADGE05_GET = 0x824` |
| 6 | Marsh Badge | Sabrina | `FLAG_BADGE06_GET = 0x825` |
| 7 | Volcano Badge | Blaine | `FLAG_BADGE07_GET = 0x826` |
| 8 | Earth Badge | Giovanni | `FLAG_BADGE08_GET = 0x827` |

> **Atenção:** parte da sequência intermediária é flexível. Koga, Sabrina e alguns objetivos de Celadon/Lavender podem ser feitos em ordens diferentes. Não use um contador linear de badges como única fonte.

---

# 6. Vars fundamentais

```text
VAR_STARTER_MON = 0x4031
```

Valores:

```text
0 = Bulbasaur
1 = Squirtle
2 = Charmander
```

Map scene vars importantes:

```text
VAR_MAP_SCENE_PALLET_TOWN_OAK                    = 0x4050
VAR_MAP_SCENE_VIRIDIAN_CITY_OLD_MAN              = 0x4051
VAR_MAP_SCENE_CERULEAN_CITY_RIVAL                = 0x4052
VAR_VERMILION_CITY_TICKET_CHECK_TRIGGER          = 0x4053
VAR_MAP_SCENE_ROUTE22                            = 0x4054
VAR_MAP_SCENE_PALLET_TOWN_PROFESSOR_OAKS_LAB     = 0x4055
VAR_MAP_SCENE_PALLET_TOWN_PLAYERS_HOUSE_2F       = 0x4056
VAR_MAP_SCENE_VIRIDIAN_CITY_MART                 = 0x4057
VAR_MAP_SCENE_PALLET_TOWN_RIVALS_HOUSE           = 0x4058
VAR_MAP_SCENE_POKEMON_TOWER_6F                   = 0x4059
VAR_MAP_SCENE_VIRIDIAN_CITY_GYM_DOOR             = 0x405A
VAR_MAP_SCENE_S_S_ANNE_2F_CORRIDOR               = 0x405B
VAR_MAP_SCENE_SILPH_CO_7F                        = 0x405C
VAR_MAP_SCENE_POKEMON_TOWER_2F                   = 0x405D
VAR_MAP_SCENE_ROUTE16                            = 0x405E
VAR_MAP_SCENE_ROUTE23                            = 0x405F
VAR_MAP_SCENE_SILPH_CO_11F                      = 0x4060
VAR_MAP_SCENE_ROUTE5_ROUTE6_ROUTE7_ROUTE8_GATES = 0x4062
VAR_MAP_SCENE_VICTORY_ROAD_1F                   = 0x4064
VAR_MAP_SCENE_VICTORY_ROAD_2F_BOULDER1          = 0x4065
VAR_MAP_SCENE_VICTORY_ROAD_2F_BOULDER2          = 0x4066
VAR_MAP_SCENE_VICTORY_ROAD_3F                   = 0x4067
VAR_MAP_SCENE_POKEMON_LEAGUE                    = 0x4068
VAR_MAP_SCENE_ROUTE24                           = 0x406B
VAR_MAP_SCENE_PEWTER_CITY                       = 0x406C
VAR_MAP_SCENE_CINNABAR_ISLAND                   = 0x4071
VAR_MAP_SCENE_ONE_ISLAND_HARBOR                 = 0x4075
VAR_MAP_SCENE_ONE_ISLAND_POKEMON_CENTER_1F      = 0x4076
```

Também é relevante:

```text
VAR_NATIONAL_DEX = 0x404E
```

> `VAR_NATIONAL_DEX` e `FLAG_SYS_NATIONAL_DEX` não devem ser confundidos. Para detectar o desbloqueio em alto nível, prefira a system flag.

---

# 7. CAMPANHA PRINCIPAL

---

## CAPÍTULO 1 — Pallet Town

### FRLG-001 — Sair de casa

```yaml
id: FRLG-001
games: [FR, LG]
category: MAIN
location: Pallet Town
```

Pré-requisito:

```text
novo jogo
```

Estado útil:

```text
VAR_MAP_SCENE_PALLET_TOWN_PLAYERS_HOUSE_2F
```

---

### FRLG-002 — Ser parado por Professor Oak

- **Jogos:** FRLG
- **Local:** Pallet Town
- **Categoria:** MAIN

Estado principal:

```text
VAR_MAP_SCENE_PALLET_TOWN_OAK
```

Professor Oak impede o jogador de entrar na Route 1 sem Pokémon e leva o personagem ao laboratório.

---

### FRLG-003 — Escolher o Pokémon inicial

- **Jogos:** FRLG
- **Categoria:** MAIN
- **Local:** Oak's Lab

Conclusão confiável:

```text
FLAG_SYS_POKEMON_GET == true
```

Valor do starter:

```text
VAR_STARTER_MON
```

Valores:

```text
0 Bulbasaur
1 Squirtle
2 Charmander
```

---

### FRLG-004 — Derrotar ou enfrentar o rival no laboratório

- **Jogos:** FRLG
- **Categoria:** MAIN-associated
- **Local:** Oak's Lab

Flag específica:

```text
FLAG_BEAT_RIVAL_IN_OAKS_LAB = 0x258
```

Se a luta for perdida, o roteiro continua.

Portanto:

```text
FLAG_BEAT_RIVAL_IN_OAKS_LAB
```

deve ser interpretada como:

```text
RIVAL_BATTLE_WON
```

e não obrigatoriamente como:

```text
RIVAL_BATTLE_EVENT_COMPLETED
```

Para detectar conclusão do evento, combine com a scene var do laboratório.

---

## CAPÍTULO 2 — Viridian / Oak's Parcel

### FRLG-005 — Chegar a Viridian City

- **Jogos:** FRLG
- **Categoria:** MAIN

Detector secundário:

```text
FLAG_WORLD_MAP_VIRIDIAN_CITY
```

---

### FRLG-006 — Receber Oak's Parcel

- **Jogos:** FRLG
- **Categoria:** MAIN
- **Local:** Viridian Poké Mart

Estado:

```text
VAR_MAP_SCENE_VIRIDIAN_CITY_MART
```

Detector alternativo:

```text
key_item: OAKS_PARCEL
```

---

### FRLG-007 — Entregar Oak's Parcel ao Professor Oak

- **Jogos:** FRLG
- **Categoria:** MAIN
- **Pré-requisito:** FRLG-006

Após a entrega, Oak entrega a Pokédex.

---

### FRLG-008 — Receber a Pokédex

Conclusão:

```text
FLAG_SYS_POKEDEX_GET == true
```

Confiança:

```text
VERY_HIGH
```

---

### FRLG-009 — Receber Poké Balls de Oak

Flag:

```text
FLAG_GOT_POKEBALLS_FROM_OAK_AFTER_22_RIVAL = 0x247
```

**Observação:** dependendo do fluxo do evento do rival em Route 22, esta flag participa da lógica. Não use isoladamente para marcar Pokédex recebida.

---

### FRLG-010 — Receber Town Map

- **Categoria:** SIDE/UTILITY
- **Local:** casa do rival

Objeto inicialmente controlado por:

```text
FLAG_HIDE_TOWN_MAP
```

Use item/key item ou flag de obtenção correspondente do script para alta confiança.

---

## CAPÍTULO 3 — Route 22 / Viridian Forest / Pewter

### FRLG-011 — Batalha opcional contra o rival na Route 22

- **Jogos:** FRLG
- **Categoria:** SIDE
- **Local:** Route 22

Estado:

```text
VAR_MAP_SCENE_ROUTE22
```

Não é necessário derrotá-lo para terminar a campanha.

---

### FRLG-012 — Atravessar Viridian Forest

- **Jogos:** FRLG
- **Categoria:** MAIN

Detector secundário:

```text
FLAG_WORLD_MAP_VIRIDIAN_FOREST
```

---

### FRLG-013 — Chegar a Pewter City

Detector:

```text
FLAG_WORLD_MAP_PEWTER_CITY
```

---

### FRLG-014 — Derrotar Brock

- **Categoria:** MAIN
- **Local:** Pewter Gym

Conclusão:

```text
FLAG_BADGE01_GET == true
```

Evidência complementar:

```text
FLAG_GOT_TM39_FROM_BROCK = 0x254
```

Resultado:

```text
Boulder Badge
TM39 Rock Tomb
```

---

### FRLG-015 — Receber Running Shoes

- **Categoria:** UTILITY
- **Pré-requisito:** Boulder Badge / saída de Pewter

System flag relacionada ao dash:

```text
FLAG_SYS_B_DASH
```

Use também o estado do NPC de entrega quando necessário.

---

# 8. Mt. Moon / Cerulean

### FRLG-016 — Entrar em Mt. Moon

Detector secundário:

```text
FLAG_WORLD_MAP_MT_MOON_1F
```

---

### FRLG-017 — Derrotar membros da Team Rocket em Mt. Moon

- **Categoria:** MAIN
- **Detecção:** trainer flags individuais + progresso do mapa.

---

### FRLG-018 — Escolher um fóssil

- **Categoria:** MAIN-associated

Flags:

```text
FLAG_GOT_FOSSIL_FROM_MT_MOON = 0x232

FLAG_GOT_DOME_FOSSIL  = 0x272
FLAG_GOT_HELIX_FOSSIL = 0x273
```

Regra:

```text
FLAG_GOT_FOSSIL_FROM_MT_MOON
AND exactly_one(
    FLAG_GOT_DOME_FOSSIL,
    FLAG_GOT_HELIX_FOSSIL
)
```

---

### FRLG-019 — Chegar a Cerulean City

Detector:

```text
FLAG_WORLD_MAP_CERULEAN_CITY
```

---

### FRLG-020 — Encontrar o rival em Cerulean

Estado:

```text
VAR_MAP_SCENE_CERULEAN_CITY_RIVAL
```

---

### FRLG-021 — Derrotar rival em Cerulean

- **Categoria:** MAIN
- **Pré-requisito:** acesso à Nugget Bridge

Usar:

```text
trainer flag do rival correspondente
+
VAR_MAP_SCENE_CERULEAN_CITY_RIVAL
```

---

### FRLG-022 — Vencer os treinadores da Nugget Bridge

- **Categoria:** MAIN-associated
- **Local:** Route 24

Estado útil:

```text
VAR_MAP_SCENE_ROUTE24
```

---

### FRLG-023 — Derrotar Rocket Grunt da Nugget Bridge

- **Categoria:** MAIN-associated

Objeto envolvido:

```text
FLAG_HIDE_NUGGET_BRIDGE_ROCKET
```

---

### FRLG-024 — Encontrar Bill na Sea Cottage

- **Categoria:** MAIN
- **Local:** Route 25

---

### FRLG-025 — Ajudar Bill a voltar à forma humana

Conclusão:

```text
FLAG_HELPED_BILL_IN_SEA_COTTAGE = 0x233
```

Confiança:

```text
VERY_HIGH
```

---

### FRLG-026 — Receber S.S. Ticket

Conclusão:

```text
FLAG_GOT_SS_TICKET = 0x234
```

Há também:

```text
FLAG_GOT_SS_TICKET_DUP = 0x235
```

Não conte ambas como objetivos separados.

---

### FRLG-027 — Derrotar Misty

- **Categoria:** MAIN
- **Local:** Cerulean Gym

Conclusão:

```text
FLAG_BADGE02_GET == true
```

Evidência complementar:

```text
FLAG_GOT_TM03_FROM_MISTY = 0x297
```

---

# 9. Cerulean Rocket / Vermilion / S.S. Anne

### FRLG-028 — Resolver o roubo da casa em Cerulean

- **Categoria:** MAIN

Derrotar Rocket Grunt e recuperar TM28.

Conclusão útil:

```text
FLAG_GOT_TM28_FROM_ROCKET = 0x23F
```

Objeto NPC:

```text
FLAG_HIDE_CERULEAN_ROCKET
```

---

### FRLG-029 — Seguir para Vermilion City

Detector:

```text
FLAG_WORLD_MAP_VERMILION_CITY
```

---

### FRLG-030 — Receber Bike Voucher

- **Categoria:** SIDE/UTILITY
- **Local:** Pokémon Fan Club

Flag:

```text
FLAG_GOT_BIKE_VOUCHER = 0x241
```

---

### FRLG-031 — Trocar Bike Voucher pela Bicycle

- **Categoria:** SIDE/UTILITY
- **Local:** Cerulean Bike Shop

Flag:

```text
FLAG_GOT_BICYCLE = 0x271
```

---

### FRLG-032 — Entrar na S.S. Anne

- **Categoria:** MAIN
- **Pré-requisito:** S.S. Ticket

Estado:

```text
VAR_VERMILION_CITY_TICKET_CHECK_TRIGGER
```

Detector secundário:

```text
FLAG_WORLD_MAP_SSANNE_EXTERIOR
```

---

### FRLG-033 — Derrotar rival na S.S. Anne

- **Categoria:** MAIN
- **Local:** corredor 2F

Estado:

```text
VAR_MAP_SCENE_S_S_ANNE_2F_CORRIDOR
```

---

### FRLG-034 — Ajudar o Capitão e receber HM01 Cut

Conclusão:

```text
FLAG_GOT_HM01 = 0x237
```

Confiança:

```text
VERY_HIGH
```

---

### FRLG-035 — S.S. Anne partir

Objeto/map state:

```text
FLAG_HIDE_SS_ANNE
```

Esta flag pode ser usada como evidência do fim do arco do navio.

---

### FRLG-036 — Resolver os interruptores do Vermilion Gym

Flag:

```text
FLAG_FOUND_BOTH_VERMILION_GYM_SWITCHES = 0x264
```

---

### FRLG-037 — Derrotar Lt. Surge

Conclusão:

```text
FLAG_BADGE03_GET == true
```

Complemento:

```text
FLAG_GOT_TM34_FROM_SURGE = 0x231
```

---

# 10. Route 9 / Rock Tunnel / Lavender

### FRLG-038 — Receber HM05 Flash

- **Categoria:** UTILITY
- **Local:** Route 2 / Oak's Aide
- **Requisito:** Pokédex com número mínimo de espécies registradas conforme evento.

Conclusão:

```text
FLAG_GOT_HM05 = 0x23B
```

Flash não é estritamente obrigatório para atravessar Rock Tunnel, então não o use como hard prerequisite da história.

---

### FRLG-039 — Atravessar Rock Tunnel

- **Categoria:** MAIN

Detector:

```text
FLAG_WORLD_MAP_ROCK_TUNNEL_1F
```

---

### FRLG-040 — Chegar a Lavender Town

Detector:

```text
FLAG_WORLD_MAP_LAVENDER_TOWN
```

---

### FRLG-041 — Encontrar rival em Pokémon Tower

- **Categoria:** MAIN-associated
- **Local:** Pokémon Tower 2F

Estado:

```text
VAR_MAP_SCENE_POKEMON_TOWER_2F
```

---

### FRLG-042 — Descobrir que é necessário Silph Scope

A primeira tentativa de subir Pokémon Tower pode ocorrer antes de Celadon.

Seu parser deve aceitar:

```text
Lavender visitada
AND Silph Scope ausente
```

como estado válido.

---

# 11. Celadon / Rocket Hideout

### FRLG-043 — Chegar a Celadon City

Detector:

```text
FLAG_WORLD_MAP_CELADON_CITY
```

---

### FRLG-044 — Obter Coin Case

- **Categoria:** SIDE

Flag:

```text
FLAG_GOT_COIN_CASE = 0x243
```

---

### FRLG-045 — Descobrir a entrada do Rocket Hideout

- **Categoria:** MAIN

Conclusão/evento:

```text
FLAG_OPENED_ROCKET_HIDEOUT = 0x26D
```

---

### FRLG-046 — Obter Lift Key

- **Categoria:** MAIN

Objeto controlado por:

```text
FLAG_HIDE_LIFT_KEY
```

Use item presente/flag do script do Rocket Grunt como detector.

---

### FRLG-047 — Habilitar uso do elevador

Flag existente:

```text
FLAG_CAN_USE_ROCKET_HIDEOUT_LIFT = 0x2A5
```

---

### FRLG-048 — Derrotar Giovanni no Rocket Hideout

- **Categoria:** MAIN
- **Local:** Rocket Hideout B4F

Use:

```text
trainer flag do Giovanni/Hideout
+
map state
```

---

### FRLG-049 — Obter Silph Scope

- **Categoria:** MAIN

Objeto inicialmente controlado por:

```text
FLAG_HIDE_SILPH_SCOPE = 0x037
```

Detector recomendado:

```text
key_item SILPH_SCOPE
OR hide/object flag correspondente pós-coleta
```

---

### FRLG-050 — Derrotar Erika

- **Categoria:** MAIN
- **Local:** Celadon Gym

Conclusão:

```text
FLAG_BADGE04_GET == true
```

Complemento:

```text
FLAG_GOT_TM19_FROM_ERIKA = 0x293
```

**Ordem flexível:** Erika pode ser derrotada antes ou depois de parte do Rocket Hideout.

---

# 12. Pokémon Tower / Mr. Fuji

### FRLG-051 — Retornar a Pokémon Tower com Silph Scope

- **Categoria:** MAIN
- **Pré-requisito:** Silph Scope

---

### FRLG-052 — Identificar o espírito de Marowak

- **Categoria:** MAIN
- **Local:** Pokémon Tower 6F

Estado:

```text
VAR_MAP_SCENE_POKEMON_TOWER_6F
```

---

### FRLG-053 — Derrotar Team Rocket no topo da torre

- **Categoria:** MAIN

Use trainer flags dos Rockets da torre.

---

### FRLG-054 — Resgatar Mr. Fuji

Conclusão:

```text
FLAG_RESCUED_MR_FUJI = 0x23C
```

---

### FRLG-055 — Receber Poké Flute

Conclusão:

```text
FLAG_GOT_POKE_FLUTE = 0x23D
```

Confiança:

```text
VERY_HIGH
```

---

# 13. Snorlax / Fuchsia

Dois Snorlax existem.

Objetos:

```text
FLAG_HIDE_ROUTE_12_SNORLAX
FLAG_HIDE_ROUTE_16_SNORLAX
```

---

### FRLG-056 — Acordar Snorlax da Route 12

Flag específica:

```text
FLAG_WOKE_UP_ROUTE_12_SNORLAX = 0x253
```

Capturar não é obrigatório.

---

### FRLG-057 — Acordar Snorlax da Route 16

- **Categoria:** SIDE/ROUTE
- **Estado:** `VAR_MAP_SCENE_ROUTE16` + hide flag.

---

### FRLG-058 — Chegar a Fuchsia City

Detector:

```text
FLAG_WORLD_MAP_FUCHSIA_CITY
```

---

### FRLG-059 — Encontrar Secret House no Safari Zone

- **Categoria:** MAIN/UTILITY

---

### FRLG-060 — Receber HM03 Surf

Conclusão:

```text
FLAG_GOT_HM03 = 0x239
```

---

### FRLG-061 — Encontrar Gold Teeth

- **Categoria:** MAIN/UTILITY

Detector:

```text
key_item GOLD_TEETH
```

---

### FRLG-062 — Devolver Gold Teeth ao Warden

- **Categoria:** MAIN/UTILITY

---

### FRLG-063 — Receber HM04 Strength

Conclusão:

```text
FLAG_GOT_HM04 = 0x23A
```

---

### FRLG-064 — Derrotar Koga

- **Categoria:** MAIN
- **Local:** Fuchsia Gym

Conclusão:

```text
FLAG_BADGE05_GET == true
```

Complemento:

```text
FLAG_GOT_TM06_FROM_KOGA = 0x259
```

**Importante:** a ordem entre Koga e Sabrina é flexível em grande parte da campanha.

---

# 14. Saffron / Silph Co.

### FRLG-065 — Obter Tea em Celadon

- **Categoria:** MAIN
- **Requisito:** acesso à Celadon Mansion.

Flag:

```text
FLAG_GOT_TEA = 0x2A6
```

---

### FRLG-066 — Liberar acesso a Saffron City

- **Categoria:** MAIN
- **Pré-requisito:** Tea

State:

```text
VAR_MAP_SCENE_ROUTE5_ROUTE6_ROUTE7_ROUTE8_GATES
```

Detector secundário:

```text
FLAG_WORLD_MAP_SAFFRON_CITY
```

---

### FRLG-067 — Entrar na Silph Co.

Detector:

```text
FLAG_WORLD_MAP_SILPH_CO_1F
```

---

### FRLG-068 — Obter Card Key

- **Categoria:** MAIN

Detector:

```text
key_item CARD_KEY
```

---

### FRLG-069 — Abrir portas da Silph Co.

Flags individuais:

```text
FLAG_SILPH_2F_DOOR_1
FLAG_SILPH_2F_DOOR_2
FLAG_SILPH_3F_DOOR_1
FLAG_SILPH_3F_DOOR_2
...
FLAG_SILPH_11F_DOOR
```

Não é necessário abrir todas para concluir.

---

### FRLG-070 — Derrotar rival na Silph Co.

- **Categoria:** MAIN
- **Local:** 7F

Estado:

```text
VAR_MAP_SCENE_SILPH_CO_7F
```

---

### FRLG-071 — Receber Lapras

- **Categoria:** SIDE

Flag:

```text
FLAG_GOT_LAPRAS_FROM_SILPH = 0x246
```

Não necessário para concluir Silph Co.

---

### FRLG-072 — Derrotar Giovanni na Silph Co.

- **Categoria:** MAIN
- **Local:** 11F

Estado:

```text
VAR_MAP_SCENE_SILPH_CO_11F
```

Use trainer flag do Giovanni correspondente.

---

### FRLG-073 — Receber Master Ball

- **Categoria:** MAIN-associated

Flag:

```text
FLAG_GOT_MASTER_BALL_FROM_SILPH = 0x250
```

É uma evidência fortíssima de Silph Co. concluída.

---

### FRLG-074 — Team Rocket abandona Saffron

Use:

```text
FLAG_HIDE_SAFFRON_ROCKETS
FLAG_HIDE_SAFFRON_CIVILIANS
```

em conjunto com Silph Co. concluída.

---

### FRLG-075 — Derrotar Fighting Dojo

- **Categoria:** SIDE

---

### FRLG-076 — Escolher Hitmonlee ou Hitmonchan

Flag geral:

```text
FLAG_GOT_HITMON_FROM_DOJO = 0x278
```

---

### FRLG-077 — Derrotar Sabrina

- **Categoria:** MAIN

Conclusão:

```text
FLAG_BADGE06_GET == true
```

Complemento:

```text
FLAG_GOT_TM04_FROM_SABRINA = 0x29A
```

---

# 15. Cinnabar Island / Pokémon Mansion

### FRLG-078 — Viajar para Cinnabar Island

Possíveis caminhos:

```text
Pallet -> Route 21 -> Cinnabar
ou
Fuchsia -> Seafoam -> Cinnabar
```

Detector:

```text
FLAG_WORLD_MAP_CINNABAR_ISLAND
```

---

### FRLG-079 — Explorar Pokémon Mansion

Detector:

```text
FLAG_WORLD_MAP_POKEMON_MANSION_1F
```

---

### FRLG-080 — Resolver os switches da Pokémon Mansion

Flag usada pelos switches:

```text
FLAG_POKEMON_MANSION_SWITCH_STATE = 0x26C
```

Esta flag sozinha não significa conclusão da mansão.

---

### FRLG-081 — Obter Secret Key

- **Categoria:** MAIN

Detector:

```text
key_item SECRET_KEY
```

---

### FRLG-082 — Abrir Cinnabar Gym

- **Categoria:** MAIN
- **Pré-requisito:** Secret Key

---

### FRLG-083 — Resolver quizzes do Cinnabar Gym

Flags:

```text
FLAG_CINNABAR_GYM_QUIZ_1 = 0x265
FLAG_CINNABAR_GYM_QUIZ_2 = 0x267
FLAG_CINNABAR_GYM_QUIZ_3 = 0x268
FLAG_CINNABAR_GYM_QUIZ_4 = 0x269
FLAG_CINNABAR_GYM_QUIZ_5 = 0x26A
FLAG_CINNABAR_GYM_QUIZ_6 = 0x26B
```

São opcionais se o jogador optar por lutar contra os treinadores.

---

### FRLG-084 — Derrotar Blaine

Conclusão:

```text
FLAG_BADGE07_GET == true
```

Complemento:

```text
FLAG_GOT_TM38_FROM_BLAINE = 0x24E
```

---

# 16. PRIMEIRO ARCO DAS SEVII ISLANDS

Após Blaine, Bill aborda o jogador em Cinnabar.

O jogador pode:

```text
aceitar imediatamente
ou
recusar e fazer a viagem depois
```

Portanto o arco Sevii inicial NÃO deve ser inferido como automaticamente concluído só porque Blaine foi derrotado.

---

### SEVII-001 — Aceitar viajar com Bill

- **Jogos:** FRLG
- **Categoria:** SEVII/MAIN-associated
- **Local:** Cinnabar

---

### SEVII-002 — Chegar a One Island

Detector:

```text
FLAG_WORLD_MAP_ONE_ISLAND
```

System flag:

```text
FLAG_SYS_SEVII_MAP_123
```

pode ser usada como evidência de desbloqueio do primeiro conjunto de ilhas.

---

### SEVII-003 — Conhecer Celio

- **Local:** One Island Pokémon Network Center

Estado:

```text
VAR_MAP_SCENE_ONE_ISLAND_POKEMON_CENTER_1F
```

---

### SEVII-004 — Receber Tri-Pass

- **Categoria:** SEVII

Detector:

```text
key_item TRI_PASS
```

---

### SEVII-005 — Receber Meteorite para entregar em Two Island

Detector:

```text
key_item METEORITE
```

---

### SEVII-006 — Visitar Two Island

Flag:

```text
FLAG_VISITED_TWO_ISLAND = 0x2A2
```

Também:

```text
FLAG_WORLD_MAP_TWO_ISLAND
```

---

### SEVII-007 — Descobrir o desaparecimento de Lostelle

- **Categoria:** SEVII

---

### SEVII-008 — Viajar para Three Island

Detector:

```text
FLAG_WORLD_MAP_THREE_ISLAND
```

---

### SEVII-009 — Derrotar os Bikers em Three Island

Objetos:

```text
FLAG_HIDE_THREE_ISLAND_BIKERS
FLAG_HIDE_THREE_ISLAND_ANTIBIKERS
```

Use trainer flags + hide flags.

---

### SEVII-010 — Entrar em Berry Forest

Detector:

```text
FLAG_WORLD_MAP_THREE_ISLAND_BERRY_FOREST
```

---

### SEVII-011 — Resgatar Lostelle do Hypno

Conclusão:

```text
FLAG_RESCUED_LOSTELLE = 0x2A3
```

Confiança:

```text
VERY_HIGH
```

---

### SEVII-012 — Devolver Lostelle ao pai

- **Local:** Two Island

---

### SEVII-013 — Entregar Meteorite

- **Local:** Two Island Game Corner

Use:

```text
key item removido
+
scene state
```

---

### SEVII-014 — Concluir primeiro desvio das Sevii Islands

Flag:

```text
FLAG_SEVII_DETOUR_FINISHED = 0x2A1
```

Confiança:

```text
VERY_HIGH
```

Esta flag é uma das melhores para seu parser.

---

### SEVII-015 — Retornar a Kanto

- **Categoria:** SEVII

Após esse ponto, Bill/Celio deixam o jogador continuar a campanha principal.

---

# 17. Viridian Gym

Após os sete primeiros badges, Viridian Gym finalmente pode abrir.

---

### FRLG-085 — Detectar Viridian Gym aberto

State:

```text
VAR_MAP_SCENE_VIRIDIAN_CITY_GYM_DOOR
```

---

### FRLG-086 — Entrar no Viridian Gym

- **Categoria:** MAIN

---

### FRLG-087 — Derrotar Giovanni no Viridian Gym

Conclusão:

```text
FLAG_BADGE08_GET == true
```

Complemento:

```text
FLAG_GOT_TM26_FROM_GIOVANNI = 0x298
```

Após essa batalha Giovanni anuncia a dissolução da Team Rocket.

---

# 18. Route 22 / Route 23 / Victory Road

### FRLG-088 — Batalha final pré-Liga contra o rival na Route 22

- **Categoria:** MAIN

Estado:

```text
VAR_MAP_SCENE_ROUTE22
```

Use trainer flag específica desta batalha.

---

### FRLG-089 — Passar pelo Badge Check Gate

- **Categoria:** MAIN
- **Local:** Route 23

State:

```text
VAR_MAP_SCENE_ROUTE23
```

---

### FRLG-090 — Entrar em Victory Road

Detector:

```text
FLAG_WORLD_MAP_VICTORY_ROAD_1F
```

---

### FRLG-091 — Resolver Boulder Puzzle do 1F

State:

```text
VAR_MAP_SCENE_VICTORY_ROAD_1F
```

---

### FRLG-092 — Resolver Boulder Puzzle do 2F

States:

```text
VAR_MAP_SCENE_VICTORY_ROAD_2F_BOULDER1
VAR_MAP_SCENE_VICTORY_ROAD_2F_BOULDER2
```

---

### FRLG-093 — Resolver Boulder Puzzle do 3F

State:

```text
VAR_MAP_SCENE_VICTORY_ROAD_3F
```

---

### FRLG-094 — Chegar ao Indigo Plateau

Detector:

```text
FLAG_WORLD_MAP_INDIGO_PLATEAU_EXTERIOR
```

---

# 19. Pokémon League

### FRLG-095 — Iniciar Elite Four

State:

```text
VAR_MAP_SCENE_POKEMON_LEAGUE
```

---

### FRLG-096 — Derrotar Lorelei

- **Categoria:** MAIN
- **Detecção:** trainer flag da primeira luta.

---

### FRLG-097 — Derrotar Bruno

- **Categoria:** MAIN

---

### FRLG-098 — Derrotar Agatha

- **Categoria:** MAIN

---

### FRLG-099 — Derrotar Lance

- **Categoria:** MAIN

---

### FRLG-100 — Derrotar Champion Rival / Blue

- **Categoria:** MAIN

Use trainer flag da batalha de Champion + scene state.

---

### FRLG-101 — Entrar no Hall of Fame

Conclusão canônica:

```text
FLAG_SYS_GAME_CLEAR = 0x82C
```

Confiança:

```text
VERY_HIGH
```

Use esta flag para:

```text
main_story_first_clear = true
```

---

# 20. PÓS-GAME — NATIONAL DEX

Após o primeiro Hall of Fame:

```text
FLAG_SYS_GAME_CLEAR == true
```

o jogador retorna a Pallet Town.

Para receber a National Dex, o jogo exige:

```text
Hall of Fame
+
pelo menos 60 espécies OWNED na Kanto Pokédex
+
ter realizado a primeira visita/arco de One Island
```

Detector final:

```text
FLAG_SYS_NATIONAL_DEX = 0x840
```

---

### POST-001 — Possuir 60 espécies na Kanto Dex

- **Categoria:** POSTGAME prerequisite

Não derive apenas de Pokédex Seen.

Calcule:

```text
kanto_owned_species_count >= 60
```

---

### POST-002 — Receber National Pokédex

Conclusão:

```text
FLAG_SYS_NATIONAL_DEX == true
```

Complemento:

```text
VAR_NATIONAL_DEX
```

---

# 21. PÓS-GAME — RUBY / CELO NETWORK MACHINE

### POST-003 — Retornar a One Island

- **Pré-requisitos:**
  - Hall of Fame
  - National Dex

---

### POST-004 — Falar com Celio sobre Network Machine

Celio pede Ruby e Sapphire.

---

### POST-005 — Ir para Mt. Ember

Detector:

```text
FLAG_WORLD_MAP_MT_EMBER_EXTERIOR
```

---

### POST-006 — Derrotar Rockets na entrada da nova caverna

Objeto:

```text
FLAG_HIDE_MT_EMBER_EXTERIOR_ROCKETS
```

Esta batalha só se torna relevante após National Dex.

---

### POST-007 — Explorar Ruby Path

- **Categoria:** POSTGAME

---

### POST-008 — Obter Ruby

Conclusão:

```text
FLAG_GOT_RUBY = 0x2DD
```

Objeto:

```text
FLAG_HIDE_RUBY = 0x08A
```

Confiança:

```text
VERY_HIGH
```

---

### POST-009 — Entregar Ruby a Celio

- **Local:** One Island Network Center

O Ruby é instalado na Network Machine.

---

### POST-010 — Receber Rainbow Pass

Detector:

```text
key_item RAINBOW_PASS
```

System flag relacionada:

```text
FLAG_SYS_SEVII_MAP_4567 = 0x846
```

Este é o marco que libera Four, Five, Six e Seven Island.

---

# 22. Four Island / Lorelei / Icefall Cave

### POST-011 — Visitar Four Island

Detector:

```text
FLAG_WORLD_MAP_FOUR_ISLAND
```

---

### POST-012 — Encontrar o rival em Four Island

Objeto:

```text
FLAG_HIDE_FOUR_ISLAND_RIVAL
```

Use map state/trainer event.

---

### POST-013 — Entrar em Icefall Cave

Detector:

```text
FLAG_WORLD_MAP_FOUR_ISLAND_ICEFALL_CAVE_ENTRANCE
```

---

### POST-014 — Obter HM07 Waterfall

Objeto:

```text
FLAG_HIDE_FOUR_ISLAND_ICEFALL_CAVE_1F_HM07
```

Detector preferido:

```text
HM07 no inventário
ou flag específica de coleta
```

---

### POST-015 — Encontrar Lorelei contra Team Rocket

Objetos:

```text
FLAG_HIDE_ICEFALL_CAVE_LORELEI
FLAG_HIDE_ICEFALL_CAVE_ROCKETS
```

---

### POST-016 — Ajudar Lorelei a derrotar Team Rocket

- **Categoria:** POSTGAME
- **Importância:** desbloqueia o avanço correto para Dotted Hole/Sapphire.

Use trainer flags dos Rockets + hide/map state.

---

# 23. Six Island / Dotted Hole / Sapphire

### POST-017 — Visitar Six Island

Detector:

```text
FLAG_WORLD_MAP_SIX_ISLAND
```

---

### POST-018 — Chegar a Ruin Valley

- **Categoria:** POSTGAME

---

### POST-019 — Abrir Dotted Hole usando Cut

Conclusão:

```text
FLAG_USED_CUT_ON_RUIN_VALLEY_BRAILLE = 0x2E3
```

Confiança:

```text
VERY_HIGH
```

---

### POST-020 — Entrar em Dotted Hole

Detector:

```text
FLAG_WORLD_MAP_SIX_ISLAND_DOTTED_HOLE_1F
```

---

### POST-021 — Resolver o puzzle Braille

- **Categoria:** POSTGAME

Usar map scene/state.

---

### POST-022 — Encontrar Sapphire

Objeto:

```text
FLAG_HIDE_SAPPHIRE = 0x08F
```

---

### POST-023 — Gideon rouba Sapphire

- **Categoria:** POSTGAME

O jogador ainda **não** deve ser marcado como tendo recuperado Sapphire aqui.

Use story state do Dotted Hole.

---

# 24. Five Island / Rocket Warehouse

### POST-024 — Descobrir segunda senha do Rocket Warehouse

- **Categoria:** POSTGAME

Pré-requisito:

```text
evento de Dotted Hole
```

---

### POST-025 — Desbloquear Rocket Warehouse

Conclusão:

```text
FLAG_UNLOCKED_ROCKET_WAREHOUSE = 0x2D6
```

Confiança:

```text
VERY_HIGH
```

---

### POST-026 — Entrar no Rocket Warehouse

Detector:

```text
FLAG_WORLD_MAP_FIVE_ISLAND_ROCKET_WAREHOUSE
```

---

### POST-027 — Derrotar Rocket Admins

Conclusão:

```text
FLAG_DEFEATED_ROCKETS_IN_WAREHOUSE = 0x2D5
```

Esta é uma das flags mais úteis do pós-game.

---

### POST-028 — Derrotar Gideon

- **Categoria:** POSTGAME

Use trainer flag.

---

### POST-029 — Recuperar Sapphire

Conclusão:

```text
FLAG_RECOVERED_SAPPHIRE = 0x2DC
```

Confiança:

```text
VERY_HIGH
```

---

### POST-030 — Entregar Sapphire a Celio

- **Categoria:** POSTGAME

---

### POST-031 — Completar Network Machine

Conclusão de alto nível:

```text
FLAG_SYS_CAN_LINK_WITH_RS = 0x844
```

Resultado:

```text
trocas com Ruby/Sapphire/Emerald habilitadas
```

Este pode ser tratado como:

```text
SEVII_MAIN_QUEST_COMPLETED
```

---

# 25. Elite Four Rematch

Depois de concluir a quest Ruby/Sapphire da Network Machine, a Elite Four recebe equipes atualizadas.

### POST-032 — Reabrir desafio da Pokémon League

- **Categoria:** POSTGAME

Pré-requisitos recomendados:

```text
FLAG_SYS_GAME_CLEAR
FLAG_SYS_NATIONAL_DEX
FLAG_SYS_CAN_LINK_WITH_RS
```

---

### POST-033 — Derrotar Lorelei — Rematch

- **Categoria:** POSTGAME

Use trainer flag/League state da versão rematch.

---

### POST-034 — Derrotar Bruno — Rematch

---

### POST-035 — Derrotar Agatha — Rematch

---

### POST-036 — Derrotar Lance — Rematch

---

### POST-037 — Derrotar Champion Rival — Rematch

---

### POST-038 — Segundo Hall of Fame

Não confundir com:

```text
FLAG_SYS_GAME_CLEAR
```

que já estará setada desde a primeira conclusão.

Para contar Hall of Fame repetido, leia os registros de Hall of Fame / game stats.

---

# 26. Cerulean Cave / Mewtwo

Cerulean Cave só deve ser tratada como liberada após o pós-game apropriado.

Detector de visita:

```text
FLAG_WORLD_MAP_CERULEAN_CAVE_1F
```

---

### POST-039 — Entrar em Cerulean Cave

- **Categoria:** POSTGAME

---

### POST-040 — Enfrentar Mewtwo

Flag:

```text
FLAG_FOUGHT_MEWTWO = 0x2BC
```

Objeto:

```text
FLAG_HIDE_MEWTWO = 0x081
```

**Importante:**

```text
FOUGHT != CAUGHT
```

Para detectar captura, consulte:

```text
Pokédex caught bit
+
party/boxes se necessário
```

---

# 27. Lendários opcionais

## Zapdos

### SIDE-001 — Entrar no Power Plant

Detector:

```text
FLAG_WORLD_MAP_POWER_PLANT
```

### SIDE-002 — Enfrentar Zapdos

Flag:

```text
FLAG_FOUGHT_ZAPDOS = 0x2BF
```

Objeto:

```text
FLAG_HIDE_ZAPDOS
```

---

## Articuno

### SIDE-003 — Entrar em Seafoam Islands

Detector:

```text
FLAG_WORLD_MAP_SEAFOAM_ISLANDS_1F
```

### SIDE-004 — Resolver correnteza do Seafoam B3F

Flag:

```text
FLAG_STOPPED_SEAFOAM_B3F_CURRENT = 0x2D2
```

### SIDE-005 — Resolver correnteza do Seafoam B4F

Flag:

```text
FLAG_STOPPED_SEAFOAM_B4F_CURRENT = 0x2D3
```

### SIDE-006 — Enfrentar Articuno

Flag:

```text
FLAG_FOUGHT_ARTICUNO = 0x2BE
```

Objeto:

```text
FLAG_HIDE_ARTICUNO
```

---

## Moltres

Em FireRed/LeafGreen, Moltres está em Mt. Ember, não em Victory Road.

### SIDE-007 — Subir Mt. Ember

Detector:

```text
FLAG_WORLD_MAP_MT_EMBER_EXTERIOR
```

### SIDE-008 — Enfrentar Moltres

Flag:

```text
FLAG_FOUGHT_MOLTRES = 0x2BD
```

Objeto:

```text
FLAG_HIDE_MOLTRES
```

---

# 28. Roaming Legendary

Após o pós-game, um dos cães lendários de Johto pode vagar por Kanto.

Depende do starter:

```text
Bulbasaur -> Entei
Charmander -> Suicune
Squirtle -> Raikou
```

Portanto:

```text
VAR_STARTER_MON
```

determina qual roamer é esperado.

Não trate essa atividade como parte da campanha principal.

---

# 29. Tanoby Ruins

### SIDE-009 — Resolver Tanoby Key

- **Categoria:** SIDE
- **Local:** Seven Island

Detector de visita:

```text
FLAG_WORLD_MAP_SEVEN_ISLAND_SEVAULT_CANYON_TANOBY_KEY
```

Conclusão do desbloqueio:

```text
FLAG_SYS_UNLOCKED_TANOBY_RUINS = 0x849
```

---

### SIDE-010 — Visitar Tanoby Chambers

Detector possível:

```text
FLAG_WORLD_MAP_SEVEN_ISLAND_TANOBY_RUINS_MONEAN_CHAMBER
```

---

# 30. Fossil Lab

### SIDE-011 — Reviver Dome Fossil

Flag:

```text
FLAG_REVIVED_DOME = 0x2EC
```

---

### SIDE-012 — Reviver Helix Fossil

Flag:

```text
FLAG_REVIVED_HELIX = 0x2ED
```

---

### SIDE-013 — Obter Old Amber

Flag:

```text
FLAG_GOT_OLD_AMBER = 0x25E
```

---

### SIDE-014 — Reviver Old Amber / Aerodactyl

Flag:

```text
FLAG_REVIVED_AMBER = 0x2EE
```

Vars:

```text
VAR_MAP_SCENE_CINNABAR_ISLAND_POKEMON_LAB_EXPERIMENT_ROOM_WHICH_FOSSIL = 0x4069
VAR_MAP_SCENE_CINNABAR_ISLAND_POKEMON_LAB_EXPERIMENT_ROOM_REVIVE_STATE = 0x406A
```

---

# 31. Oak's Aides / utilidades

### SIDE-015 — Receber HM05 Flash

```text
FLAG_GOT_HM05
```

---

### SIDE-016 — Receber Itemfinder

```text
FLAG_GOT_ITEMFINDER = 0x252
```

---

### SIDE-017 — Receber Exp. Share

```text
FLAG_GOT_EXP_SHARE_FROM_OAKS_AIDE = 0x256
```

---

### SIDE-018 — Receber Amulet Coin

```text
FLAG_GOT_AMULET_COIN_FROM_OAKS_AIDE = 0x2FD
```

---

### SIDE-019 — Receber Everstone

```text
FLAG_GOT_EVERSTONE_FROM_OAKS_AIDE = 0x2FA
```

---

# 32. Fishing Rods

### SIDE-020 — Old Rod

```text
FLAG_GOT_OLD_ROD = 0x240
```

### SIDE-021 — Good Rod

```text
FLAG_GOT_GOOD_ROD = 0x244
```

### SIDE-022 — Super Rod

```text
FLAG_GOT_SUPER_ROD = 0x255
```

---

# 33. Version differences — FireRed x LeafGreen

O grafo de objetivos principais é o mesmo.

Não crie versões separadas de:

```text
FRLG-001 ... FRLG-101
POST-001 ...
```

apenas por causa da versão.

Use diferenças de versão para:

```text
Pokémon exclusivos
encounters
Pokémon disponíveis em certas áreas
algumas opções de troca / disponibilidade
```

Exemplo de metadado:

```yaml
games:
  - FR
  - LG
storyEquivalent: true
```

Para objetivos dependentes de espécie, você pode criar:

```yaml
versionRules:
  FR:
    ...
  LG:
    ...
```

mas isso não é necessário para a campanha principal.

---

# 34. Eventos de distribuição

Esses objetivos NÃO entram no percentual padrão.

---

## EVENT-001 — Aurora Ticket / Birth Island

Flag:

```text
FLAG_RECEIVED_AURORA_TICKET = 0x2A7
```

Navio:

```text
FLAG_ENABLE_SHIP_BIRTH_ISLAND
```

---

## EVENT-002 — Resolver puzzle de Birth Island

Vars:

```text
VAR_DEOXYS_INTERACTION_STEP_COUNTER = 0x4026
VAR_DEOXYS_INTERACTION_NUM = 0x403E
```

System flag:

```text
FLAG_SYS_DEOXYS_AWAKENED
```

---

## EVENT-003 — Enfrentar Deoxys

Flag:

```text
FLAG_FOUGHT_DEOXYS = 0x2E4
```

Objeto:

```text
FLAG_HIDE_DEOXYS
```

Possível estado de fuga:

```text
FLAG_DEOXYS_FLEW_AWAY = 0x2F7
```

---

## EVENT-004 — Mystic Ticket / Navel Rock

Flag:

```text
FLAG_RECEIVED_MYSTIC_TICKET = 0x2A8
```

Navio:

```text
FLAG_ENABLE_SHIP_NAVEL_ROCK
```

---

## EVENT-005 — Enfrentar Lugia

```text
FLAG_FOUGHT_LUGIA = 0x2F2
FLAG_LUGIA_FLEW_AWAY = 0x2F5
```

---

## EVENT-006 — Enfrentar Ho-Oh

```text
FLAG_FOUGHT_HO_OH = 0x2F3
FLAG_HO_OH_FLEW_AWAY = 0x2F6
```

---

# 35. Modelo importável recomendado

```yaml
- id: FRLG-014
  order: 14
  games: [FR, LG]
  category: MAIN
  title: Defeat Brock
  location: Pewter Gym
  prerequisites:
    objectives:
      - FRLG-012
  completion:
    all:
      - type: flag
        name: FLAG_BADGE01_GET
        id: 0x820
        value: true
  evidence:
    optional:
      - type: flag
        name: FLAG_GOT_TM39_FROM_BROCK
        id: 0x254
        value: true
  confidence: VERY_HIGH
```

Exemplo do Sevii:

```yaml
- id: SEVII-011
  games: [FR, LG]
  category: SEVII
  title: Rescue Lostelle
  location: Berry Forest
  prerequisites:
    objectives:
      - SEVII-009
  completion:
    all:
      - type: flag
        name: FLAG_RESCUED_LOSTELLE
        id: 0x2A3
        value: true
  confidence: VERY_HIGH
```

Exemplo pós-game:

```yaml
- id: POST-029
  games: [FR, LG]
  category: POSTGAME
  title: Recover the Sapphire
  location: Rocket Warehouse
  prerequisites:
    objectives:
      - POST-027
      - POST-028
  completion:
    all:
      - type: flag
        name: FLAG_RECOVERED_SAPPHIRE
        id: 0x2DC
        value: true
  confidence: VERY_HIGH
```

---

# 36. Detecção da campanha concluída

Use:

```text
FLAG_SYS_GAME_CLEAR == true
```

como detector canônico da **primeira conclusão da história principal**.

Não use apenas:

```text
Badge 8
Victory Road visited
Elite Four trainer flags
```

porque o jogador ainda pode não ter derrotado o Champion.

---

# 37. Detecção de pós-game Sevii concluído

Use:

```text
FLAG_SYS_GAME_CLEAR == true
AND
FLAG_SYS_NATIONAL_DEX == true
AND
FLAG_GOT_RUBY == true
AND
FLAG_RECOVERED_SAPPHIRE == true
AND
FLAG_SYS_CAN_LINK_WITH_RS == true
```

Resultado:

```text
SEVII_POSTGAME_STORY_COMPLETED
```

---

# 38. Próximo objetivo

Pseudocódigo:

```text
version = detectGameVersion(save)

state = extract(
    eventFlags,
    trainerFlags,
    systemFlags,
    vars,
    keyItems,
    hms,
    pokedex,
    map
)

for objective in objectivesFor(version):

    if completionSatisfied(objective, state):
        objective.status = COMPLETED

    else if prerequisitesSatisfied(objective, state):
        if partialEvidence(objective, state):
            objective.status = IN_PROGRESS
        else:
            objective.status = AVAILABLE

    else:
        objective.status = LOCKED
```

---

# 39. Histórias paralelas / ordem flexível

O parser não deve exigir uma sequência totalmente rígida após Celadon.

Por exemplo:

```text
Erika
Rocket Hideout
Pokémon Tower
Koga
Sabrina
```

possuem alguma flexibilidade.

Modelo recomendado:

```yaml
prerequisites:
  all: [...]
  any: [...]
```

Exemplo:

```yaml
id: FRLG-077
title: Defeat Sabrina
prerequisites:
  all:
    - saffron_access
  any:
    - silph_completed
```

---

# 40. Regras de consistência

Exemplo muito suspeito:

```text
FLAG_SYS_GAME_CLEAR == true
AND FLAG_BADGE08_GET == false
```

Resultado:

```text
POSSIBLE_EDITED_SAVE
```

---

Outro exemplo:

```text
FLAG_SYS_CAN_LINK_WITH_RS == true
AND FLAG_RECOVERED_SAPPHIRE == false
```

Resultado:

```text
POSSIBLE_EDITED_SAVE
```

---

Mas:

```text
FLAG_BADGE06_GET == true
AND FLAG_BADGE05_GET == false
```

não deve automaticamente invalidar o save.

A ordem de certos ginásios é flexível.

---

# 41. World Map flags úteis

```text
FLAG_WORLD_MAP_PALLET_TOWN               = 0x890
FLAG_WORLD_MAP_VIRIDIAN_CITY             = 0x891
FLAG_WORLD_MAP_PEWTER_CITY               = 0x892
FLAG_WORLD_MAP_CERULEAN_CITY             = 0x893
FLAG_WORLD_MAP_LAVENDER_TOWN             = 0x894
FLAG_WORLD_MAP_VERMILION_CITY            = 0x895
FLAG_WORLD_MAP_CELADON_CITY              = 0x896
FLAG_WORLD_MAP_FUCHSIA_CITY              = 0x897
FLAG_WORLD_MAP_CINNABAR_ISLAND           = 0x898
FLAG_WORLD_MAP_INDIGO_PLATEAU_EXTERIOR   = 0x899
FLAG_WORLD_MAP_SAFFRON_CITY              = 0x89A

FLAG_WORLD_MAP_ONE_ISLAND                = 0x89B
FLAG_WORLD_MAP_TWO_ISLAND                = 0x89C
FLAG_WORLD_MAP_THREE_ISLAND              = 0x89D
FLAG_WORLD_MAP_FOUR_ISLAND               = 0x89E
FLAG_WORLD_MAP_FIVE_ISLAND               = 0x89F
FLAG_WORLD_MAP_SEVEN_ISLAND              = 0x8A0
FLAG_WORLD_MAP_SIX_ISLAND                = 0x8A1

FLAG_WORLD_MAP_VIRIDIAN_FOREST           = 0x8A4
FLAG_WORLD_MAP_MT_MOON_1F                = 0x8A5
FLAG_WORLD_MAP_SSANNE_EXTERIOR           = 0x8A6
FLAG_WORLD_MAP_VICTORY_ROAD_1F           = 0x8AA
FLAG_WORLD_MAP_ROCKET_HIDEOUT_B1F        = 0x8AB
FLAG_WORLD_MAP_SILPH_CO_1F               = 0x8AC
FLAG_WORLD_MAP_POKEMON_MANSION_1F        = 0x8AD
FLAG_WORLD_MAP_SAFARI_ZONE_CENTER        = 0x8AE
FLAG_WORLD_MAP_POKEMON_LEAGUE_LORELEIS_ROOM = 0x8AF
FLAG_WORLD_MAP_ROCK_TUNNEL_1F            = 0x8B0
FLAG_WORLD_MAP_SEAFOAM_ISLANDS_1F        = 0x8B1
FLAG_WORLD_MAP_POKEMON_TOWER_1F          = 0x8B2
FLAG_WORLD_MAP_CERULEAN_CAVE_1F          = 0x8B3
FLAG_WORLD_MAP_POWER_PLANT               = 0x8B4
FLAG_WORLD_MAP_NAVEL_ROCK_EXTERIOR       = 0x8B5
FLAG_WORLD_MAP_MT_EMBER_EXTERIOR         = 0x8B6
FLAG_WORLD_MAP_THREE_ISLAND_BERRY_FOREST = 0x8B7
FLAG_WORLD_MAP_FOUR_ISLAND_ICEFALL_CAVE_ENTRANCE = 0x8B8
FLAG_WORLD_MAP_FIVE_ISLAND_ROCKET_WAREHOUSE = 0x8B9
FLAG_WORLD_MAP_TRAINER_TOWER_LOBBY       = 0x8BA
FLAG_WORLD_MAP_SIX_ISLAND_DOTTED_HOLE_1F = 0x8BB
FLAG_WORLD_MAP_FIVE_ISLAND_LOST_CAVE_ENTRANCE = 0x8BC
FLAG_WORLD_MAP_SIX_ISLAND_PATTERN_BUSH   = 0x8BD
FLAG_WORLD_MAP_SIX_ISLAND_ALTERING_CAVE  = 0x8BE
FLAG_WORLD_MAP_SEVEN_ISLAND_TANOBY_RUINS_MONEAN_CHAMBER = 0x8BF
FLAG_WORLD_MAP_THREE_ISLAND_DUNSPARCE_TUNNEL = 0x8C0
FLAG_WORLD_MAP_SEVEN_ISLAND_SEVAULT_CANYON_TANOBY_KEY = 0x8C1
FLAG_WORLD_MAP_BIRTH_ISLAND_EXTERIOR     = 0x8C2
```

Use world-map flags apenas como:

```text
VISITED
```

e não como:

```text
MISSION_COMPLETED
```

---

# 42. Flags de história especialmente úteis

```text
FLAG_GOT_FOSSIL_FROM_MT_MOON             = 0x232
FLAG_HELPED_BILL_IN_SEA_COTTAGE          = 0x233
FLAG_GOT_SS_TICKET                       = 0x234

FLAG_GOT_HM01                            = 0x237
FLAG_GOT_HM02                            = 0x238
FLAG_GOT_HM03                            = 0x239
FLAG_GOT_HM04                            = 0x23A
FLAG_GOT_HM05                            = 0x23B

FLAG_RESCUED_MR_FUJI                     = 0x23C
FLAG_GOT_POKE_FLUTE                      = 0x23D

FLAG_GOT_TM28_FROM_ROCKET                = 0x23F

FLAG_GOT_BIKE_VOUCHER                    = 0x241
FLAG_GOT_COIN_CASE                       = 0x243

FLAG_GOT_MASTER_BALL_FROM_SILPH          = 0x250
FLAG_WOKE_UP_ROUTE_12_SNORLAX            = 0x253
FLAG_GOT_TM39_FROM_BROCK                 = 0x254
FLAG_GOT_EXP_SHARE_FROM_OAKS_AIDE        = 0x256

FLAG_GOT_TM06_FROM_KOGA                  = 0x259
FLAG_OPENED_ROCKET_HIDEOUT               = 0x26D
FLAG_GOT_BICYCLE                         = 0x271

FLAG_GOT_TM19_FROM_ERIKA                 = 0x293
FLAG_GOT_TM03_FROM_MISTY                 = 0x297
FLAG_GOT_TM26_FROM_GIOVANNI              = 0x298
FLAG_GOT_TM04_FROM_SABRINA               = 0x29A

FLAG_SEVII_DETOUR_FINISHED               = 0x2A1
FLAG_VISITED_TWO_ISLAND                  = 0x2A2
FLAG_RESCUED_LOSTELLE                    = 0x2A3
FLAG_CAN_USE_ROCKET_HIDEOUT_LIFT         = 0x2A5
FLAG_GOT_TEA                             = 0x2A6

FLAG_DEFEATED_ROCKETS_IN_WAREHOUSE       = 0x2D5
FLAG_UNLOCKED_ROCKET_WAREHOUSE           = 0x2D6
FLAG_RECOVERED_SAPPHIRE                  = 0x2DC
FLAG_GOT_RUBY                            = 0x2DD
FLAG_USED_CUT_ON_RUIN_VALLEY_BRAILLE     = 0x2E3
```

---

# 43. Percentual da campanha

Para o percentual da história principal, recomendo dividir em dois indicadores.

## Kanto Story

```text
FRLG-001 ... FRLG-101
```

Resultado:

```text
kanto_story_percent
```

Final:

```text
FLAG_SYS_GAME_CLEAR
```

---

## Sevii Story

Inclua:

```text
SEVII-001 ... SEVII-015
POST-003 ... POST-031
```

Resultado:

```text
sevii_story_percent
```

Final:

```text
FLAG_SYS_CAN_LINK_WITH_RS
```

---

## Overall Story

Pode ser:

```text
weighted average
```

Exemplo:

```text
Kanto main story = 80%
Sevii story      = 20%
```

ou simplesmente contar todos os objetivos obrigatórios.

Eu prefiro manter os dois progressos separados:

```json
{
  "kanto": 100,
  "sevii": 62,
  "postgame": 28
}
```

porque o Hall of Fame já representa um fim narrativo legítimo.

---

# 44. Estados de alto nível que seu programa pode calcular

```text
GAME_STARTED
STARTER_RECEIVED
POKEDEX_RECEIVED

BROCK_DEFEATED
MISTY_DEFEATED
SURGE_DEFEATED
ERIKA_DEFEATED
KOGA_DEFEATED
SABRINA_DEFEATED
BLAINE_DEFEATED
GIOVANNI_DEFEATED

BILL_RESCUED
SS_ANNE_COMPLETED
ROCKET_HIDEOUT_COMPLETED
MR_FUJI_RESCUED
SILPH_CO_COMPLETED

SEVII_FIRST_TRIP_STARTED
LOSTELLE_RESCUED
SEVII_FIRST_TRIP_COMPLETED

VICTORY_ROAD_AVAILABLE
POKEMON_LEAGUE_AVAILABLE
KANTO_CHAMPION

NATIONAL_DEX_AVAILABLE
NATIONAL_DEX_RECEIVED

RUBY_QUEST_STARTED
RUBY_OBTAINED
RAINBOW_PASS_OBTAINED

LORELEI_RESCUED
DOTTED_HOLE_OPENED
SAPPHIRE_STOLEN
ROCKET_WAREHOUSE_UNLOCKED
ROCKET_WAREHOUSE_CLEARED
SAPPHIRE_RECOVERED
NETWORK_MACHINE_COMPLETED

ELITE_FOUR_REMATCH_AVAILABLE
CERULEAN_CAVE_AVAILABLE
```

---

# 45. Exemplo de resposta do parser

```json
{
  "game": "POKEMON_FIRE_RED",
  "story": {
    "kanto": {
      "status": "IN_PROGRESS",
      "percent": 54,
      "lastCompleted": "FRLG-055",
      "lastCompletedTitle": "Receive the Poke Flute"
    },
    "sevii": {
      "status": "LOCKED",
      "percent": 0
    }
  },
  "badges": {
    "boulder": true,
    "cascade": true,
    "thunder": true,
    "rainbow": true,
    "soul": false,
    "marsh": false,
    "volcano": false,
    "earth": false
  },
  "availableObjectives": [
    "FRLG-056",
    "FRLG-057",
    "FRLG-058"
  ],
  "recommendedNextObjective": {
    "id": "FRLG-058",
    "title": "Reach Fuchsia City"
  }
}
```

---

# 46. Regra para missões opcionais

Não bloqueie a campanha se faltar:

```text
Bike
Flash
Fishing Rods
Eevee
Hitmonlee/Hitmonchan
Articuno
Zapdos
Moltres
Mewtwo
fósseis revividos
Tanoby Ruins
Trainer Tower
Lost Cave
Alter­ing Cave
eventos de ticket
```

---

# 47. Não confundir evento com resultado

Exemplo:

```text
FLAG_FOUGHT_ARTICUNO == true
```

significa:

```text
a batalha aconteceu / foi resolvida
```

Não significa automaticamente:

```text
Articuno capturado
```

Use:

```text
Pokedex caught
```

para captura.

Mesma regra para:

```text
Mewtwo
Moltres
Zapdos
Deoxys
Lugia
Ho-Oh
```

---

# 48. Conteúdo do save que vale extrair

Para suportar este catálogo:

```text
game_code / game_version

player_name
trainer_id

current_map
current_map_group
current_x
current_y

event_flags[0x000..0x4FF]
trainer_flags[0x500..0x7FF]
system_flags[0x800..0x8FF]

vars[0x4000..]

bag
key_items
hms

pokedex_seen
pokedex_caught

party
pc_boxes

hall_of_fame_records
game_stats
```

---

# 49. Detecção de versão

Não tente diferenciar FR e LG pelas flags da história.

Detecte a versão usando metadado de ROM/save/game code quando disponível.

Exemplo conceitual:

```text
BPRE = FireRed (região/revisão conforme header)
BPGE = LeafGreen (região/revisão conforme header)
```

Depois:

```text
mission graph = FRLG
encounter rules = version specific
```

---

# 50. Arquitetura sugerida

```text
SaveReader
  |
  +-- FireRedLeafGreenSaveDecoder
  |
  +-- ProgressState
        |
        +-- Flags
        +-- TrainerFlags
        +-- Vars
        +-- Inventory
        +-- Pokedex
        +-- WorldState
  |
  +-- ObjectiveEngine
        |
        +-- PrerequisiteEvaluator
        +-- CompletionEvaluator
        +-- ConsistencyValidator
        +-- NextObjectiveResolver
```

---

# 51. Modelo de condição

```yaml
completion:
  all:
    - type: flag
      id: 0x2DC
      name: FLAG_RECOVERED_SAPPHIRE
      expected: true

evidence:
  any:
    - type: trainer
      trainer: GIDEON
      defeated: true
    - type: mapVisited
      flag: FLAG_WORLD_MAP_FIVE_ISLAND_ROCKET_WAREHOUSE
```

---

# 52. Condições compostas

Exemplo National Dex:

```yaml
id: POST-002
title: Obtain National Dex

prerequisites:
  all:
    - type: flag
      name: FLAG_SYS_GAME_CLEAR
      value: true

    - type: pokedexOwnedCount
      region: KANTO
      op: ">="
      value: 60

    - type: objective
      id: SEVII-014
      status: COMPLETED

completion:
  all:
    - type: flag
      name: FLAG_SYS_NATIONAL_DEX
      id: 0x840
      value: true
```

---

# 53. Condição da Network Machine

```yaml
id: POST-031
title: Complete Celio's Network Machine

prerequisites:
  all:
    - POST-008
    - POST-029

completion:
  all:
    - type: flag
      name: FLAG_SYS_CAN_LINK_WITH_RS
      id: 0x844
      value: true
```

---

# 54. Ordem lógica resumida

```text
Pallet
↓
Oak / Starter
↓
Oak's Parcel / Pokédex
↓
Viridian Forest
↓
Brock
↓
Mt. Moon
↓
Cerulean / Rival / Bill
↓
Misty
↓
Vermilion / S.S. Anne
↓
Lt. Surge
↓
Rock Tunnel
↓
Lavender
↓
Celadon
├─ Erika
└─ Rocket Hideout / Giovanni / Silph Scope
↓
Pokémon Tower / Mr. Fuji / Poké Flute
↓
Fuchsia / Safari Zone / Surf / Koga
↓
Saffron / Silph Co. / Giovanni / Sabrina
↓
Cinnabar / Mansion / Blaine
↓
Sevii 1-3 / Lostelle
↓
Viridian Gym / Giovanni
↓
Victory Road
↓
Elite Four
↓
Champion
↓
Hall of Fame
↓
National Dex
↓
Mt. Ember / Ruby
↓
Rainbow Pass
↓
Four Island / Lorelei
↓
Six Island / Dotted Hole / Sapphire stolen
↓
Five Island / Rocket Warehouse
↓
Recover Sapphire
↓
Celio Network Machine
↓
Elite Four Rematch / Cerulean Cave / Mewtwo
```

---

# 55. Fontes técnicas

Para implementar o parser, use como fonte primária:

```text
pret/pokefirered
```

Arquivos principais:

```text
include/constants/flags.h
include/constants/vars.h
include/constants/trainers.h
include/constants/items.h

data/maps/**/scripts.inc
scripts/**/*.inc
```

Sempre que uma missão deste catálogo tiver:

```text
trainer flag
map scene
story var
```

sem um valor semântico explicitado aqui, consulte o `scripts.inc` do mapa.

O `vars.h` fornece o endereço da variável; o script fornece os valores que significam cada estágio.

---

# 56. Resultado esperado

Com esta estrutura, um save como:

```text
Boulder = true
Cascade = true
Thunder = true
Rainbow = true

FLAG_OPENED_ROCKET_HIDEOUT = true
Silph Scope = true

FLAG_RESCUED_MR_FUJI = true
FLAG_GOT_POKE_FLUTE = true

Soul Badge = false
Marsh Badge = false
```

pode ser interpretado como:

```text
Rocket Hideout concluído
Pokémon Tower concluída
Poké Flute obtida

Koga ainda não derrotado
Sabrina ainda não derrotada

próximos grandes objetivos possíveis:
- Fuchsia / Koga
- Tea / Saffron / Silph Co. se ainda não concluído
```

em vez de simplesmente:

```text
"o jogador tem 4 badges"
```

Essa é a diferença entre um contador de progresso e um **reconstrutor real do estado narrativo do save**.
