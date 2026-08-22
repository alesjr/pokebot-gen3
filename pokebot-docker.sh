#!/bin/sh
set -eu

project_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$project_dir"

action="${1:-gui}"
profile="${2:-${POKEBOT_PROFILE:-Sapphire}}"
mode="${POKEBOT_MODE:-Living Dex Gen III}"

case "$profile" in
    Sapphire) default_dashboard_port=8888 ;;
    Ruby) default_dashboard_port=8889 ;;
    Emerald) default_dashboard_port=8890 ;;
    *) default_dashboard_port=8891 ;;
esac

dashboard_port="${3:-${POKEBOT_DASHBOARD_PORT:-${POKEBOT_GUI_DASHBOARD_PORT:-$default_dashboard_port}}}"
emulation_speed="${4:-${POKEBOT_EMULATION_SPEED:-}}"
profile_slug="$(printf '%s' "$profile" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9_-' '-')"
compose_project="pokebot-$profile_slug"

usage() {
    echo "Uso: $0 [gui|headless|stop|logs|status|build|start-all|stop-all|status-all|logs-all] [perfil] [porta] [velocidade]"
    echo
    echo "  gui       Emulador visual + dashboard (padrão)"
    echo "  headless  Emulador sem janela + dashboard"
    echo "  stop      Para somente instância do perfil"
    echo "  logs      Acompanha logs da instância"
    echo "  status    Mostra estado da instância"
    echo "  build     Constrói imagem sem iniciar"
    echo "  start-all Valida e inicia cinco perfis Living Dex Gen III"
    echo "  stop-all  Para somente cinco instâncias da frota"
    echo "  status-all Mostra estado das cinco instâncias"
    echo "  logs-all  Mostra logs recentes das cinco instâncias"
    echo
    echo "Portas padrão: Sapphire 8888, Ruby 8889, Emerald 8890"
    echo "Velocidade: 0 = máxima; 1, 2, 4, 8, 16 ou 32 = multiplicador"
    echo "Exemplo: $0 headless Emerald 8890 0"
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
    case "$profile" in
        ""|*/*|*\\*|.|..)
            echo "Erro: nome de perfil inválido '$profile'." >&2
            exit 1
            ;;
    esac
    if [ ! -f "profiles/$profile/metadata.yml" ]; then
        echo "Erro: perfil '$profile' não existe em profiles/$profile/." >&2
        echo "Crie ou importe perfil pela GUI antes da execução headless." >&2
        exit 1
    fi
}

require_port() {
    case "$dashboard_port" in
        ""|*[!0-9]*)
            echo "Erro: porta inválida '$dashboard_port'." >&2
            exit 1
            ;;
    esac
    if [ "$dashboard_port" -lt 1 ] || [ "$dashboard_port" -gt 65535 ]; then
        echo "Erro: porta deve estar entre 1 e 65535." >&2
        exit 1
    fi
}

compose() {
    docker compose -p "$compose_project" "$@"
}

fleet_rows() {
    python3 utility/fleet.py list
}

fleet_project() {
    printf 'pokebot-%s' "$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9_-' '-')"
}

fleet_stop_started() {
    for started_profile in $1; do
        "$0" stop "$started_profile" >/dev/null 2>&1 || true
    done
}

ensure_fleet_network() {
    docker network inspect pokebot-fleet >/dev/null 2>&1 || docker network create pokebot-fleet >/dev/null
}

load_fleet_token() {
    token_file="stats/fleet-token"
    mkdir -p stats
    if [ ! -s "$token_file" ]; then
        python3 -c 'import secrets; print(secrets.token_urlsafe(32))' >"$token_file"
        chmod 600 "$token_file"
    fi
    POKEBOT_FLEET_TOKEN="$(tr -d '\r\n' <"$token_file")"
    export POKEBOT_FLEET_TOKEN
}

if [ "$action" = "help" ] || [ "$action" = "-h" ] || [ "$action" = "--help" ]; then
    usage
    exit 0
fi

require_docker
mkdir -p roms profiles

case "$action" in
    start-all)
        python3 utility/fleet.py validate
        python3 utility/fleet.py check-ports
        while IFS='|' read -r fleet_profile fleet_port fleet_game fleet_starter; do
            fleet_compose_project="$(fleet_project "$fleet_profile")"
            if [ -n "$(docker compose -p "$fleet_compose_project" ps -q 2>/dev/null)" ]; then
                echo "Erro: perfil '$fleet_profile' já está aberto." >&2
                exit 1
            fi
        done <<EOF
$(fleet_rows)
EOF
        python3 utility/fleet.py init-profiles
        ensure_fleet_network
        load_fleet_token
        if ! docker compose -p pokebot-fleet -f docker-compose.fleet.yml up --build -d fleet-coordinator; then
            echo "Erro: coordenador da frota não iniciou." >&2
            exit 1
        fi
        started_profiles=""
        while IFS='|' read -r fleet_profile fleet_port fleet_game fleet_starter; do
            if ! POKEBOT_MODE="Living Dex Gen III" "$0" headless "$fleet_profile" "$fleet_port" 0; then
                fleet_stop_started "$started_profiles"
                docker compose -p pokebot-fleet -f docker-compose.fleet.yml down >/dev/null 2>&1 || true
                echo "Erro: falha ao iniciar frota; instâncias iniciadas nesta tentativa foram paradas." >&2
                exit 1
            fi
            started_profiles="$started_profiles $fleet_profile"
        done <<EOF
$(fleet_rows)
EOF
        ;;
    stop-all)
        while IFS='|' read -r fleet_profile fleet_port fleet_game fleet_starter; do
            "$0" stop "$fleet_profile"
        done <<EOF
$(fleet_rows)
EOF
        docker compose -p pokebot-fleet -f docker-compose.fleet.yml down
        ;;
    status-all)
        while IFS='|' read -r fleet_profile fleet_port fleet_game fleet_starter; do
            echo "$fleet_game ($fleet_profile)"
            "$0" status "$fleet_profile"
        done <<EOF
$(fleet_rows)
EOF
        ;;
    logs-all)
        while IFS='|' read -r fleet_profile fleet_port fleet_game fleet_starter; do
            echo "$fleet_game ($fleet_profile)"
            fleet_compose_project="$(fleet_project "$fleet_profile")"
            docker compose -p "$fleet_compose_project" --profile gui logs --tail=200
        done <<EOF
$(fleet_rows)
EOF
        ;;
    gui)
        require_profile
        require_port
        ensure_fleet_network
        emulation_speed="${emulation_speed:-1}"
        if [ -z "${DISPLAY:-}" ]; then
            echo "Erro: DISPLAY não definido; GUI Docker requer X11." >&2
            exit 1
        fi
        if command -v xhost >/dev/null 2>&1; then
            xhost +local:docker >/dev/null
        fi
        compose stop pokebot >/dev/null 2>&1 || true
        POKEBOT_PROFILE="$profile" \
        POKEBOT_PROFILE_SLUG="pokebot-$profile_slug" \
        POKEBOT_MODE="$mode" \
        POKEBOT_DASHBOARD_PORT="$dashboard_port" \
        POKEBOT_EMULATION_SPEED="$emulation_speed" \
            compose --profile gui up --build -d pokebot-gui
        echo "Instância GUI: $compose_project"
        echo "Dashboard: http://localhost:$dashboard_port/"
        ;;
    headless)
        require_profile
        require_port
        ensure_fleet_network
        emulation_speed="${emulation_speed:-0}"
        compose --profile gui stop pokebot-gui >/dev/null 2>&1 || true
        POKEBOT_PROFILE="$profile" \
        POKEBOT_PROFILE_SLUG="pokebot-$profile_slug" \
        POKEBOT_MODE="$mode" \
        POKEBOT_DASHBOARD_PORT="$dashboard_port" \
        POKEBOT_EMULATION_SPEED="$emulation_speed" \
            compose up --build -d pokebot
        echo "Instância headless: $compose_project"
        echo "Dashboard: http://localhost:$dashboard_port/"
        ;;
    stop)
        compose --profile gui down
        ;;
    logs)
        compose --profile gui logs -f --tail=200
        ;;
    status)
        compose --profile gui ps
        ;;
    build)
        compose --profile gui build
        ;;
    *)
        echo "Erro: ação desconhecida '$action'." >&2
        usage >&2
        exit 2
        ;;
esac
