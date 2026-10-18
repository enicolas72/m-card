"""Roon client: server discovery, pairing, album playback,
commandes de transport et suivi du morceau en cours.

Built on the `roonapi` library (pyroon). On first run, the "M-Card"
extension must be enabled in Roon: Settings -> Extensions -> Enable. The
token is then persisted in `token_file` and reused.

All interactions go through a supervisor thread that (re)connects in a
loop, so a Roon restart or a Wi-Fi drop needs no intervention.
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


# Words ignored when comparing: "Vol. 1", "Volume 1" and "1" are equivalent.
_NOISE_WORDS = {"vol", "volume"}


def _norm(text: str) -> str:
    """Normalize a title for comparison: case, accents, punctuation, spaces.

    The result is a sequence of words separated by a single space.
    """
    text = text.replace("’", "'").replace("‘", "'").casefold()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.replace("'", "")  # "l'emprise" ~ "lemprise", not "l emprise"
    words = re.sub(r"[\W_]+", " ", text).split()
    return " ".join(w for w in words if w not in _NOISE_WORDS)


def _contains_words(outer: str, inner: str) -> bool:
    """Does `inner` appear in `outer` as whole words? (normalized titles)
    Keeps an album named "I" from matching every title containing the letter i."""
    return f" {inner} " in f" {outer} "


def _loose_eq(na: str, nb: str) -> bool:
    return bool(na) and bool(nb) and (
        na == nb or _contains_words(na, nb) or _contains_words(nb, na))


def titles_match(a: str, b: str) -> bool:
    """Do two album titles refer to the same album? (tolerant: case/accents/
    punctuation ignored, whole-word inclusion accepted —
    "Nevermore" ~ "Nevermore 2023")."""
    return _loose_eq(_norm(a), _norm(b))


def best_album_match(target: str, candidates: list[str]) -> tuple[Optional[str], list[str]]:
    """Find `target` in `candidates`, tolerantly.

    Returns (exact_library_title | None, suggestions).
    Priority: normalized equality, then whole-word inclusion (either way),
    the longest shared part winning. On a tie, returns None and up to 5
    suggestions for the logs.
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
    # Several inclusions: the longest shared part wins
    # ("Electronica: The Heart of Noise, Vol. 2" beats "Noise").
    # An inclusion = the shorter of the two titles, counted in words.
    shared = {c: min(len(nt.split()), len(_norm(c).split())) for c in partial}
    best = max(shared.values(), default=0)
    top = [c for c in partial if shared[c] == best]
    if len(top) == 1:
        return top[0], []
    return None, top[:5]


def album_path(title: str, artist: str, artists: set[str]) -> list[str]:
    """Roon browse path (for play_media) pointing at the album unambiguously:
    through the artist when listed in Library › Artists, otherwise through
    the album list (multi-artist albums, unknown artist)."""
    if artist and artist in artists:
        return ["Library", "Artists", artist, title]
    return ["Library", "Albums", title]


def search_library(
    query: str,
    albums: list[tuple[str, str]],
    artists: set[str],
    limit: int = 50,
) -> list[dict]:
    """Free-text library search: every word of `query` must appear
    (start or middle of a word, case/accents ignored) in the title or the
    artist. Returns at most `limit` sorted results
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
            warning = ("artist not in Library › Artists: path goes through "
                       "the album list")
            if title_count[title] > 1:
                warning += " — duplicate title, the first one will play"
        results.append({"title": title, "artist": artist, "path": path,
                        "warning": warning})
    results.sort(key=lambda r: (_norm(r["title"]), _norm(r["artist"])))
    return results[:limit]


class RoonClient:
    """Robust wrapper around RoonApi."""

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
        self._albums_cache: list[tuple[str, str]] = []  # (title, artist)
        self._albums_cache_ts: float = 0.0
        self._artists_cache: set[str] = set()
        self._lock = threading.Lock()
        # serializes library browsing (a card being played and a search from
        # the web UI can happen at the same time)
        self._browse_lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._supervise, daemon=True, name="roon-client")
        self.connected = False

    # ---- lifecycle -------------------------------------------------------

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
                # Connected: sleep while the API is alive; events arrive
                # through callbacks. Re-check periodically.
                while not self._stop.wait(10.0):
                    with self._lock:
                        api = self._api
                    if api is None:
                        break
                    try:
                        # a lightweight access serves as a heartbeat
                        _ = api.zones
                    except Exception as exc:
                        raise ConnectionError(f"Roon connection lost: {exc}")
            except Exception as exc:
                if self._stop.is_set():
                    break
                self._set_connected(False, str(exc))
                log.warning("Roon unavailable (%s), retrying in %.0fs", exc, RECONNECT_DELAY_S)
                with self._lock:
                    if self._api is not None:
                        try:
                            self._api.stop()
                        except Exception:
                            pass
                        self._api = None
                self._stop.wait(RECONNECT_DELAY_S)

    def _connect_once(self) -> None:
        from roonapi import RoonApi, RoonDiscovery  # lazy import

        host, port = self._host, self._port
        if not host:
            log.info("Discovering the Roon server on the local network...")
            discovery = RoonDiscovery(None)
            try:
                server = discovery.first()
            finally:
                discovery.stop()
            if not server or not server[0]:
                raise ConnectionError("no Roon server found")
            host, port = server[0], server[1]
            log.info("Roon server found: %s:%s", host, port)

        token = None
        if self._token_file.exists():
            token = self._token_file.read_text(encoding="utf-8").strip() or None

        if token is None:
            log.warning(
                "No Roon token: enable the \"M-Card\" extension in "
                "Roon -> Settings -> Extensions (this may take a while)"
            )

        api = RoonApi(APP_INFO, token, host, port, blocking_init=True)
        if api.token is None:
            raise ConnectionError("extension not enabled in Roon")

        self._token_file.parent.mkdir(parents=True, exist_ok=True)
        self._token_file.write_text(api.token, encoding="utf-8")

        with self._lock:
            self._api = api
        api.register_state_callback(self._on_state_change, event_filter=["zones_changed"])
        self._set_connected(True, f"{host}:{port}")
        log.info("Connected to Roon (%s:%s), zones: %s",
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
            log.warning("Zone \"%s\" not found, zones: %s",
                        self._zone_name, [z.get("display_name") for z in zones.values()])
            return None
        return next(iter(zones.values()))

    def zone_display_name(self) -> str:
        zone = self._zone()
        return zone.get("display_name", "?") if zone else "?"

    # ---- commands --------------------------------------------------------

    def play_album(self, entry: AlbumEntry) -> bool:
        """Start playing an album (by explicit path or by name).

        play_media needs the exact title (case and accents included) and its
        return value is unreliable (None either way depending on the pyroon
        version): so the canonical title is resolved BEFORE playing, from the
        library's actual album list (cached).
        """
        with self._lock:
            api = self._api
        zone = self._zone()
        if api is None or zone is None:
            log.error("Cannot play: no Roon connection or zone")
            return False
        zone_id = zone["zone_id"]

        if entry.path:  # explicit path: strict match assumed
            log.info("Playing %s on zone \"%s\" (path %s)",
                     entry.display_name(), zone.get("display_name"), entry.path)
            return self._play_path(api, zone_id, entry.path)

        with self._browse_lock:
            title = self._resolve_album_title(api, entry.album)
        if title is None:
            return False
        if title != entry.album:
            log.info("\"%s\" resolved to \"%s\" — tip: copy this title into "
                     "albums.yaml", entry.album, title)
        log.info("Playing \"%s\" on zone \"%s\"", title, zone.get("display_name"))
        return self._play_path(api, zone_id, ["Library", "Albums", title])

    def _play_path(self, api, zone_id: str, path: list[str]) -> bool:
        try:
            with self._browse_lock:
                api.play_media(zone_id, path)
            return True
        except Exception as exc:
            log.error("play_media failed: %s", exc)
            return False

    def _resolve_album_title(self, api, album: str) -> Optional[str]:
        """Canonical title of the album in the library, or None (with logs)."""
        titles, from_cache = self._album_titles_cached(api)
        found, suggestions = best_album_match(album, titles)
        if found is None and from_cache:
            # the library may have changed since caching: refresh
            titles, _ = self._album_titles_cached(api, force_refresh=True)
            found, suggestions = best_album_match(album, titles)
        if found is not None:
            return found
        if suggestions:
            log.error("\"%s\" is ambiguous in the library, candidates: %s — "
                      "use a more precise title in albums.yaml", album, suggestions)
        else:
            log.error("\"%s\" not found in the library (%d albums scanned)",
                      album, len(titles))
        return None

    def search_albums(self, query: str, limit: int = 50) -> Optional[list[dict]]:
        """Free-text search for the web UI; None if Roon is disconnected."""
        with self._lock:
            api = self._api
        if api is None:
            return None
        with self._browse_lock:
            self._album_titles_cached(api)
            albums, artists = self._albums_cache, self._artists_cache
        return search_library(query, albums, artists, limit)

    def _album_titles_cached(self, api, force_refresh: bool = False) -> tuple[list[str], bool]:
        """(titles, served_from_cache) — cache refreshed after 5 min.
        Also refreshes the artist list (used by the search)."""
        import time

        now = time.monotonic()
        if (not force_refresh and self._albums_cache
                and now - self._albums_cache_ts < 300):
            return [t for t, _ in self._albums_cache], True
        albums = [(item.get("title", ""), item.get("subtitle", "") or "")
                  for item in self._list_items(api, "albums")]
        if albums:  # never overwrite a valid cache with a failed scan
            self._albums_cache = albums
            self._albums_cache_ts = now
            artists = {item.get("title", "") for item in self._list_items(api, "artists")}
            if artists:
                self._artists_cache = artists
        return [t for t, _ in self._albums_cache], False

    def _list_items(self, api, hierarchy: str) -> list[dict]:
        """List every item of a Roon hierarchy ('albums', 'artists'),
        paginated. For 'albums': title = album, subtitle = artist."""
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
            log.error("Cannot scan the library (%s): %s", hierarchy, exc)
            return []

    def control(self, action: str) -> None:
        """action: play | pause | playpause | next | previous | stop"""
        with self._lock:
            api = self._api
        zone = self._zone()
        if api is None or zone is None:
            log.warning("Command \"%s\" ignored: Roon not connected", action)
            return
        try:
            api.playback_control(zone["zone_id"], control=action)
            log.info("Transport command: %s", action)
        except Exception as exc:
            log.error("Command \"%s\" failed: %s", action, exc)

    # ---- state -----------------------------------------------------------

    def _on_state_change(self, event: str, changed_ids: list[str]) -> None:
        try:
            self._publish_now_playing()
        except Exception as exc:  # a callback must never kill the roonapi thread
            log.error("Error in the Roon state callback: %s", exc)

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
