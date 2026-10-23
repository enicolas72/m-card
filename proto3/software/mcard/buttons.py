"""Physical prev / play / pause / next buttons on GPIO (BCM numbering).

Each button connects its GPIO pin to GND; the Pi's internal pull-ups are
enabled. gpiozero handles debouncing.
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
        from gpiozero import Button  # lazy import (unavailable off the Pi)

        for name, pin in self._pins.items():
            button = Button(pin, pull_up=True, bounce_time=0.05)
            button.when_pressed = self._make_handler(name)
            self._buttons.append(button)
            log.info("Button \"%s\" on GPIO%d", name, pin)

    def _make_handler(self, name: str):
        def handler():
            log.info("Button pressed: %s", name)
            self._queue.put(ButtonPressed(name=name))

        return handler

    def stop(self) -> None:
        for button in self._buttons:
            try:
                button.close()
            except Exception:
                pass
        self._buttons = []
