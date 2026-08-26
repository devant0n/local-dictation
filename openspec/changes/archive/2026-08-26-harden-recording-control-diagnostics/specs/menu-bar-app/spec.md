## MODIFIED Requirements

### Requirement: Status line in menu
The system SHALL surface a live status line reflecting Input Monitoring state, a hotkey-loss interruption affecting the current or most recent recording, the latest capture or transcription non-success outcome, and the outcome of the most recent paste attempt. There is no reliable way to check paste permission ahead of time, so the status reflects the last real attempt rather than a prediction.

#### Scenario: Input Monitoring not granted
- **WHEN** Input Monitoring is not granted or has been revoked
- **THEN** the status line reports that the trigger is off pending that permission

#### Scenario: Hotkey loss stops a recording
- **WHEN** the event tap becomes unavailable while recording
- **THEN** the status line reports that recording was stopped because the hotkey became unavailable

#### Scenario: Capture or transcription is not successful
- **WHEN** a capture finalization fails or a dictation is rejected
- **THEN** the status line reports the latest content-free failure or rejection category

#### Scenario: Last paste attempt failed
- **WHEN** the most recent dictation's paste attempt did not succeed
- **THEN** the status line reports that outcome

#### Scenario: Everything working
- **WHEN** Input Monitoring is granted and the most recent paste attempt succeeded or no attempt has been made
- **THEN** the status line reflects a working or ready state

## ADDED Requirements

### Requirement: Independent recording stop control
The system SHALL provide a menu-bar control that stops an active recording without requiring the global hotkey. The control SHALL only be available while recording and SHALL use the same recording finalization behavior as a normal hotkey stop.

#### Scenario: Stop recording from menu
- **WHEN** the user selects Stop Recording while an active recording is shown
- **THEN** the microphone closes, the clip is handed off for transcription once, and the control is no longer available
