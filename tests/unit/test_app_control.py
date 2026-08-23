"""Tests for main-thread handoff from the global hotkey callback."""

from unittest.mock import MagicMock, patch

from local_dictation.app import DictationApp


def test_hotkey_callback_only_schedules_main_thread_work():
    app = object.__new__(DictationApp)
    with patch("local_dictation.app.AppHelper.callAfter") as call_after:
        app._dispatch_hotkey_toggle()

    call_after.assert_called_once_with(app._handle_hotkey_toggle)


def test_tap_loss_callback_only_schedules_main_thread_recovery():
    app = object.__new__(DictationApp)
    with patch("local_dictation.app.AppHelper.callAfter") as call_after:
        app._dispatch_tap_disabled("timeout")

    call_after.assert_called_once_with(app._handle_tap_disabled, "timeout")


def test_tap_reenabled_callback_only_schedules_main_thread_diagnostics():
    app = object.__new__(DictationApp)
    with patch("local_dictation.app.AppHelper.callAfter") as call_after:
        app._dispatch_tap_reenabled("timeout")

    call_after.assert_called_once_with(app._handle_tap_reenabled, "timeout")


def test_tap_loss_stops_active_recording_once_and_surfaces_feedback():
    app = object.__new__(DictationApp)
    app.controller = MagicMock()
    app.controller.stop.return_value = True
    app._show_steady_state = MagicMock()

    with patch("local_dictation.app.rumps.notification") as notification:
        app._handle_tap_disabled("timeout")

    app.controller.stop.assert_called_once_with("hotkey_unavailable")
    notification.assert_called_once()
    app._show_steady_state.assert_called_once()
    assert app._last_hotkey_issue == "recording stopped — hotkey unavailable"
