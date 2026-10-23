"""Approximate album name matching (play_media needs the exact title)."""

import queue

from mcard.roon_client import (RoonClient, album_path, best_album_match,
                                search_library, titles_match)

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
    # the Diana Krall case: "in The" spelled "in the" in Roon
    found, _ = best_album_match("The Girl in The Other Room", LIBRARY)
    assert found == "The Girl in the Other Room"


def test_accents_and_apostrophes():
    found, _ = best_album_match("l’emprise", LIBRARY)
    assert found == "L'Emprise"


def test_partial_match_when_unambiguous():
    # the Mylène Farmer case: "Nevermore" is called "Nevermore 2023"
    found, _ = best_album_match("Nevermore", LIBRARY)
    assert found == "Nevermore 2023"


def test_ambiguous_returns_suggestions():
    found, suggestions = best_album_match("Live", LIBRARY)
    assert found is None
    assert set(suggestions) == {"Live at the Roxy", "Live in Paris"}


def test_not_found():
    found, suggestions = best_album_match("Never Heard Of It", LIBRARY)
    assert found is None
    assert suggestions == []


def test_empty_target():
    assert best_album_match("", LIBRARY) == (None, [])


def test_short_titles_do_not_match_inside_words():
    # albums "I" and "V": must not match every letter i/v
    library = ["I", "V", "Electronica 1: The Time Machine"]
    found, _ = best_album_match("Electronica Vol 1 The Time Machine", library)
    assert found == "Electronica 1: The Time Machine"


def test_punctuation_and_volume_ignored():
    library = ["Electronica 2: The Heart of Noise"]
    found, _ = best_album_match("Electronica Vol. 2 - The Heart Of Noise", library)
    assert found == "Electronica 2: The Heart of Noise"


class FakeBrowseApi:
    """Simulates pyroon's browse_browse/browse_load (pages of 100).
    `titles`: plain titles or (title, artist) pairs."""

    def __init__(self, titles, artists=()):
        self.titles = titles
        self.artists = list(artists)
        self.load_calls = 0

    def _items(self, hierarchy):
        if hierarchy == "artists":
            return [{"title": a} for a in self.artists]
        assert hierarchy == "albums"
        return [{"title": t[0], "subtitle": t[1]} if isinstance(t, tuple)
                else {"title": t} for t in self.titles]

    def browse_browse(self, opts):
        return {"list": {"count": len(self._items(opts["hierarchy"]))}}

    def browse_load(self, opts):
        self.load_calls += 1
        offset = opts["offset"]
        return {"items": self._items(opts["hierarchy"])[offset:offset + 100]}


def make_client():
    return RoonClient(queue.Queue())


def test_list_album_titles_paginates():
    titles = [f"Album {i:03d}" for i in range(250)]
    api = FakeBrowseApi(titles)
    client = make_client()
    items = client._list_items(api, "albums")
    assert [i["title"] for i in items] == titles
    assert api.load_calls == 3  # 100 + 100 + 50


def test_resolve_uses_cache_then_refreshes_on_miss():
    client = make_client()
    api = FakeBrowseApi(["Abbey Road"])
    assert client._resolve_album_title(api, "abbey road") == "Abbey Road"
    calls_after_first = api.load_calls
    # new album added in Roon after caching
    api.titles = ["Abbey Road", "Nevermore 2023"]
    assert client._resolve_album_title(api, "Nevermore") == "Nevermore 2023"
    assert api.load_calls > calls_after_first  # a refresh happened


def test_resolve_unknown_returns_none():
    client = make_client()
    api = FakeBrowseApi(["Abbey Road"])
    assert client._resolve_album_title(api, "Unknown") is None


def test_titles_match_tolerant():
    assert titles_match("Kind of Blue", "kind of blue")
    assert titles_match("Nevermore", "Nevermore 2023")
    assert titles_match("L'Emprise", "l\u2019emprise")
    assert not titles_match("Kind of Blue", "Abbey Road")
    assert not titles_match("", "Abbey Road")


def test_longest_shared_part_wins():
    library = ["Electronica: The Heart of Noise, Vol. 2", "Noise"]
    found, _ = best_album_match("Electronica The Heart of Noise", library)
    assert found == "Electronica: The Heart of Noise, Vol. 2"


# ---- free-text search (/search page) -----------------------------------

SEARCH_LIBRARY = [
    ("Electronica 1: The Time Machine", "Jean-Michel Jarre"),
    ("Electronica 2: The Heart of Noise", "Jean-Michel Jarre"),
    ("Oxygène", "Jean-Michel Jarre"),
    ("Greatest Hits", "Queen"),
    ("Greatest Hits", "ABBA"),
    ("Original Soundtrack", "Various Artists"),
]
SEARCH_ARTISTS = {"Jean-Michel Jarre", "Queen", "ABBA"}


def test_search_all_words_any_order_accents_ignored():
    results = search_library("jarre oxygene", SEARCH_LIBRARY, SEARCH_ARTISTS)
    assert [r["title"] for r in results] == ["Oxygène"]


def test_search_partial_words_and_sorted():
    results = search_library("electr", SEARCH_LIBRARY, SEARCH_ARTISTS)
    assert [r["title"] for r in results] == [
        "Electronica 1: The Time Machine", "Electronica 2: The Heart of Noise"]


def test_search_path_goes_through_artist():
    results = search_library("greatest", SEARCH_LIBRARY, SEARCH_ARTISTS)
    assert {tuple(r["path"]) for r in results} == {
        ("Library", "Artists", "ABBA", "Greatest Hits"),
        ("Library", "Artists", "Queen", "Greatest Hits"),
    }
    assert all(r["warning"] == "" for r in results)


def test_search_falls_back_to_albums_path_with_warning():
    (result,) = search_library("soundtrack", SEARCH_LIBRARY, SEARCH_ARTISTS)
    assert result["path"] == ["Library", "Albums", "Original Soundtrack"]
    assert "Artists" in result["warning"]


def test_search_empty_query_and_limit():
    assert search_library("  ", SEARCH_LIBRARY, SEARCH_ARTISTS) == []
    assert len(search_library("e", SEARCH_LIBRARY, SEARCH_ARTISTS, limit=2)) == 2


def test_album_path_without_artist():
    assert album_path("X", "", {"A"}) == ["Library", "Albums", "X"]


def test_client_search_uses_library_and_artists():
    client = make_client()
    client._api = FakeBrowseApi(SEARCH_LIBRARY, SEARCH_ARTISTS)
    (result,) = client.search_albums("time machine")
    assert result["path"] == ["Library", "Artists", "Jean-Michel Jarre",
                              "Electronica 1: The Time Machine"]


def test_client_search_disconnected_returns_none():
    assert make_client().search_albums("x") is None
