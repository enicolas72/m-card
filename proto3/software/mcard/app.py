"""Application wiring: instantiates the components (real or simulated),
starts the threads and runs the controller loop.
"""

from __future__ import annotations

import logging
import signal
from pathlib import Path

from . import __version__
from .config import AlbumStore, AppConfig
from .controller import Controller
from .display import Display
from .logging_setup import setup_logging
from .webserver import create_app, start_in_thread

log = logging.getLogger(__name__)


def run(config_dir: Path, fake: bool = False) -> int:
    config_dir = Path(config_dir)
    config = AppConfig.load(config_dir)

    log_file = setup_logging(
        config.get("log", "file", default="/var/log/mcard/mcard.log"),
        level=config.get("log", "level", default="INFO"),
        max_bytes=config.get("log", "max_bytes", default=1_000_000),
        backup_count=config.get("log", "backup_count", default=5),
    )
    log.info("M-Card v%s starting (config: %s, fake=%s)", __version__, config_dir, fake)

    albums = AlbumStore(config_dir / "albums.yaml")

    # --- real or simulated hardware --------------------------------------
    backlight_timeout = config.get("lcd", "backlight_timeout_s", default=120)

    if fake:
        from .fakes import FakeLcdBackend, FakeNfcReader, FakeRoonClient

        display = Display(FakeLcdBackend(), backlight_timeout_s=backlight_timeout)
        controller = Controller(config, albums, display)
        roon = FakeRoonClient(controller.queue)
        nfc = FakeNfcReader(controller.queue)
        buttons = None
    else:
        from .buttons import Buttons
        from .display import CharLcdBackend
        from .nfc_reader import NfcReader
        from .roon_client import RoonClient

        try:
            backend = CharLcdBackend(
                i2c_address=config.get("lcd", "i2c_address", default=0x27),
                i2c_port=config.get("lcd", "i2c_port", default=1),
                cols=config.get("lcd", "cols", default=20),
                rows=config.get("lcd", "rows", default=4),
            )
        except Exception as exc:
            log.error("LCD unavailable (%s) — continuing without a display", exc)
            from .fakes import FakeLcdBackend

            backend = FakeLcdBackend()
        display = Display(backend, backlight_timeout_s=backlight_timeout)
        controller = Controller(config, albums, display)
        roon = RoonClient(
            controller.queue,
            host=config.get("roon", "host", default=""),
            port=config.get("roon", "port", default=9330),
            zone_name=config.get("roon", "zone_name", default=""),
            token_file=config.get("roon", "token_file",
                                  default="/var/lib/mcard/roon_token.txt"),
        )
        nfc = NfcReader(
            controller.queue,
            removal_grace_s=config.get("behavior", "removal_grace_s", default=1.0),
        )
        buttons = Buttons(controller.queue, config.get("buttons", default={}))

    controller.roon = roon
    display.show_boot(__version__)

    # --- web server -------------------------------------------------------
    web_app = create_app(
        config_dir=config_dir,
        log_file=log_file,
        status_fn=lambda: dict(controller.status),
        on_albums_saved=albums.reload_and_normalize,
        search_fn=roon.search_albums,
        cards_fn=albums.all,
        assign_fn=albums.assign,
        language=config.get("web", "language", default="en"),
    )
    start_in_thread(
        web_app,
        host=config.get("web", "host", default="0.0.0.0"),
        port=config.get("web", "port", default=8088),
    )

    # --- startup ----------------------------------------------------------
    roon.start()
    nfc.start()
    if buttons is not None:
        try:
            buttons.start()
        except Exception as exc:
            log.error("GPIO buttons unavailable (%s) — continuing without buttons", exc)

    def _sig_handler(signum, frame):
        log.info("Signal %s received, shutting down...", signum)
        controller.shutdown()

    signal.signal(signal.SIGTERM, _sig_handler)
    signal.signal(signal.SIGINT, _sig_handler)

    try:
        controller.run()
    finally:
        nfc.stop()
        if buttons is not None:
            buttons.stop()
        roon.stop()
        display.set_lines("M-Card stopped", "", "", "")
        display.close()
    return 0
