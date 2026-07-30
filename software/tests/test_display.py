import time

from conftest import MemoryLcd

from mcard.display import Display, to_lcd_ascii


def test_transliteration_of_accents():
    assert to_lcd_ascii("Éléphant à l'œuvre — déjà…") == "Elephant a l'oeuvre - deja..."


def test_short_lines_padded_to_width():
    lcd = MemoryLcd()
    display = Display(lcd)
    display.set_lines("Bonjour", "", "Ligne 3", "")
    assert lcd.rows_content[0] == "Bonjour".ljust(20)
    assert lcd.rows_content[2].startswith("Ligne 3")
    display.close()


def test_long_line_scrolls():
    lcd = MemoryLcd()
    display = Display(lcd)
    long_title = "Un titre d'album vraiment beaucoup trop long pour un 20x4"
    display.set_lines(long_title, "", "", "")
    first = lcd.rows_content[0]
    assert len(first) == 20
    time.sleep(1.5)  # laisser le ticker défiler
    assert lcd.rows_content[0] != first
    display.close()


def test_now_playing_layout():
    lcd = MemoryLcd()
    display = Display(lcd)
    display.show_now_playing("playing", "Kind of Blue", "So What", "Miles Davis")
    assert lcd.rows_content[0].startswith("> playing")
    assert lcd.rows_content[1].startswith("Kind of Blue")
    display.close()


def test_backlight_sleeps_after_timeout_and_wakes():
    lcd = MemoryLcd()
    display = Display(lcd, backlight_timeout_s=60)
    assert lcd.backlight is True
    display._last_wake -= 61                     # simule 61 s d'inactivité
    with display._lock:
        display._maybe_sleep_locked(time.monotonic())
    assert lcd.backlight is False
    display.wake()
    assert lcd.backlight is True
    display.close()


def test_backlight_timeout_zero_never_sleeps():
    lcd = MemoryLcd()
    display = Display(lcd, backlight_timeout_s=0)
    display._last_wake -= 10000
    with display._lock:
        display._maybe_sleep_locked(time.monotonic())
    assert lcd.backlight is True
    display.close()
