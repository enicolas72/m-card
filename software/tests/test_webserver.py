import json

import pytest

from mcard.webserver import create_app


@pytest.fixture
def client(tmp_path):
    config_dir = tmp_path
    (config_dir / "albums.yaml").write_text('"04A1B2C3":\n  album: "Kind of Blue"\n',
                                            encoding="utf-8")
    (config_dir / "mcard.yaml").write_text("web:\n  port: 8088\n", encoding="utf-8")
    log_file = tmp_path / "mcard.log"
    log_file.write_text("ligne1\nligne2\nligne3\n", encoding="utf-8")

    reloaded = []
    app = create_app(
        config_dir=config_dir,
        log_file=log_file,
        status_fn=lambda: {"roon_connected": True, "state": "playing",
                           "album": "Kind of Blue", "track": "So What",
                           "artist": "Miles Davis", "card_uid": "04A1B2C3",
                           "card_album": "Kind of Blue", "roon_message": "ok"},
        on_albums_saved=lambda: reloaded.append(True),
    )
    app.config["TESTING"] = True
    test_client = app.test_client()
    test_client.reloaded = reloaded
    test_client.config_dir = config_dir
    return test_client


def test_index_shows_status(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Kind of Blue" in response.get_data(as_text=True)


def test_api_status_json(client):
    response = client.get("/api/status")
    assert response.status_code == 200
    assert response.get_json()["track"] == "So What"


def test_logs_tail(client):
    response = client.get("/logs?n=10")
    assert "ligne3" in response.get_data(as_text=True)


def test_logs_download(client):
    response = client.get("/logs/download")
    assert response.status_code == 200
    assert b"ligne1" in response.data


def test_config_edit_form(client):
    response = client.get("/config/albums.yaml")
    assert "Kind of Blue" in response.get_data(as_text=True)


def test_config_save_valid_yaml_triggers_reload(client):
    response = client.post("/config/albums.yaml",
                           data={"content": '"AABB":\n  album: "Blue Train"\n'})
    assert response.status_code == 302
    assert "saved" in response.headers["Location"]
    assert client.reloaded == [True]
    assert "Blue Train" in (client.config_dir / "albums.yaml").read_text(encoding="utf-8")


def test_config_save_invalid_yaml_rejected(client):
    original = (client.config_dir / "albums.yaml").read_text(encoding="utf-8")
    response = client.post("/config/albums.yaml", data={"content": "a: [not closed"})
    assert response.status_code == 302
    assert "error" in response.headers["Location"]
    # the file was not modified
    assert (client.config_dir / "albums.yaml").read_text(encoding="utf-8") == original


def test_unknown_config_file_404(client):
    assert client.get("/config/../etc/passwd").status_code in (404, 308)
    assert client.get("/config/autre.yaml").status_code == 404
    assert client.post("/config/autre.yaml", data={"content": "x: 1"}).status_code == 404


# ---- search + assignment (/search page) ---------------------------------

@pytest.fixture
def search_client(tmp_path):
    from mcard.config import AlbumStore
    from mcard.roon_client import search_library

    (tmp_path / "albums.yaml").write_text('"04AA":\n  album: TODO\n', encoding="utf-8")
    store = AlbumStore(tmp_path / "albums.yaml")
    library = [("Electronica 1: The Time Machine", "Jean-Michel Jarre")]
    app = create_app(
        config_dir=tmp_path,
        log_file=tmp_path / "mcard.log",
        status_fn=dict,
        on_albums_saved=store.reload_and_normalize,
        search_fn=lambda q: search_library(q, library, {"Jean-Michel Jarre"}),
        cards_fn=store.all,
        assign_fn=store.assign,
    )
    app.config["TESTING"] = True
    test_client = app.test_client()
    test_client.store = store
    return test_client


def test_search_shows_path_fragment(search_client):
    page = search_client.get("/search?q=time+machine").get_data(as_text=True)
    assert ('path: [&quot;Library&quot;, &quot;Artists&quot;, &quot;Jean-Michel Jarre&quot;, '
            '&quot;Electronica 1: The Time Machine&quot;]') in page
    assert "04AA — TODO" in page


def test_search_roon_disconnected(tmp_path):
    app = create_app(config_dir=tmp_path, log_file=tmp_path / "x.log", status_fn=dict,
                     on_albums_saved=lambda: None, search_fn=lambda q: None)
    page = app.test_client().get("/search?q=x").get_data(as_text=True)
    assert "Roon not connected" in page


def test_assign_writes_path_to_albums_yaml(search_client):
    path = ["Library", "Artists", "Jean-Michel Jarre", "Electronica 1: The Time Machine"]
    response = search_client.post("/search/assign", data={
        "uid": "04aa", "path": json.dumps(path), "artist": "Jean-Michel Jarre", "q": "time"})
    assert response.status_code == 302
    assert "assigned=04AA" in response.headers["Location"]
    entry = search_client.store.lookup("04AA")
    assert entry.path == path and not entry.is_todo
    search_client.store.reload()  # really persisted to disk
    assert search_client.store.lookup("04AA").path == path


def test_assign_rejects_unknown_card_and_bad_path(search_client):
    bad_uid = search_client.post("/search/assign", data={
        "uid": "FFFF", "path": '["Library", "Albums", "X"]'})
    assert "error=" in bad_uid.headers["Location"]
    bad_path = search_client.post("/search/assign", data={"uid": "04AA", "path": "pas du json"})
    assert "error=" in bad_path.headers["Location"]
    assert search_client.store.lookup("04AA").is_todo


def test_ui_save_normalizes_albums_format(search_client):
    content = ('"04AA":\n  artist: Angèle\n  path:\n  - Library\n  - Artists\n'
               '  - Angèle\n  - Instinct\n'
               '"04BB":\n  path: ["Library", "Artists", "AC/DC", "Back in Black"]\n')
    search_client.post("/config/albums.yaml", data={"content": content})
    text = search_client.store.path.read_text(encoding="utf-8")
    assert '  path: ["Library", "Artists", "Angèle", "Instinct"]\n  artist: "Angèle"\n' in text
    assert '  path: ["Library", "Artists", "AC/DC", "Back in Black"]\n' in text


def test_config_download_returns_raw_file(client):
    response = client.get("/config/albums.yaml/download")
    assert response.status_code == 200
    assert response.get_data(as_text=True) == '"04A1B2C3":\n  album: "Kind of Blue"\n'
    assert "attachment" in response.headers["Content-Disposition"]


def test_config_download_rejects_other_files(client):
    assert client.get("/config/mcard.log/download").status_code == 404
    assert client.get("/config/..%2Fmcard.log/download").status_code == 404
