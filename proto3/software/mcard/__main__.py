"""Entry point: python -m mcard [--config DIR] [--fake]"""

import argparse
import sys
from pathlib import Path

from . import __version__
from .app import run


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="mcard",
        description="M-Card — plays a Roon album when an RFID-tagged CD/vinyl is placed",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("/etc/mcard"),
        help="directory containing mcard.yaml and albums.yaml (default: /etc/mcard)",
    )
    parser.add_argument(
        "--fake",
        action="store_true",
        help="simulated hardware (development without a Raspberry Pi)",
    )
    parser.add_argument("--version", action="version", version=f"mcard {__version__}")
    args = parser.parse_args()
    return run(config_dir=args.config, fake=args.fake)


if __name__ == "__main__":
    sys.exit(main())
