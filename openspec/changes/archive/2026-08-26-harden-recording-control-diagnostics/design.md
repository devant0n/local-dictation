## Context

The trigger's Quartz callback currently invokes the complete recording toggle lifecycle, including microphone start and stop. The duration-cap timer can also call that lifecycle from a separate thread. The app already has a main-thread run loop and a file/console logging boundary, but no per-recording correlation or hotkey-loss callback.

## Goals / Non-Goals

**Goals:**

- Keep event-tap callbacks bounded and make every recording stop source idempotent.
- Stop active recording immediately on event-tap loss, while retaining tap re-enablement for later use.
- Make incidents diagnosable with bounded, local, content-free records.

**Non-Goals:**

- Replace the Quartz trigger backend, alter the configured shortcut, add telemetry, or lower the five-minute maximum duration.

## Decisions

- **Main-thread control dispatch:** the app passes a lightweight dispatcher to the trigger; it only schedules recording actions on the Cocoa main thread. This avoids latency-sensitive event-tap work without moving MLX inference off its established main-thread execution path. A dedicated control thread was rejected because it would introduce another state owner and Cocoa marshaling boundary.
- **Single public stop operation:** the controller exposes an idempotent stop action with a reason. Hotkey, menu, duration-cap, and tap-loss paths use it. The duration timer schedules rather than directly executing the stop, eliminating cross-thread finalization races.
- **Tap loss is fail-safe:** disable detection logs the reason, schedules immediate stop if active, then re-enables the event tap. This follows the selected privacy preference over preserving a recording that cannot be reliably stopped by its primary control.
- **Correlation and sanitization:** a monotonic recording ID flows from capture to worker and paste diagnostics. Logs use an explicit whitelist of metadata; raw subprocess output, executable paths, error values, and exception tracebacks are replaced by categories. A rotating file handler keeps the active 1 MiB log plus two backups.
- **Terminal outcome evidence:** every capture records its duration, sample count, RMS level, callback count, and recognized stream-status flags. Filtering returns a non-content reason code for every rejection. Worker failures identify the operational stage and sanitized error type; UI callback failures are recorded separately and never trigger another transcription attempt.
- **Status presentation:** a Stop Recording item is enabled only while active. A hotkey-loss status remains visible until the next accepted hotkey request, so recovery is not hidden by immediate event-tap re-enablement.

## Risks / Trade-offs

- [Main-thread stream stop briefly delays the menu UI] → keep control work limited to existing stream-finalization behavior and return the event-tap callback first.
- [Tap-loss false positives truncate dictation] → this is the selected immediate-stop policy; retain the finalized partial clip for normal transcription.
- [More metadata still reveals use patterns] → retain only 3 MiB locally and log no content, paths, raw output, or raw exception data.
- [Exact capture metrics reveal limited usage patterns] → the user selected exact duration, sample-count, and RMS records because they are necessary to tune the short/quiet thresholds; bounded local retention remains in force.
- [Tests cannot trigger real TCC/event-tap failures] → inject callbacks and mock the recorder, dispatcher, Quartz status, and logging handlers in deterministic tests; perform a manual macOS smoke check.
