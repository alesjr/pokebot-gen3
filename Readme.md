# PokéBot Gen3 — Campaign RSE

Fork focado em automação de campanha para Pokémon Ruby, Sapphire e Emerald.

## Escopo atual

- modo `Campaign` disponível somente para RSE;
- primeira missão automatizada: criação do save, relógio, rival e escolha do inicial;
- progresso de missões persistido em `stats/missions.db`;
- dashboard e emulador executados no mesmo container;
- modos tradicionais do PokéBot continuam disponíveis.

FireRed e LeafGreen não fazem parte da automação de campanha.

## Requisitos

- Python 3.12;
- dependências nativas exigidas por mGBA e SDL;
- ROM original compatível;
- Docker e Docker Compose para execução em containers.

Instale dependências Python:

```bash
python -m pip install -r requirements.txt
```

## Execução local

Crie ou importe perfil pela interface padrão. Depois execute:

```bash
python pokebot.py Sapphire -m Campaign
```

Para execução headless:

```bash
python pokebot.py Campaign-Sapphire --bot-mode Campaign --headless --emulation-speed 0 --no-audio
```

Configuração de treinador e inicial usa variáveis de ambiente:

```bash
export POKEBOT_CAMPAIGN_TRAINER_NAME=Alesjr
export POKEBOT_CAMPAIGN_STARTER=Treecko
```

## Docker

Configure `POKEBOT_PROFILE` no `.env` e suba a aplicação:

```bash
cp .env.example .env
docker compose up -d --build
```

Um container `pokebot` executa emulador, bot e dashboard. Dashboard: `http://localhost:8888/`.

## Projeto original

Baseado em [pokebot-gen3](https://github.com/40Cakes/pokebot-gen3).
