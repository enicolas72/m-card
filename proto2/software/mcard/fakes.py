"""Simulated hardware implementations, to develop and test without a
Raspberry Pi (`--fake` mode, usable on Mac/PC).

- FakeLcdBackend  : prints the 4 LCD lines in the terminal
- FakeNfcReader   : type a UID + Enter to "place" a card,
                    Enter alone to "remove" it
- FakeRoonClient  : logs the commands and simulates a track playing
"""

from __future__ import annotations

import logging
import queue
import sys
import threading

from .config import AlbumEntry
from .roon_client import search_library
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
        print(f"[LCD] backlight {'ON' if on else 'OFF (sleep)'}")


class FakeNfcReader:
    """Simulates the reader: UIDs typed on the keyboard."""

    def __init__(self, event_queue: "queue.Queue"):
        self._queue = event_queue
        self._current: str | None = None
        self._thread = threading.Thread(target=self._run, daemon=True, name="fake-nfc")

    def start(self) -> None:
        print("[FAKE NFC] type a UID (e.g. 04A1B2C3) + Enter to place a card, "
              "Enter alone to remove it")
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
        # stdin closed (EOF): in fake mode, stop the application
        self._queue.put(Shutdown())


FAKE_LIBRARY = [
    ("Kind of Blue", "Miles Davis"),
    ("Electronica 1: The Time Machine", "Jean-Michel Jarre"),
    ("Electronica 2: The Heart of Noise", "Jean-Michel Jarre"),
    ("Greatest Hits", "Queen"),
    ("Greatest Hits", "ABBA"),
    ("Original Soundtrack", "Various Artists"),
]
FAKE_ARTISTS = {"Miles Davis", "Jean-Michel Jarre", "Queen", "ABBA"}


class FakeRoonClient:
    """Simulates Roon: accepts any album whose name doesn't contain "notfound"."""

    def __init__(self, event_queue: "queue.Queue"):
        self._queue = event_queue
        self.connected = False

    def start(self) -> None:
        self.connected = True
        self._queue.put(RoonConnection(connected=True, message="simulated"))

    def stop(self) -> None:
        pass

    def zone_display_name(self) -> str:
        return "Simulated zone"

    def play_album(self, entry: AlbumEntry) -> bool:
        if "notfound" in entry.display_name().lower():
            return False
        log.info("[FAKE ROON] playing \"%s\"", entry.display_name())
        self._queue.put(NowPlaying(state="playing", album=entry.display_name(),
                                   track="Track 1", artist=entry.artist))
        return True

    def search_albums(self, query: str, limit: int = 50) -> list[dict]:
        return search_library(query, FAKE_LIBRARY, FAKE_ARTISTS, limit)

    def control(self, action: str) -> None:
        log.info("[FAKE ROON] command: %s", action)
        state = {"pause": "paused", "stop": "stopped"}.get(action, "playing")
        self._queue.put(NowPlaying(state=state, album="Simulated album",
                                   track=f"Track after \"{action}\"", artist=""))
