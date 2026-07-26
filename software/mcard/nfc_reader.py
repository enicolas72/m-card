"""Lecture des cartes RFID via l'ACR122U (USB, pilote nfcpy).

Un thread surveille en continu le lecteur :
- carte posée   -> CardPresented(uid) dans la queue d'événements
- carte retirée -> CardRemoved(uid)

Particularité importante : avec l'ACR122U, le test de présence de nfcpy
échoue sur certains tags (Mifare Ultralight notamment) et connect() rend
la main immédiatement alors que la carte est toujours posée. On lisse donc
avec une période de grâce : une carte n'est « retirée » que si elle reste
invisible pendant `removal_grace_s`, et les re-détections de la même carte
sont silencieuses.

Le thread survit aux débranchements/erreurs USB (réouverture avec backoff).

Prérequis système (voir docs/SETUP.md) : blacklister les modules noyau
pn533_usb/pn533/nfc qui monopolisent le lecteur, et une règle udev pour
l'accès sans root.
"""

from __future__ import annotations

import logging
import queue
import threading
import time

from .events import CardPresented, CardRemoved

log = logging.getLogger(__name__)

POLL_WINDOW_S = 0.3  # durée d'un cycle de détection quand aucune carte n'est posée


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

    # ---- machine à états présence/absence (testable sans matériel) ----

    def _on_connect(self, tag) -> bool:
        try:
            uid = tag.identifier.hex().upper()
        except Exception:
            log.warning("Tag sans identifiant lisible: %r", tag)
            return False
        now = time.monotonic()
        if uid != self._current_uid:
            if self._current_uid is not None:
                self._queue.put(CardRemoved(uid=self._current_uid))
                log.info("Carte retirée: %s (remplacée)", self._current_uid)
            self._current_uid = uid
            self._queue.put(CardPresented(uid=uid))
            log.info("Carte détectée: %s (%s)", uid, tag)
        # même carte revue pendant la période de grâce : silencieux
        self._last_seen = now
        return True  # garder la connexion tant que la carte répond

    def _note_tag_seen(self) -> None:
        self._last_seen = time.monotonic()

    def _maybe_emit_removed(self, now: float | None = None) -> None:
        if self._current_uid is None:
            return
        now = time.monotonic() if now is None else now
        if now - self._last_seen > self._grace:
            self._queue.put(CardRemoved(uid=self._current_uid))
            log.info("Carte retirée: %s", self._current_uid)
            self._current_uid = None

    # ---- boucle matérielle -------------------------------------------

    def _run(self) -> None:
        import nfc  # import paresseux (indisponible hors Pi)

        backoff = 1.0
        while not self._stop.is_set():
            clf = None
            try:
                clf = nfc.ContactlessFrontend(self._device)
                log.info("Lecteur NFC ouvert: %s", clf)
                backoff = 1.0
                self._poll_loop(clf)
            except Exception as exc:
                if not self._stop.is_set():
                    log.error("Erreur lecteur NFC (%s), nouvel essai dans %.0fs", exc, backoff)
                    self._stop.wait(backoff)
                    backoff = min(backoff * 2, 30.0)
            finally:
                if clf is not None:
                    try:
                        clf.close()
                    except Exception:
                        pass
                if self._current_uid is not None:
                    # lecteur perdu alors qu'une carte était posée
                    self._queue.put(CardRemoved(uid=self._current_uid))
                    self._current_uid = None

    def _poll_loop(self, clf) -> None:
        while not self._stop.is_set():
            started = time.monotonic()
            # connect() bloque tant que la carte répond (on_connect -> True) ;
            # avec les tags au test de présence défaillant, il rend la main
            # très vite : la période de grâce fait le tri.
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
