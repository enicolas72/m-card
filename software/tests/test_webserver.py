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
    response = client.post("/config/albums.yaml", data={"content": "a: [pas fermé"})
    assert response.status_code == 302
    assert "error" in response.headers["Location"]
    # le fichier n'a pas été modifié
    assert (client.config_dir / "albums.yaml").read_text(encoding="utf-8") == original


def test_unknown_config_file_404(client):
    assert client.get("/config/../etc/passwd").status_code in (404, 308)
    assert client.get("/config/autre.yaml").status_code == 404
    assert client.post("/config/autre.yaml", data={"content": "x: 1"}).status_code == 404
