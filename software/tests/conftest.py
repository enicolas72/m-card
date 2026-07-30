import sys
from pathlib import Path

import pytest

# rendre le package mcard importable depuis software/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mcard.config import AlbumStore, AppConfig  # noqa: E402


class MemoryLcd:
    """Backend LCD en mémoire pour vérifier ce qui est affiché."""

    cols = 20
    rows = 4

    def __init__(self):
        self.rows_content = [""] * self.rows
        self.backlight = True

    def write_row(self, row, text):
        self.rows_content[row] = text

    def set_backlight(self, on):
        self.backlight = on

    def close(self):
        pass


class SpyRoon:
    """Client Roon espion : mémorise les appels."""

    def __init__(self, play_result=True):
        self.played = []
        self.controls = []
        self.play_result = play_result
        self.connected = True

    def play_album(self, entry):
        self.played.append(entry)
        return self.play_result

    def control(self, action):
        self.controls.append(action)


@pytest.fixture
def albums_file(tmp_path):
    path = tmp_path / "albums.yaml"
    path.write_text(
        '"04A1B2C3":\n  album: "Kind of Blue"\n  artist: "Miles Davis"\n'
        '"0FTODO01":\n  album: TODO\n'
        '"0FPATH01":\n  path: ["Library", "Artists", "Nina Simone", "Baltimore"]\n',
        encoding="utf-8",
    )
    return path


@pytest.fixture
def store(albums_file):
    return AlbumStore(albums_file)


@pytest.fixture
def app_config(tmp_path):
    return AppConfig.load(tmp_path)  # fichier absent => valeurs par défaut
