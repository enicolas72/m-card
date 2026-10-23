"""Driver for the 2004 LCD (20x4) through a PCF8574 I2C backpack.

The HD44780 (ROM A00) cannot display accented characters: text is
transliterated to ASCII. Lines longer than 20 characters scroll in a loop
thanks to a small "ticker" thread.

The hardware implementation (RPLCD) is imported lazily so that the rest of
the software (tests, --fake mode) runs without the Pi libraries.
"""

from __future__ import annotations

import logging
import threading
import time
import unicodedata

log = logging.getLogger(__name__)

SCROLL_PERIOD_S = 0.6
SCROLL_GAP = "   "  # visual separator between the end and the start of scrolling text

STATE_ICONS = {
    "playing": ">",
    "paused": "||",
    "stopped": "[]",
    "loading": "..",
}


def to_lcd_ascii(text: str) -> str:
    """Transliterates Unicode accents/typography to the HD44780's printable ASCII."""
    text = text.replace("œ", "oe").replace("Œ", "OE").replace("æ", "ae").replace("Æ", "AE")
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    text = text.replace("–", "-").replace("—", "-").replace("…", "...")
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if ord(c) < 128 and c.isprintable() or c == " ")


class LcdBackend:
    """Minimal interface expected by Display (implemented by the real LCD and the fake)."""

    cols = 20
    rows = 4

    def write_row(self, row: int, text: str) -> None:  # pragma: no cover
        raise NotImplementedError

    def set_backlight(self, on: bool) -> None:  # pragma: no cover
        pass

    def close(self) -> None:  # pragma: no cover
        pass


class CharLcdBackend(LcdBackend):
    """Real backend: RPLCD on the Raspberry Pi's I2C bus."""

    def __init__(self, i2c_address: int, i2c_port: int, cols: int, rows: int):
        from RPLCD.i2c import CharLCD  # lazy import (unavailable off the Pi)

        self.cols = cols
        self.rows = rows
        self._lcd = CharLCD(
            i2c_expander="PCF8574",
            address=i2c_address,
            port=i2c_port,
            cols=cols,
            rows=rows,
            auto_linebreaks=False,
        )
        self._lcd.clear()

    def write_row(self, row: int, text: str) -> None:
        self._lcd.cursor_pos = (row, 0)
        self._lcd.write_string(text.ljust(self.cols)[: self.cols])

    def set_backlight(self, on: bool) -> None:
        self._lcd.backlight_enabled = on

    def close(self) -> None:
        try:
            self._lcd.clear()
            self._lcd.close()
        except Exception:  # the display may already be unplugged at shutdown
            pass


class Display:
    """4-line display: automatic scrolling of lines that are too long,
    backlight sleep after `backlight_timeout_s` without interaction
    (0 = never). wake() turns it back on and re-arms the delay."""

    def __init__(self, backend: LcdBackend, backlight_timeout_s: float = 0):
        self._backend = backend
        self._lock = threading.Lock()
        self._lines = [""] * backend.rows
        self._offsets = [0] * backend.rows
        self._bl_timeout = float(backlight_timeout_s)
        self._bl_on = True
        self._last_wake = time.monotonic()
        self._stop = threading.Event()
        self._ticker = threading.Thread(target=self._tick_loop, daemon=True, name="lcd-ticker")
        self._ticker.start()

    # ---- High-level API -------------------------------------------------

    def set_lines(self, *lines: str) -> None:
        with self._lock:
            for row in range(self._backend.rows):
                new = to_lcd_ascii(lines[row]) if row < len(lines) and lines[row] else ""
                if new != self._lines[row]:
                    self._lines[row] = new
                    self._offsets[row] = 0
            self._render_locked()

    def show_boot(self, version: str) -> None:
        self.set_lines("M-Card", f"v{version}", "Starting...", "")

    def show_waiting(self) -> None:
        self.set_lines("M-Card", "", "Place an album", "")

    def show_now_playing(self, state: str, album: str, track: str, artist: str = "") -> None:
        icon = STATE_ICONS.get(state, "?")
        self.set_lines(f"{icon} {state}", album, track, artist)

    def show_unknown_card(self, uid: str) -> None:
        self.set_lines("Unknown card", f"UID {uid}", "Added to", "albums.yaml (TODO)")

    def show_todo_card(self, uid: str) -> None:
        self.set_lines("Card to set up", f"UID {uid}", "Edit albums.yaml", "via the web UI")

    def show_error(self, line1: str, line2: str = "") -> None:
        self.set_lines("! " + line1, line2, "", "")

    def wake(self) -> None:
        """Turns the backlight back on and re-arms the sleep delay."""
        with self._lock:
            self._last_wake = time.monotonic()
            if not self._bl_on:
                self._bl_on = True
                try:
                    self._backend.set_backlight(True)
                except Exception as exc:
                    log.error("Backlight control failed: %s", exc)

    def _maybe_sleep_locked(self, now: float) -> None:
        if (self._bl_timeout > 0 and self._bl_on
                and now - self._last_wake > self._bl_timeout):
            self._bl_on = False
            try:
                self._backend.set_backlight(False)
            except Exception as exc:
                log.error("Backlight control failed: %s", exc)

    def close(self) -> None:
        self._stop.set()
        self._ticker.join(timeout=2)
        self._backend.close()

    # ---- Rendering / scrolling ------------------------------------------

    def _visible_part(self, row: int) -> str:
        text, cols = self._lines[row], self._backend.cols
        if len(text) <= cols:
            return text.ljust(cols)
        loop = text + SCROLL_GAP
        offset = self._offsets[row] % len(loop)
        window = (loop + loop)[offset : offset + cols]
        return window

    def _render_locked(self) -> None:
        for row in range(self._backend.rows):
            try:
                self._backend.write_row(row, self._visible_part(row))
            except Exception as exc:
                log.error("LCD write failed: %s", exc)
                return

    def _tick_loop(self) -> None:
        while not self._stop.wait(SCROLL_PERIOD_S):
            with self._lock:
                self._maybe_sleep_locked(time.monotonic())
                changed = False
                for row in range(self._backend.rows):
                    if len(self._lines[row]) > self._backend.cols:
                        self._offsets[row] += 1
                        changed = True
                if changed:
                    self._render_locked()
