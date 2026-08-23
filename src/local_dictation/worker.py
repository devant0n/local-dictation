"""Serialized transcription queue, processed on demand from a single thread.

MLX's GPU stream is thread-local and its model-loading / first-inference path proved
unreliable to invoke from a freshly spawned Python thread during development -- it crashed
with "There is no Stream(gpu, N) in current thread" even after explicitly registering a
stream on that thread. Every call made from the main thread, by contrast, has always worked
reliably in this codebase.

So: submit() is thread-safe and can be called from any thread (e.g. the Fn-tap event-tap
thread) -- it just enqueues and never blocks. Actual transcription happens via
process_pending(), which must always be called from the same thread; in the app this is
the main thread, driven by a periodic rumps.Timer (see app.py), or a simple polling loop
in hotkey.py's standalone CLI mode. This keeps clips processed strictly one at a time, in
submission order, without ever touching MLX from more than one thread.
"""

import logging
import queue
import time

import numpy as np

from local_dictation import config
from local_dictation.core import filters
from local_dictation.adapters import paste
from local_dictation.core.transcriber import transcribe_full, unload_model

WARM_UP_SECONDS = 0.5
SAMPLE_RATE = 16_000
log = logging.getLogger(__name__)


def _model_is_cached() -> bool | None:
    """Best-effort check for whether config.MODEL is already in the local HF cache.

    Never raises: an unreliable answer just means the log line omits the cached/downloading
    claim (see design.md's cache-status-detection risk).
    """
    try:
        from huggingface_hub import scan_cache_dir

        return any(repo.repo_id == config.MODEL for repo in scan_cache_dir().repos)
    except Exception:
        return None


class TranscriptionWorker:
    """Serializes transcription: submit() from any thread, process_pending() from one."""

    def __init__(self, on_transcribing=None, on_result=None, on_rejected=None,
                 on_reloading=None, on_failure=None):
        self.on_transcribing = on_transcribing
        self.on_result = on_result
        self.on_rejected = on_rejected
        self.on_reloading = on_reloading  # Called before model reload due to idle unload
        self.on_failure = on_failure
        self._queue: "queue.Queue[tuple[np.ndarray, str | None, int, int | None]]" = queue.Queue()
        self._failed: list[tuple[np.ndarray, str | None, int | None]] = []
        self._warmed_up = False
        self._is_processing = False

    def warm_up(self) -> None:
        """Load the model and run one dummy inference. Call once, from the processing thread."""
        if self._warmed_up:
            return
        cached = _model_is_cached()
        status = "cached" if cached else "not cached, downloading" if cached is False else "status unknown"
        log.info("loading model %s (%s)", config.MODEL, status)
        started = time.monotonic()
        dummy = np.zeros(int(WARM_UP_SECONDS * SAMPLE_RATE), dtype=np.float32)
        transcribe_full(dummy)
        self._warmed_up = True
        log.info("model ready in %.1fs", time.monotonic() - started)

    def unload(self) -> bool:
        """Unload the model from memory to reduce idle footprint."""
        if not self._warmed_up:
            return False
        unload_model()
        self._warmed_up = False
        return True

    def submit(
        self,
        audio: np.ndarray,
        frontmost_app_at_stop: str | None = None,
        recording_id: int | None = None,
    ) -> None:
        """Enqueue a captured clip for transcription. Thread-safe; never blocks.

        `frontmost_app_at_stop` is the app that was focused the moment recording stopped
        (see paste.frontmost_app_identifier()); it's used for the focus-changed paste
        guard once this clip's transcription is ready.
        """
        self._queue.put((audio, frontmost_app_at_stop, 0, recording_id))
        log.info(
            "transcription_queued recording_id=%s queue_depth=%d",
            recording_id,
            self._queue.qsize(),
        )

    def is_processing(self) -> bool:
        """Return whether a transcription is currently in progress."""
        return self._is_processing

    def has_pending(self) -> bool:
        return self._is_processing or not self._queue.empty()

    def failed_count(self) -> int:
        return len(self._failed)

    def retry_failed(self) -> bool:
        if not self._failed:
            return False
        audio, frontmost, recording_id = self._failed.pop(0)
        self._queue.put((audio, frontmost, 0, recording_id))
        log.info("transcription_retry_requested recording_id=%s", recording_id)
        return True

    def discard_failed(self) -> bool:
        if not self._failed:
            return False
        self._failed.pop(0)
        return True

    def process_pending(self) -> None:
        """Process one queued clip, if any is waiting. Call repeatedly from one thread."""
        try:
            audio, frontmost_app_at_stop, retry_count, recording_id = self._queue.get_nowait()
        except queue.Empty:
            return
        self._process(audio, frontmost_app_at_stop, retry_count, recording_id)

    def _process(self, audio: np.ndarray, frontmost_app_at_stop: str | None,
                 retry_count: int = 0, recording_id: int | None = None) -> None:
        self._is_processing = True
        started = time.monotonic()
        log.info(
            "transcription_started recording_id=%s attempt=%d",
            recording_id,
            retry_count + 1,
        )
        try:
            # If model was unloaded (after idle timeout), reload it with a UI cue
            if not self._warmed_up:
                if self.on_reloading:
                    self.on_reloading()
                self.warm_up()

            if self.on_transcribing:
                self.on_transcribing()

            result = transcribe_full(audio)

            text = filters.accepted_text(audio, result)
            if text is None:
                log.info("transcription_rejected recording_id=%s", recording_id)
                if self.on_rejected:
                    self.on_rejected()
                return

            language = result["language"]
            paste_status = paste.paste(text, frontmost_app_at_stop, recording_id=recording_id)
            log.info(
                "transcription_completed recording_id=%s language=%s elapsed_seconds=%.3f paste_status=%s",
                recording_id,
                language,
                time.monotonic() - started,
                paste_status,
            )

            if self.on_result:
                self.on_result(language, text, paste_status)
        except Exception as error:
            if retry_count == 0:
                log.warning(
                    "transcription_failed recording_id=%s attempt=1 error_type=%s retrying=true",
                    recording_id,
                    type(error).__name__,
                )
                self._process(audio, frontmost_app_at_stop, retry_count=1, recording_id=recording_id)
            else:
                log.warning(
                    "transcription_failed recording_id=%s attempt=%d error_type=%s retained=true",
                    recording_id,
                    retry_count + 1,
                    type(error).__name__,
                )
                self._failed.append((audio, frontmost_app_at_stop, recording_id))
                if self.on_failure:
                    self.on_failure(type(error).__name__)
        finally:
            self._is_processing = False
