import yaml

from mcard.config import AlbumStore, AppConfig, DEFAULTS


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
    entry = store.lookup("04a1b2c3")  # insensible à la casse
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
    # relecture du fichier : l'entrée doit être écrite en majuscules avec TODO
    data = yaml.safe_load(albums_file.read_text(encoding="utf-8"))
    assert data["AABBCCDD"]["album"] == "TODO"
    # les entrées existantes sont préservées
    assert data["04A1B2C3"]["album"] == "Kind of Blue"
    assert data["0FPATH01"]["path"][-1] == "Baltimore"
    # l'en-tête explicatif est conservé
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
