"""Tunable configuration for local-dictation v2."""

import logging
import os
import sys
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path

import tqdm

# Must be set before huggingface_hub/mlx_whisper are imported anywhere, so import this
# module before importing transcriber/mlx_whisper. Silences the "Fetching N files"
# progress bar noise.
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")

# Store diagnostics outside the installed package and never log dictation/clipboard text.
# Set LOCAL_DICTATION_LOG_DIR for an explicit location; otherwise use the conventional
# per-user macOS log directory. Set LOCAL_DICTATION_LOG_LEVEL (e.g. "DEBUG") to change
# verbosity on both the file and the console; an unrecognized value falls back to INFO
# rather than raising before the app has even started.
LOG_DIR = Path(os.environ.get("LOCAL_DICTATION_LOG_DIR", "~/Library/Logs/local-dictation")).expanduser()
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "local-dictation.log"
LOG_MAX_BYTES = 1 * 1024 * 1024
LOG_BACKUP_COUNT = 2
LOG_LEVEL = getattr(logging, os.environ.get("LOCAL_DICTATION_LOG_LEVEL", "INFO").upper(), logging.INFO)
logging.basicConfig(
    handlers=[
        RotatingFileHandler(
            LOG_FILE,
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8",
        ),
        logging.StreamHandler(sys.stderr),
    ],
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    force=True,
)
# Quiet down third-party libraries (httpx/huggingface_hub make INFO-level HTTP request
# logs that would otherwise bury the diagnostics this file exists for) without affecting
# our own modules, which all log at INFO via the root config above.
for _noisy_logger in ("httpx", "httpcore", "urllib3", "huggingface_hub", "filelock"):
    logging.getLogger(_noisy_logger).setLevel(logging.WARNING)

# Neutralize tqdm's multiprocessing lock to prevent resource_tracker warnings on shutdown.
# tqdm lazily creates a multiprocessing.RLock the first time an instance is created (even
# if disabled). This pre-sets a threading.RLock so the multiprocessing semaphore is never
# created, preventing the "leaked semaphore" warning when the app exits via Cocoa's
# NSApp.terminate_() which skips normal Python atexit cleanup.
tqdm.tqdm.set_lock(threading.RLock())

# Trigger: "combo" (default) is a configurable modifier+key combo, matched via a
# CGEventTap -- see trigger.py's ComboTrigger. "fn" is also available (FnTapTrigger,
# bare Fn-key tap) for anyone who wants it back. The string is a seam for future
# "mouse:<button>" backends too.
TRIGGER = "combo"

# Only used when TRIGGER == "combo". TRIGGER_KEY is a single letter/number key (see
# trigger.py's keycode table); TRIGGER_MODIFIERS is any subset of
# {"control", "option", "command", "shift"}. Default is an uncommon 4-key chord unlikely
# to collide with existing system/app shortcuts.
TRIGGER_KEY = "d"
TRIGGER_MODIFIERS = {"control", "shift"}

# Auto-paste the transcription into the frontmost app (Cmd+V) after copying to clipboard.
# When False, behavior matches v1: clipboard only.
AUTO_PASTE = True

MODEL = "mlx-community/whisper-large-v3-turbo"

# --- Fn bare-tap discrimination (only used if TRIGGER == "fn") ---
# A Fn press/release is only treated as a toggle if released within this window and with
# no other key pressed in between (see trigger.py FnTapTrigger).
FN_TAP_HOLD_WINDOW_SECONDS = 0.5
FN_TAP_DEBOUNCE_SECONDS = 0.2

# --- Combo trigger debounce (only used if TRIGGER == "combo") ---
# Prevents OS key-repeat (holding the combo down) from toggling more than once per press.
COMBO_DEBOUNCE_SECONDS = 0.3

# --- Capture hardening ---
# No pre-roll: the mic is only ever open during an active recording (see recorder.py).
MAX_RECORDING_SECONDS = 5 * 60

# --- Hallucination / short-clip guards ---
MIN_RECORDING_SECONDS = 0.3
RMS_SILENCE_THRESHOLD = 0.008
NO_SPEECH_PROB_THRESHOLD = 0.6
AVG_LOGPROB_THRESHOLD = -1.0
COMPRESSION_RATIO_THRESHOLD = 2.4

# --- Paste timing ---
# No restore delay: the dictated text is left on the clipboard after pasting rather than
# restoring the prior clipboard value, since there's no reliable signal for when the
# target app has actually consumed the paste -- a fixed-delay restore is a race condition
# (confirmed in real use: it can overwrite the clipboard before the target reads it,
# causing stale text to be pasted instead of the dictation). See paste.py.
CLIPBOARD_WRITE_SETTLE_SECONDS = 0.05

# --- Idle-unload lifecycle ---
# Unload the model from memory after N minutes of inactivity (no transcription requests).
# Reduces time-averaged footprint for bursty-usage patterns. Set to 0 to disable idle-unload
# (keeps model resident indefinitely, original v2 behavior). Can be adjusted at runtime for
# different balance between memory savings (lower values) and reload convenience (higher values).
IDLE_TIMEOUT_MINUTES = 10
