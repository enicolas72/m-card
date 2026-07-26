"""Pilotage de l'écran LCD 2004 (20x4) via backpack I2C PCF8574.

Le HD44780 (ROM A00) n'affiche pas les caractères accentués : on translittère
en ASCII. Les lignes plus longues que 20 caractères défilent en boucle grâce
à un petit thread « ticker ».

L'implémentation matérielle (RPLCD) est importée paresseusement pour que le
reste du logiciel (tests, mode --fake) tourne sans les bibliothèques Pi.
"""

from __future__ import annotations

import logging
import threading
import time
import unicodedata

log = logging.getLogger(__name__)

SCROLL_PERIOD_S = 0.6
SCROLL_GAP = "   "  # séparateur visuel entre fin et début du texte qui défile

STATE_ICONS = {
    "playing": ">",
    "paused": "||",
    "stopped": "[]",
    "loading": "..",
}


def to_lcd_ascii(text: str) -> str:
    """Translittère les accents/typo Unicode vers l'ASCII affichable du HD44780."""
    text = text.replace("œ", "oe").replace("Œ", "OE").replace("æ", "ae").replace("Æ", "AE")
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    text = text.replace("–", "-").replace("—", "-").replace("…", "...")
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if ord(c) < 128 and c.isprintable() or c == " ")


class LcdBackend:
    """Interface minimale attendue par Display (implémentée par le vrai LCD et le fake)."""

    cols = 20
    rows = 4

    def write_row(self, row: int, text: str) -> None:  # pragma: no cover
        raise NotImplementedError

    def close(self) -> None:  # pragma: no cover
        pass


class CharLcdBackend(LcdBackend):
    """Backend réel : RPLCD sur le bus I2C du Raspberry Pi."""

    def __init__(self, i2c_address: int, i2c_port: int, cols: int, rows: int):
        from RPLCD.i2c import CharLCD  # import paresseux (indisponible hors Pi)

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

    def close(self) -> None:
        try:
            self._lcd.clear()
            self._lcd.close()
        except Exception:  # l'écran peut déjà être débranché à l'arrêt
            pass


class Display:
    """Affichage 4 lignes avec défilement automatique des lignes trop longues."""

    def __init__(self, backend: LcdBackend):
        self._backend = backend
        self._lock = threading.Lock()
        self._lines = [""] * backend.rows
        self._offsets = [0] * backend.rows
        self._stop = threading.Event()
        self._ticker = threading.Thread(target=self._tick_loop, daemon=True, name="lcd-ticker")
        self._ticker.start()

    # ---- API haut niveau -------------------------------------------------

    def set_lines(self, *lines: str) -> None:
        with self._lock:
            for row in range(self._backend.rows):
                new = to_lcd_ascii(lines[row]) if row < len(lines) and lines[row] else ""
                if new != self._lines[row]:
                    self._lines[row] = new
                    self._offsets[row] = 0
            self._render_locked()

    def show_boot(self, version: str) -> None:
        self.set_lines("M-Card", f"v{version}", "Demarrage...", "")

    def show_waiting(self) -> None:
        self.set_lines("M-Card", "", "Posez un album", "")

    def show_now_playing(self, state: str, album: str, track: str, artist: str = "") -> None:
        icon = STATE_ICONS.get(state, "?")
        self.set_lines(f"{icon} {state}", album, track, artist)

    def show_unknown_card(self, uid: str) -> None:
        self.set_lines("Carte inconnue", f"UID {uid}", "Ajoutee au fichier", "albums.yaml (TODO)")

    def show_todo_card(self, uid: str) -> None:
        self.set_lines("Carte a configurer", f"UID {uid}", "Editez albums.yaml", "via l'interface web")

    def show_error(self, line1: str, line2: str = "") -> None:
        self.set_lines("! " + line1, line2, "", "")

    def close(self) -> None:
        self._stop.set()
        self._ticker.join(timeout=2)
        self._backend.close()

    # ---- Rendu / défilement ---------------------------------------------

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
                log.error("Ecriture LCD impossible: %s", exc)
                return

    def _tick_loop(self) -> None:
        while not self._stop.wait(SCROLL_PERIOD_S):
            with self._lock:
                changed = False
                for row in range(self._backend.rows):
                    if len(self._lines[row]) > self._backend.cols:
                        self._offsets[row] += 1
                        changed = True
                if changed:
                    self._render_locked()
