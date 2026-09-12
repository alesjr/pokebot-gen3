# Design: Dashboard Reference Layout

## Existing integration

The page is served from `modules/web/static/fleet` and uses plain HTML, CSS, and JavaScript. `modules/web/static/fleet/app.js` already consumes `/api/*` state and control endpoints. Existing IDs and `data-*` hooks are integration contracts and must remain stable.

## Layout

- Compact top bar with game/profile selection and online status.
- Left profile/save management panel.
- Center emulator frame with toolbar directly below it.
- Right operational column containing bot-mode select, manual controls, and two recent-Pokémon panels.
- Activity and bot log remain immediately below the emulator.
- System/error log remains distinct and visible below the primary operation area.

## Controls and save states

Reuse current `[data-button]` controls and `/control` endpoint. Keep directional, A/B, Start, Select, L/R controls visible. Keep current reset, screen, pause, speed, and save-state toolbar actions. Render `save_states` into the existing select and use `/load-state` for loading.

## Recent Pokémon

The backend already returns encounters with `captured`, `shiny`, species, and level. The frontend will derive two ordered views from that array: all recent encounters and captured-only entries, newest first. No endpoint or persistence change.

## Compatibility

Preserve i18n attributes and existing localization mechanism. Any new visible frontend text must use i18n keys. Preserve responsive fallback without introducing a framework.
