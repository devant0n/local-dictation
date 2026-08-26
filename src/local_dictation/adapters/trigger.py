"""Global toggle triggers via a Quartz CGEventTap.

Two backends are available, selected by config.TRIGGER:

- "combo" (default): ComboTrigger, a configurable modifier+key chord (e.g. Control+
  Option+Cmd+D). Unambiguous the instant it's pressed -- no discrimination logic needed,
  since a multi-key chord doesn't fire by accident. Replaced the Fn backend as the default
  after real use showed Fn's bare-tap-vs-combo discrimination and its unavoidable clash
  with Apple's own Fn-dictation shortcut were more trouble than they were worth.
- "fn": FnTapTrigger, a bare tap of the Fn/Globe key. pynput cannot detect Fn on macOS --
  it's exposed only as a modifier flag (kCGEventFlagMaskSecondaryFn) on flagsChanged
  events, never as a normal key event -- so this taps flagsChanged + keyDown events
  directly to detect a *bare* Fn tap: Fn pressed and released with no other key pressed in
  between, within a short hold-time window. Fn+Delete, Fn+arrows, Fn+F-keys etc. are left
  untouched since a keyDown between the Fn-set and Fn-clear flag transitions marks it as a
  combo, not a toggle. Kept available for anyone who wants it back; see README.md for the
  extra setup step it requires (disabling Apple's own Fn-dictation shortcut).

Both use kCGEventTapOptionListenOnly -- no event suppression -- since neither trigger types
a character, so there is nothing to consume.
"""

import threading
import time
import logging

import Quartz

from local_dictation import config

log = logging.getLogger(__name__)


class FnTapTrigger:
    """Watches for a bare Fn key tap and calls on_toggle() for each valid tap."""

    def __init__(self, on_toggle, on_tap_disabled=None, on_tap_reenabled=None):
        self.on_toggle = on_toggle
        self.on_tap_disabled = on_tap_disabled
        self.on_tap_reenabled = on_tap_reenabled
        self._thread: threading.Thread | None = None
        self._run_loop = None
        self._tap = None
        self._fn_down_at: float | None = None
        self._other_key_seen = False
        self._last_toggle_at = 0.0

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run_guarded, daemon=True)
        self._thread.start()

    def _run_guarded(self) -> None:
        try:
            self._run()
        except Exception as error:
            log.warning("trigger_runtime_failed backend=fn error_type=%s", type(error).__name__)

    def stop(self) -> None:
        if self._run_loop is not None:
            Quartz.CFRunLoopStop(self._run_loop)

    def _run(self) -> None:
        event_mask = Quartz.CGEventMaskBit(Quartz.kCGEventFlagsChanged) | Quartz.CGEventMaskBit(
            Quartz.kCGEventKeyDown
        )
        self._tap = Quartz.CGEventTapCreate(
            Quartz.kCGSessionEventTap,
            Quartz.kCGHeadInsertEventTap,
            Quartz.kCGEventTapOptionListenOnly,
            event_mask,
            self._handle_event,
            None,
        )
        if self._tap is None:
            raise RuntimeError(
                "Failed to create the Fn key event tap. Grant Input Monitoring and "
                "Accessibility permission (System Settings > Privacy & Security) to the "
                "process running this app, then restart it."
            )

        run_loop_source = Quartz.CFMachPortCreateRunLoopSource(None, self._tap, 0)
        self._run_loop = Quartz.CFRunLoopGetCurrent()
        Quartz.CFRunLoopAddSource(self._run_loop, run_loop_source, Quartz.kCFRunLoopCommonModes)
        Quartz.CGEventTapEnable(self._tap, True)
        Quartz.CFRunLoopRun()

    def is_tap_enabled(self) -> bool:
        return bool(self._tap is not None and Quartz.CGEventTapIsEnabled(self._tap))

    def _handle_event(self, proxy, event_type, event, refcon):
        if event_type in (
            Quartz.kCGEventTapDisabledByTimeout,
            Quartz.kCGEventTapDisabledByUserInput,
        ):
            # macOS disabled the tap (e.g. it was too slow, or the user toggled
            # accessibility settings); re-enable it so the toggle keeps working.
            reason = (
                "timeout"
                if event_type == Quartz.kCGEventTapDisabledByTimeout
                else "user_input"
            )
            if self.on_tap_disabled is not None:
                self.on_tap_disabled(reason)
            Quartz.CGEventTapEnable(self._tap, True)
            if self.on_tap_reenabled is not None:
                self.on_tap_reenabled(reason)
            return event

        if event_type == Quartz.kCGEventKeyDown:
            if self._fn_down_at is not None:
                self._other_key_seen = True
            return event

        if event_type == Quartz.kCGEventFlagsChanged:
            self._handle_flags_changed(event)

        return event

    def _handle_flags_changed(self, event) -> None:
        flags = Quartz.CGEventGetFlags(event)
        fn_down = bool(flags & Quartz.kCGEventFlagMaskSecondaryFn)
        now = time.monotonic()

        if fn_down and self._fn_down_at is None:
            self._fn_down_at = now
            self._other_key_seen = False
            return

        if not fn_down and self._fn_down_at is not None:
            held_for = now - self._fn_down_at
            bare_tap = not self._other_key_seen and held_for <= config.FN_TAP_HOLD_WINDOW_SECONDS
            self._fn_down_at = None
            self._other_key_seen = False

            if bare_tap and (now - self._last_toggle_at) >= config.FN_TAP_DEBOUNCE_SECONDS:
                self._last_toggle_at = now
                self.on_toggle()


# Virtual keycodes for the ANSI US keyboard layout (kVK_ANSI_*), the keys plausible as a
# combo trigger. Extend as needed for other layouts/keys.
_KEYCODES = {
    "a": 0, "b": 11, "c": 8, "d": 2, "e": 14, "f": 3, "g": 5, "h": 4, "i": 34,
    "j": 38, "k": 40, "l": 37, "m": 46, "n": 45, "o": 31, "p": 35, "q": 12, "r": 15,
    "s": 1, "t": 17, "u": 32, "v": 9, "w": 13, "x": 7, "y": 16, "z": 6,
    "0": 29, "1": 18, "2": 19, "3": 20, "4": 21, "5": 23, "6": 22, "7": 26, "8": 28, "9": 25,
    "space": 49,
}

_MODIFIER_FLAGS = {
    "control": Quartz.kCGEventFlagMaskControl,
    "option": Quartz.kCGEventFlagMaskAlternate,
    "command": Quartz.kCGEventFlagMaskCommand,
    "shift": Quartz.kCGEventFlagMaskShift,
}


class ComboTrigger:
    """Toggles on a configured modifier+key combo. No bare-tap discrimination needed --
    a multi-key chord is unambiguous the instant it's pressed."""

    def __init__(self, on_toggle, key: str, modifiers: set[str], on_tap_disabled=None,
                 on_tap_reenabled=None):
        self.on_toggle = on_toggle
        self.on_tap_disabled = on_tap_disabled
        self.on_tap_reenabled = on_tap_reenabled
        try:
            self._target_keycode = _KEYCODES[key.lower()]
        except KeyError:
            raise ValueError(f"Unknown trigger key {key!r}; add it to trigger.py's _KEYCODES") from None
        self._required_flags = 0
        for name in modifiers:
            try:
                self._required_flags |= _MODIFIER_FLAGS[name.lower()]
            except KeyError:
                raise ValueError(
                    f"Unknown modifier {name!r}; must be one of {sorted(_MODIFIER_FLAGS)}"
                ) from None

        self._thread: threading.Thread | None = None
        self._run_loop = None
        self._tap = None
        self._last_toggle_at = 0.0

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run_guarded, daemon=True)
        self._thread.start()

    def _run_guarded(self) -> None:
        try:
            self._run()
        except Exception as error:
            log.warning("trigger_runtime_failed backend=combo error_type=%s", type(error).__name__)

    def stop(self) -> None:
        if self._run_loop is not None:
            Quartz.CFRunLoopStop(self._run_loop)

    def _run(self) -> None:
        event_mask = Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown)
        self._tap = Quartz.CGEventTapCreate(
            Quartz.kCGSessionEventTap,
            Quartz.kCGHeadInsertEventTap,
            Quartz.kCGEventTapOptionListenOnly,
            event_mask,
            self._handle_event,
            None,
        )
        if self._tap is None:
            raise RuntimeError(
                "Failed to create the combo event tap. Grant Input Monitoring and "
                "Accessibility permission (System Settings > Privacy & Security) to the "
                "process running this app, then restart it."
            )

        run_loop_source = Quartz.CFMachPortCreateRunLoopSource(None, self._tap, 0)
        self._run_loop = Quartz.CFRunLoopGetCurrent()
        Quartz.CFRunLoopAddSource(self._run_loop, run_loop_source, Quartz.kCFRunLoopCommonModes)
        Quartz.CGEventTapEnable(self._tap, True)
        Quartz.CFRunLoopRun()

    def is_tap_enabled(self) -> bool:
        return bool(self._tap is not None and Quartz.CGEventTapIsEnabled(self._tap))

    def _handle_event(self, proxy, event_type, event, refcon):
        if event_type in (
            Quartz.kCGEventTapDisabledByTimeout,
            Quartz.kCGEventTapDisabledByUserInput,
        ):
            reason = (
                "timeout"
                if event_type == Quartz.kCGEventTapDisabledByTimeout
                else "user_input"
            )
            if self.on_tap_disabled is not None:
                self.on_tap_disabled(reason)
            Quartz.CGEventTapEnable(self._tap, True)
            if self.on_tap_reenabled is not None:
                self.on_tap_reenabled(reason)
            return event

        if event_type == Quartz.kCGEventKeyDown:
            # Ignore OS-synthesized auto-repeat key-downs from holding the combo -- only a
            # genuine fresh press should toggle. A multi-key chord takes real, deliberate
            # time to press, and macOS key-repeat is driven by the base key regardless of
            # which modifiers are held; without this check, holding the combo past the
            # repeat-delay threshold generates a second keyDown that lands after the
            # debounce window and silently re-toggles state, making stop/start behave
            # unpredictably based on exactly how long the key was physically held.
            if Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventAutorepeat):
                return event

            keycode = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
            flags = Quartz.CGEventGetFlags(event)
            # Match the target key with (at least) the required modifiers held. Using
            # "at least" rather than an exact-flags match tolerates incidental extra flags
            # (e.g. caps-lock, secondary-fn) some keyboards/utilities set.
            if keycode == self._target_keycode and (flags & self._required_flags) == self._required_flags:
                self._maybe_toggle()

        return event

    def _maybe_toggle(self) -> None:
        # Secondary guard only now that autorepeat key-downs are filtered above (real
        # repeats never reach here) -- kept as cheap protection against genuine
        # ultra-fast double-taps.
        now = time.monotonic()
        if (now - self._last_toggle_at) >= config.COMBO_DEBOUNCE_SECONDS:
            self._last_toggle_at = now
            self.on_toggle()


def create_trigger(on_toggle, on_tap_disabled=None, on_tap_reenabled=None):
    """Instantiate whichever trigger backend config.TRIGGER selects."""
    if config.TRIGGER == "combo":
        return ComboTrigger(
            on_toggle, config.TRIGGER_KEY, config.TRIGGER_MODIFIERS, on_tap_disabled,
            on_tap_reenabled
        )
    if config.TRIGGER == "fn":
        return FnTapTrigger(on_toggle, on_tap_disabled, on_tap_reenabled)
    raise ValueError(f"Unknown config.TRIGGER {config.TRIGGER!r}; expected 'combo' or 'fn'")
