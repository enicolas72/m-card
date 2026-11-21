"""Driver for the 256x64 greyscale OLED (SSD1322 controller, 4-wire SPI).

Same high-level API as the LCD `Display` (show_now_playing, set_lines,
wake...), but drawn with Pillow: proportional anti-aliased font (bundled
Inter: accents are displayed as-is, no transliteration; characters outside
the font are replaced, see fit_to_font), a large title on the "now
playing" screen, smooth pixel scrolling of the lines that are too wide.

OLED pixels wear out when they display the same thing for hours: the panel
is switched off after `sleep_timeout_s` without interaction, and the whole
picture moves by one pixel every few minutes (pixel shift).

The hardware implementation (luma.oled) is imported lazily so that the
rest of the software (tests, --fake mode) runs without the Pi libraries.
"""

from __future__ import annotations

import functools
import io
import logging
import threading
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .display import ScreenMessages

log = logging.getLogger(__name__)

WIDTH, HEIGHT = 256, 64
SCROLL_SPEED_PX_S = 30.0   # scrolling speed of the lines that are too wide
SCROLL_HOLD_S = 2.0        # pause on the start of the text before each loop
SCROLL_GAP_PX = 40         # space between the end and the start of scrolling text
SHIFT_PERIOD_S = 300.0     # pixel shift period (burn-in protection)
SHIFT_STEPS = [(0, 0), (1, 0), (1, 1), (0, 1)]
MARGIN = 2                 # free border, leaves room for the pixel shift


class OledBackend:
    """Minimal interface expected by OledDisplay (real panel, fake, tests)."""

    size = (WIDTH, HEIGHT)

    def show(self, image: Image.Image) -> None:  # pragma: no cover
        raise NotImplementedError

    def set_power(self, on: bool) -> None:  # pragma: no cover
        pass

    def describe(self, lines: list[str]) -> None:
        """Text content of the new screen (used by the fake to print it)."""

    def close(self) -> None:  # pragma: no cover
        pass


class LumaOledBackend(OledBackend):
    """Real backend: luma.oled SSD1322 on the Raspberry Pi's SPI bus."""

    def __init__(self, spi_port: int = 0, spi_device: int = 0, gpio_dc: int = 24,
                 gpio_rst: int = 25, rotate: int = 0, contrast: int = 180,
                 bus_speed_hz: int = 8_000_000):
        from luma.core.interface.serial import spi  # lazy import (unavailable off the Pi)
        from luma.oled.device import ssd1322

        serial = spi(port=spi_port, device=spi_device, gpio_DC=gpio_dc,
                     gpio_RST=gpio_rst, bus_speed_hz=bus_speed_hz)
        self._device = ssd1322(serial, width=WIDTH, height=HEIGHT, rotate=rotate, mode="RGB")
        self._device.contrast(max(0, min(255, int(contrast))))

    def show(self, image: Image.Image) -> None:
        self._device.display(image.convert(self._device.mode))

    def set_power(self, on: bool) -> None:
        if on:
            self._device.show()
        else:
            self._device.hide()

    def close(self) -> None:
        try:
            self._device.clear()
            self._device.cleanup()
        except Exception:  # the display may already be unplugged at shutdown
            pass


FONT_DIR = Path(__file__).resolve().parent / "fonts"


def load_font(size: int, path: str = "", weight: int = 500) -> ImageFont.FreeTypeFont:
    """TrueType font from `path`, or the bundled Inter (latin subset:
    French accents, ligatures, typographic quotes; SIL OFL, see fonts/)."""
    if path:
        try:
            return ImageFont.truetype(path, size)
        except OSError as exc:
            log.error("Font %s unusable (%s), using the bundled font", path, exc)
    return ImageFont.truetype(str(FONT_DIR / f"Inter-{weight}.ttf"), size)


# Letters without a Unicode decomposition to a plain base letter.
_LETTER_FALLBACKS = {"ł": "l", "Ł": "L", "đ": "d", "Đ": "D", "ħ": "h", "Ħ": "H", "ŧ": "t", "Ŧ": "T"}


def _glyph_print(font: ImageFont.FreeTypeFont, ch: str) -> tuple:
    left, top, right, bottom = font.getbbox(ch)
    img = Image.new("L", (max(1, right - left), max(1, bottom - top)), 0)
    ImageDraw.Draw(img).text((-left, -top), ch, font=font, fill=255)
    return img.size, img.tobytes()


@functools.lru_cache(maxsize=16)
def _notdef_print(font: ImageFont.FreeTypeFont) -> tuple:
    return _glyph_print(font, "￿")  # never mapped: drawn as the .notdef box


@functools.lru_cache(maxsize=4096)
def has_glyph(font: ImageFont.FreeTypeFont, ch: str) -> bool:
    """True if `font` can draw `ch`. Pillow does not expose the font's
    character map, so the rendering is compared with the .notdef box."""
    return _glyph_print(font, ch) != _notdef_print(font)


def fit_to_font(text: str, font: ImageFont.FreeTypeFont) -> str:
    """Replaces the characters `font` cannot draw (they would show as a box).
    Roon writes "Jean‐Michel Jarre" with U+2010 HYPHEN, which the bundled
    latin subset lacks: dashes become "-", spaces " ", other letters their
    base letter (ř → r), anything else "?"."""
    out = []
    for ch in unicodedata.normalize("NFC", text):
        if has_glyph(font, ch):
            out.append(ch)
            continue
        category = unicodedata.category(ch)
        if category == "Pd":
            out.append("-")
        elif category == "Zs":
            out.append(" ")
        elif category in ("Cc", "Cf"):
            continue  # control and invisible format characters
        else:
            base = _LETTER_FALLBACKS.get(ch) or "".join(
                c for c in unicodedata.normalize("NFKD", ch) if not unicodedata.combining(c))
            out.append(base if base and all(has_glyph(font, c) for c in base) else "?")
    return "".join(out)


@dataclass
class _Row:
    """One line of text in its own box; scrolls if wider than the box."""

    text: str
    font: ImageFont.FreeTypeFont
    x: int
    y: int
    w: int
    h: int
    align: str = "left"     # left | center (only for text that fits)
    offset: float = 0.0
    hold: float = SCROLL_HOLD_S
    text_w: float = field(init=False)

    def __post_init__(self):
        self.text = fit_to_font(self.text, self.font)
        self.text_w = self.font.getlength(self.text)

    @property
    def scrolls(self) -> bool:
        return self.text_w > self.w

    def advance(self, dt: float) -> bool:
        """Moves the scrolling by dt seconds; True if the row changed."""
        if not self.scrolls:
            return False
        if self.hold > 0:
            self.hold -= dt
            return False
        self.offset += SCROLL_SPEED_PX_S * dt
        if self.offset >= self.text_w + SCROLL_GAP_PX:
            self.offset = 0.0
            self.hold = SCROLL_HOLD_S
        return True

    def render(self) -> Image.Image:
        box = Image.new("L", (self.w, self.h), 0)
        draw = ImageDraw.Draw(box)
        mid = self.h / 2
        if not self.scrolls:
            x = (self.w - self.text_w) / 2 if self.align == "center" else 0
            draw.text((x, mid), self.text, font=self.font, fill=255, anchor="lm")
        else:
            x = -round(self.offset)
            draw.text((x, mid), self.text, font=self.font, fill=255, anchor="lm")
            draw.text((x + self.text_w + SCROLL_GAP_PX, mid), self.text,
                      font=self.font, fill=255, anchor="lm")
        return box


class OledDisplay(ScreenMessages):
    """256x64 OLED screen: layouts, scrolling, sleep and pixel shift.
    wake() switches the panel back on and re-arms the sleep delay."""

    def __init__(self, backend: OledBackend, sleep_timeout_s: float = 0,
                 fps: float = 20, font_path: str = ""):
        self._backend = backend
        self._lock = threading.Lock()
        self._fonts = {size: load_font(size, font_path) for size in (12, 13)}
        self._fonts[22] = load_font(22, font_path, weight=600)
        self._rows: list[_Row] = []
        self._icon = ""
        self._frame = Image.new("L", (WIDTH, HEIGHT), 0)
        self._sleep_timeout = float(sleep_timeout_s)
        self._awake = True
        self._last_wake = time.monotonic()
        self._shift_index = 0
        self._last_shift = time.monotonic()
        self._period = 1.0 / max(1.0, float(fps))
        self._stop = threading.Event()
        self._ticker = threading.Thread(target=self._tick_loop, daemon=True, name="oled-ticker")
        self._ticker.start()

    # ---- High-level API -------------------------------------------------

    def set_lines(self, *lines: str) -> None:
        """4 lines of small text (generic messages)."""
        font = self._fonts[13]
        rows = [_Row(text or "", font, MARGIN, MARGIN + i * 15, WIDTH - 2 * MARGIN, 15)
                for i, text in enumerate(lines[:4])]
        self._set_screen(rows)

    def show_waiting(self) -> None:
        self._set_screen([
            _Row("M-Card", self._fonts[12], MARGIN, MARGIN, WIDTH - 2 * MARGIN, 14, "center"),
            _Row("Place an album", self._fonts[22], MARGIN, 22, WIDTH - 2 * MARGIN, 28, "center"),
        ])

    def show_now_playing(self, state: str, album: str, track: str, artist: str = "") -> None:
        """Artist on top (with the state icon), large track title, album below."""
        text_x = MARGIN + 16
        self._set_screen([
            _Row(artist or "", self._fonts[13], text_x, MARGIN, WIDTH - text_x - MARGIN, 15),
            _Row(track or album or "", self._fonts[22], MARGIN, 18, WIDTH - 2 * MARGIN, 28),
            _Row(album if track else "", self._fonts[13], MARGIN, 47, WIDTH - 2 * MARGIN, 15),
        ], icon=state)

    def wake(self) -> None:
        """Switches the panel back on and re-arms the sleep delay."""
        with self._lock:
            self._last_wake = time.monotonic()
            if not self._awake:
                self._awake = True
                self._power_locked(True)
                self._render_locked()

    def snapshot_png(self) -> bytes:
        """Current picture (white on black), for the web console preview."""
        with self._lock:
            frame = self._frame.copy() if self._awake else Image.new("L", (WIDTH, HEIGHT), 0)
        buf = io.BytesIO()
        frame.save(buf, format="PNG")
        return buf.getvalue()

    def close(self) -> None:
        self._stop.set()
        self._ticker.join(timeout=2)
        self._backend.close()

    # ---- Rendering -------------------------------------------------------

    def _set_screen(self, rows: list[_Row], icon: str = "") -> None:
        with self._lock:
            old = [(r.text, r.y) for r in self._rows]
            if old == [(r.text, r.y) for r in rows] and icon == self._icon:
                return  # same content: keep the scrolling position
            self._rows, self._icon = rows, icon
            try:
                self._backend.describe([r.text for r in rows])
            except Exception as exc:
                log.error("OLED describe failed: %s", exc)
            self._render_locked()

    def _draw_icon(self, draw: ImageDraw.ImageDraw, dx: int, dy: int) -> None:
        x, y = MARGIN + 1 + dx, MARGIN + 2 + dy  # 10x10 box left of the top line
        if self._icon == "playing":
            draw.polygon([(x, y), (x + 9, y + 5), (x, y + 10)], fill=255)
        elif self._icon == "paused":
            draw.rectangle([x, y, x + 3, y + 10], fill=255)
            draw.rectangle([x + 6, y, x + 9, y + 10], fill=255)
        elif self._icon == "stopped":
            draw.rectangle([x, y + 1, x + 9, y + 10], fill=255)
        elif self._icon == "loading":
            for i in range(3):
                draw.ellipse([x + i * 4, y + 4, x + i * 4 + 2, y + 6], fill=255)

    def _render_locked(self) -> None:
        dx, dy = SHIFT_STEPS[self._shift_index]
        frame = Image.new("L", (WIDTH, HEIGHT), 0)
        for row in self._rows:
            if row.text:
                frame.paste(row.render(), (row.x + dx - 1, row.y + dy - 1))
        self._draw_icon(ImageDraw.Draw(frame), dx - 1, dy - 1)
        self._frame = frame
        if not self._awake:
            return
        try:
            self._backend.show(frame)
        except Exception as exc:
            log.error("OLED write failed: %s", exc)

    def _power_locked(self, on: bool) -> None:
        try:
            self._backend.set_power(on)
        except Exception as exc:
            log.error("OLED power control failed: %s", exc)

    def _maybe_sleep_locked(self, now: float) -> None:
        if (self._sleep_timeout > 0 and self._awake
                and now - self._last_wake > self._sleep_timeout):
            self._awake = False
            self._power_locked(False)

    def _maybe_shift_locked(self, now: float) -> bool:
        if now - self._last_shift < SHIFT_PERIOD_S:
            return False
        self._last_shift = now
        self._shift_index = (self._shift_index + 1) % len(SHIFT_STEPS)
        return True

    def _tick_loop(self) -> None:
        while not self._stop.wait(self._period):
            with self._lock:
                now = time.monotonic()
                self._maybe_sleep_locked(now)
                if not self._awake:
                    continue
                moved = [row.advance(self._period) for row in self._rows]
                if self._maybe_shift_locked(now) or any(moved):
                    self._render_locked()
