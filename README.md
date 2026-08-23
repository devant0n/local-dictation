# local-dictation

> **Research preview.** Source-only and experimental; no notarization, PyPI package, or support SLA.
> A local, ad-hoc-signed `.app` build is available (see Install) — nothing is distributed or
> published. Supported baseline: macOS on Apple Silicon with Python 3.13.

A fully local, on-device macOS speech-to-text dictation app. Press **Control+Shift+D** (default,
configurable) to start listening, speak, press it again to stop — the transcription (auto-detected
English or German) is automatically pasted wherever your cursor is, and stays on the clipboard
afterward either way. If auto-paste can't land, a small HUD shows the text near your cursor so
grabbing it is still a single ⌘V away. No cloud, no API keys; transcription runs entirely on-device
via [mlx-whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper).

## Install

```bash
uv sync --all-extras --locked
```

Installs the `local-dictation` and `local-dictation-dictate` console scripts from the committed
lockfile — the same path CI uses. Without [uv](https://docs.astral.sh/uv/), fall back to a plain
venv:

```bash
python3.13 -m venv .venv && source .venv/bin/activate && pip install -e .
```

First run downloads the `whisper-large-v3-turbo` model (~1.61 GB) from Hugging Face; everything
after that is offline.

**Tests:** `pytest tests/unit/ -v` (fast) or `pytest tests/integration/ -v` (full suite, real model
loading). Integration tests use audio fixtures in `fixtures/`; regenerate them with
`./fixtures/generate.sh` if missing.

**App bundle (recommended for actually running the app):** `./scripts/build_app.sh` builds
`dist/local-dictation.app` — an ad-hoc-signed, local-only bundle referencing this environment (no
vendoring, nothing published). Unlike the bare console script, it gives macOS a process identity
that doesn't drift from unrelated system changes, so Activity Monitor and permission grants say
`local-dictation` instead of `Python`, and grants survive a `brew upgrade python@3.13`. They do
**not** survive rebuilding the bundle itself — see Permissions below. Requires the `bundle` extra:
`uv sync --extra bundle --locked`.

## Usage

- **App bundle (recommended):** `open dist/local-dictation.app` after building it (see Install).
  Behaves identically to the console script below; the only difference is process identity.
- **Menu-bar app, development:** run `local-dictation` or `python -m local_dictation.app` directly
  from the venv. Convenient while iterating, but the process appears as the underlying Python
  interpreter to Activity Monitor and TCC — use the app bundle for everyday use. Press the trigger
  combo to start recording (icon turns 🔴; mic is only active while recording), press it again to
  stop — or use **Stop Recording** from the menu if the hotkey is unavailable. The clip is
  transcribed and, if a text field is focused, pasted automatically. A
  notification shows the detected language and a preview. While transcribing, the icon shows an
  hourglass; if processing fails twice, the recording is retained and the menu offers **Retry
  Failed Dictation** or **Discard Failed Dictation**. **Copy Last Dictation** recovers the most
  recent transcription at any time. A live **Status** line shows Input Monitoring state, any
  hotkey-loss interruption, and the outcome of the last paste attempt. If macOS disables the
  event tap while recording, local-dictation stops the recording immediately and transcribes the
  captured portion rather than leaving the microphone active.
- **CLI, fixed-duration recording:** `local-dictation-dictate [seconds]` (default 5s) — records,
  transcribes, copies the result to the clipboard. Simplest way to test the raw pipeline.

## Permissions (macOS)

Three permissions are needed:

- **Microphone** — prompted automatically on first recording; only open while actually recording.
- **Input Monitoring** — needed to observe the trigger combo globally. Not always auto-prompted; if
  the combo does nothing, enable it under **System Settings → Privacy & Security → Input
  Monitoring** for your terminal app or the Python interpreter.
- **Automation** (System Events) — needed for auto-paste, which is synthesized via AppleScript
  rather than a raw keystroke API, since a raw-keystroke approach proved unreliable for an unbundled
  interpreter. Should prompt on first paste; otherwise enable it under **System Settings → Privacy
  & Security → Automation**. If missing, auto-paste fails but the transcription stays on the
  clipboard and the HUD still shows it — or set `AUTO_PASTE = False` in `config.py` to disable
  paste attempts entirely.

If a permission keeps regressing after being granted, it's a macOS code-identity issue: whatever's
running has no stable signed identity, so macOS periodically treats it as a new, ungranted process.
This affects both run paths, for different reasons:

- **Console script:** the venv interpreter's identity can shift (e.g. after `brew upgrade
  python@3.13`), unpredictably breaking a grant that used to work. Confirm which binary needs the
  grant with `python3 -c "import sys, os; print(os.path.realpath(sys.executable))"`.
- **App bundle:** ad-hoc signing (no Apple certificate) derives identity from a hash of the binary
  itself, so **every rebuild of the bundle invalidates its Input Monitoring and Automation grants**,
  even with no source changes. This is predictable (only a rebuild triggers it, not an unrelated
  system update) but not eliminated. After rebuilding, reset and re-grant:
  `tccutil reset ListenEvent com.devant0n.local-dictation && tccutil reset AppleEvents
  com.devant0n.local-dictation`, then fully quit and relaunch the bundle (not just re-toggling the
  checkbox — toggling alone does not re-bind the grant to the new binary).

**Switching from the console script to the app bundle:** the two have separate identities and
therefore separate grants. The first time you run `dist/local-dictation.app`, expect to re-grant all
three permissions even if you'd already granted them to the console script/interpreter.

## Configuration

All tunables live in `config.py` — no code changes needed elsewhere:

| Setting | Default | Purpose |
|---|---|---|
| `TRIGGER` | `"combo"` | `"combo"` (modifier+key) or `"fn"` (bare Fn/Globe tap) |
| `TRIGGER_KEY` / `TRIGGER_MODIFIERS` | `"d"` / `{control, shift}` | Combo backend only; any key + subset of `{control, option, command, shift}` |
| `AUTO_PASTE` | `True` | Synthesize ⌘V after transcribing; `False` copies to clipboard only |
| `MODEL` | `whisper-large-v3-turbo` | mlx-whisper model repo |
| `MAX_RECORDING_SECONDS` | `300` | Safety cap for one recording |
| `IDLE_TIMEOUT_MINUTES` | — | Unload model memory after inactivity; `0` disables |

Diagnostics are written to `~/Library/Logs/local-dictation/local-dictation.log` (or
`LOCAL_DICTATION_LOG_DIR`) and mirrored to stderr. They rotate at 1 MiB with two backups (3 MiB
total), correlate one recording's capture/transcription/paste lifecycle, and never include dictated
text, clipboard content, raw audio, raw OS command output, exception tracebacks, or executable paths.

Debounce and guard thresholds (`COMBO_DEBOUNCE_SECONDS`, `MIN_RECORDING_SECONDS`,
`RMS_SILENCE_THRESHOLD`, `NO_SPEECH_PROB_THRESHOLD`, `AVG_LOGPROB_THRESHOLD`,
`COMPRESSION_RATIO_THRESHOLD`) are also tunable there if real-world use suggests different defaults.

**Fn/Globe key backend:** set `TRIGGER = "fn"` for a bare Fn tap instead of a combo. First disable
macOS's own Fn dictation shortcut (**System Settings → Keyboard → Dictation → Shortcut → Off**) so
it doesn't race this app's toggle; tune detection via `FN_TAP_HOLD_WINDOW_SECONDS` /
`FN_TAP_DEBOUNCE_SECONDS`.

## Privacy and diagnostics

Audio and transcription are processed locally; the only outbound network access is the first model
download. No telemetry, accounts, or API keys. Dictated text remains on the clipboard after use.
Diagnostic logs go to `~/Library/Logs/local-dictation/` (or `LOCAL_DICTATION_LOG_DIR`) and mirror to
the terminal (stderr) so startup and model loading are visible instead of appearing to hang — never
containing dictated text. Set `LOCAL_DICTATION_LOG_LEVEL` (default `INFO`) to change verbosity.

## Releases

Conventional Commits (`fix:` patch, `feat:` minor, `feat!:`/`BREAKING CHANGE:` major) on merge to
protected `main` trigger Python Semantic Release, which creates a Git tag and GitHub release.
Source-only — no PyPI package or app bundle is published. Inspect the next version locally with:

```bash
semantic-release --noop version
```

## Limitations

- Batch transcription only (record fully, then transcribe) — no live streaming.
- One language per utterance — no mid-sentence English/German code-switching.
- The mic is only active during a recording, so there's a small, unmitigated stream-startup latency
  at the start of each recording (a pre-roll buffer was tried and removed — it required keeping the
  mic continuously active, which is worse).
- No automatic clipboard restore — dictated text stays on the clipboard after a dictation rather
  than reverting to what was there before.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`AGENTS.md`](AGENTS.md) for the branch/PR workflow,
spec-alignment rules, and testing conventions.
