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
import re
import threading
import unicodedata
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


# Mots ignorés à la comparaison : « Vol. 1 », « Volume 1 » et « 1 » se valent.
_NOISE_WORDS = {"vol", "volume"}


def _norm(text: str) -> str:
    """Normalise un titre pour comparaison : casse, accents, ponctuation, espaces.

    Le résultat est une suite de mots séparés par une espace unique.
    """
    text = text.replace("’", "'").replace("‘", "'").casefold()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.replace("'", "")  # « l'emprise » ~ « lemprise », pas « l emprise »
    words = re.sub(r"[\W_]+", " ", text).split()
    return " ".join(w for w in words if w not in _NOISE_WORDS)


def _contains_words(outer: str, inner: str) -> bool:
    """`inner` apparaît-il dans `outer` en mots entiers ? (titres normalisés)
    Évite qu'un album « I » corresponde à tout titre contenant la lettre i."""
    return f" {inner} " in f" {outer} "


def _loose_eq(na: str, nb: str) -> bool:
    return bool(na) and bool(nb) and (
        na == nb or _contains_words(na, nb) or _contains_words(nb, na))


def titles_match(a: str, b: str) -> bool:
    """Deux titres d'album désignent-ils le même album ? (tolérant :
    casse/accents/ponctuation ignorés, inclusion en mots entiers acceptée —
    « Nevermore » ~ « Nevermore 2023 »)."""
    return _loose_eq(_norm(a), _norm(b))


def best_album_match(target: str, candidates: list[str]) -> tuple[Optional[str], list[str]]:
    """Retrouve `target` dans `candidates` avec tolérance.

    Retourne (titre_exact_de_la_bibliothèque | None, suggestions).
    Priorité : égalité normalisée, puis inclusion en mots entiers (dans un
    sens ou l'autre), la plus longue partie commune l'emportant. En cas
    d'égalité, retourne None et jusqu'à 5 suggestions pour les logs.
    """
    nt = _norm(target)
    if not nt:
        return None, []
    exact = [c for c in candidates if _norm(c) == nt]
    if exact:
        return exact[0], []
    partial = [c for c in candidates if _loose_eq(nt, _norm(c))]
    if len(partial) == 1:
        return partial[0], []
    # Plusieurs inclusions : la plus longue partie commune l'emporte
    # (« Electronica: The Heart of Noise, Vol. 2 » bat « Noise »).
    # Une inclusion = le plus court des deux titres, compté en mots.
    shared = {c: min(len(nt.split()), len(_norm(c).split())) for c in partial}
    best = max(shared.values(), default=0)
    top = [c for c in partial if shared[c] == best]
    if len(top) == 1:
        return top[0], []
    return None, top[:5]


def album_path(title: str, artist: str, artists: set[str]) -> list[str]:
    """Chemin de navigation Roon (pour play_media) désignant l'album sans
    ambiguïté : par l'artiste quand il figure dans Library › Artists, sinon
    par la liste des albums (albums multi-artistes, artiste inconnu)."""
    if artist and artist in artists:
        return ["Library", "Artists", artist, title]
    return ["Library", "Albums", title]


def search_library(
    query: str,
    albums: list[tuple[str, str]],
    artists: set[str],
    limit: int = 50,
) -> list[dict]:
    """Recherche libre dans la bibliothèque : chaque mot de `query` doit
    apparaître (début de mot ou au milieu, casse/accents ignorés) dans le
    titre ou l'artiste. Retourne au plus `limit` résultats triés
    {title, artist, path, warning}."""
    words = _norm(query).split()
    if not words:
        return []
    title_count: dict[str, int] = {}
    for title, _ in albums:
        title_count[title] = title_count.get(title, 0) + 1
    results = []
    for title, artist in albums:
        haystack = _norm(f"{title} {artist}")
        if not all(w in haystack for w in words):
            continue
        path = album_path(title, artist, artists)
        warning = ""
        if path[1] == "Albums":
            warning = ("artiste absent de Library › Artists : chemin par la "
                       "liste des albums")
            if title_count[title] > 1:
                warning += " — titre homonyme, le premier sera joué"
        results.append({"title": title, "artist": artist, "path": path,
                        "warning": warning})
    results.sort(key=lambda r: (_norm(r["title"]), _norm(r["artist"])))
    return results[:limit]


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
        self._albums_cache: list[tuple[str, str]] = []  # (titre, artiste)
        self._albums_cache_ts: float = 0.0
        self._artists_cache: set[str] = set()
        self._lock = threading.Lock()
        # sérialise les parcours de la bibliothèque (lecture d'une carte et
        # recherche depuis l'interface web peuvent arriver en même temps)
        self._browse_lock = threading.Lock()
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
        """Lance la lecture d'un album (par chemin explicite ou par nom).

        play_media exige le titre exact (casse et accents compris) et sa
        valeur de retour n'est pas fiable (None dans les deux cas selon les
        versions de pyroon) : on résout donc le titre canonique AVANT de
        jouer, via la liste réelle des albums de la bibliothèque (en cache).
        """
        with self._lock:
            api = self._api
        zone = self._zone()
        if api is None or zone is None:
            log.error("Lecture impossible: pas de connexion Roon ou de zone")
            return False
        zone_id = zone["zone_id"]

        if entry.path:  # chemin explicite : correspondance stricte assumée
            log.info("Lecture de %s sur la zone «%s» (chemin %s)",
                     entry.display_name(), zone.get("display_name"), entry.path)
            return self._play_path(api, zone_id, entry.path)

        with self._browse_lock:
            title = self._resolve_album_title(api, entry.album)
        if title is None:
            return False
        if title != entry.album:
            log.info("«%s» résolu en «%s» — conseil : reporter ce titre dans "
                     "albums.yaml", entry.album, title)
        log.info("Lecture de «%s» sur la zone «%s»", title, zone.get("display_name"))
        return self._play_path(api, zone_id, ["Library", "Albums", title])

    def _play_path(self, api, zone_id: str, path: list[str]) -> bool:
        try:
            with self._browse_lock:
                api.play_media(zone_id, path)
            return True
        except Exception as exc:
            log.error("play_media a échoué: %s", exc)
            return False

    def _resolve_album_title(self, api, album: str) -> Optional[str]:
        """Titre canonique de l'album dans la bibliothèque, ou None (avec logs)."""
        titles, from_cache = self._album_titles_cached(api)
        found, suggestions = best_album_match(album, titles)
        if found is None and from_cache:
            # la bibliothèque a pu changer depuis le cache : on rafraîchit
            titles, _ = self._album_titles_cached(api, force_refresh=True)
            found, suggestions = best_album_match(album, titles)
        if found is not None:
            return found
        if suggestions:
            log.error("«%s» est ambigu dans la bibliothèque, candidats : %s — "
                      "précisez le titre dans albums.yaml", album, suggestions)
        else:
            log.error("«%s» introuvable dans la bibliothèque (%d albums parcourus)",
                      album, len(titles))
        return None

    def search_albums(self, query: str, limit: int = 50) -> Optional[list[dict]]:
        """Recherche libre pour l'interface web ; None si Roon est déconnecté."""
        with self._lock:
            api = self._api
        if api is None:
            return None
        with self._browse_lock:
            self._album_titles_cached(api)
            albums, artists = self._albums_cache, self._artists_cache
        return search_library(query, albums, artists, limit)

    def _album_titles_cached(self, api, force_refresh: bool = False) -> tuple[list[str], bool]:
        """(titres, servi_depuis_le_cache) — cache rafraîchi au-delà de 5 min.
        Rafraîchit aussi la liste des artistes (utilisée par la recherche)."""
        import time

        now = time.monotonic()
        if (not force_refresh and self._albums_cache
                and now - self._albums_cache_ts < 300):
            return [t for t, _ in self._albums_cache], True
        albums = [(item.get("title", ""), item.get("subtitle", "") or "")
                  for item in self._list_items(api, "albums")]
        if albums:  # ne pas écraser un cache valide par un échec de parcours
            self._albums_cache = albums
            self._albums_cache_ts = now
            artists = {item.get("title", "") for item in self._list_items(api, "artists")}
            if artists:
                self._artists_cache = artists
        return [t for t, _ in self._albums_cache], False

    def _list_items(self, api, hierarchy: str) -> list[dict]:
        """Liste tous les éléments d'une hiérarchie Roon ('albums', 'artists'),
        paginée. Pour 'albums' : title = album, subtitle = artiste."""
        try:
            resp = api.browse_browse({"hierarchy": hierarchy, "pop_all": True})
            total = (resp or {}).get("list", {}).get("count", 0)
            items: list[dict] = []
            offset = 0
            while offset < total:
                load = api.browse_load(
                    {"hierarchy": hierarchy, "offset": offset,
                     "set_display_offset": offset}
                )
                batch = (load or {}).get("items", [])
                if not batch:
                    break
                items.extend(batch)
                offset += len(batch)
            return items
        except Exception as exc:
            log.error("Parcours de la bibliothèque (%s) impossible: %s", hierarchy, exc)
            return []

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
