## ADDED Requirements

### Requirement: Serialized recording finalization
The system SHALL serialize hotkey, menu, duration-cap, and hotkey-loss stop requests so an active recording is finalized at most once. Every successful stop source SHALL close the microphone and submit the captured clip through the same transcription handoff.

#### Scenario: Concurrent stop sources
- **WHEN** two stop requests arrive for the same active recording
- **THEN** only the first request finalizes and submits the recording, and the later request has no effect on the microphone, clip, or transcription queue

#### Scenario: Hotkey-loss stop
- **WHEN** the event tap becomes unavailable while recording
- **THEN** the system closes the microphone and hands off the captured clip without waiting for the maximum recording duration
