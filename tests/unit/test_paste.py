"""Tests for the osascript-based paste synthesis, in particular non-ASCII stderr handling."""

import subprocess
import unittest.mock as mock

from local_dictation.adapters import paste


def test_synthesize_paste_pins_encoding_to_survive_non_ascii_stderr():
    """Without an explicit encoding/errors, subprocess.run(text=True) decodes via
    locale.getpreferredencoding(), which is plain ASCII when this process has no inherited
    shell locale (e.g. launched as a GUI .app rather than from a terminal). A localized
    (non-English) permission-denial message from osascript would then raise
    UnicodeDecodeError before classification ever runs. This fake reproduces that: it
    raises the same error subprocess.run itself would raise if called without pinning
    encoding="utf-8", errors="replace"."""
    non_ascii_stderr = "„System Events“ ist nicht berechtigt (-1743)"

    def fake_run(*args, **kwargs):
        if kwargs.get("encoding") != "utf-8" or kwargs.get("errors") != "replace":
            non_ascii_stderr.encode("utf-8").decode("ascii")  # raises UnicodeDecodeError
        return subprocess.CompletedProcess(
            args=["osascript"], returncode=1, stdout="", stderr=non_ascii_stderr
        )

    with mock.patch("subprocess.run", side_effect=fake_run):
        success, error = paste._synthesize_cmd_v_osascript()

    assert success is False
    assert error == "permission"


def test_synthesize_paste_classifies_non_ascii_permission_error():
    """The full paste() pipeline should classify a non-ASCII permission-denial message as
    PASTE_FAILED_PERMISSION, not crash before classification runs."""
    non_ascii_stderr = "„System Events“ ist nicht berechtigt (-1743)"

    def fake_synthesize():
        return False, "permission"

    pasteboard = mock.Mock()
    pasteboard.changeCount.return_value = 0

    with mock.patch("local_dictation.adapters.paste.frontmost_app_identifier", return_value="x"):
        status = paste.paste(
            "hello",
            frontmost_app_at_stop="x",
            pasteboard=pasteboard,
            synthesize_paste=fake_synthesize,
        )

    assert status == paste.PASTE_FAILED_PERMISSION
