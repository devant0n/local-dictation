"""Microphone recording into a 16kHz mono float32 buffer for Whisper.

The input stream is opened only for the duration of an actual recording and fully closed
(not merely paused) between recordings, so the microphone is never active while the app is
idle. (v2 originally kept the stream continuously open to support a pre-roll buffer, but
that meant the mic-in-use indicator stayed on for the app's entire runtime -- a real privacy
problem. Pre-roll is fundamentally incompatible with a cold mic, so it was removed rather
than tuned; the resulting stream-startup latency at the start of each recording is an
accepted, unmitigated trade-off.) A recording window is also capped at a maximum duration so
a forgotten toggle doesn't record indefinitely.
"""

import threading

import numpy as np
import sounddevice as sd

from local_dictation import config

SAMPLE_RATE = 16_000
CHANNELS = 1
DTYPE = "float32"


class Recorder:
    """Opens a fresh input stream per recording window; start()/stop() bracket it."""

    def __init__(self) -> None:
        self._chunks: list[np.ndarray] = []
        self._lock = threading.Lock()
        self._stream: sd.InputStream | None = None
        self._recording = False
        self._max_duration_timer: threading.Timer | None = None
        self._on_max_duration_reached = None
        self._callback_count = 0
        self._stream_status_flags: set[str] = set()
        self.last_capture_diagnostics = {"callback_count": 0, "stream_status_flags": ()}

    def _callback(self, indata, frames, time_info, status) -> None:
        chunk = indata.copy().reshape(-1)
        with self._lock:
            self._chunks.append(chunk)
            self._callback_count += 1
            for name in ("input_overflow", "input_underflow", "output_overflow", "output_underflow"):
                if getattr(status, name, False):
                    self._stream_status_flags.add(name)

    def start(self, on_max_duration_reached=None) -> None:
        """Open the microphone and begin a recording window."""
        if self._recording:
            return  # guard against rapid re-toggling calling start() twice

        with self._lock:
            self._chunks = []
            self._callback_count = 0
            self._stream_status_flags = set()

        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            callback=self._callback,
        )
        self._stream.start()
        self._recording = True

        self._on_max_duration_reached = on_max_duration_reached
        if on_max_duration_reached is not None:
            self._max_duration_timer = threading.Timer(
                config.MAX_RECORDING_SECONDS, self._handle_max_duration
            )
            self._max_duration_timer.daemon = True
            self._max_duration_timer.start()

    def _handle_max_duration(self) -> None:
        if self._on_max_duration_reached is not None:
            self._on_max_duration_reached()

    def stop(self) -> np.ndarray:
        """Stop the recording window, close the microphone, and return the captured audio."""
        if not self._recording:
            return np.zeros(0, dtype=np.float32)

        if self._max_duration_timer is not None:
            self._max_duration_timer.cancel()
            self._max_duration_timer = None

        # Stop/close the stream *before* touching _chunks under the lock. stream.stop()
        # blocks until the realtime callback drains, and that callback acquires self._lock
        # -- calling stop() while holding the lock would deadlock. PortAudio guarantees no
        # callback fires after stop() returns, so reading _chunks afterward is safe and
        # captures every chunk, including the last one.
        stream = self._stream
        self._stream = None
        self._recording = False
        if stream is not None:
            stream.stop()
            stream.close()

        with self._lock:
            chunks = self._chunks
            self._chunks = []
            self.last_capture_diagnostics = {
                "callback_count": self._callback_count,
                "stream_status_flags": tuple(sorted(self._stream_status_flags)),
            }

        if not chunks:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(chunks, axis=0).astype(np.float32)
