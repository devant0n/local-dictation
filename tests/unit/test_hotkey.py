"""Regression tests for serialized recording control."""

from unittest.mock import MagicMock, patch

import numpy as np
import logging

from local_dictation.adapters.hotkey import DictationController


@patch("local_dictation.adapters.hotkey.Recorder")
def test_duration_cap_schedules_the_same_stop_path(mock_recorder_class):
    recorder = mock_recorder_class.return_value
    recorder.stop.return_value = np.zeros(10, dtype=np.float32)
    scheduled = []
    clip_ready = MagicMock()
    controller = DictationController(
        on_clip_ready=clip_ready,
        control_dispatch=scheduled.append,
    )

    assert controller.toggle() is True
    cap_callback = recorder.start.call_args.kwargs["on_max_duration_reached"]
    cap_callback()

    assert len(scheduled) == 1
    scheduled.pop()()
    assert controller.recording is False
    recorder.stop.assert_called_once()
    clip_ready.assert_called_once()
    assert controller.stop("menu") is False


@patch("local_dictation.adapters.hotkey.Recorder")
def test_stop_reason_and_recording_id_are_forwarded_once(mock_recorder_class):
    recorder = mock_recorder_class.return_value
    recorder.stop.return_value = np.zeros(10, dtype=np.float32)
    stopped = MagicMock()
    clip_ready = MagicMock()
    controller = DictationController(on_recording_stop=stopped, on_clip_ready=clip_ready)

    controller.toggle()
    assert controller.stop("hotkey_unavailable") is True

    stopped.assert_called_once_with(1, "hotkey_unavailable")
    clip_ready.assert_called_once_with(recorder.stop.return_value, 1, "hotkey_unavailable")


@patch("local_dictation.adapters.hotkey.Recorder")
def test_capture_failure_is_logged_and_reported(mock_recorder_class, caplog):
    recorder = mock_recorder_class.return_value
    recorder.stop.side_effect = RuntimeError("secret /path")
    capture_failure = MagicMock()
    controller = DictationController(on_capture_failure=capture_failure)

    with caplog.at_level(logging.INFO, logger="local_dictation.adapters.hotkey"):
        controller.toggle()
        assert controller.stop("menu") is False

    capture_failure.assert_called_once_with(1, "capture", "RuntimeError")
    messages = [record.message for record in caplog.records]
    assert any("recording_capture_failed recording_id=1 stage=capture error_type=RuntimeError" in message for message in messages)
    assert all("secret" not in message and "/path" not in message for message in messages)


@patch("local_dictation.adapters.hotkey.Recorder")
def test_duplicate_stop_is_logged(mock_recorder_class, caplog):
    recorder = mock_recorder_class.return_value
    recorder.stop.return_value = np.zeros(10, dtype=np.float32)
    controller = DictationController()

    with caplog.at_level(logging.INFO, logger="local_dictation.adapters.hotkey"):
        controller.toggle()
        controller.stop("menu")
        assert controller.stop("menu") is False

    assert any("recording_stop_ignored reason=menu state=inactive" in record.message for record in caplog.records)
