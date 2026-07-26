"""Boutons physiques prev / play / pause / next sur GPIO (numérotation BCM).

Chaque bouton relie sa broche GPIO à GND ; on active les pull-ups internes
du Pi. gpiozero gère l'anti-rebond.
"""

from __future__ import annotations

import logging
import queue

from .events import ButtonPressed

log = logging.getLogger(__name__)


class Buttons:
    def __init__(self, event_queue: "queue.Queue", pins: dict[str, int]):
        self._queue = event_queue
        self._pins = pins
        self._buttons = []

    def start(self) -> None:
        from gpiozero import Button  # import paresseux (indisponible hors Pi)

        for name, pin in self._pins.items():
            button = Button(pin, pull_up=True, bounce_time=0.05)
            button.when_pressed = self._make_handler(name)
            self._buttons.append(button)
            log.info("Bouton «%s» sur GPIO%d", name, pin)

    def _make_handler(self, name: str):
        def handler():
            log.info("Bouton pressé: %s", name)
            self._queue.put(ButtonPressed(name=name))

        return handler

    def stop(self) -> None:
        for button in self._buttons:
            try:
                button.close()
            except Exception:
                pass
        self._buttons = []
