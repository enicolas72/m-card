"""Événements échangés entre les threads matériels et le contrôleur central.

Tous les composants (NFC, boutons, Roon) poussent des événements dans une
queue.Queue unique ; le contrôleur les consomme séquentiellement, ce qui
évite tout verrouillage compliqué.
"""

from dataclasses import dataclass, field
import time


@dataclass
class Event:
    ts: float = field(default_factory=time.time, init=False)


@dataclass
class CardPresented(Event):
    uid: str


@dataclass
class CardRemoved(Event):
    uid: str


@dataclass
class ButtonPressed(Event):
    name: str  # "prev" | "play" | "pause" | "next"


@dataclass
class NowPlaying(Event):
    state: str  # "playing" | "paused" | "loading" | "stopped"
    album: str = ""
    track: str = ""
    artist: str = ""


@dataclass
class RoonConnection(Event):
    connected: bool
    message: str = ""


@dataclass
class Shutdown(Event):
    pass
