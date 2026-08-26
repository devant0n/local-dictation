## 1. Recording control and recovery

- [x] 1.1 Dispatch accepted hotkey events to the app control thread and report tap availability changes without blocking the event-tap callback.
- [x] 1.2 Serialize all recording stop sources, add immediate tap-loss stopping, and expose an idempotent menu stop action.
- [x] 1.3 Update menu state, status feedback, and user-facing documentation for independent stop and hotkey-loss recovery.

## 2. Privacy-safe diagnostics

- [x] 2.1 Configure bounded file-log rotation and replace unsafe raw path, subprocess, and exception diagnostics with whitelisted metadata.
- [x] 2.2 Add correlated capture, queue, transcription, retry, paste, and idle-unload lifecycle diagnostics.

## 3. Verification

- [x] 3.1 Add deterministic tests for event-tap dispatch, tap-loss finalization, menu stop, serialized stops, and menu state.
- [x] 3.2 Add diagnostics and retention regression tests, then run OpenSpec validation, focused tests, the unit suite, and Ruff.

## 4. Complete terminal diagnostics

- [x] 4.1 Record capture metrics and stream-status summaries, and report start, stop, handoff, and duplicate-stop failures through correlated content-free records.
- [x] 4.2 Return explicit filtering rejection reasons; record operational stage/error categories without retrying UI callback failures; surface the latest non-success outcome in status.
- [x] 4.3 Add privacy regression tests for all terminal outcomes, update diagnostics documentation, and run the full automated and real-fixture suites.
