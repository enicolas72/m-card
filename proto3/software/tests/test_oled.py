import time

from conftest import MemoryOled

from mcard import oled
from mcard.app import make_display
from mcard.config import AppConfig
from mcard.display import Display
from mcard.oled import OledDisplay


def _lit_pixels(image):
    return sum(image.histogram()[1:])


def test_now_playing_layout_keeps_accents():
    panel = MemoryOled()
    screen = OledDisplay(panel)
    screen.show_now_playing("playing", "Oxygène", "Oxygène, Pt. 4", "Jean-Michel Jarre")
    assert panel.lines == ["Jean-Michel Jarre", "Oxygène, Pt. 4", "Oxygène"]
    frame = panel.frames[-1]
    assert frame.size == (256, 64)
    assert _lit_pixels(frame) > 200
    screen.close()


def test_characters_missing_from_the_font_are_replaced():
    font = oled.load_font(13)
    assert oled.fit_to_font("Jean‐Michel Jarre", font) == "Jean-Michel Jarre"  # Roon's hyphen
    assert oled.fit_to_font("Dvořák", font) == "Dvorák"
    assert oled.fit_to_font("Łódź", font) == "Lódz"
    assert oled.fit_to_font("10 000", font) == "10 000"
    assert oled.fit_to_font("坂本", font) == "??"
    assert oled.fit_to_font("Oxygène — « Pt. 4 »", font) == "Oxygène — « Pt. 4 »"


def test_roon_hyphen_displays_like_ascii_hyphen():
    panel = MemoryOled()
    screen = OledDisplay(panel)
    screen.show_now_playing("playing", "Electronica 1", "The Time Machine", "Jean‐Michel Jarre")
    count = len(panel.frames)
    screen.show_now_playing("playing", "Electronica 1", "The Time Machine", "Jean-Michel Jarre")
    assert len(panel.frames) == count   # same picture: nothing to redraw
    assert panel.lines[0] == "Jean-Michel Jarre"
    screen.close()


def test_same_content_does_not_redraw():
    panel = MemoryOled()
    screen = OledDisplay(panel)
    screen.show_now_playing("playing", "Kind of Blue", "So What", "Miles Davis")
    count = len(panel.frames)
    screen.show_now_playing("playing", "Kind of Blue", "So What", "Miles Davis")
    assert len(panel.frames) == count
    screen.show_now_playing("paused", "Kind of Blue", "So What", "Miles Davis")
    assert len(panel.frames) == count + 1   # the icon changed
    screen.close()


def test_long_title_scrolls_after_hold():
    panel = MemoryOled()
    screen = OledDisplay(panel)
    screen._stop.set()                       # drive the ticker by hand
    screen._ticker.join()
    screen.show_now_playing("playing", "Album", "A track title far too wide for 256 pixels", "")
    title = screen._rows[1]
    assert title.scrolls
    first = panel.frames[-1]
    assert not title.advance(oled.SCROLL_HOLD_S / 2)   # still holding on the start
    title.advance(oled.SCROLL_HOLD_S)
    assert title.advance(0.5)
    with screen._lock:
        screen._render_locked()
    assert panel.frames[-1].tobytes() != first.tobytes()


def test_short_text_does_not_scroll():
    screen = OledDisplay(MemoryOled())
    screen.set_lines("Short", "", "", "")
    assert not any(row.scrolls for row in screen._rows)
    screen.close()


def test_sleeps_after_timeout_and_wakes():
    panel = MemoryOled()
    screen = OledDisplay(panel, sleep_timeout_s=60)
    screen._last_wake -= 61
    with screen._lock:
        screen._maybe_sleep_locked(time.monotonic())
    assert panel.power is False
    count = len(panel.frames)
    screen.set_lines("Hidden", "", "", "")   # drawn but not sent while asleep
    assert len(panel.frames) == count
    screen.wake()
    assert panel.power is True
    assert len(panel.frames) == count + 1
    screen.close()


def test_pixel_shift_moves_the_picture():
    panel = MemoryOled()
    screen = OledDisplay(panel)
    screen.set_lines("M-Card", "", "", "")
    before = panel.frames[-1]
    with screen._lock:
        assert screen._maybe_shift_locked(time.monotonic() + oled.SHIFT_PERIOD_S + 1)
        screen._render_locked()
    after = panel.frames[-1]
    assert _lit_pixels(after) == _lit_pixels(before)
    assert after.tobytes() != before.tobytes()
    screen.close()


def test_snapshot_is_png():
    screen = OledDisplay(MemoryOled())
    screen.show_waiting()
    assert screen.snapshot_png().startswith(b"\x89PNG")
    screen.close()


def test_make_display_follows_config(tmp_path):
    (tmp_path / "mcard.yaml").write_text("display:\n  type: lcd\n", encoding="utf-8")
    lcd = make_display(AppConfig.load(tmp_path), fake=True)
    assert isinstance(lcd, Display)
    lcd.close()
    default = make_display(AppConfig.load(tmp_path / "missing"), fake=True)
    assert isinstance(default, OledDisplay)
    default.close()


def test_proto3_defaults():
    config = AppConfig()
    assert config.get("nfc", "device") == "tty:AMA0:pn532"
    assert config.get("display", "type") == "oled"
