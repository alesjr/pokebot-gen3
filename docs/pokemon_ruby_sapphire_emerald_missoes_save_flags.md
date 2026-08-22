# Pokémon Ruby / Sapphire / Emerald — Catálogo de objetivos para detecção de progresso por save

> **Importante:** Ruby/Sapphire e Emerald usam conjuntos de flags/vars parecidos, mas **não são binariamente intercambiáveis**. Nunca aplique offsets ou IDs de Emerald diretamente em Ruby/Sapphire sem identificar primeiro a versão do save.

---

## 1. Convenções

### Jogos

- `R` = Pokémon Ruby
- `S` = Pokémon Sapphire
- `E` = Pokémon Emerald
- `RS` = Ruby e Sapphire
- `RSE` = Ruby, Sapphire e Emerald

### Status sugeridos para o programa

```text
LOCKED      = pré-requisitos ainda não cumpridos
AVAILABLE   = objetivo disponível
IN_PROGRESS = evento iniciado, mas não concluído
COMPLETED   = evidência confiável de conclusão encontrada no save
SKIPPED     = objetivo opcional não realizado e já ultrapassado
UNKNOWN     = save inconsistente ou detecção insuficiente
```

### Prioridade de evidência

Ao determinar se um objetivo foi concluído, use nesta ordem:

1. `event flag` específica do evento;
2. `system flag` específica;
3. `story var` + valor esperado;
4. `trainer flag` do chefe/NPC obrigatório;
5. item-chave/HM/TM entregue exclusivamente pelo evento;
6. badge;
7. localização visitada;
8. posição atual do jogador.

**Nunca use apenas a posição atual do jogador como prova de conclusão.**

---

# 2. Estrutura sugerida para importação

Cada objetivo abaixo segue semanticamente este formato:

```yaml
id: string
order: integer
games: [R, S, E]
category: MAIN | OPTIONAL | POSTGAME
title: string
location: string
prerequisites:
  objectives: []
completion:
  any: []
  all: []
notes: string
```

Tipos de detectores recomendados:

```yaml
flag:
  name: FLAG_...
  value: true

var:
  name: VAR_...
  op: ">="
  value: 1

badge:
  number: 1

item:
  name: HM03_SURF
  owned_or_received: true

trainer:
  name: ROXANNE
  defeated: true

system:
  name: FLAG_SYS_GAME_CLEAR
  value: true
```

---

# 3. Flags de sistema fundamentais

## Emerald

O decomp `pret/pokeemerald` define `SYSTEM_FLAGS = 0x860`.

| Estado | Símbolo | ID lógico |
|---|---|---:|
| Pokémon inicial obtido | `FLAG_SYS_POKEMON_GET` | `0x860` |
| Pokédex obtida | `FLAG_SYS_POKEDEX_GET` | `0x861` |
| PokéNav obtido | `FLAG_SYS_POKENAV_GET` | `0x862` |
| jogo concluído / Hall of Fame | `FLAG_SYS_GAME_CLEAR` | `0x864` |
| Stone Badge | `FLAG_BADGE01_GET` | `0x867` |
| Knuckle Badge | `FLAG_BADGE02_GET` | `0x868` |
| Dynamo Badge | `FLAG_BADGE03_GET` | `0x869` |
| Heat Badge | `FLAG_BADGE04_GET` | `0x86A` |
| Balance Badge | `FLAG_BADGE05_GET` | `0x86B` |
| Feather Badge | `FLAG_BADGE06_GET` | `0x86C` |
| Mind Badge | `FLAG_BADGE07_GET` | `0x86D` |
| Rain Badge | `FLAG_BADGE08_GET` | `0x86E` |

## Ruby / Sapphire

O decomp `pret/pokeruby` define `SYSTEM_FLAGS = 0x800`.

| Estado | Símbolo | ID lógico |
|---|---|---:|
| Pokémon inicial obtido | `FLAG_SYS_POKEMON_GET` | `0x800` |
| Pokédex obtida | `FLAG_SYS_POKEDEX_GET` | `0x801` |
| PokéNav obtido | `FLAG_SYS_POKENAV_GET` | `0x802` |
| jogo concluído / Hall of Fame | `FLAG_SYS_GAME_CLEAR` | `0x804` |
| Stone Badge | `FLAG_BADGE01_GET` | `0x807` |
| Knuckle Badge | `FLAG_BADGE02_GET` | `0x808` |
| Dynamo Badge | `FLAG_BADGE03_GET` | `0x809` |
| Heat Badge | `FLAG_BADGE04_GET` | `0x80A` |
| Balance Badge | `FLAG_BADGE05_GET` | `0x80B` |
| Feather Badge | `FLAG_BADGE06_GET` | `0x80C` |
| Mind Badge | `FLAG_BADGE07_GET` | `0x80D` |
| Rain Badge | `FLAG_BADGE08_GET` | `0x80E` |

> O número acima é o **ID da flag no sistema de eventos**, não um offset absoluto no arquivo `.sav`.

---

# 4. Campanha principal

## CAPÍTULO 01 — Littleroot / início da jornada

### RSE-001 — Ajustar o relógio

- **Jogos:** RSE
- **Categoria:** MAIN
- **Local:** Littleroot Town — casa do jogador
- **Pré-requisito:** novo jogo
- **Concluído quando:**
  - Emerald: `FLAG_SET_WALL_CLOCK = true`
  - RS: usar a var/flag equivalente da introdução
- **Observação:** primeiro marco persistente útil.

### RSE-002 — Conhecer o rival

- **Jogos:** RSE
- **Categoria:** MAIN
- **Local:** Littleroot Town
- **Pré-requisito:** RSE-001
- **Detecção:** var de estado da casa/rival avançada.
- **RS vars úteis:** `VAR_LITTLEROOT_RIVAL_STATE`, `VAR_LITTLEROOT_HOUSES_STATE`.

### RSE-003 — Resgatar Professor Birch e escolher o inicial

- **Jogos:** RSE
- **Categoria:** MAIN
- **Local:** Route 101
- **Pré-requisito:** RSE-002
- **Concluído quando:**
  - `FLAG_SYS_POKEMON_GET = true`
  - Emerald também possui `FLAG_RESCUED_BIRCH = true`
- **Resultado:** Treecko, Torchic ou Mudkip.

### RSE-004 — Derrotar May/Brendan na Route 103

- **Jogos:** RSE
- **Categoria:** MAIN
- **Local:** Route 103
- **Pré-requisito:** RSE-003
- **Concluído quando:**
  - Emerald: `FLAG_DEFEATED_RIVAL_ROUTE103 = true`
  - RS: trainer/story state equivalente.
- **Resultado:** libera retorno ao laboratório.

### RSE-005 — Receber a Pokédex e Poké Balls

- **Jogos:** RSE
- **Categoria:** MAIN
- **Local:** Birch's Lab
- **Pré-requisito:** RSE-004
- **Concluído quando:**
  - `FLAG_SYS_POKEDEX_GET = true`
  - Emerald: `FLAG_ADVENTURE_STARTED = true`
- **Detector recomendado:** exigir `FLAG_SYS_POKEDEX_GET`.

### RSE-006 — Receber Running Shoes

- **Jogos:** RSE
- **Categoria:** MAIN
- **Local:** saída de Littleroot
- **Pré-requisito:** RSE-005
- **Concluído quando:**
  - Emerald: `FLAG_RECEIVED_RUNNING_SHOES = true`
- **Observação:** marco secundário, mas fácil de detectar.

---

## CAPÍTULO 02 — Petalburg / Petalburg Woods / Rustboro

### RSE-007 — Encontrar Norman em Petalburg Gym

- **Jogos:** RSE
- **Categoria:** MAIN
- **Local:** Petalburg City
- **Pré-requisito:** RSE-005
- **Concluído quando:** `VAR_PETALBURG_STATE`/equivalente avança.

### RSE-008 — Acompanhar Wally capturando Ralts

- **Jogos:** RSE
- **Categoria:** MAIN
- **Local:** Petalburg / Route 102
- **Pré-requisito:** RSE-007
- **Concluído quando:** estado de Petalburg avança após tutorial de captura.
- **Observação:** necessário para Norman permitir que a aventura prossiga.

### RSE-009 — Derrotar o membro da equipe vilã em Petalburg Woods

- **Jogos:** RSE
- **Equipe inimiga:**
  - Ruby: Team Magma
  - Sapphire: Team Aqua
  - Emerald: Team Aqua
- **Categoria:** MAIN
- **Local:** Petalburg Woods
- **Pré-requisito:** RSE-008
- **Concluído quando:** story state do bosque avança.
- **RS var útil:** `VAR_PETALBURG_WOODS_STATE`.

### RSE-010 — Chegar a Rustboro City

- **Jogos:** RSE
- **Categoria:** MAIN
- **Pré-requisito:** RSE-009
- **Concluído quando:** `FLAG_VISITED_RUSTBORO_CITY = true`
- **Nota:** visita não substitui a flag do objetivo seguinte.

### RSE-011 — Derrotar Roxanne

- **Jogos:** RSE
- **Categoria:** MAIN
- **Local:** Rustboro Gym
- **Pré-requisito:** RSE-010
- **Concluído quando:** `FLAG_BADGE01_GET = true`
- **Recompensa:** Stone Badge.
- **Detector adicional:** flag de TM Rock Tomb recebida.

### RSE-012 — Iniciar o caso dos Devon Goods

- **Jogos:** RSE
- **Categoria:** MAIN
- **Local:** Rustboro City
- **Pré-requisito:** RSE-011
- **Concluído quando:**
  - Emerald: `FLAG_DEVON_GOODS_STOLEN = true`

### RSE-013 — Resgatar Peeko e recuperar Devon Goods

- **Jogos:** RSE
- **Categoria:** MAIN
- **Local:** Route 116 / Rusturf Tunnel
- **Pré-requisito:** RSE-012
- **Concluído quando:**
  - Emerald: `FLAG_RECOVERED_DEVON_GOODS = true`
- **Não confundir com:** entrega final em Slateport.

### RSE-014 — Devolver Devon Goods em Rustboro

- **Jogos:** RSE
- **Categoria:** MAIN
- **Local:** Devon Corporation
- **Pré-requisito:** RSE-013
- **Concluído quando:**
  - Emerald: `FLAG_RETURNED_DEVON_GOODS = true`

### RSE-015 — Receber PokéNav e carta para Steven

- **Jogos:** RSE
- **Categoria:** MAIN
- **Local:** Devon Corporation
- **Pré-requisito:** RSE-014
- **Concluído quando:**
  - `FLAG_SYS_POKENAV_GET = true`
  - Emerald: `FLAG_RECEIVED_POKENAV = true`
- **Próximos objetivos possíveis:** Dewford/Steven e Slateport.

---

## CAPÍTULO 03 — Dewford / Steven

### RSE-016 — Viajar com Mr. Briney até Dewford

- **Jogos:** RSE
- **Categoria:** MAIN
- **Pré-requisito:** RSE-015
- **Concluído quando:** `FLAG_VISITED_DEWFORD_TOWN = true`

### RSE-017 — Receber HM05 Flash

- **Jogos:** RSE
- **Categoria:** OPTIONAL para concluir a história, recomendado
- **Local:** Granite Cave
- **Pré-requisito:** RSE-016
- **Emerald:** `FLAG_RECEIVED_HM_FLASH = true`
- **Nota:** Brawly pode ser adiado em Gen III.

### RSE-018 — Entregar a carta a Steven

- **Jogos:** RSE
- **Categoria:** MAIN
- **Local:** Granite Cave
- **Pré-requisito:** RSE-015
- **Concluído quando:**
  - Emerald: `FLAG_DELIVERED_STEVEN_LETTER = true`
- **Observação:** pode acontecer antes ou depois de Brawly.

### RSE-019 — Derrotar Brawly

- **Jogos:** RSE
- **Categoria:** MAIN, mas a ordem é parcialmente flexível
- **Local:** Dewford Gym
- **Concluído quando:** `FLAG_BADGE02_GET = true`
- **Recompensa:** Knuckle Badge.
- **Importante:** a Knuckle Badge pode ser obtida depois de Dynamo/Heat, portanto **não derive ordem rígida só pelos badges**.

---

## CAPÍTULO 04 — Slateport / Oceanic Museum

### RSE-020 — Viajar para Route 109 / Slateport

- **Jogos:** RSE
- **Categoria:** MAIN
- **Pré-requisito:** acesso por Mr. Briney
- **Concluído quando:** `FLAG_VISITED_SLATEPORT_CITY = true`

### RSE-021 — Falar com Dock no estaleiro

- **Jogos:** RSE
- **Categoria:** MAIN
- **Local:** Stern's Shipyard
- **Pré-requisito:** carregar Devon Goods
- **Emerald:** pode usar `FLAG_DOCK_REJECTED_DEVON_GOODS`.

### RSE-022 — Entregar Devon Goods ao Captain Stern

- **Jogos:** RSE
- **Categoria:** MAIN
- **Local:** Oceanic Museum
- **Pré-requisito:** RSE-021
- **Concluído quando:**
  - Emerald: `FLAG_DELIVERED_DEVON_GOODS = true`
  - Emerald: `FLAG_EVIL_TEAM_ESCAPED_STERN_SPOKE = true` é evidência posterior forte.
- **Equipe:**
  - R: Magma
  - S/E: Aqua

---

## CAPÍTULO 05 — Route 110 / Mauville

### RSE-023 — Derrotar o rival na Route 110

- **Jogos:** RSE
- **Categoria:** MAIN
- **Local:** Route 110
- **Pré-requisito:** RSE-022
- **Detecção:** trainer flag/story var da Route 110.
- **RS var útil:** `VAR_ROUTE110_STATE`.

### RSE-024 — Chegar a Mauville

- **Jogos:** RSE
- **Categoria:** MAIN
- **Concluído quando:** `FLAG_VISITED_MAUVILLE_CITY = true`

### RSE-025 — Derrotar Wally em frente ao Gym

- **Jogos:** RSE
- **Categoria:** MAIN
- **Local:** Mauville
- **Concluído quando:**
  - Emerald: `FLAG_DEFEATED_WALLY_MAUVILLE = true`

### RSE-026 — Receber HM06 Rock Smash

- **Jogos:** RSE
- **Categoria:** MAIN/UTILITY
- **Emerald:** `FLAG_RECEIVED_HM_ROCK_SMASH = true`

### RSE-027 — Derrotar Wattson

- **Jogos:** RSE
- **Categoria:** MAIN
- **Local:** Mauville Gym
- **Concluído quando:** `FLAG_BADGE03_GET = true`
- **Recompensa:** Dynamo Badge.

### RSE-028 — Abrir Rusturf Tunnel completamente

- **Jogos:** RSE
- **Categoria:** OPTIONAL para história imediata
- **Local:** Rusturf Tunnel
- **Pré-requisito:** Rock Smash utilizável
- **Emerald:** `FLAG_RUSTURF_TUNNEL_OPENED = true`
- **Emerald:** `FLAG_RECEIVED_HM_STRENGTH = true` é forte evidência.

---

## CAPÍTULO 06 — Fallarbor / Meteor Falls / Mt. Chimney

### RSE-029 — Chegar a Fallarbor

- **Jogos:** RSE
- **Categoria:** MAIN
- **Concluído quando:** `FLAG_VISITED_FALLARBOR_TOWN = true`

### RSE-030 — Encontrar o conflito em Meteor Falls

- **Jogos:** RSE
- **Categoria:** MAIN
- **Pré-requisito:** RSE-029
- **Diferenças:**
  - Ruby: Team Magma é a principal vilã.
  - Sapphire: Team Aqua é a principal vilã.
  - Emerald: ambas aparecem; a dinâmica é própria.
- **Emerald:** `FLAG_MET_ARCHIE_METEOR_FALLS` pode participar do estado.

### RSE-031 — Perseguir a equipe até Mt. Chimney

- **Jogos:** RSE
- **Categoria:** MAIN
- **Pré-requisito:** RSE-030

### RSE-032 — Derrotar a equipe vilã no topo de Mt. Chimney

- **Jogos:** RSE
- **Categoria:** MAIN
- **Concluído quando:**
  - Emerald: `FLAG_DEFEATED_EVIL_TEAM_MT_CHIMNEY = true`

### RSE-033 — Recuperar o Meteorite

- **Jogos:** RSE
- **Categoria:** MAIN/OPTIONAL de entrega posterior
- **Emerald:** `FLAG_RECEIVED_METEORITE = true`

### RSE-034 — Chegar a Lavaridge

- **Jogos:** RSE
- **Categoria:** MAIN
- **Concluído quando:** `FLAG_VISITED_LAVARIDGE_TOWN = true`

### RSE-035 — Derrotar Flannery

- **Jogos:** RSE
- **Categoria:** MAIN
- **Concluído quando:** `FLAG_BADGE04_GET = true`
- **Recompensa:** Heat Badge.

### RSE-036 — Receber Go-Goggles

- **Jogos:** RSE
- **Categoria:** MAIN/UTILITY
- **Pré-requisito:** RSE-035
- **Emerald:** `FLAG_RECEIVED_GO_GOGGLES = true`

---

## CAPÍTULO 07 — Petalburg Gym / Surf

### RSE-037 — Voltar a Petalburg para desafiar Norman

- **Jogos:** RSE
- **Categoria:** MAIN
- **Pré-requisito:** quatro primeiras badges exigidas para o desafio
- **Nota:** Brawly pode ter sido adiado; valide as quatro badges antes de marcar AVAILABLE.

### RSE-038 — Derrotar Norman

- **Jogos:** RSE
- **Categoria:** MAIN
- **Local:** Petalburg Gym
- **Concluído quando:** `FLAG_BADGE05_GET = true`
- **RS flag adicional conhecida:** `FLAG_DEFEATED_PETALBURG_GYM = 0x4C1`

### RSE-039 — Receber HM03 Surf

- **Jogos:** RSE
- **Categoria:** MAIN
- **Pré-requisito:** RSE-038
- **Concluído quando:**
  - Emerald: `FLAG_RECEIVED_HM_SURF = true`

---

## CAPÍTULO 08 — Route 118 / Weather Institute / Fortree

### RSE-040 — Atravessar Route 118 e encontrar Steven

- **Jogos:** RSE
- **Categoria:** MAIN
- **Pré-requisito:** Surf
- **RS var:** `VAR_ROUTE118_STATE`

### RSE-041 — Libertar Weather Institute

- **Jogos:** RSE
- **Categoria:** MAIN
- **Local:** Route 119
- **Equipe:**
  - R: Magma
  - S/E: Aqua
- **Detector:** story var Route 119 e trainer flags dos admins.
- **RS var:** `VAR_ROUTE119_STATE`.

### RSE-042 — Receber Castform

- **Jogos:** RSE
- **Categoria:** MAIN-associated
- **Emerald:** `FLAG_RECEIVED_CASTFORM = true`
- **Boa evidência de:** Weather Institute concluído.

### RSE-043 — Derrotar o rival após Weather Institute

- **Jogos:** RSE
- **Categoria:** MAIN
- **Local:** Route 119
- **Resultado:** HM02 Fly
- **Emerald:** `FLAG_RECEIVED_HM_FLY = true`

### RSE-044 — Chegar a Fortree

- **Jogos:** RSE
- **Categoria:** MAIN
- **Concluído quando:** `FLAG_VISITED_FORTREE_CITY = true`

### RSE-045 — Encontrar Steven e obter Devon Scope

- **Jogos:** RSE
- **Categoria:** MAIN
- **Local:** Route 120
- **Pré-requisito:** RSE-044
- **Emerald:** `FLAG_RECEIVED_DEVON_SCOPE = true`

### RSE-046 — Remover Kecleon que bloqueia Fortree Gym

- **Jogos:** RSE
- **Categoria:** MAIN
- **Detecção:** Devon Scope + estado do Kecleon/objeto oculto.

### RSE-047 — Derrotar Winona

- **Jogos:** RSE
- **Categoria:** MAIN
- **Concluído quando:** `FLAG_BADGE06_GET = true`
- **RS flag adicional:** `FLAG_DEFEATED_FORTREE_GYM = 0x4C9`
- **Nota:** Feather Badge pode ser adiada em Gen III; não presuma sequência absoluta.

---

## CAPÍTULO 09 — Mt. Pyre / Orbs / Lilycove

### RSE-048 — Seguir a equipe até Mt. Pyre

- **Jogos:** RSE
- **Categoria:** MAIN
- **Local:** Route 121 → Route 122 → Mt. Pyre
- **RS var útil:** `VAR_ROUTE121_STATE`.

### RSE-049 — Concluir o evento do topo de Mt. Pyre

- **Jogos:** RSE
- **Categoria:** MAIN
- **Diferenças críticas:**
  - Ruby/Sapphire: o jogador recebe a Orb correspondente necessária à resolução da crise.
  - Emerald: Team Magma e Team Aqua roubam as Orbs; a resolução segue outro caminho.
- **Emerald:** `FLAG_RECEIVED_RED_OR_BLUE_ORB` existe, mas não deve ser interpretada com a mesma semântica de RS sem validar o script/versionamento.

### RSE-050 — Retornar a Slateport e testemunhar o roubo do submarino

- **Jogos:** RSE
- **Categoria:** MAIN
- **Local:** Slateport Harbor
- **Pré-requisito:** evento de Mt. Pyre
- **Emerald:** `FLAG_TEAM_AQUA_ESCAPED_IN_SUBMARINE = true`
- **Ruby/Sapphire:** equipe principal da versão rouba o submarino.

### RSE-051 — Chegar a Lilycove

- **Jogos:** RSE
- **Categoria:** MAIN
- **Concluído quando:** `FLAG_VISITED_LILYCOVE_CITY = true`

### RSE-052 — Derrotar rival em Lilycove

- **Jogos:** RSE
- **Categoria:** MAIN-associated
- **Emerald:** `FLAG_MET_RIVAL_LILYCOVE`; trainer flag do encontro é detector mais forte.

---

# 5. Divergência grande de roteiro: Ruby/Sapphire x Emerald

## Ruby — Team Magma Hideout

### R-053 — Invadir Team Magma Hideout

- **Jogos:** R
- **Categoria:** MAIN
- **Local:** hideout da Team Magma
- **Pré-requisito:** eventos de Mt. Pyre/Slateport.
- **Conclusão:** derrotar admins e avançar até a fuga do submarino/continuação da trama.

## Sapphire — Team Aqua Hideout

### S-053 — Invadir Team Aqua Hideout

- **Jogos:** S
- **Categoria:** MAIN
- **Local:** hideout da Team Aqua
- **Pré-requisito:** eventos de Mt. Pyre/Slateport.

## Emerald — Magma Hideout adicional

### E-053A — Derrotar o Magma Grunt em Jagged Pass

- **Jogos:** E
- **Categoria:** MAIN
- **Emerald:** `FLAG_BEAT_MAGMA_GRUNT_JAGGED_PASS = true`

### E-053B — Encontrar a entrada do Magma Hideout

- **Jogos:** E
- **Categoria:** MAIN
- **Pré-requisito:** evento de Mt. Pyre/Jagged Pass.

### E-053C — Invadir Magma Hideout

- **Jogos:** E
- **Categoria:** MAIN
- **Local:** interior de Mt. Chimney/Jagged Pass.

### E-053D — Groudon é despertado no Magma Hideout

- **Jogos:** E
- **Categoria:** MAIN
- **Concluído quando:** `FLAG_GROUDON_AWAKENED_MAGMA_HIDEOUT = true`

### E-053E — Invadir Team Aqua Hideout em Lilycove

- **Jogos:** E
- **Categoria:** MAIN
- **Pré-requisito:** E-053D / evento do submarino.
- **Concluído quando:** Aqua abandona a base e segue para Seafloor Cavern.

---

## CAPÍTULO 10 — Mossdeep

### RSE-054 — Chegar a Mossdeep

- **Jogos:** RSE
- **Categoria:** MAIN
- **Concluído quando:** `FLAG_VISITED_MOSSDEEP_CITY = true`

### RSE-055 — Derrotar Tate & Liza

- **Jogos:** RSE
- **Categoria:** MAIN
- **Concluído quando:** `FLAG_BADGE07_GET = true`
- **RS flag adicional:** `FLAG_DEFEATED_MOSSDEEP_GYM = 0x4CD`

---

## Emerald exclusivo — Space Center

### E-056 — Team Magma invade Mossdeep Space Center

- **Jogos:** E
- **Categoria:** MAIN
- **Pré-requisito:** Mind Badge.

### E-057 — Derrotar Magma Grunts do 1F

- **Jogos:** E
- **Categoria:** MAIN
- **Emerald:** `FLAG_DEFEATED_GRUNT_SPACE_CENTER_1F = true`

### E-058 — Lutar ao lado de Steven contra Maxie e Tabitha

- **Jogos:** E
- **Categoria:** MAIN
- **Local:** Mossdeep Space Center
- **Concluído quando:** `FLAG_DEFEATED_MAGMA_SPACE_CENTER = true`

---

## CAPÍTULO 11 — Dive / Seafloor Cavern

### RSE-059 — Receber HM08 Dive

- **Jogos:** RSE
- **Categoria:** MAIN
- **Local:** Steven's House, Mossdeep
- **Emerald:** `FLAG_RECEIVED_HM_DIVE = true`

### RSE-060 — Localizar o submarino submerso

- **Jogos:** RSE
- **Categoria:** MAIN
- **Local:** Route 128
- **Pré-requisito:** Dive.
- **RS var:** `VAR_ROUTE128_STATE`

### RSE-061 — Entrar na Seafloor Cavern

- **Jogos:** RSE
- **Categoria:** MAIN

### RSE-062 — Derrotar o líder da equipe na Seafloor Cavern

- **Jogos:** RSE
- **Categoria:** MAIN
- **Ruby:** Maxie
- **Sapphire:** Archie
- **Emerald:** Archie; Maxie participa da crise por outra linha narrativa.

### R-063 — Groudon desperta e escapa

- **Jogos:** R
- **Categoria:** MAIN

### S-063 — Kyogre desperta e escapa

- **Jogos:** S
- **Categoria:** MAIN

### E-063 — Kyogre desperta e escapa

- **Jogos:** E
- **Categoria:** MAIN
- **Emerald:** `FLAG_KYOGRE_ESCAPED_SEAFLOOR_CAVERN = true`

---

# 6. Crise de Sootopolis

### RSE-064 — Chegar a Sootopolis durante a crise

- **Jogos:** RSE
- **Categoria:** MAIN
- **Concluído quando:** `FLAG_VISITED_SOOTOPOLIS_CITY = true`

### RSE-065 — Encontrar Steven/Wallace na Cave of Origin

- **Jogos:** RSE
- **Categoria:** MAIN
- **Emerald:** `FLAG_STEVEN_GUIDES_TO_CAVE_OF_ORIGIN = true` é um marco forte.

---

## Ruby/Sapphire — resolução direta

### RS-066 — Entrar na Cave of Origin

- **Jogos:** RS
- **Categoria:** MAIN
- **Pré-requisito:** Orb/eventos da crise.

### R-067 — Enfrentar Groudon

- **Jogos:** R
- **Categoria:** MAIN
- **Concluído quando:** flag de batalha do lendário/Cave of Origin indica capturado ou derrotado.
- **Importante:** **não exija captura**. Derrotar também prossegue a história.

### S-067 — Enfrentar Kyogre

- **Jogos:** S
- **Categoria:** MAIN
- **Concluído quando:** flag de batalha do lendário/Cave of Origin indica capturado ou derrotado.
- **Importante:** **não exija captura**.

### RS-068 — Crise climática resolvida

- **Jogos:** RS
- **Categoria:** MAIN
- **Pré-requisito:** R-067 ou S-067.

---

## Emerald — resolução por Rayquaza

### E-066 — Falar com Wallace na Cave of Origin

- **Jogos:** E
- **Categoria:** MAIN
- **Concluído quando:** `FLAG_WALLACE_GOES_TO_SKY_PILLAR = true`

### E-067 — Encontrar Wallace em Sky Pillar

- **Jogos:** E
- **Categoria:** MAIN
- **Story vars importantes:**
  - `VAR_SKY_PILLAR_STATE = 0x40CA`
  - `VAR_SOOTOPOLIS_WALLACE_STATE = 0x40D8`

### E-068 — Subir Sky Pillar e despertar Rayquaza

- **Jogos:** E
- **Categoria:** MAIN
- **Detecção:** `VAR_SKY_PILLAR_STATE` + estado do Rayquaza.
- **Var auxiliar:** `VAR_SKY_PILLAR_RAYQUAZA_CRY_DONE = 0x40D7`

### E-069 — Rayquaza interrompe Groudon e Kyogre

- **Jogos:** E
- **Categoria:** MAIN
- **Concluído quando:** estado de Sootopolis pós-crise / flags de Archie e Maxie.
- **Flags úteis:**
  - `FLAG_LEGENDARIES_IN_SOOTOPOLIS`
  - `FLAG_SOOTOPOLIS_ARCHIE_MAXIE_LEAVE`
  - `FLAG_MET_ARCHIE_SOOTOPOLIS`
  - `FLAG_MET_MAXIE_SOOTOPOLIS`
- **Atenção:** algumas dessas flags marcam fases do evento, não necessariamente sua conclusão isoladamente.

### E-070 — Receber HM07 Waterfall de Wallace

- **Jogos:** E
- **Categoria:** MAIN
- **Concluído quando:** `FLAG_RECEIVED_HM_WATERFALL = true`

---

# 7. Oitava insígnia

### RS-071 — Derrotar Wallace

- **Jogos:** RS
- **Categoria:** MAIN
- **Local:** Sootopolis Gym
- **Concluído quando:** `FLAG_BADGE08_GET = true`
- **RS flag adicional:** `FLAG_DEFEATED_SOOTOPOLIS_GYM = 0x4D4`

### E-071 — Derrotar Juan

- **Jogos:** E
- **Categoria:** MAIN
- **Local:** Sootopolis Gym
- **Pré-requisito:** crise resolvida
- **Concluído quando:** `FLAG_BADGE08_GET = true`
- **Observação:** Wallace não é Gym Leader em Emerald.

---

# 8. Victory Road / Pokémon League

### RSE-072 — Chegar a Ever Grande

- **Jogos:** RSE
- **Categoria:** MAIN
- **Pré-requisito:** oito badges + Waterfall
- **Concluído quando:** `FLAG_VISITED_EVER_GRANDE_CITY = true`

### RSE-073 — Entrar em Victory Road

- **Jogos:** RSE
- **Categoria:** MAIN

### RSE-074 — Derrotar Wally em Victory Road

- **Jogos:** RSE
- **Categoria:** MAIN-associated
- **Emerald:** `FLAG_DEFEATED_WALLY_VICTORY_ROAD = true`

### RSE-075 — Sair de Victory Road / chegar à Liga

- **Jogos:** RSE
- **Categoria:** MAIN

### RSE-076 — Entrar no desafio da Elite Four

- **Jogos:** RSE
- **Categoria:** MAIN
- **Emerald:** `FLAG_ENTERED_ELITE_FOUR = true`

### RSE-077 — Derrotar Sidney

- **Jogos:** RSE
- **Categoria:** MAIN
- **RS:** `FLAG_DEFEATED_ELITE_4_SYDNEY = 0x4DD`
- **Emerald:** use trainer flag / Elite Four state.

### RSE-078 — Derrotar Phoebe

- **Jogos:** RSE
- **Categoria:** MAIN
- **RS:** `FLAG_DEFEATED_ELITE_4_PHOEBE = 0x4DE`

### RSE-079 — Derrotar Glacia

- **Jogos:** RSE
- **Categoria:** MAIN
- **RS:** `FLAG_DEFEATED_ELITE_4_GLACIA = 0x4DF`

### RSE-080 — Derrotar Drake

- **Jogos:** RSE
- **Categoria:** MAIN
- **RS:** `FLAG_DEFEATED_ELITE_4_DRAKE = 0x4E0`

### RS-081 — Derrotar Champion Steven

- **Jogos:** RS
- **Categoria:** MAIN

### E-081 — Derrotar Champion Wallace

- **Jogos:** E
- **Categoria:** MAIN

### RSE-082 — Entrar no Hall of Fame

- **Jogos:** RSE
- **Categoria:** MAIN
- **Concluído quando:**
  - `FLAG_SYS_GAME_CLEAR = true`
- **Detector recomendado:** este é o detector canônico para "campanha concluída".
- **Emerald:** ID lógico `0x864`
- **RS:** ID lógico `0x804`

---

# 9. Objetivos opcionais importantes durante a campanha

## HM01 Cut

### OPT-001 — Receber HM01 Cut

- **Jogos:** RSE
- **Local:** Rustboro
- **Emerald:** `FLAG_RECEIVED_HM_CUT = true`

## Bike

### OPT-002 — Receber Mach Bike ou Acro Bike

- **Jogos:** RSE
- **Local:** Mauville
- **Emerald:** `FLAG_RECEIVED_BIKE = true`

## New Mauville

### OPT-003 — Receber Basement Key de Wattson

- **Jogos:** RSE
- **Emerald:** `FLAG_GOT_BASEMENT_KEY_FROM_WATTSON = true`

### OPT-004 — Desativar o gerador de New Mauville

- **Jogos:** RSE
- **Detecção:** state/flag do gerador.

### OPT-005 — Receber TM24 Thunderbolt de Wattson

- **Jogos:** RSE
- **Emerald:** `FLAG_GOT_TM_THUNDERBOLT_FROM_WATTSON = true`

## Desert Fossil

### OPT-006 — Obter Root Fossil

- **Jogos:** RSE
- **Emerald:** `FLAG_CHOSE_ROOT_FOSSIL = true`

### OPT-007 — Obter Claw Fossil

- **Jogos:** RSE
- **Emerald:** `FLAG_CHOSE_CLAW_FOSSIL = true`

### OPT-008 — Reviver fóssil

- **Jogos:** RSE
- **Emerald:** `FLAG_RECEIVED_REVIVED_FOSSIL_MON = true`
- **Emerald vars:**
  - `VAR_FOSSIL_RESURRECTION_STATE`
  - `VAR_WHICH_FOSSIL_REVIVED`

## Abandoned Ship

### OPT-009 — Explorar Abandoned Ship

- **Jogos:** RSE
- **Categoria:** OPTIONAL

### OPT-010 — Usar Storage Key

- **Jogos:** RSE
- **Emerald:** `FLAG_USED_STORAGE_KEY = true`

### OPT-011 — Usar Room 1 Key

- **Emerald:** `FLAG_USED_ROOM_1_KEY = true`

### OPT-012 — Usar Room 2 Key

- **Emerald:** `FLAG_USED_ROOM_2_KEY = true`

### OPT-013 — Usar Room 4 Key

- **Emerald:** `FLAG_USED_ROOM_4_KEY = true`

### OPT-014 — Usar Room 6 Key

- **Emerald:** `FLAG_USED_ROOM_6_KEY = true`

### OPT-015 — Trocar Scanner com Captain Stern

- **Jogos:** RSE
- **Emerald:** `FLAG_EXCHANGED_SCANNER = true`

---

# 10. Regi — side quest detectável

### REGI-001 — Abrir Sealed Chamber

- **Jogos:** RSE
- **Categoria:** OPTIONAL
- **Pré-requisitos usuais:** Surf, Dive; Relicanth e Wailord na equipe em posições exigidas pelo jogo.
- **Concluído quando:** `FLAG_REGI_DOORS_OPENED = true`

### REGI-002 — Abrir Desert Ruins / enfrentar Regirock

- **Jogos:** RSE
- **Categoria:** OPTIONAL
- **Emerald:** `FLAG_DEFEATED_REGIROCK` indica batalha encerrada por derrota; para captura, valide dados de Pokédex/party/boxes ou flag de captura se disponível na versão.
- **Não use "defeated" como sinônimo automático de "caught".**

### REGI-003 — Abrir Island Cave / enfrentar Regice

- **Jogos:** RSE
- **Categoria:** OPTIONAL
- **Emerald:** `FLAG_DEFEATED_REGICE`

### REGI-004 — Abrir Ancient Tomb / enfrentar Registeel

- **Jogos:** RSE
- **Categoria:** OPTIONAL
- **Emerald:** `FLAG_DEFEATED_REGISTEEL`

---

# 11. Pós-game

## RSE — retorno a Littleroot

### POST-001 — Receber S.S. Ticket

- **Jogos:** RSE
- **Pré-requisito:** Hall of Fame
- **Emerald:** `FLAG_RECEIVED_SS_TICKET = true`

### POST-002 — Liberar roaming Latias/Latios

- **Jogos:** RSE
- **Pré-requisito:** Hall of Fame
- **Emerald:**
  - `FLAG_LATIOS_OR_LATIAS_ROAMING`
  - `VAR_ROAMER_POKEMON` (`0 = Latias`, `1 = Latios`)
- **Diferença:** Emerald permite escolha ligada ao noticiário pós-game.

### POST-003 — Encontrar Latias/Latios

- **Jogos:** RSE
- **Emerald:** `FLAG_ENCOUNTERED_LATIAS_OR_LATIOS = true`

### POST-004 — Capturar Latias/Latios

- **Jogos:** RSE
- **Emerald:** `FLAG_CAUGHT_LATIAS_OR_LATIOS = true`

---

## Ruby/Sapphire — Battle Tower

### RS-POST-005 — Viajar no S.S. Tidal

- **Jogos:** RS
- **Categoria:** POSTGAME

### RS-POST-006 — Acessar Battle Tower

- **Jogos:** RS
- **Categoria:** POSTGAME

### RS-POST-007 — Acessar Sky Pillar pós-game

- **Jogos:** RS
- **Categoria:** POSTGAME

### RS-POST-008 — Enfrentar/Capturar Rayquaza

- **Jogos:** RS
- **Categoria:** POSTGAME
- **Observação:** em RS Rayquaza não é necessário para resolver a campanha principal.

---

## Emerald — Battle Frontier

### E-POST-005 — Receber convite para Battle Frontier

- **Jogos:** E
- **Emerald:** `FLAG_SCOTT_CALL_BATTLE_FRONTIER = true`

### E-POST-006 — Viajar no S.S. Tidal

- **Jogos:** E
- **Categoria:** POSTGAME

### E-POST-007 — Entrar no Battle Frontier

- **Jogos:** E
- **Emerald:** `VAR_HAS_ENTERED_BATTLE_FRONTIER` funciona como flag.

### E-POST-008 — Obter todos Silver Symbols

- **Jogos:** E
- **Emerald:** `FLAG_COLLECTED_ALL_SILVER_SYMBOLS = true`

### E-POST-009 — Obter todos Gold Symbols

- **Jogos:** E
- **Emerald:** `FLAG_COLLECTED_ALL_GOLD_SYMBOLS = true`

---

## Emerald — Groudon e Kyogre pós-game

### E-POST-010 — Liberar investigação de clima anormal

- **Jogos:** E
- **Categoria:** POSTGAME
- **Pré-requisito:** Hall of Fame.

### E-POST-011 — Localizar Terra Cave

- **Jogos:** E
- **Categoria:** POSTGAME

### E-POST-012 — Enfrentar/Capturar Groudon

- **Jogos:** E
- **Emerald:** `FLAG_DEFEATED_GROUDON` marca batalha resolvida; validar captura separadamente se necessário.

### E-POST-013 — Localizar Marine Cave

- **Jogos:** E
- **Categoria:** POSTGAME

### E-POST-014 — Enfrentar/Capturar Kyogre

- **Jogos:** E
- **Emerald:** `FLAG_DEFEATED_KYOGRE`

---

## Emerald — Rayquaza capturável

### E-POST-015 — Retornar a Sky Pillar após a crise

- **Jogos:** E
- **Categoria:** OPTIONAL/POSTGAME dependendo do momento

### E-POST-016 — Enfrentar/Capturar Rayquaza

- **Jogos:** E
- **Emerald:** `FLAG_DEFEATED_RAYQUAZA`
- **Nota:** Rayquaza é despertado durante a campanha, mas a captura é um objetivo separado.

---

# 12. Eventos por ticket — não considerar campanha obrigatória

Esses objetivos dependem de itens/eventos promocionais e devem ficar fora do percentual padrão da campanha.

### EVENT-001 — Southern Island / Eon Ticket

- **Jogos:** RSE
- **Categoria:** EVENT

### EVENT-002 — Birth Island / Aurora Ticket / Deoxys

- **Jogos:** E e distribuições compatíveis
- **Emerald:** `FLAG_RECEIVED_AURORA_TICKET`

### EVENT-003 — Navel Rock / Mystic Ticket / Ho-Oh e Lugia

- **Jogos:** E e distribuições compatíveis
- **Emerald:**
  - `FLAG_RECEIVED_MYSTIC_TICKET`
  - `FLAG_DEFEATED_HO_OH`
  - `FLAG_DEFEATED_LUGIA`
  - `FLAG_CAUGHT_HO_OH`
  - `FLAG_CAUGHT_LUGIA`

### EVENT-004 — Faraway Island / Old Sea Map / Mew

- **Jogos:** Emerald (evento)
- **Emerald:**
  - `FLAG_RECEIVED_OLD_SEA_MAP`
  - `FLAG_DEFEATED_MEW`
  - `FLAG_CAUGHT_MEW`

---

# 13. Story vars conhecidas úteis

## Ruby / Sapphire

O `pret/pokeruby` documenta, entre outras:

```text
VAR_BIRCH_STATE                  = 0x4049
VAR_LITTLEROOT_STATE             = 0x4050
VAR_ROUTE102_ACCESSIBLE          = 0x4051
VAR_LAVARIDGE_RIVAL_STATE        = 0x4053
VAR_PETALBURG_STATE              = 0x4057
VAR_SLATEPORT_STATE              = 0x4058
VAR_RUSTBORO_STATE               = 0x405A
VAR_SOOTOPOLIS_STATE             = 0x405E
VAR_ROUTE101_STATE               = 0x4060
VAR_ROUTE103_STATE               = 0x4062
VAR_ROUTE110_STATE               = 0x4069
VAR_ROUTE116_STATE               = 0x406F
VAR_ROUTE118_STATE               = 0x4071
VAR_ROUTE119_STATE               = 0x4072
VAR_ROUTE121_STATE               = 0x4074
VAR_ROUTE128_STATE               = 0x407B
VAR_LITTLEROOT_HOUSES_STATE      = 0x4082
VAR_BIRCH_LAB_STATE              = 0x4084
VAR_PETALBURG_GYM_STATE          = 0x4085
VAR_LITTLEROOT_RIVAL_STATE       = 0x408D
VAR_DEVON_CORP_3F_STATE          = 0x408F
VAR_BRINEY_HOUSE_STATE           = 0x4090
VAR_LITTLEROOT_INTRO_STATE       = 0x4092
VAR_MAUVILLE_GYM_STATE           = 0x4093
VAR_BRINEY_LOCATION              = 0x4096
VAR_PETALBURG_WOODS_STATE        = 0x4098
VAR_RUSTURF_TUNNEL_STATE         = 0x409A
VAR_CAVE_OF_ORIGIN_B4F_STATE     = 0x409B
VAR_ELITE_4_STATE                = 0x409C
```

**Atenção:** o endereço da var e seu **valor semântico** são coisas diferentes. Para um detector confiável, extraia do script de cada mapa quais valores correspondem a cada fase.

## Emerald

Entre as vars específicas úteis ao fim da história:

```text
VAR_VICTORY_ROAD_1F_STATE            = 0x40C3
VAR_FOSSIL_RESURRECTION_STATE        = 0x40C4
VAR_WHICH_FOSSIL_REVIVED             = 0x40C5
VAR_STEVENS_HOUSE_STATE              = 0x40C6
VAR_JAGGED_PASS_STATE                = 0x40C8
VAR_SKY_PILLAR_STATE                 = 0x40CA
VAR_MIRAGE_TOWER_STATE               = 0x40CB
VAR_HAS_ENTERED_BATTLE_FRONTIER      = 0x40D0
VAR_ROAMER_POKEMON                   = 0x40D5
VAR_SKY_PILLAR_RAYQUAZA_CRY_DONE     = 0x40D7
VAR_SOOTOPOLIS_WALLACE_STATE         = 0x40D8
```

---

# 14. Regras de inferência recomendadas

## 14.1 Não confundir "possuir item" com "evento concluído"

Exemplo:

```text
HM03 Surf no inventário
```

pode ter sido alterado por cheat/editor. Melhor:

```text
FLAG_RECEIVED_HM_SURF == true
AND FLAG_BADGE05_GET == true
```

Quando houver flag de recebimento, prefira-a.

## 14.2 Badges não determinam uma sequência totalmente linear

No Gen III:

- Brawly pode ser adiado.
- Winona pode ser adiada.
- portanto um save com Badge 3 sem Badge 2 pode ser válido.

Não marque o save como corrompido por isso.

## 14.3 "Lendário derrotado" != "lendário capturado"

Seu modelo deve distinguir:

```text
ENCOUNTER_COMPLETED
DEFEATED
CAUGHT
```

Para a campanha de Ruby/Sapphire, derrotar Groudon/Kyogre na Cave of Origin é suficiente para continuar.

## 14.4 Hall of Fame

Use:

```text
FLAG_SYS_GAME_CLEAR
```

como principal evidência de campanha finalizada.

Não tente deduzir apenas pelas quatro flags da Elite Four.

## 14.5 Versão primeiro, interpretação depois

Pseudocódigo:

```text
version = detectGameVersion(save)

switch version:
    RUBY:
        use rubySapphireFlagMap
        use rubyMissionVariants
    SAPPHIRE:
        use rubySapphireFlagMap
        use sapphireMissionVariants
    EMERALD:
        use emeraldFlagMap
        use emeraldMissionVariants
```

---

# 15. Modelo de avaliação de objetivo

```yaml
- id: RSE-038
  order: 38
  games: [R, S, E]
  category: MAIN
  title: Defeat Norman
  location: Petalburg Gym
  prerequisites:
    objectives:
      - RSE-035
  completion:
    all:
      - type: flag
        name: FLAG_BADGE05_GET
        value: true
  confidence: HIGH

- id: E-058
  order: 58
  games: [E]
  category: MAIN
  title: Defeat Team Magma at Mossdeep Space Center
  location: Mossdeep Space Center
  prerequisites:
    objectives:
      - RSE-055
  completion:
    all:
      - type: flag
        name: FLAG_DEFEATED_MAGMA_SPACE_CENTER
        id: 0x75
        value: true
  confidence: HIGH

- id: RSE-082
  order: 82
  games: [R, S, E]
  category: MAIN
  title: Enter the Hall of Fame
  prerequisites:
    objectives:
      - RSE-080
  completion:
    all:
      - type: system_flag
        name: FLAG_SYS_GAME_CLEAR
        value: true
  confidence: VERY_HIGH
```

---

# 16. Algoritmo recomendado para calcular "próxima missão"

```text
1. detectar versão do jogo;
2. carregar apenas objetivos aplicáveis à versão;
3. ler flags, vars, trainer flags, badges e itens recebidos;
4. avaliar todos objetivos na ordem lógica;
5. para cada objetivo:
      se completion == true:
          COMPLETED
      senão se prerequisites == true:
          AVAILABLE ou IN_PROGRESS
      senão:
          LOCKED
6. retornar:
      - último objetivo concluído;
      - objetivos atualmente disponíveis;
      - próximo objetivo principal recomendado;
      - objetivos opcionais disponíveis;
      - percentual da campanha.
```

### Percentual recomendado

Use apenas `category = MAIN`.

```text
progress =
  completed_main_objectives_for_game
  /
  total_main_objectives_for_game
```

Não inclua:

- Battle Frontier;
- Regis;
- fósseis;
- tickets/eventos promocionais;
- lendários opcionais;
- Abandoned Ship;
- New Mauville;

no percentual da história principal.

---

# 17. Validação de consistência do save

Seu programa pode produzir alertas sem rejeitar o save.

Exemplos:

```text
FLAG_SYS_GAME_CLEAR == true
e FLAG_BADGE08_GET == false
=> POSSIBLE_EDITED_SAVE
```

```text
FLAG_RECEIVED_HM_SURF == true
e FLAG_BADGE05_GET == false
=> POSSIBLE_EDITED_SAVE
```

Mas:

```text
FLAG_BADGE03_GET == true
e FLAG_BADGE02_GET == false
```

**não é necessariamente inválido**, pois Brawly pode ser adiado.

Da mesma forma, Feather Badge pode ser obtida fora da sequência mais comum.

---

# 18. Mapeamento resumido das diferenças de campanha

| Trecho | Ruby | Sapphire | Emerald |
|---|---|---|---|
| Petalburg Woods | Magma | Aqua | Aqua |
| Oceanic Museum | Magma | Aqua | Aqua |
| Weather Institute | Magma | Aqua | Aqua |
| Mt. Chimney | Magma principal | Aqua principal | Magma/Aqua |
| Mt. Pyre | conflito da versão | conflito da versão | ambas roubam Orbs |
| Hideout principal | Magma | Aqua | Magma + Aqua |
| Mossdeep Space Center | sem invasão principal | sem invasão principal | **Team Magma invade** |
| Ancient Pokémon principal | Groudon | Kyogre | Groudon + Kyogre |
| Cave of Origin | batalha com Groudon | batalha com Kyogre | busca por solução |
| Sky Pillar na história | não | não | **sim** |
| Rayquaza obrigatório | não | não | **sim, para interromper a crise** |
| Sootopolis Gym Leader | Wallace | Wallace | Juan |
| Champion | Steven | Steven | Wallace |
| Battle facility principal pós-game | Battle Tower | Battle Tower | Battle Frontier |

---

# 19. Fontes técnicas recomendadas para implementação

Use os projetos de decompilação como fonte canônica dos nomes de flags/vars e dos scripts:

- `pret/pokeruby`
  - `include/constants/flags.h`
  - `include/constants/vars.h`
  - `data/maps/**/scripts.inc` ou estrutura equivalente do decomp
- `pret/pokeemerald`
  - `include/constants/flags.h`
  - `include/constants/vars.h`
  - `data/maps/**/scripts.inc`

Para sequência narrativa:

- Bulbapedia — Pokémon Ruby and Sapphire walkthrough
- Bulbapedia — Pokémon Emerald walkthrough

---

# 20. Próxima etapa técnica recomendada

Este catálogo já pode ser usado como **camada de domínio de objetivos**, mas para um leitor de `.sav` 100% determinístico ainda é necessário criar dois mapas técnicos separados:

```text
ruby_sapphire_save_map
emerald_save_map
```

Cada mapa deve definir:

```yaml
flags:
  section: ...
  base_offset: ...
  bit_order: ...

vars:
  section: ...
  base_offset: ...
  size: 2
  endian: little

trainer_flags:
  section: ...
  base_offset: ...

game_version:
  detection: ROM/game_code/save_context
```

Depois, cada objetivo deste MD pode ser convertido em YAML/JSON e avaliado sem conhecimento de interface.

---

# 21. Identificadores mínimos que vale extrair do save

Para a primeira versão do programa, extraia pelo menos:

```text
game_version
player_name
trainer_id
current_map
current_position

event_flags[]
system_flags[]
trainer_flags[]
vars[]

badges[8]

received_hms[]
key_items[]

pokedex_seen[]
pokedex_caught[]

hall_of_fame / FLAG_SYS_GAME_CLEAR
```

Com isso você consegue determinar praticamente todo o progresso da campanha e grande parte do conteúdo opcional sem depender da posição atual do personagem.

---

# 22. Regra final

A unidade correta de progresso não deve ser:

> "o jogador está em Fortree"

e sim:

> "o jogador concluiu Weather Institute, derrotou o rival, recebeu Fly, obteve Devon Scope e ainda não possui Feather Badge; portanto Fortree Gym é o próximo objetivo principal disponível."

Esse modelo torna o sistema resistente a:

- backtracking;
- Fly;
- ordem flexível de algumas badges;
- objetivos opcionais ignorados;
- save carregado em qualquer mapa;
- jogador que deixou um objetivo intermediário para depois.
