"""Central controller: consumes the event queue and orchestrates Roon,
the display and the album table.

Business rules:
- known card       -> play the album on Roon
- TODO card        -> "to set up" message on the display
- unknown card     -> automatically added as TODO to albums.yaml + message
- card removed     -> pause / stop / nothing (configurable)
- buttons          -> Roon transport commands
"""

from __future__ import annotations

import logging
import queue
import time
from typing import Optional

from .config import AlbumStore, AppConfig
from .roon_client import titles_match
from .events import (
    ButtonPressed,
    CardPresented,
    CardRemoved,
    NowPlaying,
    RoonConnection,
    Shutdown,
)

log = logging.getLogger(__name__)

BUTTON_TO_ROON = {
    "prev": "previous",
    "playpause": "playpause",  # play/pause toggle on the Roon side
    "next": "next",
    # legacy names (4-button config) still accepted
    "play": "play",
    "pause": "pause",
}


class Controller:
    def __init__(self, config: AppConfig, albums: AlbumStore, display, roon=None):
        self._config = config
        self._albums = albums
        self._display = display
        self.roon = roon  # injected after creation (it needs our queue)
        self.queue: "queue.Queue" = queue.Queue()

        self._on_card_removed = config.get("behavior", "on_card_removed", default="pause")
        self._cooldown_s = float(config.get("behavior", "redetect_cooldown_s", default=3.0))
        self._last_uid: Optional[str] = None
        self._last_uid_ts: float = 0.0

        # state exposed to the web server
        self.status: dict = {
            "roon_connected": False,
            "roon_message": "",
            "state": "stopped",
            "album": "",
            "track": "",
            "artist": "",
            "card_uid": "",
            "card_album": "",
        }

    # ------------------------------------------------------------------

    def run(self) -> None:
        """Main loop (blocking); returns on a Shutdown event."""
        self._display.show_waiting()
        while True:
            event = self.queue.get()
            try:
                if isinstance(event, Shutdown):
                    log.info("Controller stopping")
                    return
                self._handle(event)
            except Exception:
                log.exception("Error while handling %r", event)

    def shutdown(self) -> None:
        self.queue.put(Shutdown())

    # ------------------------------------------------------------------

    def _handle(self, event) -> None:
        # any physical interaction wakes the backlight up
        if isinstance(event, (CardPresented, CardRemoved, ButtonPressed)):
            self._display.wake()
        if isinstance(event, CardPresented):
            self._handle_card(event.uid)
        elif isinstance(event, CardRemoved):
            self._handle_card_removed(event.uid)
        elif isinstance(event, ButtonPressed):
            action = BUTTON_TO_ROON.get(event.name)
            if action:
                self.roon.control(action)
        elif isinstance(event, NowPlaying):
            self.status.update(
                state=event.state, album=event.album, track=event.track, artist=event.artist
            )
            if event.state in ("playing", "paused", "loading"):
                self._display.show_now_playing(event.state, event.album, event.track, event.artist)
            else:
                self._display.show_waiting()
        elif isinstance(event, RoonConnection):
            self.status.update(roon_connected=event.connected, roon_message=event.message)
            if event.connected:
                log.info("Roon connected (%s)", event.message)
                if self.status["state"] not in ("playing", "paused"):
                    self._display.show_waiting()
            else:
                log.warning("Roon disconnected (%s)", event.message)
                self._display.show_error("Roon unreachable", "Check server/Wi-Fi")
        else:
            log.debug("Event ignored: %r", event)

    def _handle_card(self, uid: str) -> None:
        now = time.monotonic()
        if uid == self._last_uid and (now - self._last_uid_ts) < self._cooldown_s:
            log.debug("Card %s re-detected during the cooldown, ignored", uid)
            self._last_uid_ts = now
            return
        self._last_uid = uid
        self._last_uid_ts = now

        entry = self._albums.lookup(uid)
        if entry is None:
            entry = self._albums.add_todo(uid)
            self.status.update(card_uid=uid, card_album="TODO (new card)")
            self._display.show_unknown_card(uid)
            return
        if entry.is_todo:
            self.status.update(card_uid=uid, card_album="TODO")
            self._display.show_todo_card(uid)
            return

        self.status.update(card_uid=uid, card_album=entry.display_name())

        # same album as the one playing: don't disturb playback
        # (lets you pick the record up, look at it and put it back)
        if titles_match(entry.display_name(), self.status.get("album", "")):
            state = self.status.get("state", "")
            if state == "playing":
                log.info("Card %s: \"%s\" is already playing, nothing to do",
                         uid, entry.display_name())
                return
            if state == "paused":
                log.info("Card %s: \"%s\" is paused, resuming", uid, entry.display_name())
                self.roon.control("playpause")
                return

        self._display.set_lines("Starting...", entry.display_name(), entry.artist, "")
        if not self.roon.play_album(entry):
            self._display.show_error("Album not found", entry.display_name())

    def _handle_card_removed(self, uid: str) -> None:
        self.status.update(card_uid="", card_album="")
        action = self._on_card_removed
        if action == "pause":
            self.roon.control("pause")
        elif action == "stop":
            self.roon.control("stop")
        elif action != "none":
            log.warning("Invalid behavior.on_card_removed: %r", action)
