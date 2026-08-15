# PokéBot Gen3 — Living Dex RSE

Automação experimental para Pokémon Ruby, Sapphire e Emerald usando Python,
`libmgba` e os bindings do mGBA. Este fork mantém os modos úteis do projeto
original e adiciona a base do desafio Living Dex RSE.

## Objetivo do desafio

- Coleção separada por perfil e jogo: Ruby, Sapphire e Emerald.
- Somente Pokémon shiny ou com seis IVs iguais a 31 entram na coleção.
- Até seis Pokémon comuns podem permanecer no time para campanha e HMs.
- O inicial configurado deve ser shiny.
- Após receber Poké Balls, o primeiro Pokémon comum com soma de IVs mínima
  configurada vira o `founder_operational`.
- Com founder confirmado, o inicial shiny é depositado no PC de Oldale.
- Duplicatas qualificadas são preservadas enquanto houver espaço.
- Variações persistentes usam gênero e as 28 formas de Unown. Padrões de
  manchas de Spinda e formas temporárias não fazem parte da meta.

## Estado atual

Implementado:

- modo `Living Dex RSE` disponível em Ruby, Sapphire e Emerald;
- captura direta de shiny e Pokémon 6×31 IV;
- seleção e proteção lógica do founder somente após captura confirmada;
- depósito automático do inicial shiny no PC de Oldale após obter founder;
- progresso persistente por perfil em `living_dex_progress.json`;
- RTC histórico baseado no RTC real do RSE;
- preditor RNG somente leitura, desativado por padrão;
- bloqueio de `random_soft_reset_rng` dentro do modo Living Dex;
- dashboard público, somente leitura, para rede doméstica;
- inspeção de dumps de distribuição fornecidos pelo usuário por header, idioma,
  game code e CRC32.

Ainda pendente:

- automação integral da campanha, ginásios, HMs e quests;
- caça autônoma completa por área;
- soft reset do inicial integrado ao mesmo fluxo contínuo do Living Dex;
- execução de distribuições oficiais por segundo core e link emulado;
- transferência real para Geração IV/Pal Park.

O modo atual não deve ser descrito como bot capaz de finalizar a campanha sem
supervisão. Ele implementa políticas de coleção, founder, depósito, RTC e
observabilidade sobre as primitivas existentes do PokéBot.

## RTC histórico

O horário vem do RTC do mGBA, não de escrita direta na memória do jogo.

| Jogo | Data inicial virtual |
|---|---:|
| Ruby / Sapphire | 25/08/2003 |
| Emerald | 21/11/2005 |

Na primeira execução do perfil, o bot cria `rtc_anchor.json`. A partir desse
marco, o relógio avança pelo tempo real de parede, inclusive enquanto o emulador
está desligado e independentemente da velocidade de emulação. Saves e states já
existentes recebem cópia em `rtc_migration_backup/` antes da primeira ancoragem.

Arquivos `.pk3` da Geração III não armazenam data de captura. A data configurada
para futura transferência via Pal Park é `27/08/2007`, mas a transferência ainda
não está implementada.

## RNG

Configuração padrão:

```yaml
rng:
  mode: disabled
  targets:
    - wild
    - static
    - starter
```

O preditor futuro lê `gRngValue` e calcula frames Method 1. Ele não escreve RNG,
save ou dados de Pokémon. `random_soft_reset_rng` deve continuar `false`.

## Dashboard

Disponível por padrão em:

```text
http://localhost:8888/
```

O servidor escuta `0.0.0.0:8888`, sem autenticação ou TLS, para uso em rede
doméstica confiável. Ele não oferece controles do emulador. Exibe:

- Pokédex vista, capturada e qualificada;
- variantes coletadas;
- quests e objetivo atual;
- time, boxes, founder e inicial depositado;
- RTC, TID, SID e caminhos absolutos do perfil, ROM e save.

Não exponha a porta diretamente à internet.

## Instalação local

Requisitos principais:

- Python 3.12 ou superior;
- dependências nativas do mGBA;
- ROM obtida legalmente pelo usuário.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python pokebot.py
```

Coloque ROMs em `roms/`. Na interface, crie um perfil separado para cada jogo.
ROMs, saves, states, estatísticas e perfis são ignorados pelo Git.

Execução direta de perfil:

```bash
python pokebot.py Sapphire -m "Living Dex RSE"
```

## Docker

Headless, dashboard na porta `8888`:

```bash
POKEBOT_PROFILE=Sapphire docker compose up --build pokebot
```

GUI via X11, dashboard publicado na porta `8889`:

```bash
POKEBOT_PROFILE=Sapphire docker compose up --build pokebot-gui
```

Volumes locais preservam ROMs, perfis, saves, screenshots, estatísticas e logs.

## Configuração

Arquivos padrão ficam em `modules/config/templates/`:

- `living_dex.yml`: starter, fóssil, founder, RTC, RNG e transferência futura;
- `dashboard.yml`: bind e porta do dashboard;
- `battle.yml`: estratégia de batalha e captura;
- `cheats.yml`: opções invasivas, mantidas desativadas.

Valores principais:

```yaml
gameplay:
  progression: area
  starter: Mudkip
  fossil: Root Fossil
  founder_min_iv_sum: 93
quality:
  shiny: true
  perfect_ivs: true
duplicates: keep_until_full
recovery:
  mode: rollback
  max_attempts: 3
```

## Distribuições oficiais

O projeto não inclui nem baixa ROMs de distribuição. O validador aceita somente
arquivos fornecidos pelo usuário e pode conferir:

- header GBA;
- checksum do header;
- código do jogo;
- idioma;
- CRC32 permitido.

A validação existe; emulação do segundo core e protocolo de link ainda estão
pendentes.

## Verificação

Testes específicos adicionados:

```bash
python -m unittest tests.test_living_dex
python -m compileall -q modules tests plugins
```

## Origem e atribuições

Baseado em [40Cakes/pokebot-gen3](https://github.com/40Cakes/pokebot-gen3).

- [mGBA](https://github.com/mgba-emu/mgba)
- [libmgba-py](https://github.com/hanzi/libmgba-py/)
- [pret/pokeemerald](https://github.com/pret/pokeemerald)
- [pret/pokeruby](https://github.com/pret/pokeruby)
- [pret/pokefirered](https://github.com/pret/pokefirered)

Pokémon e nomes relacionados pertencem aos respectivos detentores. Este projeto
não distribui ROMs comerciais.

Licença: consulte [LICENSE](LICENSE).
