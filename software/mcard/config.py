"""Chargement de la configuration générale (mcard.yaml) et de la table
RFID → album (albums.yaml).

albums.yaml est la seule donnée « vivante » : le contrôleur y ajoute
automatiquement une entrée `album: TODO` quand une carte inconnue est
présentée, et le serveur web permet de l'éditer. Le fichier est réécrit
entier à chaque modification, avec un en-tête explicatif.
"""

from __future__ import annotations

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
        # Laisser host vide => découverte automatique (SOOD) sur le réseau local.
        "host": "",
        "port": 9330,
        "zone_name": "",          # vide => première zone disponible
        "token_file": "/var/lib/mcard/roon_token.txt",
    },
    "behavior": {
        # Que faire quand on retire le CD/vinyle : none (l'album continue,
        # les boutons restent actifs) | pause | stop
        "on_card_removed": "none",
        # Ignorer une re-détection de la même carte pendant N secondes
        "redetect_cooldown_s": 3.0,
        # Carte considérée retirée après N secondes sans réponse (lisse le
        # test de présence défaillant de l'ACR122U sur certains tags)
        "removal_grace_s": 1.0,
    },
    "lcd": {
        "i2c_address": 0x27,       # PCF8574 « MH » : 0x27 par défaut (0x3F si A0-A2 pontés)
        "i2c_port": 1,
        "cols": 20,
        "rows": 4,
        # Veille du rétro-éclairage après N secondes sans interaction
        # (carte posée/retirée, bouton) ; 0 = toujours allumé
        "backlight_timeout_s": 120,
    },
    "buttons": {
        # Numérotation BCM. Chaque bouton relie la broche GPIO à GND.
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
    """Configuration générale, fusion des défauts et de mcard.yaml."""

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
                raise ValueError(f"{path}: le contenu doit être un mapping YAML")
            data = _deep_merge(DEFAULTS, loaded)
        else:
            log.warning("%s absent, utilisation des valeurs par défaut", path)
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
# M-Card — table de correspondance carte RFID -> album Roon
#
# Chaque clé est l'UID hexadécimal de la carte (affiché sur l'écran LCD et
# dans les logs quand une carte inconnue est posée).
#
# Formats acceptés pour chaque entrée :
#   "UID":
#     album: "Nom exact de l'album dans Roon"     # requis
#     artist: "Nom de l'artiste"                  # optionnel (info)
#   ou, pour lever une ambiguïté (albums homonymes), un chemin Roon explicite :
#   "UID":
#     path: ["Library", "Artists", "Miles Davis", "Kind of Blue"]
#
# Une entrée `album: TODO` est ajoutée automatiquement quand une carte
# inconnue est présentée : remplacez TODO par le nom de l'album, ou mieux,
# utilisez la page /search de l'interface web, qui donne (ou écrit
# directement) le chemin `path:` exact.
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
    """Accès thread-safe à albums.yaml (lecture, ajout auto, rechargement)."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = threading.Lock()
        self._entries: dict[str, AlbumEntry] = {}
        self.reload()

    def reload(self) -> None:
        with self._lock:
            self._entries = {}
            if not self.path.exists():
                log.warning("%s absent, table d'albums vide", self.path)
                return
            with open(self.path, encoding="utf-8") as fh:
                raw = yaml.safe_load(fh) or {}
            if not isinstance(raw, dict):
                raise ValueError(f"{self.path}: le contenu doit être un mapping YAML")
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
                    log.warning("%s: entrée %r ignorée (format invalide)", self.path, uid)
                    continue
                self._entries[uid] = entry
            log.info("%d albums chargés depuis %s", len(self._entries), self.path)

    def lookup(self, uid: str) -> Optional[AlbumEntry]:
        with self._lock:
            return self._entries.get(uid.upper())

    def add_todo(self, uid: str) -> AlbumEntry:
        """Enregistre une carte inconnue avec `album: TODO` et sauvegarde."""
        uid = uid.upper()
        with self._lock:
            if uid in self._entries:
                return self._entries[uid]
            entry = AlbumEntry(uid=uid, album=TODO_ALBUM)
            self._entries[uid] = entry
            self._save_locked()
            log.info("Carte inconnue %s ajoutée à %s avec album: TODO", uid, self.path)
            return entry

    def assign(self, uid: str, path: list[str], artist: str = "") -> AlbumEntry:
        """Associe une carte (existante ou non) à un chemin Roon et sauvegarde."""
        uid = uid.upper()
        with self._lock:
            entry = AlbumEntry(uid=uid, artist=artist, path=list(path))
            self._entries[uid] = entry
            self._save_locked()
            log.info("Carte %s associée à %s", uid, path)
            return entry

    def all(self) -> dict[str, AlbumEntry]:
        with self._lock:
            return dict(self._entries)

    def _save_locked(self) -> None:
        data: dict[str, Any] = {}
        for uid, entry in sorted(self._entries.items()):
            spec: dict[str, Any] = {}
            if entry.path:
                spec["path"] = entry.path
            else:
                spec["album"] = entry.album or TODO_ALBUM
            if entry.artist:
                spec["artist"] = entry.artist
            data[uid] = spec
        body = yaml.safe_dump(
            data, allow_unicode=True, sort_keys=True, default_flow_style=False
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".yaml.tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(ALBUMS_HEADER + "\n" + body)
        tmp.replace(self.path)
