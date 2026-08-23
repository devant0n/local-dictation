## Why

The recording-stop hotkey can become unavailable while the microphone remains active, and current diagnostics cannot distinguish that failure from capture or transcription failures. The app needs a reliable, privacy-safe recovery path and enough local evidence to diagnose a recurrence.

## What Changes

- Dispatch recording control off the macOS event-tap callback and serialize hotkey, menu, and duration-cap stops.
- Stop an active recording immediately when the event tap is disabled; retain automatic re-enablement for later recordings.
- Add a menu-bar Stop Recording action and clear degraded-status feedback.
- Add correlated, privacy-safe local diagnostics for recording, transcription, retry, paste, and idle-unload lifecycles; rotate the log at 3 MiB total retention.
- Remove unsafe path and raw subprocess/error values from diagnostic records.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `global-hotkey`: hotkey actions must not block the event-tap callback, and tap loss must safely end active recording.
- `menu-bar-app`: users must be able to stop recording independently of the global hotkey and see a hotkey-loss outcome.
- `dictation-pipeline`: all recording-stop sources must finalize a clip through one serialized path.
- `logging-diagnostics`: local diagnostics must cover lifecycle outcomes and use bounded, privacy-safe retention.

## Impact

Updates the trigger, recorder/controller, menu-bar shell, worker, paste diagnostics, logging setup, specs, README, and unit/integration coverage. No cloud service, telemetry, new dependency, or public network API is introduced.
