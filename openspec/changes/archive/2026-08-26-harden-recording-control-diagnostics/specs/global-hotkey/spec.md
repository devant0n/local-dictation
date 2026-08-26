## MODIFIED Requirements

### Requirement: Toggle global hotkey via a configurable key combo
The system SHALL provide a system-wide toggle, triggered by a configurable modifier+key combination (default: Control+Shift+D), that starts audio recording on the first trigger and stops recording (handing the clip off for transcription) on the next trigger, regardless of focus. The trigger key and modifiers SHALL be user-configurable without modifying application logic. Event-tap callbacks SHALL only recognize and dispatch a toggle request; microphone or recording-finalization work SHALL run outside the event-tap callback.

#### Scenario: Recording starts on first trigger
- **WHEN** the user presses the configured combo while any application has focus and no recording is in progress
- **THEN** audio recording starts immediately

#### Scenario: Recording stops on second trigger
- **WHEN** the user presses the configured combo while a recording is in progress
- **THEN** audio recording stops and the captured clip is handed off for transcription

#### Scenario: Toggle works regardless of focused app
- **WHEN** the user presses the configured combo while a non-Terminal application has keyboard focus
- **THEN** recording starts or stops correctly, and no character is inserted into the focused application

#### Scenario: Combo is configurable
- **WHEN** the user changes the configured trigger key and/or modifiers and restarts the app
- **THEN** the new combination toggles dictation instead of the previous one

#### Scenario: Holding the combo does not repeatedly toggle
- **WHEN** the user holds the configured combo down
- **THEN** the system toggles at most once per press, not once per repeated key event

#### Scenario: Slow recording control does not disable the active callback
- **WHEN** recording start or stop work takes longer than the event-tap callback budget
- **THEN** the event-tap callback has already returned and the requested recording action completes through the serialized control path

### Requirement: Trigger tap self-healing
The system SHALL detect when macOS disables the global event tap, immediately stop an active recording through the serialized control path, and automatically re-enable the tap so later recordings can use the toggle without an app restart.

#### Scenario: Tap disabled by timeout
- **WHEN** macOS disables the global event tap due to a timeout condition
- **THEN** the system detects the disable event and re-enables the tap automatically

#### Scenario: Tap disabled by timeout while recording
- **WHEN** macOS disables the event tap due to a timeout condition while a recording is active
- **THEN** the recording stops promptly, the captured clip is finalized once, and the user is informed that the hotkey interruption stopped recording

#### Scenario: Tap disabled while idle
- **WHEN** macOS disables the event tap while no recording is active
- **THEN** the system re-enables the tap without creating or altering a recording

## ADDED Requirements

### Requirement: Hotkey availability is diagnosable
The system SHALL record privacy-safe diagnostics when a hotkey request is dispatched and when the event tap is disabled or re-enabled, including the disable reason and a correlation identifier when an active recording is affected.

#### Scenario: Tap-loss incident is inspected later
- **WHEN** a user reports that a recording stopped because the hotkey became unavailable
- **THEN** the local diagnostics identify the tap-loss event, recovery attempt, and affected recording lifecycle without containing dictated text or raw key-event data
