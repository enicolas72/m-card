"""Events exchanged between the hardware threads and the central controller.

Every component (NFC, buttons, Roon) pushes events into a single
queue.Queue; the controller consumes them sequentially, which avoids any
complicated locking.
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
