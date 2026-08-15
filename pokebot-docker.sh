#!/usr/bin/env bash
set -Eeuo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$project_dir"

action="${1:-gui}"
profile="${2:-${POKEBOT_PROFILE:-Sapphire}}"
mode="${POKEBOT_MODE:-Living Dex RSE}"
dashboard_port="${POKEBOT_DASHBOARD_PORT:-8888}"
gui_dashboard_port="${POKEBOT_GUI_DASHBOARD_PORT:-8889}"

usage() {
    echo "Uso: $0 [gui|headless|stop|logs|status|build] [perfil]"
    echo
    echo "  gui       Emulador visual + dashboard (padrão)"
    echo "  headless  Emulador sem janela + dashboard"
    echo "  stop      Para containers do projeto"
    echo "  logs      Acompanha logs"
    echo "  status    Mostra estado dos containers"
    echo "  build     Constrói imagem sem iniciar"
    echo
    echo "Exemplo: $0 gui Emerald"
}

require_docker() {
    if ! command -v docker >/dev/null 2>&1; then
        echo "Erro: Docker não encontrado." >&2
        exit 1
    fi
    if ! docker info >/dev/null 2>&1; then
        echo "Erro: daemon Docker indisponível ou sem permissão." >&2
        exit 1
    fi
}

require_profile() {
    if [[ ! -f "profiles/$profile/metadata.yml" ]]; then
        echo "Erro: perfil '$profile' não existe em profiles/$profile/." >&2
        echo "Crie ou importe perfil pela GUI antes da execução headless." >&2
        exit 1
    fi
}

if [[ "$action" == "help" || "$action" == "-h" || "$action" == "--help" ]]; then
    usage
    exit 0
fi

require_docker
mkdir -p roms profiles

case "$action" in
    gui)
        require_profile
        if [[ -z "${DISPLAY:-}" ]]; then
            echo "Erro: DISPLAY não definido; GUI Docker requer X11." >&2
            exit 1
        fi
        if command -v xhost >/dev/null 2>&1; then
            xhost +local:docker >/dev/null
        fi
        docker compose stop pokebot >/dev/null 2>&1 || true
        POKEBOT_PROFILE="$profile" \
        POKEBOT_MODE="$mode" \
        POKEBOT_GUI_DASHBOARD_PORT="$gui_dashboard_port" \
            docker compose --profile gui up --build -d pokebot-gui
        echo "Emulador GUI: container pokebot-gen3-gui"
        echo "Dashboard: http://localhost:$gui_dashboard_port/"
        ;;
    headless)
        require_profile
        docker compose --profile gui stop pokebot-gui >/dev/null 2>&1 || true
        POKEBOT_PROFILE="$profile" \
        POKEBOT_MODE="$mode" \
        POKEBOT_DASHBOARD_PORT="$dashboard_port" \
            docker compose up --build -d pokebot
        echo "Emulador headless: container pokebot-gen3"
        echo "Dashboard: http://localhost:$dashboard_port/"
        ;;
    stop)
        docker compose --profile gui down
        ;;
    logs)
        docker compose --profile gui logs -f --tail=200
        ;;
    status)
        docker compose --profile gui ps
        ;;
    build)
        docker compose --profile gui build
        ;;
    *)
        echo "Erro: ação desconhecida '$action'." >&2
        usage >&2
        exit 2
        ;;
esac
