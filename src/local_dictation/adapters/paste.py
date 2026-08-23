"""Auto-paste transcribed text into the frontmost app, with a focus-changed guard.

Synthesizes Cmd+V via AppleScript/System Events (`osascript`) rather than a raw Quartz
CGEventPost. Both ultimately require the calling process to be permitted to inject input,
but they're gated by different, independent TCC services: CGEventPost needs Accessibility
trust for *this exact process's code identity*, which turned out to be unreliable for a
bare venv Python interpreter (an ad-hoc-signed binary living at the end of a multi-hop
symlink chain into a Homebrew Cellar path that changes on every `brew upgrade` -- macOS
ties Accessibility grants to code identity, and ad-hoc-signed code has no stable identity
across rebuilds, per Apple's own guidance on this exact failure class). Going through
System Events instead needs the Automation permission ("this process wants to control
System Events") -- a separate service that (a) reliably triggers its own system prompt for
unbundled interpreter binaries, where the Accessibility prompt often silently fails to
appear at all, and (b) actually reports success/failure via osascript's exit code, unlike
CGEventPost which posts the event and tells you nothing.

The dictated text is left on the clipboard after pasting rather than restoring the user's
prior clipboard contents because automatic restore is a race condition -- a "Copy Last
Dictation" menu item (app.py) and the HUD (hud.py) both provide a clipboard-independent
way to recover the text if the paste itself doesn't land.
"""

import logging
import subprocess
import time

import AppKit

from local_dictation import config

log = logging.getLogger(__name__)

PASTED = "pasted"
SKIPPED_DISABLED = "skipped_disabled"
SKIPPED_FOCUS_CHANGED = "skipped_focus_changed"
PASTE_FAILED_PERMISSION = "paste_failed_permission"
PASTE_FAILED_OTHER = "paste_failed_other"

_PASTE_SCRIPT = 'tell application "System Events" to keystroke "v" using command down'
_PERMISSION_ERROR_MARKERS = (
    "not allowed",
    "not authorized",
    "-1743",
    "assistive access",
    "timed out",  # likely blocked on an unanswered "control System Events" dialog
)


def frontmost_app_identifier() -> str | None:
    """A stable identifier for the current frontmost app, or None if unavailable."""
    app = AppKit.NSWorkspace.sharedWorkspace().frontmostApplication()
    if app is None:
        return None
    return app.bundleIdentifier() or str(app.processIdentifier())


def accessibility_trusted() -> bool:
    """Whether this process is a trusted Accessibility client. No longer used to gate the
    paste attempt itself (see module docstring -- this check proved unreliable for a bare
    venv interpreter), but still surfaced in the menu as a secondary diagnostic hint."""
    try:
        import ApplicationServices
    except ImportError:
        return False
    return bool(ApplicationServices.AXIsProcessTrusted())


def request_accessibility_trust() -> bool:
    """Same check, but prompts the user once (a system dialog deep-linking to the
    Accessibility settings pane) if not already trusted. Safe to call repeatedly --
    macOS only shows the prompt once per grant/revoke cycle."""
    try:
        import ApplicationServices
    except ImportError:
        return False
    options = {ApplicationServices.kAXTrustedCheckOptionPrompt: True}
    return bool(ApplicationServices.AXIsProcessTrustedWithOptions(options))


def _default_pasteboard():
    return AppKit.NSPasteboard.generalPasteboard()


def _read_clipboard_text(pasteboard) -> str | None:
    return pasteboard.stringForType_(AppKit.NSPasteboardTypeString)


def _write_clipboard_text(pasteboard, text: str) -> None:
    pasteboard.clearContents()
    pasteboard.declareTypes_owner_([AppKit.NSPasteboardTypeString], None)
    pasteboard.setString_forType_(text, AppKit.NSPasteboardTypeString)


def _synthesize_cmd_v_osascript() -> tuple[bool, str]:
    """Ask System Events to press Cmd+V. Returns (success, error_message). This is a real
    attempt with a real result, unlike CGEventPost -- osascript's exit code and stderr
    tell us whether it actually happened, including distinguishing a permission problem
    (catchable, actionable) from other failures."""
    try:
        # encoding/errors pinned explicitly: without them, text=True decodes via
        # locale.getpreferredencoding(), which is plain ASCII when this process has no
        # inherited shell locale (e.g. launched as a GUI .app rather than from a
        # terminal) -- a localized (non-English) permission-denial message from
        # osascript would then raise UnicodeDecodeError here, before it ever reaches
        # the classification below.
        result = subprocess.run(
            ["osascript", "-e", _PASTE_SCRIPT],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except FileNotFoundError:
        return False, "unavailable"
    except OSError:
        return False, "os_error"

    if result.returncode == 0:
        return True, ""
    if _is_permission_error(result.stderr or ""):
        return False, "permission"
    return False, "failed"


def _is_permission_error(message: str) -> bool:
    lowered = message.lower()
    return any(marker in lowered for marker in _PERMISSION_ERROR_MARKERS)


def paste(
    text: str,
    frontmost_app_at_stop: str | None,
    pasteboard=None,
    synthesize_paste=None,
    *,
    recording_id: int | None = None,
) -> str:
    """Copy `text` to the clipboard and, if auto-paste is enabled and focus hasn't changed
    since `frontmost_app_at_stop` was captured, attempt to synthesize Cmd+V via System
    Events. The dictated text is left on the clipboard afterward in every case -- see
    module docstring for why automatic restore was removed.

    `pasteboard` and `synthesize_paste` are both injectable for testing (default to the
    real system clipboard and the real osascript-based keystroke sender). Never call this
    with AUTO_PASTE enabled and the default `synthesize_paste` in automated tests -- even
    with an isolated `pasteboard`, the default sender still fires a real, system-wide
    Cmd+V that reads from whatever app is actually frontmost. Pass a stub returning
    `(True, "")` or `(False, "...")` for `synthesize_paste` (and
    `AppKit.NSPasteboard.pasteboardWithUniqueName()` for `pasteboard`) to exercise this
    function without touching the live system at all.

    Returns one of PASTED / SKIPPED_DISABLED / SKIPPED_FOCUS_CHANGED /
    PASTE_FAILED_PERMISSION / PASTE_FAILED_OTHER.
    """
    pasteboard = pasteboard if pasteboard is not None else _default_pasteboard()
    synthesize_paste = synthesize_paste if synthesize_paste is not None else _synthesize_cmd_v_osascript

    log.info("paste_started recording_id=%s auto_paste=%s", recording_id, config.AUTO_PASTE)

    _write_clipboard_text(pasteboard, text)

    if not config.AUTO_PASTE:
        log.info("paste_completed recording_id=%s status=%s", recording_id, SKIPPED_DISABLED)
        return SKIPPED_DISABLED

    current_frontmost = frontmost_app_identifier()
    if current_frontmost != frontmost_app_at_stop:
        log.info("paste_completed recording_id=%s status=%s", recording_id, SKIPPED_FOCUS_CHANGED)
        return SKIPPED_FOCUS_CHANGED

    our_change_count = pasteboard.changeCount()
    time.sleep(config.CLIPBOARD_WRITE_SETTLE_SECONDS)

    # Extra hardening: if something else wrote to the clipboard during the settle window
    # (e.g. the user copied something else, or another app wrote to it), re-assert our
    # text immediately before firing the paste so the target has the best chance of
    # reading the dictation rather than whatever else showed up.
    if pasteboard.changeCount() != our_change_count:
        log.info("paste_clipboard_reasserted recording_id=%s", recording_id)
        _write_clipboard_text(pasteboard, text)

    success, error_category = synthesize_paste()
    if success:
        log.info("paste_completed recording_id=%s status=%s", recording_id, PASTED)
        return PASTED
    if error_category == "permission":
        log.info("paste_completed recording_id=%s status=%s", recording_id, PASTE_FAILED_PERMISSION)
        return PASTE_FAILED_PERMISSION
    log.info(
        "paste_completed recording_id=%s status=%s error_category=%s",
        recording_id,
        PASTE_FAILED_OTHER,
        error_category,
    )
    return PASTE_FAILED_OTHER
