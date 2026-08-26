# logging-diagnostics Specification

## Purpose
Defines what local-dictation logs, where diagnostics are emitted (file and console), the default
verbosity and how it is configured, and the privacy constraints on log content, so startup and
model-loading progress are observable without exposing sensitive data.
## Requirements
### Requirement: Console mirrors file diagnostics by default
The system SHALL emit its diagnostic log records to the process's standard error stream, in addition
to the existing log file, without requiring any flag or environment variable to enable it.

#### Scenario: Running from a terminal shows live diagnostics
- **WHEN** a user starts `local-dictation` or `local-dictation-dictate` from a terminal
- **THEN** log records appear on stderr as they are emitted, and the same records are also written to
  the log file at `~/Library/Logs/local-dictation/local-dictation.log` (or
  `$LOCAL_DICTATION_LOG_DIR` if set)

### Requirement: Console diagnostics never appear on stdout
The system SHALL NOT write log records to standard output.

#### Scenario: CLI output stays pipeable
- **WHEN** a user runs `local-dictation-dictate | some-other-command`
- **THEN** only the CLI's own transcription-result output (language, text, clipboard confirmation)
  reaches the pipe, with no log records mixed in

### Requirement: Log verbosity is configurable via environment variable
The system SHALL read a `LOCAL_DICTATION_LOG_LEVEL` environment variable to set the minimum level of
records emitted to both the file and the console, defaulting to `INFO` when unset.

#### Scenario: Default verbosity
- **WHEN** `LOCAL_DICTATION_LOG_LEVEL` is not set
- **THEN** the system logs at `INFO` level and above to both file and console

#### Scenario: Custom verbosity
- **WHEN** `LOCAL_DICTATION_LOG_LEVEL=DEBUG` is set in the environment before startup
- **THEN** the system logs at `DEBUG` level and above to both file and console

### Requirement: Model load progress is observable
The system SHALL log, for the Whisper model load performed during startup, a record naming the
configured model and indicating whether it is already present in the local cache or is being
downloaded, and a record on completion stating the elapsed load time.

#### Scenario: Cold cache
- **WHEN** the configured model is not yet present in the local model cache and `warm_up()` runs
- **THEN** a log record is emitted before loading begins, naming the model and indicating it is being
  downloaded, and a log record is emitted after loading completes, stating the elapsed time

#### Scenario: Warm cache
- **WHEN** the configured model is already present in the local model cache and `warm_up()` runs
- **THEN** a log record is emitted before loading begins, naming the model and indicating it is
  cached, and a log record is emitted after loading completes, stating the elapsed time

### Requirement: Trigger-armed confirmation is observable
The system SHALL log a record once the global-hotkey trigger has started successfully, confirming the
app is ready to receive the hotkey.

#### Scenario: App startup completes
- **WHEN** the app finishes starting and the global-hotkey trigger begins listening
- **THEN** a log record is emitted confirming the trigger is armed

### Requirement: Dictation lifecycle diagnostics
The system SHALL record privacy-safe local diagnostics for recording start and stop, stop reason, ignored duplicate stops, hotkey dispatch and availability, microphone stream outcomes, queueing, model reload, transcription completion or rejection, retry, retained failure, paste outcome, and idle unload. Records belonging to one recording SHALL share a non-content correlation identifier. Each completed capture SHALL record duration, sample count, RMS level, callback count, and recognized stream-status flags. Each rejection SHALL record a reason code; each operational failure SHALL record its stage and sanitized error type.

#### Scenario: Transcription failure is investigated
- **WHEN** transcription fails and its automatic retry is exhausted
- **THEN** the local log identifies the affected recording, lifecycle phase, retry outcome, and sanitized error category without containing dictated text, audio, clipboard content, raw exception text, or a filesystem path

#### Scenario: Short or quiet capture is rejected
- **WHEN** a completed capture is below the configured duration or RMS threshold
- **THEN** the local log identifies the recording, exact capture metrics, and `too_short` or `too_quiet` reason without containing audio or dictated text

#### Scenario: Capture handoff fails
- **WHEN** microphone finalization or clip handoff fails
- **THEN** the local log identifies the recording, `capture` or `handoff` stage, and sanitized error type; the menu-bar status exposes the non-success outcome

### Requirement: Bounded local diagnostic retention
The system SHALL retain at most 3 MiB of local diagnostic log data through rotation, while console diagnostics continue to mirror emitted records.

#### Scenario: Log reaches the rotation threshold
- **WHEN** the active diagnostic log reaches its configured 1 MiB threshold
- **THEN** it rotates while retaining the active file and at most two prior files

### Requirement: Diagnostics never include sensitive content
The system SHALL NOT include transcribed text, clipboard content, raw audio data, raw OS command output, credentials, unfiltered exception messages or tracebacks, or filesystem paths outside the documented log file location in any log record, on file or console. Diagnostic records SHALL use whitelisted status values, durations, counts, and error categories instead.

#### Scenario: Model-load and trigger records carry no sensitive data
- **WHEN** any log record introduced by this capability is emitted
- **THEN** the record contains only the model repository name, a cached/downloading indicator, elapsed durations, and trigger status — never dictated text, clipboard contents, audio samples, credentials, or a user-specific filesystem path

#### Scenario: Lifecycle diagnostics carry no sensitive data
- **WHEN** any recording, transcription, paste, or hotkey diagnostic record is emitted
- **THEN** it contains only a correlation identifier, event status, configured model name where applicable, elapsed durations, counts, or sanitized error categories — never dictated text, clipboard content, raw audio samples, raw OS output, credentials, an exception traceback, or a user-specific filesystem path

