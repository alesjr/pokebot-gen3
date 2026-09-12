# Proposal: Dashboard Reference Layout

## Summary

Refresh the existing dashboard frontend to closely follow the supplied operational emulator screenshot while preserving current APIs, behavior, and HTML/CSS/JavaScript-only architecture.

## Motivation

The dashboard is functional but its visual hierarchy differs from the reference. Operators need the emulator, profile controls, bot mode, manual controls, save states, activity, recent encounters, captures, and logs visible in a compact desktop layout.

## Scope

- Reorganize existing dashboard markup without breaking current element IDs or API hooks.
- Restyle the page to match the reference's dark, compact operational layout.
- Keep bot mode as a select populated by registered backend modes.
- Make manual emulator controls clearly visible beside/below the emulator.
- Expose save-state creation, state selection, and state loading.
- Split recent encounters and captures visually using the existing encounter data.
- Preserve current activity and system/error log sections.

## Non-goals

- No backend endpoint redesign.
- No new framework, dependency, database, or emulator implementation.
- No changes to Campaign behavior, profile semantics, or emulator lifecycle.
- No tests or validation work.
