"""Regression tests for serialized recording control."""

from unittest.mock import MagicMock, patch

import numpy as np

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
