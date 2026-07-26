"""Contrôleur central : consomme la queue d'événements et orchestre
Roon, l'écran et la table d'albums.

Logique métier :
- carte connue     -> lecture de l'album sur Roon
- carte en TODO    -> message « à configurer » sur l'écran
- carte inconnue   -> ajout automatique en TODO dans albums.yaml + message
- carte retirée    -> pause / stop / rien (configurable)
- boutons          -> commandes de transport Roon
"""

from __future__ import annotations

import logging
import queue
import time
from typing import Optional

from .config import AlbumStore, AppConfig
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
    "playpause": "playpause",  # bascule lecture/pause côté Roon
    "next": "next",
    # anciens noms (config 4 boutons) toujours acceptés
    "play": "play",
    "pause": "pause",
}


class Controller:
    def __init__(self, config: AppConfig, albums: AlbumStore, display, roon=None):
        self._config = config
        self._albums = albums
        self._display = display
        self.roon = roon  # injecté après création (il a besoin de notre queue)
        self.queue: "queue.Queue" = queue.Queue()

        self._on_card_removed = config.get("behavior", "on_card_removed", default="pause")
        self._cooldown_s = float(config.get("behavior", "redetect_cooldown_s", default=3.0))
        self._last_uid: Optional[str] = None
        self._last_uid_ts: float = 0.0

        # état exposé au serveur web
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
        """Boucle principale (bloquante) ; sort sur événement Shutdown."""
        self._display.show_waiting()
        while True:
            event = self.queue.get()
            try:
                if isinstance(event, Shutdown):
                    log.info("Arrêt du contrôleur")
                    return
                self._handle(event)
            except Exception:
                log.exception("Erreur lors du traitement de %r", event)

    def shutdown(self) -> None:
        self.queue.put(Shutdown())

    # ------------------------------------------------------------------

    def _handle(self, event) -> None:
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
                log.info("Roon connecté (%s)", event.message)
                if self.status["state"] not in ("playing", "paused"):
                    self._display.show_waiting()
            else:
                log.warning("Roon déconnecté (%s)", event.message)
                self._display.show_error("Roon inaccessible", "Verifiez serveur/wifi")
        else:
            log.debug("Événement ignoré: %r", event)

    def _handle_card(self, uid: str) -> None:
        now = time.monotonic()
        if uid == self._last_uid and (now - self._last_uid_ts) < self._cooldown_s:
            log.debug("Carte %s re-détectée pendant le cooldown, ignorée", uid)
            self._last_uid_ts = now
            return
        self._last_uid = uid
        self._last_uid_ts = now

        entry = self._albums.lookup(uid)
        if entry is None:
            entry = self._albums.add_todo(uid)
            self.status.update(card_uid=uid, card_album="TODO (nouvelle carte)")
            self._display.show_unknown_card(uid)
            return
        if entry.is_todo:
            self.status.update(card_uid=uid, card_album="TODO")
            self._display.show_todo_card(uid)
            return

        self.status.update(card_uid=uid, card_album=entry.display_name())
        self._display.set_lines("Lancement...", entry.display_name(), entry.artist, "")
        if not self.roon.play_album(entry):
            self._display.show_error("Album introuvable", entry.display_name())

    def _handle_card_removed(self, uid: str) -> None:
        self.status.update(card_uid="", card_album="")
        action = self._on_card_removed
        if action == "pause":
            self.roon.control("pause")
        elif action == "stop":
            self.roon.control("stop")
        elif action != "none":
            log.warning("behavior.on_card_removed invalide: %r", action)
