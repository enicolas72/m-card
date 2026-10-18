import yaml

from mcard.config import ALBUMS_HEADER, AlbumStore, AppConfig, DEFAULTS


def test_defaults_when_no_file(tmp_path):
    config = AppConfig.load(tmp_path)
    assert config.get("web", "port") == 8088
    assert config.get("buttons", "next") == 13
    assert config.get("buttons", "playpause") == 6


def test_partial_override_merges_with_defaults(tmp_path):
    (tmp_path / "mcard.yaml").write_text("web:\n  port: 9999\n", encoding="utf-8")
    config = AppConfig.load(tmp_path)
    assert config.get("web", "port") == 9999
    assert config.get("web", "host") == DEFAULTS["web"]["host"]
    assert config.get("roon", "port") == 9330


def test_lookup_known_card(store):
    entry = store.lookup("04a1b2c3")  # case-insensitive
    assert entry is not None
    assert entry.album == "Kind of Blue"
    assert not entry.is_todo


def test_lookup_path_entry(store):
    entry = store.lookup("0FPATH01")
    assert entry.path == ["Library", "Artists", "Nina Simone", "Baltimore"]
    assert entry.display_name() == "Baltimore"
    assert not entry.is_todo


def test_todo_entry_flag(store):
    assert store.lookup("0FTODO01").is_todo


def test_add_unknown_card_persists_todo(store, albums_file):
    entry = store.add_todo("aabbccdd")
    assert entry.is_todo
    # re-read the file: the entry must be written uppercase with TODO
    data = yaml.safe_load(albums_file.read_text(encoding="utf-8"))
    assert data["AABBCCDD"]["album"] == "TODO"
    # existing entries are preserved
    assert data["04A1B2C3"]["album"] == "Kind of Blue"
    assert data["0FPATH01"]["path"][-1] == "Baltimore"
    # the explanatory header is kept
    assert albums_file.read_text(encoding="utf-8").startswith("# M-Card")


def test_add_todo_twice_is_idempotent(store, albums_file):
    store.add_todo("AABBCCDD")
    store.add_todo("AABBCCDD")
    data = yaml.safe_load(albums_file.read_text(encoding="utf-8"))
    assert list(data).count("AABBCCDD") == 1


def test_reload_picks_up_external_edit(store, albums_file):
    content = albums_file.read_text(encoding="utf-8").replace(
        "album: TODO", "album: Nouveau Disque"
    )
    albums_file.write_text(content, encoding="utf-8")
    store.reload()
    assert store.lookup("0FTODO01").album == "Nouveau Disque"


def test_saved_format_matches_search_fragment(tmp_path):
    store = AlbumStore(tmp_path / "albums.yaml")
    store.assign("042f9b7aaa4881", ["Library", "Artists", "Angèle", "Instinct"], "Angèle")
    store.add_todo("0412345678")  # all-digit UID: must stay a string
    body = (tmp_path / "albums.yaml").read_text(encoding="utf-8").split(ALBUMS_HEADER)[1]
    assert body == (
        '\n"0412345678":\n'
        '  album: "TODO"\n'
        '"042F9B7AAA4881":\n'
        '  path: ["Library", "Artists", "Angèle", "Instinct"]\n'
        '  artist: "Angèle"\n'
    )


def test_saved_file_round_trips_tricky_titles(tmp_path):
    path = ["Library", "Artists", "AC/DC", 'Live "at" Donington \\ 1991: Vol. 1']
    store = AlbumStore(tmp_path / "albums.yaml")
    store.assign("AA01", path, "AC/DC")
    store.add_todo("0012")
    store.reload()
    assert store.lookup("AA01").path == path
    assert store.lookup("AA01").artist == "AC/DC"
    assert store.lookup("0012").is_todo


def test_unknown_settings_are_reported(tmp_path, caplog):
    # the classic mistake: `language` not indented under `web`
    (tmp_path / "mcard.yaml").write_text(
        "web:\n  port: 8088\n\nlanguage:\n  fr\n\nlcd:\n  colz: 20\n", encoding="utf-8")
    config = AppConfig.load(tmp_path)
    assert config.get("web", "language") == "en"
    messages = " ".join(r.getMessage() for r in caplog.records)
    assert "unknown setting 'language' ignored (did you mean web.language?" in messages
    assert "unknown setting 'lcd.colz' ignored" in messages


def test_legacy_button_names_are_not_reported(tmp_path, caplog):
    (tmp_path / "mcard.yaml").write_text("buttons:\n  play: 6\n  pause: 19\n", encoding="utf-8")
    AppConfig.load(tmp_path)
    assert "unknown setting" not in caplog.text
