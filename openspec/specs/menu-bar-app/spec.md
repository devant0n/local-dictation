## Purpose

The macOS menu-bar shell that hosts the status icon, wires the global hotkey to the
dictation pipeline, and surfaces recording state, status, and completion feedback to the
user.
## Requirements
### Requirement: Menu-bar presence
The system SHALL run as a macOS menu-bar app with a status icon, providing a persistent,
low-footprint presence while active.

#### Scenario: App launched
- **WHEN** the app is started
- **THEN** a status icon appears in the macOS menu bar and remains visible while the app
  runs

### Requirement: Visual recording state indicator
The system SHALL visually change the status icon while audio is being recorded, and
revert it to the idle appearance once recording stops.

#### Scenario: Icon changes when recording starts via toggle
- **WHEN** the user toggles the trigger and recording starts
- **THEN** the menu-bar icon changes to a distinct "recording" appearance

#### Scenario: Icon reverts after recording
- **WHEN** the user toggles the trigger again and the recorded clip has been handed off for
  transcription
- **THEN** the menu-bar icon shows the transcribing appearance until no queued transcription
  remains

### Requirement: Completion feedback
The system SHALL notify the user of a dictation's outcome, using a real system
notification only for infrequent, actionable exceptions rather than every completion (see
"Brief completion flash on the status icon" below for the common/successful case).

#### Scenario: Focus changed before paste
- **WHEN** the frontmost application changed between recording stopping and the
  transcription being ready to paste
- **THEN** the system shows a notification explaining that the paste was skipped and the
  text is on the clipboard

#### Scenario: Paste permission problem
- **WHEN** a paste attempt fails due to a missing permission
- **THEN** the system shows a notification explaining that a permission is needed, and
  that the text is on the clipboard

### Requirement: Brief completion flash on the status icon
The system SHALL briefly flash a distinct glyph on the menu-bar icon to indicate a
dictation's outcome — a success indicator when a clip is accepted (whether or not
auto-paste itself landed), and a distinct no-speech indicator when a clip is rejected as
containing no speech — before reverting to the idle appearance after a short delay. Real
notifications are reserved for the infrequent, actionable exceptions covered by
"Completion feedback" above.

#### Scenario: Successful dictation flashes success
- **WHEN** a dictation completes and is accepted
- **THEN** the menu-bar icon briefly shows a success glyph, then reverts to idle, without a
  system notification

#### Scenario: No-speech clip flashes distinctly
- **WHEN** a dictation is rejected for containing no speech
- **THEN** the menu-bar icon briefly shows a distinct no-speech glyph, then reverts to
  idle, without a system notification

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

### Requirement: App quit control
The system SHALL provide a menu item that quits the application.

#### Scenario: User quits from menu
- **WHEN** the user clicks the status icon and selects the quit menu item
- **THEN** the app terminates and the status icon is removed from the menu bar

### Requirement: Independent recording stop control
The system SHALL provide a menu-bar control that stops an active recording without requiring the global hotkey. The control SHALL only be available while recording and SHALL use the same recording finalization behavior as a normal hotkey stop.

#### Scenario: Stop recording from menu
- **WHEN** the user selects Stop Recording while an active recording is shown
- **THEN** the microphone closes, the clip is handed off for transcription once, and the control is no longer available

### Requirement: Visual transcription and failure state
The system SHALL show a distinct menu-bar state while one or more recordings are transcribing and
another distinct state when a recoverable transcription failure is awaiting user action.

#### Scenario: Recording handed off for transcription
- **WHEN** recording stops and a clip is queued or being transcribed
- **THEN** the status icon shows the transcribing state until no queued transcription remains

#### Scenario: Recoverable failure is retained
- **WHEN** transcription still fails after its automatic retry
- **THEN** the status icon and status line identify the failure and available recovery action

### Requirement: Descriptive process identity

The macOS `.app` bundle SHALL identify itself as `local-dictation` to both process-level tooling
(`ps`) and macOS's process-identity-based UI (Activity Monitor's Process Name column). The
development-only console-script entry point SHALL continue to identify itself as `local-dictation` to
`ps` via argv, without asserting an Activity Monitor claim for that path.

#### Scenario: App is running

- **WHEN** the `.app` bundle is launched
- **THEN** `ps` reports its process name (`comm` and `ucomm`) as `local-dictation`, and Activity
  Monitor's Process Name column shows `local-dictation`

#### Scenario: Kernel-level process name may still differ

- **WHEN** the app is launched via the `local-dictation` console script or
  `python -m local_dictation.app` from a source checkout, without the `.app` bundle
- **THEN** `ps` reports its process name (`comm`) as `local-dictation`, but macOS tools that read the
  exec'd binary's identity rather than argv (e.g. Activity Monitor's Process Name column) show the
  underlying interpreter instead — expected for this development-only path, not a defect

### Requirement: App bundle build

The project SHALL provide a committed script that builds a macOS `.app` bundle in py2app alias mode
(referencing the project's installed environment, vendoring nothing) and ad-hoc signs it with a
fixed, stable bundle identifier.

#### Scenario: Bundle is built

- **WHEN** a developer runs the committed build script on a checkout with dependencies installed
- **THEN** a `local-dictation.app` bundle is produced, ad-hoc signed with the identifier
  `com.devant0n.local-dictation`, and the identifier does not change between builds

#### Scenario: Bundle does not vendor the runtime

- **WHEN** the bundle is built
- **THEN** it references the existing Python environment in alias mode rather than freezing or
  vendoring the interpreter, mlx/Metal libraries, or other dependencies

#### Scenario: Rebuilding invalidates TCC grants (documented limitation)

- **WHEN** the bundle is rebuilt, including with no source changes
- **THEN** ad-hoc signing (no Apple-issued certificate) derives the bundle's code identity from a
  hash of its contents, so the rebuilt binary is a distinct, ungranted identity to macOS even though
  its `CFBundleIdentifier` string is unchanged — any previously granted Input Monitoring or
  Automation permission stops working until reset (`tccutil reset`) and re-granted; this is verified
  behavior, documented in the README, not a defect to silently discover

