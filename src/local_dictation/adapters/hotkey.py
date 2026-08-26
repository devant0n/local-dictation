"""Toggle-driven dictation controller: the configured trigger starts recording, the
next trigger stops it and hands the clip off for transcription.

This module only owns the recording toggle lifecycle. Transcription runs in worker.py's
serialized background queue -- DictationController just calls on_clip_ready(audio) with
the finished clip and doesn't know or care how it gets transcribed.

Requires macOS Input Monitoring and Accessibility permission for the trigger's event tap
(see trigger.py), and Microphone permission for audio capture. See README.md for setup.
"""

import logging
import time

from .recorder import Recorder

log = logging.getLogger(__name__)


class DictationController:
    """Owns the toggle -> record -> hand-off flow, with optional UI hooks."""

    def __init__(
        self,
        on_recording_start=None,
        on_recording_stop=None,
        on_clip_ready=None,
        on_capture_failure=None,
        control_dispatch=None,
    ):
        self.recorder = Recorder()
        self._recording = False
        self._recording_id = 0
        self._recording_started_at: float | None = None
        self.on_recording_start = on_recording_start
        self.on_recording_stop = on_recording_stop
        self.on_clip_ready = on_clip_ready
        self.on_capture_failure = on_capture_failure
        self._control_dispatch = control_dispatch or (lambda callback: callback())

    @property
    def recording(self) -> bool:
        return self._recording

    @property
    def recording_id(self) -> int | None:
        return self._recording_id if self._recording else None

    def toggle(self) -> bool:
        """Called once per trigger activation: starts recording, or stops it if already
        recording."""
        if self._recording:
            return self.stop("hotkey")
        return self._start()

    def _start(self) -> bool:
        """Start a recording. Call only from the serialized app control thread."""
        if self._recording:
            return False

        recording_id = self._recording_id + 1
        try:
            self.recorder.start(
                on_max_duration_reached=lambda: self._control_dispatch(
                    lambda: self.stop("maximum_duration")
                )
            )
        except Exception as error:
            log.warning(
                "recording_start_failed recording_id=%d error_type=%s",
                recording_id,
                type(error).__name__,
            )
            return False

        self._recording_id = recording_id
        self._recording = True
        self._recording_started_at = time.monotonic()
        log.info("recording_started recording_id=%d", recording_id)
        if self.on_recording_start:
            self.on_recording_start(recording_id)
        return True

    def stop(self, reason: str) -> bool:
        """Finalize an active recording once, regardless of which stop source won."""
        if not self._recording:
            log.info("recording_stop_ignored reason=%s state=inactive", reason)
            return False

        recording_id = self._recording_id
        self._recording = False
        started_at = self._recording_started_at
        self._recording_started_at = None
        duration_seconds = 0.0 if started_at is None else time.monotonic() - started_at
        log.info(
            "recording_stopping recording_id=%d reason=%s duration_seconds=%.3f",
            recording_id,
            reason,
            duration_seconds,
        )
        try:
            audio = self.recorder.stop()
        except Exception as error:
            log.warning(
                "recording_capture_failed recording_id=%d stage=capture error_type=%s",
                recording_id,
                type(error).__name__,
            )
            if self.on_recording_stop:
                self.on_recording_stop(recording_id, reason)
            if self.on_capture_failure:
                self.on_capture_failure(recording_id, "capture", type(error).__name__)
            return False

        capture = getattr(self.recorder, "last_capture_diagnostics", {})
        log.info(
            "recording_captured recording_id=%d duration_seconds=%.3f sample_count=%d "
            "rms=%.6f callback_count=%d stream_status_flags=%s",
            recording_id,
            duration_seconds,
            int(audio.size),
            float((audio ** 2).mean() ** 0.5) if audio.size else 0.0,
            int(capture.get("callback_count", 0)),
            ",".join(capture.get("stream_status_flags", ())) or "none",
        )
        if self.on_recording_stop:
            self.on_recording_stop(recording_id, reason)
        if self.on_clip_ready:
            try:
                self.on_clip_ready(audio, recording_id, reason)
            except Exception as error:
                log.warning(
                    "recording_capture_failed recording_id=%d stage=handoff error_type=%s",
                    recording_id,
                    type(error).__name__,
                )
                if self.on_capture_failure:
                    self.on_capture_failure(recording_id, "handoff", type(error).__name__)
                return False
        log.info("recording_stopped recording_id=%d reason=%s", recording_id, reason)
        return True


def main() -> None:
    """Standalone smoke test: the configured trigger toggles recording; transcription runs
    on this (main) thread via a simple polling loop, matching app.py's rumps.Timer
    approach."""
    import time

    import config
    import paste as paste_module
    from trigger import create_trigger
    from worker import TranscriptionWorker

    def on_result(lang, text, paste_status):
        print(f"[{lang}] {text}\n(paste: {paste_status})")

    print("Loading model...")
    worker = TranscriptionWorker(
        on_transcribing=lambda: print("transcribing..."),
        on_result=on_result,
        on_rejected=lambda reason: print(f"(dictation rejected: {reason})"),
    )
    worker.warm_up()

    print(f"Trigger: {config.TRIGGER}. Activate it to start recording, again to stop. Ctrl+C to quit.")
    controller = DictationController(
        on_recording_start=lambda _recording_id: print("recording started..."),
        on_recording_stop=lambda _recording_id, _reason: print("recording stopped."),
        on_clip_ready=lambda audio, recording_id, _reason: worker.submit(
            audio, paste_module.frontmost_app_identifier(), recording_id
        ),
    )
    trigger = create_trigger(on_toggle=controller.toggle)
    trigger.start()
    try:
        while True:
            worker.process_pending()
            time.sleep(0.05)
    except KeyboardInterrupt:
        trigger.stop()


if __name__ == "__main__":
    main()
