"""Correspondance approchée des noms d'albums (play_media exige le titre exact)."""

import queue

from mcard.roon_client import RoonClient, best_album_match, titles_match

LIBRARY = [
    "The Girl in the Other Room",
    "Nevermore 2023",
    "L'Emprise",
    "Abbey Road",
    "Live at the Roxy",
    "Live in Paris",
]


def test_exact_match_passthrough():
    found, _ = best_album_match("Abbey Road", LIBRARY)
    assert found == "Abbey Road"


def test_case_insensitive():
    # le cas Diana Krall : « in The » écrit « in the » dans Roon
    found, _ = best_album_match("The Girl in The Other Room", LIBRARY)
    assert found == "The Girl in the Other Room"


def test_accents_and_apostrophes():
    found, _ = best_album_match("l’emprise", LIBRARY)
    assert found == "L'Emprise"


def test_partial_match_when_unambiguous():
    # le cas Mylène Farmer : « Nevermore » s'appelle « Nevermore 2023 »
    found, _ = best_album_match("Nevermore", LIBRARY)
    assert found == "Nevermore 2023"


def test_ambiguous_returns_suggestions():
    found, suggestions = best_album_match("Live", LIBRARY)
    assert found is None
    assert set(suggestions) == {"Live at the Roxy", "Live in Paris"}


def test_not_found():
    found, suggestions = best_album_match("Inconnu au bataillon", LIBRARY)
    assert found is None
    assert suggestions == []


def test_empty_target():
    assert best_album_match("", LIBRARY) == (None, [])


class FakeBrowseApi:
    """Simule browse_browse/browse_load de pyroon (pagination par 100)."""

    def __init__(self, titles):
        self.titles = titles
        self.load_calls = 0

    def browse_browse(self, opts):
        assert opts["hierarchy"] == "albums"
        return {"list": {"count": len(self.titles)}}

    def browse_load(self, opts):
        self.load_calls += 1
        offset = opts["offset"]
        return {"items": [{"title": t} for t in self.titles[offset:offset + 100]]}


def make_client():
    return RoonClient(queue.Queue())


def test_list_album_titles_paginates():
    titles = [f"Album {i:03d}" for i in range(250)]
    api = FakeBrowseApi(titles)
    client = make_client()
    assert client._list_album_titles(api) == titles
    assert api.load_calls == 3  # 100 + 100 + 50


def test_resolve_uses_cache_then_refreshes_on_miss():
    client = make_client()
    api = FakeBrowseApi(["Abbey Road"])
    assert client._resolve_album_title(api, "abbey road") == "Abbey Road"
    calls_after_first = api.load_calls
    # nouvel album ajouté dans Roon après la mise en cache
    api.titles = ["Abbey Road", "Nevermore 2023"]
    assert client._resolve_album_title(api, "Nevermore") == "Nevermore 2023"
    assert api.load_calls > calls_after_first  # un rafraîchissement a eu lieu


def test_resolve_unknown_returns_none():
    client = make_client()
    api = FakeBrowseApi(["Abbey Road"])
    assert client._resolve_album_title(api, "Inconnu") is None


def test_titles_match_tolerant():
    assert titles_match("Kind of Blue", "kind of blue")
    assert titles_match("Nevermore", "Nevermore 2023")
    assert titles_match("L'Emprise", "l\u2019emprise")
    assert not titles_match("Kind of Blue", "Abbey Road")
    assert not titles_match("", "Abbey Road")
