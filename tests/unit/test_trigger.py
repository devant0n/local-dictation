"""Tests for Quartz event-tap availability callbacks."""

from unittest.mock import patch

import Quartz

from local_dictation.adapters.trigger import ComboTrigger


def test_tap_timeout_reports_recovery_without_touching_recording_control():
    disabled = []
    reenabled = []
    trigger = ComboTrigger(
        lambda: None,
        "d",
        {"control"},
        on_tap_disabled=disabled.append,
        on_tap_reenabled=reenabled.append,
    )
    trigger._tap = object()

    with patch("local_dictation.adapters.trigger.Quartz.CGEventTapEnable") as enable:
        trigger._handle_event(None, Quartz.kCGEventTapDisabledByTimeout, None, None)

    assert disabled == ["timeout"]
    assert reenabled == ["timeout"]
    enable.assert_called_once_with(trigger._tap, True)
