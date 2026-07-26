"""Point d'entrée : python -m mcard [--config DIR] [--fake]"""

import argparse
import sys
from pathlib import Path

from . import __version__
from .app import run


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="mcard",
        description="M-Card — lance un album Roon en posant un CD/vinyle à carte RFID",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("/etc/mcard"),
        help="répertoire contenant mcard.yaml et albums.yaml (défaut: /etc/mcard)",
    )
    parser.add_argument(
        "--fake",
        action="store_true",
        help="matériel simulé (développement sans Raspberry Pi)",
    )
    parser.add_argument("--version", action="version", version=f"mcard {__version__}")
    args = parser.parse_args()
    return run(config_dir=args.config, fake=args.fake)


if __name__ == "__main__":
    sys.exit(main())
