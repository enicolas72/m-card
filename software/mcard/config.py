"""Loading of the general settings (mcard.yaml) and of the RFID → album
table (albums.yaml).

albums.yaml is the only "live" data: the controller automatically adds an
`album: TODO` entry when an unknown card is presented, and the web server
lets the user edit it. The file is rewritten in full on every change, with
an explanatory header.
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

log = logging.getLogger(__name__)

TODO_ALBUM = "TODO"

DEFAULTS: dict[str, Any] = {
    "roon": {
        # Leave host empty => automatic discovery (SOOD) on the local network.
        "host": "",
        "port": 9330,
        "zone_name": "",          # empty => first available zone
        "token_file": "/var/lib/mcard/roon_token.txt",
    },
    "behavior": {
        # What to do when the CD/vinyl is removed: none (the album keeps
        # playing, buttons stay active) | pause | stop
        "on_card_removed": "none",
        # Ignore a re-detection of the same card for N seconds
        "redetect_cooldown_s": 3.0,
        # Card considered removed after N seconds without an answer (smooths
        # the ACR122U's flaky presence check on some tags)
        "removal_grace_s": 1.0,
    },
    "lcd": {
        "i2c_address": 0x27,       # PCF8574 "MH": 0x27 by default (0x3F if A0-A2 bridged)
        "i2c_port": 1,
        "cols": 20,
        "rows": 4,
        # Backlight sleeps after N seconds without interaction
        # (card placed/removed, button); 0 = always on
        "backlight_timeout_s": 120,
    },
    "buttons": {
        # BCM numbering. Each button connects the GPIO pin to GND.
        "prev": 5,
        "playpause": 6,
        "next": 13,
    },
    "web": {
        "host": "0.0.0.0",
        "port": 8088,
    },
    "log": {
        "file": "/var/log/mcard/mcard.log",
        "level": "INFO",
        "max_bytes": 1_000_000,
        "backup_count": 5,
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


@dataclass
class AppConfig:
    """General settings: defaults merged with mcard.yaml."""

    data: dict[str, Any] = field(default_factory=lambda: dict(DEFAULTS))
    path: Optional[Path] = None

    @classmethod
    def load(cls, config_dir: Path) -> "AppConfig":
        path = config_dir / "mcard.yaml"
        data: dict[str, Any] = dict(DEFAULTS)
        if path.exists():
            with open(path, encoding="utf-8") as fh:
                loaded = yaml.safe_load(fh) or {}
            if not isinstance(loaded, dict):
                raise ValueError(f"{path}: content must be a YAML mapping")
            data = _deep_merge(DEFAULTS, loaded)
        else:
            log.warning("%s missing, using default values", path)
        return cls(data=data, path=path)

    def __getitem__(self, key: str) -> Any:
        return self.data[key]

    def get(self, *keys: str, default: Any = None) -> Any:
        node: Any = self.data
        for key in keys:
            if not isinstance(node, dict) or key not in node:
                return default
            node = node[key]
        return node


ALBUMS_HEADER = """\
# M-Card — RFID card -> Roon album mapping
#
# Each key is the card's hexadecimal UID (shown on the LCD and in the logs
# when an unknown card is placed).
#
# Accepted formats for each entry:
#   "UID":
#     path: ["Library", "Artists", "Miles Davis", "Kind of Blue"]   # recommended
#     artist: "Miles Davis"                                         # optional (info)
#   or the album title alone (matched tolerantly against the library):
#   "UID":
#     album: "Kind of Blue"
#
# An `album: TODO` entry is added automatically when an unknown card is
# placed: pair it from the /search page of the web console, which writes
# the exact `path:` for you.
"""


@dataclass
class AlbumEntry:
    uid: str
    album: str = ""
    artist: str = ""
    path: Optional[list[str]] = None

    @property
    def is_todo(self) -> bool:
        return self.path is None and (not self.album or self.album == TODO_ALBUM)

    def display_name(self) -> str:
        if self.path:
            return self.path[-1]
        return self.album


class AlbumStore:
    """Thread-safe access to albums.yaml (read, auto-add, reload)."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = threading.Lock()
        self._entries: dict[str, AlbumEntry] = {}
        self.reload()

    def reload(self) -> None:
        with self._lock:
            self._entries = {}
            if not self.path.exists():
                log.warning("%s missing, empty album table", self.path)
                return
            with open(self.path, encoding="utf-8") as fh:
                raw = yaml.safe_load(fh) or {}
            if not isinstance(raw, dict):
                raise ValueError(f"{self.path}: content must be a YAML mapping")
            for uid, spec in raw.items():
                uid = str(uid).upper()
                if isinstance(spec, str):
                    entry = AlbumEntry(uid=uid, album=spec)
                elif isinstance(spec, dict):
                    path = spec.get("path")
                    entry = AlbumEntry(
                        uid=uid,
                        album=str(spec.get("album", "") or ""),
                        artist=str(spec.get("artist", "") or ""),
                        path=[str(p) for p in path] if path else None,
                    )
                else:
                    log.warning("%s: entry %r ignored (invalid format)", self.path, uid)
                    continue
                self._entries[uid] = entry
            log.info("%d albums loaded from %s", len(self._entries), self.path)

    def reload_and_normalize(self) -> None:
        """Reload, then rewrite the file in the canonical format (after a
        manual edit through the web UI). Comments are lost, as with any
        automatic addition."""
        self.reload()
        with self._lock:
            self._save_locked()

    def lookup(self, uid: str) -> Optional[AlbumEntry]:
        with self._lock:
            return self._entries.get(uid.upper())

    def add_todo(self, uid: str) -> AlbumEntry:
        """Record an unknown card with `album: TODO` and save."""
        uid = uid.upper()
        with self._lock:
            if uid in self._entries:
                return self._entries[uid]
            entry = AlbumEntry(uid=uid, album=TODO_ALBUM)
            self._entries[uid] = entry
            self._save_locked()
            log.info("Unknown card %s added to %s with album: TODO", uid, self.path)
            return entry

    def assign(self, uid: str, path: list[str], artist: str = "") -> AlbumEntry:
        """Assign a card (existing or not) to a Roon path and save."""
        uid = uid.upper()
        with self._lock:
            entry = AlbumEntry(uid=uid, artist=artist, path=list(path))
            self._entries[uid] = entry
            self._save_locked()
            log.info("Card %s assigned to %s", uid, path)
            return entry

    def all(self) -> dict[str, AlbumEntry]:
        with self._lock:
            return dict(self._entries)

    def _save_locked(self) -> None:
        # Written by hand rather than with yaml.safe_dump: same format as the
        # /search page snippets (path on one line, path then artist), and the
        # UID always quoted (an all-digit UID would otherwise be read back as
        # an integer, losing its leading zeros).
        def q(text: str) -> str:
            return json.dumps(text, ensure_ascii=False)  # JSON ⊂ YAML

        lines: list[str] = []
        for uid, entry in sorted(self._entries.items()):
            lines.append(f"{q(uid)}:")
            if entry.path:
                lines.append(f"  path: [{', '.join(q(p) for p in entry.path)}]")
            else:
                lines.append(f"  album: {q(entry.album or TODO_ALBUM)}")
            if entry.artist:
                lines.append(f"  artist: {q(entry.artist)}")
        body = "\n".join(lines) + "\n" if lines else ""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".yaml.tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(ALBUMS_HEADER + "\n" + body)
        tmp.replace(self.path)
