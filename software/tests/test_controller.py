import yaml

from conftest import MemoryLcd, SpyRoon

from mcard.controller import Controller
from mcard.display import Display
from mcard.events import ButtonPressed, CardPresented, CardRemoved, NowPlaying


def make_controller(app_config, store, roon=None):
    display = Display(MemoryLcd())
    controller = Controller(app_config, store, display)
    controller.roon = roon or SpyRoon()
    return controller


def test_known_card_plays_album(app_config, store):
    controller = make_controller(app_config, store)
    controller._handle(CardPresented(uid="04A1B2C3"))
    assert [e.album for e in controller.roon.played] == ["Kind of Blue"]
    assert controller.status["card_album"] == "Kind of Blue"


def test_unknown_card_added_as_todo_and_not_played(app_config, store, albums_file):
    controller = make_controller(app_config, store)
    controller._handle(CardPresented(uid="DEADBEEF"))
    assert controller.roon.played == []
    data = yaml.safe_load(albums_file.read_text(encoding="utf-8"))
    assert data["DEADBEEF"]["album"] == "TODO"


def test_todo_card_not_played(app_config, store):
    controller = make_controller(app_config, store)
    controller._handle(CardPresented(uid="0FTODO01"))
    assert controller.roon.played == []


def test_same_card_within_cooldown_ignored(app_config, store):
    controller = make_controller(app_config, store)
    controller._handle(CardPresented(uid="04A1B2C3"))
    controller._handle(CardPresented(uid="04A1B2C3"))  # re-détection immédiate
    assert len(controller.roon.played) == 1


def test_different_card_bypasses_cooldown(app_config, store):
    controller = make_controller(app_config, store)
    controller._handle(CardPresented(uid="04A1B2C3"))
    controller._handle(CardPresented(uid="0FPATH01"))
    assert [e.display_name() for e in controller.roon.played] == ["Kind of Blue", "Baltimore"]


def test_card_removed_keeps_playing_by_default(app_config, store):
    controller = make_controller(app_config, store)
    controller._handle(CardRemoved(uid="04A1B2C3"))
    assert controller.roon.controls == []          # l'album continue
    assert controller.status["card_uid"] == ""


def test_card_removed_pauses_when_configured(tmp_path, store):
    from mcard.config import AppConfig

    (tmp_path / "mcard.yaml").write_text(
        "behavior:\n  on_card_removed: pause\n", encoding="utf-8"
    )
    controller = make_controller(AppConfig.load(tmp_path), store)
    controller._handle(CardRemoved(uid="04A1B2C3"))
    assert controller.roon.controls == ["pause"]


def test_buttons_map_to_transport(app_config, store):
    controller = make_controller(app_config, store)
    for name in ("prev", "playpause", "next"):
        controller._handle(ButtonPressed(name=name))
    assert controller.roon.controls == ["previous", "playpause", "next"]


def test_legacy_button_names_still_work(app_config, store):
    controller = make_controller(app_config, store)
    for name in ("play", "pause"):
        controller._handle(ButtonPressed(name=name))
    assert controller.roon.controls == ["play", "pause"]


def test_now_playing_updates_status_and_display(app_config, store):
    controller = make_controller(app_config, store)
    controller._handle(
        NowPlaying(state="playing", album="Kind of Blue", track="So What", artist="Miles Davis")
    )
    assert controller.status["track"] == "So What"
    lcd = controller._display._backend
    assert "So What" in lcd.rows_content[2]


def test_same_album_already_playing_is_not_restarted(app_config, store):
    controller = make_controller(app_config, store)
    controller.status.update(state="playing", album="Kind of Blue")
    controller._handle(CardPresented(uid="04A1B2C3"))
    assert controller.roon.played == []          # on ne relance pas l'album
    assert controller.roon.controls == []


def test_same_album_paused_resumes(app_config, store):
    controller = make_controller(app_config, store)
    controller.status.update(state="paused", album="Kind of Blue")
    controller._handle(CardPresented(uid="04A1B2C3"))
    assert controller.roon.played == []
    assert controller.roon.controls == ["playpause"]


def test_different_album_playing_switches(app_config, store):
    controller = make_controller(app_config, store)
    controller.status.update(state="playing", album="Abbey Road")
    controller._handle(CardPresented(uid="04A1B2C3"))
    assert [e.album for e in controller.roon.played] == ["Kind of Blue"]


def test_interactions_wake_backlight(app_config, store):
    controller = make_controller(app_config, store)
    lcd = controller._display._backend
    controller._display._bl_on = False
    lcd.backlight = False
    controller._handle(ButtonPressed(name="playpause"))
    assert lcd.backlight is True


def test_play_failure_shows_error(app_config, store):
    controller = make_controller(app_config, store, roon=SpyRoon(play_result=False))
    controller._handle(CardPresented(uid="04A1B2C3"))
    lcd = controller._display._backend
    assert "introuvable" in lcd.rows_content[0].lower()
