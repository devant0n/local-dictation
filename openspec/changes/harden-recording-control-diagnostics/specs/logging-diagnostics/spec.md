## ADDED Requirements

### Requirement: Dictation lifecycle diagnostics
The system SHALL record privacy-safe local diagnostics for recording start and stop, stop reason, hotkey dispatch and availability, microphone stream outcomes, queueing, model reload, transcription completion or rejection, retry, retained failure, paste outcome, and idle unload. Records belonging to one recording SHALL share a non-content correlation identifier.

#### Scenario: Transcription failure is investigated
- **WHEN** transcription fails and its automatic retry is exhausted
- **THEN** the local log identifies the affected recording, lifecycle phase, retry outcome, and sanitized error category without containing dictated text, audio, clipboard content, raw exception text, or a filesystem path

### Requirement: Bounded local diagnostic retention
The system SHALL retain at most 3 MiB of local diagnostic log data through rotation, while console diagnostics continue to mirror emitted records.

#### Scenario: Log reaches the rotation threshold
- **WHEN** the active diagnostic log reaches its configured 1 MiB threshold
- **THEN** it rotates while retaining the active file and at most two prior files

## MODIFIED Requirements

### Requirement: Diagnostics never include sensitive content
The system SHALL NOT include transcribed text, clipboard content, raw audio data, raw OS command output, credentials, unfiltered exception messages or tracebacks, or filesystem paths outside the documented log file location in any log record, on file or console. Diagnostic records SHALL use whitelisted status values, durations, counts, and error categories instead.

#### Scenario: Model-load and trigger records carry no sensitive data
- **WHEN** any log record introduced by this capability is emitted
- **THEN** the record contains only the model repository name, a cached/downloading indicator, elapsed durations, and trigger status — never dictated text, clipboard contents, audio samples, credentials, or a user-specific filesystem path

#### Scenario: Lifecycle diagnostics carry no sensitive data
- **WHEN** any recording, transcription, paste, or hotkey diagnostic record is emitted
- **THEN** it contains only a correlation identifier, event status, configured model name where applicable, elapsed durations, counts, or sanitized error categories — never dictated text, clipboard content, raw audio samples, raw OS output, credentials, an exception traceback, or a user-specific filesystem path
