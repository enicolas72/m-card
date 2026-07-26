"""Client Roon : découverte du serveur, appairage, lancement d'albums,
commandes de transport et suivi du morceau en cours.

S'appuie sur la bibliothèque `roonapi` (pyroon). Au premier lancement,
l'extension « M-Card » doit être autorisée dans Roon :
Settings -> Extensions -> Enable. Le jeton est ensuite persisté dans
`token_file` et réutilisé.

Toutes les interactions passent par un thread superviseur qui (re)connecte
en boucle, si bien qu'un redémarrage de Roon ou une coupure Wi-Fi ne
nécessite aucune intervention.
"""

from __future__ import annotations

import logging
import queue
import threading
from pathlib import Path
from typing import Any, Optional

from . import __version__
from .config import AlbumEntry
from .events import NowPlaying, RoonConnection

log = logging.getLogger(__name__)

APP_INFO = {
    "extension_id": "fr.famille-nicolas.mcard",
    "display_name": "M-Card",
    "display_version": __version__,
    "publisher": "eric@famille-nicolas.fr",
    "email": "eric@famille-nicolas.fr",
}

RECONNECT_DELAY_S = 5.0


class RoonClient:
    """Enveloppe robuste autour de RoonApi."""

    def __init__(
        self,
        event_queue: "queue.Queue",
        host: str = "",
        port: int = 9330,
        zone_name: str = "",
        token_file: str | Path = "roon_token.txt",
    ):
        self._queue = event_queue
        self._host = host
        self._port = port
        self._zone_name = zone_name
        self._token_file = Path(token_file)
        self._api = None
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._supervise, daemon=True, name="roon-client")
        self.connected = False

    # ---- cycle de vie ----------------------------------------------------

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        with self._lock:
            if self._api is not None:
                try:
                    self._api.stop()
                except Exception:
                    pass
                self._api = None
        self._thread.join(timeout=5)

    def _supervise(self) -> None:
        while not self._stop.is_set():
            try:
                self._connect_once()
                # Connexion OK : on dort tant que l'API vit ; les événements
                # arrivent par callback. On revalide périodiquement.
                while not self._stop.wait(10.0):
                    with self._lock:
                        api = self._api
                    if api is None:
                        break
                    try:
                        # un accès léger sert de battement de coeur
                        _ = api.zones
                    except Exception as exc:
                        raise ConnectionError(f"connexion Roon perdue: {exc}")
            except Exception as exc:
                if self._stop.is_set():
                    break
                self._set_connected(False, str(exc))
                log.warning("Roon indisponible (%s), nouvel essai dans %.0fs", exc, RECONNECT_DELAY_S)
                with self._lock:
                    if self._api is not None:
                        try:
                            self._api.stop()
                        except Exception:
                            pass
                        self._api = None
                self._stop.wait(RECONNECT_DELAY_S)

    def _connect_once(self) -> None:
        from roonapi import RoonApi, RoonDiscovery  # import paresseux

        host, port = self._host, self._port
        if not host:
            log.info("Découverte du serveur Roon sur le réseau local...")
            discovery = RoonDiscovery(None)
            try:
                server = discovery.first()
            finally:
                discovery.stop()
            if not server or not server[0]:
                raise ConnectionError("aucun serveur Roon découvert")
            host, port = server[0], server[1]
            log.info("Serveur Roon découvert: %s:%s", host, port)

        token = None
        if self._token_file.exists():
            token = self._token_file.read_text(encoding="utf-8").strip() or None

        if token is None:
            log.warning(
                "Pas de jeton Roon : autorisez l'extension « M-Card » dans "
                "Roon -> Settings -> Extensions (l'attente peut durer)"
            )

        api = RoonApi(APP_INFO, token, host, port, blocking_init=True)
        if api.token is None:
            raise ConnectionError("extension non autorisée dans Roon")

        self._token_file.parent.mkdir(parents=True, exist_ok=True)
        self._token_file.write_text(api.token, encoding="utf-8")

        with self._lock:
            self._api = api
        api.register_state_callback(self._on_state_change, event_filter=["zones_changed"])
        self._set_connected(True, f"{host}:{port}")
        log.info("Connecté à Roon (%s:%s), zones: %s",
                 host, port, [z.get("display_name") for z in api.zones.values()])
        self._publish_now_playing()

    # ---- zone ------------------------------------------------------------

    def _zone(self) -> Optional[dict[str, Any]]:
        with self._lock:
            api = self._api
        if api is None:
            return None
        zones = dict(api.zones)
        if not zones:
            return None
        if self._zone_name:
            for zone in zones.values():
                if zone.get("display_name", "").lower() == self._zone_name.lower():
                    return zone
            log.warning("Zone «%s» introuvable, zones: %s",
                        self._zone_name, [z.get("display_name") for z in zones.values()])
            return None
        return next(iter(zones.values()))

    def zone_display_name(self) -> str:
        zone = self._zone()
        return zone.get("display_name", "?") if zone else "?"

    # ---- commandes -------------------------------------------------------

    def play_album(self, entry: AlbumEntry) -> bool:
        """Lance la lecture d'un album (par chemin explicite ou par nom)."""
        with self._lock:
            api = self._api
        zone = self._zone()
        if api is None or zone is None:
            log.error("Lecture impossible: pas de connexion Roon ou de zone")
            return False
        path = entry.path or ["Library", "Albums", entry.album]
        zone_id = zone["zone_id"]
        log.info("Lecture de %s sur la zone «%s» (chemin %s)",
                 entry.display_name(), zone.get("display_name"), path)
        try:
            result = api.play_media(zone_id, path)
        except Exception as exc:
            log.error("play_media a échoué: %s", exc)
            return False
        if result is False:
            log.error("Album introuvable dans Roon: %s", path)
            return False
        return True

    def control(self, action: str) -> None:
        """action : play | pause | playpause | next | previous | stop"""
        with self._lock:
            api = self._api
        zone = self._zone()
        if api is None or zone is None:
            log.warning("Commande «%s» ignorée: Roon non connecté", action)
            return
        try:
            api.playback_control(zone["zone_id"], control=action)
            log.info("Commande transport: %s", action)
        except Exception as exc:
            log.error("Commande «%s» en échec: %s", action, exc)

    # ---- état ------------------------------------------------------------

    def _on_state_change(self, event: str, changed_ids: list[str]) -> None:
        try:
            self._publish_now_playing()
        except Exception as exc:  # un callback ne doit jamais tuer le thread roonapi
            log.error("Erreur dans le callback d'état Roon: %s", exc)

    def _publish_now_playing(self) -> None:
        zone = self._zone()
        if zone is None:
            return
        state = zone.get("state", "stopped")
        now = zone.get("now_playing") or {}
        three = now.get("three_line") or {}
        self._queue.put(
            NowPlaying(
                state=state,
                track=three.get("line1", ""),
                artist=three.get("line2", ""),
                album=three.get("line3", ""),
            )
        )

    def _set_connected(self, connected: bool, message: str = "") -> None:
        if connected != self.connected:
            self.connected = connected
            self._queue.put(RoonConnection(connected=connected, message=message))
