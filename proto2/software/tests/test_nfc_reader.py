"""Presence/absence state machine of the NFC reader (no hardware).

Reproduces the real ACR122U behavior with a Mifare Ultralight tag: the
presence check fails and connect() "sees" the card intermittently while it
doesn't move. The grace period must smooth out this flickering.
"""

import queue

import pytest

from mcard.events import CardPresented, CardRemoved
from mcard.nfc_reader import NfcReader


class Tag:
    def __init__(self, uid_hex: str):
        self.identifier = bytes.fromhex(uid_hex)


@pytest.fixture
def reader():
    events = queue.Queue()
    r = NfcReader(events, removal_grace_s=1.0)
    return r, events


def drain(events):
    out = []
    while not events.empty():
        out.append(events.get_nowait())
    return out


def test_first_detection_emits_presented(reader):
    r, events = reader
    r._on_connect(Tag("040B9B7AAA4880"))
    (event,) = drain(events)
    assert isinstance(event, CardPresented)
    assert event.uid == "040B9B7AAA4880"


def test_flapping_same_card_is_silent(reader):
    """Repeated detections of the same card (every ~200 ms): no event."""
    r, events = reader
    r._on_connect(Tag("040B9B7AAA4880"))
    drain(events)
    for _ in range(10):
        r._on_connect(Tag("040B9B7AAA4880"))  # the card "flickers"
        r._note_tag_seen()
        r._maybe_emit_removed()               # the grace period is never exceeded
    assert drain(events) == []


def test_removed_only_after_grace(reader):
    r, events = reader
    r._on_connect(Tag("040B9B7AAA4880"))
    drain(events)
    r._last_seen -= 0.5                        # invisible for 0.5 s
    r._maybe_emit_removed()
    assert drain(events) == []                 # not removed yet
    r._last_seen -= 0.6                        # invisible for 1.1 s
    r._maybe_emit_removed()
    (event,) = drain(events)
    assert isinstance(event, CardRemoved)
    assert r._current_uid is None


def test_card_swap_emits_removed_then_presented(reader):
    r, events = reader
    r._on_connect(Tag("AAAAAAAA"))
    drain(events)
    r._on_connect(Tag("BBBBBBBB"))             # another card placed directly
    removed, presented = drain(events)
    assert isinstance(removed, CardRemoved) and removed.uid == "AAAAAAAA"
    assert isinstance(presented, CardPresented) and presented.uid == "BBBBBBBB"


def test_represent_after_removal_is_new_presentation(reader):
    r, events = reader
    r._on_connect(Tag("AAAAAAAA"))
    drain(events)
    r._last_seen -= 2.0
    r._maybe_emit_removed()                    # real absence
    drain(events)
    r._on_connect(Tag("AAAAAAAA"))             # the same card is placed again
    (event,) = drain(events)
    assert isinstance(event, CardPresented)
