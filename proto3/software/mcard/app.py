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
from .oled import OledDisplay
from .logging_setup import setup_logging
from .webserver import create_app, start_in_thread

log = logging.getLogger(__name__)


def make_display(config: AppConfig, fake: bool):
    """OLED (proto 3) or LCD (proto 2) per `display.type`; the real panel
    falls back to its fake when unavailable, so the device keeps working."""
    kind = config.get("display", "type", default="oled")
    timeout = config.get("display", "sleep_timeout_s", default=120)
    if kind not in ("oled", "lcd"):
        log.error("Unknown display.type %r, using oled", kind)
        kind = "oled"

    if kind == "lcd":
        from .fakes import FakeLcdBackend

        backend = FakeLcdBackend()
        if not fake:
            from .display import CharLcdBackend

            try:
                backend = CharLcdBackend(
                    i2c_address=config.get("lcd", "i2c_address", default=0x27),
                    i2c_port=config.get("lcd", "i2c_port", default=1),
                    cols=config.get("lcd", "cols", default=20),
                    rows=config.get("lcd", "rows", default=4),
                )
            except Exception as exc:
                log.error("LCD unavailable (%s) — continuing without a display", exc)
        return Display(backend, backlight_timeout_s=timeout)

    from .fakes import FakeOledBackend

    oled = config.get("oled", default={})
    backend = FakeOledBackend()
    if not fake:
        from .oled import LumaOledBackend

        try:
            backend = LumaOledBackend(
                spi_port=oled.get("spi_port", 0), spi_device=oled.get("spi_device", 0),
                gpio_dc=oled.get("gpio_dc", 24), gpio_rst=oled.get("gpio_rst", 25),
                rotate=oled.get("rotate", 0), contrast=oled.get("contrast", 180),
            )
        except Exception as exc:
            log.error("OLED unavailable (%s) — continuing without a display", exc)
    return OledDisplay(backend, sleep_timeout_s=timeout, fps=oled.get("fps", 20),
                       font_path=oled.get("font", ""))


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
    display = make_display(config, fake)
    controller = Controller(config, albums, display)

    if fake:
        from .fakes import FakeNfcReader, FakeRoonClient

        roon = FakeRoonClient(controller.queue)
        nfc = FakeNfcReader(controller.queue)
        buttons = None
    else:
        from .buttons import Buttons
        from .nfc_reader import NfcReader
        from .roon_client import RoonClient

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
            device=config.get("nfc", "device", default="tty:AMA0:pn532"),
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
        display_png_fn=getattr(display, "snapshot_png", None),
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
