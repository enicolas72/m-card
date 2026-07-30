"""Implémentations simulées du matériel, pour développer et tester sans
Raspberry Pi (mode `--fake`, utilisable sur Mac/PC).

- FakeLcdBackend  : affiche les 4 lignes du LCD dans le terminal
- FakeNfcReader   : tapez un UID + Entrée pour « poser » une carte,
                    Entrée seule pour la « retirer »
- FakeRoonClient  : journalise les commandes et simule un morceau en cours
"""

from __future__ import annotations

import logging
import queue
import sys
import threading

from .config import AlbumEntry
from .display import LcdBackend
from .events import CardPresented, CardRemoved, NowPlaying, RoonConnection, Shutdown

log = logging.getLogger(__name__)


class FakeLcdBackend(LcdBackend):
    cols = 20
    rows = 4

    def __init__(self):
        self._lines = [""] * self.rows

    def write_row(self, row: int, text: str) -> None:
        self._lines[row] = text
        border = "+" + "-" * self.cols + "+"
        print("\n".join(["[LCD]", border] +
                        [f"|{line.ljust(self.cols)[:self.cols]}|" for line in self._lines] +
                        [border]))

    def set_backlight(self, on: bool) -> None:
        print(f"[LCD] rétro-éclairage {'ON' if on else 'OFF (veille)'}")


class FakeNfcReader:
    """Simule le lecteur : saisie d'UID au clavier."""

    def __init__(self, event_queue: "queue.Queue"):
        self._queue = event_queue
        self._current: str | None = None
        self._thread = threading.Thread(target=self._run, daemon=True, name="fake-nfc")

    def start(self) -> None:
        print("[FAKE NFC] tapez un UID (ex: 04A1B2C3) + Entrée pour poser une carte, "
              "Entrée seule pour la retirer")
        self._thread.start()

    def stop(self) -> None:
        pass

    def _run(self) -> None:
        for line in sys.stdin:
            uid = line.strip().upper()
            if uid:
                if self._current:
                    self._queue.put(CardRemoved(uid=self._current))
                self._current = uid
                self._queue.put(CardPresented(uid=uid))
            elif self._current:
                self._queue.put(CardRemoved(uid=self._current))
                self._current = None
        # stdin fermé (EOF) : en mode simulé, on arrête l'application
        self._queue.put(Shutdown())


class FakeRoonClient:
    """Simule Roon : accepte tout album ne contenant pas « introuvable »."""

    def __init__(self, event_queue: "queue.Queue"):
        self._queue = event_queue
        self.connected = False

    def start(self) -> None:
        self.connected = True
        self._queue.put(RoonConnection(connected=True, message="simulé"))

    def stop(self) -> None:
        pass

    def zone_display_name(self) -> str:
        return "Zone simulée"

    def play_album(self, entry: AlbumEntry) -> bool:
        if "introuvable" in entry.display_name().lower():
            return False
        log.info("[FAKE ROON] lecture de «%s»", entry.display_name())
        self._queue.put(NowPlaying(state="playing", album=entry.display_name(),
                                   track="Piste 1", artist=entry.artist))
        return True

    def control(self, action: str) -> None:
        log.info("[FAKE ROON] commande: %s", action)
        state = {"pause": "paused", "stop": "stopped"}.get(action, "playing")
        self._queue.put(NowPlaying(state=state, album="Album simulé",
                                   track=f"Piste après «{action}»", artist=""))
