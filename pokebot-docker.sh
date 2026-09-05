#!/bin/sh
set -eu

project_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$project_dir"

action="${1:-start}"
profile="${2:-${POKEBOT_PROFILE:-Sapphire}}"
dashboard_port="${3:-${POKEBOT_DASHBOARD_PORT:-8888}}"
emulation_speed="${4:-${POKEBOT_EMULATION_SPEED:-0}}"
mode="${POKEBOT_MODE:-Campaign}"

usage() {
    echo "Uso: $0 [start|stop|logs|status|build] [perfil] [porta] [velocidade]"
    echo "Exemplo: $0 start Sapphire 8888 0"
}

require_docker() {
    command -v docker >/dev/null 2>&1 || { echo "Erro: Docker não encontrado." >&2; exit 1; }
    docker info >/dev/null 2>&1 || { echo "Erro: daemon Docker indisponível." >&2; exit 1; }
}

require_profile() {
    case "$profile" in
        ""|*/*|*\\*|.|..) echo "Erro: profile inválido '$profile'." >&2; exit 1 ;;
    esac
    [ -f "profiles/$profile/metadata.yml" ] || {
        echo "Erro: profile '$profile' não existe." >&2
        exit 1
    }
}

require_port() {
    case "$dashboard_port" in
        ""|*[!0-9]*) echo "Erro: porta inválida '$dashboard_port'." >&2; exit 1 ;;
    esac
    [ "$dashboard_port" -ge 1 ] && [ "$dashboard_port" -le 65535 ] || {
        echo "Erro: porta deve estar entre 1 e 65535." >&2
        exit 1
    }
}

if [ "$action" = "help" ] || [ "$action" = "-h" ] || [ "$action" = "--help" ]; then
    usage
    exit 0
fi

require_docker
mkdir -p roms profiles stats

case "$action" in
    start|headless)
        require_profile
        require_port
        POKEBOT_PROFILE="$profile" \
        POKEBOT_MODE="$mode" \
        POKEBOT_DASHBOARD_PORT="$dashboard_port" \
        POKEBOT_EMULATION_SPEED="$emulation_speed" \
            docker compose up --build -d pokebot
        echo "Container: pokebot"
        echo "Dashboard: http://localhost:$dashboard_port/"
        ;;
    stop) docker compose down --remove-orphans ;;
    logs) docker compose logs -f --tail=200 pokebot ;;
    status) docker compose ps ;;
    build) docker compose build pokebot ;;
    *)
        echo "Erro: ação desconhecida '$action'." >&2
        usage >&2
        exit 2
        ;;
esac
