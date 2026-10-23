"""Reads RFID cards through the ACR122U (USB, nfcpy driver).

A thread watches the reader continuously:
- card placed   -> CardPresented(uid) on the event queue
- card removed  -> CardRemoved(uid)

Important quirk: with the ACR122U, nfcpy's presence check fails on some
tags (Mifare Ultralight in particular) and connect() returns right away
while the card is still there. This is smoothed with a grace period: a card
is only "removed" if it stays invisible for `removal_grace_s`, and
re-detections of the same card are silent.

The thread survives USB unplugs/errors (reopens with backoff).

System prerequisites (see docs/SETUP.md): blacklist the pn533_usb/pn533/nfc
kernel modules that grab the reader, and a udev rule for access without
root.
"""

from __future__ import annotations

import logging
import queue
import threading
import time

from .events import CardPresented, CardRemoved

log = logging.getLogger(__name__)

POLL_WINDOW_S = 0.3  # length of a detection cycle when no card is present


class NfcReader:
    def __init__(self, event_queue: "queue.Queue", device: str = "usb",
                 removal_grace_s: float = 1.0):
        self._queue = event_queue
        self._device = device
        self._grace = float(removal_grace_s)
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True, name="nfc-reader")
        self._current_uid: str | None = None
        self._last_seen: float = 0.0

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=3)

    # ---- presence/absence state machine (testable without hardware) ----

    def _on_connect(self, tag) -> bool:
        try:
            uid = tag.identifier.hex().upper()
        except Exception:
            log.warning("Tag without a readable identifier: %r", tag)
            return False
        now = time.monotonic()
        if uid != self._current_uid:
            if self._current_uid is not None:
                self._queue.put(CardRemoved(uid=self._current_uid))
                log.info("Card removed: %s (replaced)", self._current_uid)
            self._current_uid = uid
            self._queue.put(CardPresented(uid=uid))
            log.info("Card detected: %s (%s)", uid, tag)
        # same card seen again during the grace period: silent
        self._last_seen = now
        return True  # keep the connection while the card answers

    def _note_tag_seen(self) -> None:
        self._last_seen = time.monotonic()

    def _maybe_emit_removed(self, now: float | None = None) -> None:
        if self._current_uid is None:
            return
        now = time.monotonic() if now is None else now
        if now - self._last_seen > self._grace:
            self._queue.put(CardRemoved(uid=self._current_uid))
            log.info("Card removed: %s", self._current_uid)
            self._current_uid = None

    # ---- hardware loop ------------------------------------------------

    def _run(self) -> None:
        import nfc  # lazy import (unavailable off the Pi)

        backoff = 1.0
        while not self._stop.is_set():
            clf = None
            try:
                clf = nfc.ContactlessFrontend(self._device)
                log.info("NFC reader opened: %s", clf)
                backoff = 1.0
                self._poll_loop(clf)
            except Exception as exc:
                if not self._stop.is_set():
                    log.error("NFC reader error (%s), retrying in %.0fs", exc, backoff)
                    self._stop.wait(backoff)
                    backoff = min(backoff * 2, 30.0)
            finally:
                if clf is not None:
                    try:
                        clf.close()
                    except Exception:
                        pass
                if self._current_uid is not None:
                    # reader lost while a card was present
                    self._queue.put(CardRemoved(uid=self._current_uid))
                    self._current_uid = None

    def _poll_loop(self, clf) -> None:
        while not self._stop.is_set():
            started = time.monotonic()
            # connect() blocks while the card answers (on_connect -> True);
            # with tags whose presence check is flaky it returns very
            # quickly: the grace period sorts it out.
            tag = clf.connect(
                rdwr={
                    "on-connect": self._on_connect,
                    "beep-on-connect": False,
                },
                terminate=lambda: self._stop.is_set()
                or (time.monotonic() - started > POLL_WINDOW_S),
            )
            if tag:
                self._note_tag_seen()
            self._maybe_emit_removed()
