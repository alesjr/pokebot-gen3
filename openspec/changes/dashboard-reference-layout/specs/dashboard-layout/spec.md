## ADDED Requirements

### Requirement: Reference-aligned operational layout
The dashboard SHALL present the emulator as the primary visual element with profile management, bot mode, manual controls, save-state controls, activity, recent Pokémon, and logs arranged in a compact desktop layout matching the supplied reference's hierarchy.

#### Scenario: Operator opens dashboard
- **WHEN** the dashboard loads
- **THEN** game/profile selection and online state are immediately visible, the emulator is central, and operational panels are visible without navigating to another page

### Requirement: Manual emulator controls
The dashboard SHALL expose the existing manual emulator controls near the emulator, including directional, A, B, Start, Select, L, and R actions, without adding alternate control implementations.

#### Scenario: Operator controls game manually
- **WHEN** an active profile is running and the operator presses a visible control
- **THEN** the existing control endpoint receives the corresponding emulator action

### Requirement: Selectable bot mode
The dashboard SHALL render registered bot modes in a select element and SHALL not replace mode selection with radio buttons or invented modes.

#### Scenario: Operator changes mode
- **WHEN** the operator selects a registered mode
- **THEN** the existing mode endpoint is used and unavailable modes remain unselectable

### Requirement: Save-state management
The dashboard SHALL provide visible actions to create a save state, choose an available save state, and load the selected state using existing backend operations.

#### Scenario: Operator loads save state
- **WHEN** the operator selects a listed state and confirms loading
- **THEN** the selected state is loaded through the existing `/load-state` operation

### Requirement: Recent encounter and capture views
The dashboard SHALL show recent encounters and recent captures as distinct views, ordered newest first, using the existing encounter state and without creating a Pokédex or new API.

#### Scenario: Encounter stream updates
- **WHEN** backend state contains encountered and captured Pokémon
- **THEN** encounters appear in the encounter view and captured entries appear in the capture view with available species, level, shiny, and status information
