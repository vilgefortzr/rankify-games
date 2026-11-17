import pytest
import requests

from rankify import steam
from rankify.exception_handler import SteamUnavailableError


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status

    def raise_for_status(self):
        if self.status >= 400:
            raise requests.HTTPError(f"{self.status} error")

    def json(self):
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


@pytest.fixture
def fake_steam(monkeypatch):
    """Route requests.get to a handler: handler(url, params) -> FakeResponse."""
    calls = []

    def install(handler):
        def fake_get(url, params=None, timeout=None):
            calls.append((url, params))
            return handler(url, params)

        monkeypatch.setattr("rankify.steam.requests.get", fake_get)
        return calls

    return install


def app_details(steam_id, data, success=True):
    return {str(steam_id): {"success": success, "data": data}}


class TestGetJson:
    @pytest.mark.parametrize(
        "response",
        [
            FakeResponse({}, status=500),
            FakeResponse(ValueError("not json")),
            FakeResponse(["not", "a", "dict"]),
        ],
        ids=["http-error", "invalid-json", "not-a-dict"],
    )
    def test_bad_responses_raise_steam_unavailable(self, fake_steam, response):
        fake_steam(lambda url, params: response)

        with pytest.raises(SteamUnavailableError):
            steam._get_json(steam.APPDETAILS_URL, {})

    def test_network_error_raises_steam_unavailable(self):
        # The autouse no_steam_network fixture makes requests.get fail.
        with pytest.raises(SteamUnavailableError):
            steam._get_json(steam.APPDETAILS_URL, {})


class TestSearchGames:
    def test_returns_only_available_apps(self, fake_steam):
        search_payload = {
            "items": [
                {"id": 1, "name": "Available in UA", "type": "app"},
                {"id": 2, "name": "Only in US", "type": "app"},
                {"id": 3, "name": "Unavailable", "type": "app"},
                {"id": 4, "name": "A bundle", "type": "sub"},
            ]
        }

        def handler(url, params):
            if url == steam.STORESEARCH_URL:
                return FakeResponse(search_payload)
            available = {"ua": {"1"}, "us": {"2"}}[params["cc"]]
            ids = params["appids"].split(",")
            return FakeResponse(
                {app_id: {"success": app_id in available} for app_id in ids}
            )

        fake_steam(handler)

        results = steam.search_games("game")

        assert results == [
            {"steam_id": 1, "title": "Available in UA",
             "img_url": steam.HEADER_URL.format(1)},
            {"steam_id": 2, "title": "Only in US",
             "img_url": steam.HEADER_URL.format(2)},
        ]

    def test_no_results(self, fake_steam):
        calls = fake_steam(lambda url, params: FakeResponse({"items": []}))

        assert steam.search_games("nothing") == []
        assert len(calls) == 1  # no availability lookup for an empty list


class TestFetchGame:
    def test_returns_title_and_image(self, fake_steam):
        data = {"name": "Hades", "header_image": "https://img/hades.jpg"}
        fake_steam(lambda url, params: FakeResponse(app_details(1145360, data)))

        assert steam.fetch_game(1145360) == {
            "title": "Hades",
            "img_url": "https://img/hades.jpg",
        }

    def test_falls_back_to_us_store(self, fake_steam):
        def handler(url, params):
            success = params["cc"] == "us"
            return FakeResponse(app_details(10, {"name": "US only"}, success))

        calls = fake_steam(handler)

        game = steam.fetch_game(10)

        assert game == {"title": "US only", "img_url": steam.HEADER_URL.format(10)}
        assert [params["cc"] for _, params in calls] == ["ua", "us"]

    def test_unknown_game_returns_none(self, fake_steam):
        fake_steam(lambda url, params: FakeResponse(app_details(1, None, False)))

        assert steam.fetch_game(1) is None


class TestFetchAppDetails:
    def test_maps_steam_data(self, fake_steam):
        data = {
            "short_description": "Tom &amp; Jerry",
            "screenshots": [
                {"path_thumbnail": "t1", "path_full": "f1"},
                {"path_thumbnail": "t2"},
            ],
            "release_date": {"date": "1 Jan, 2020", "coming_soon": False},
            "developers": ["Dev"],
            "publishers": ["Pub"],
            "genres": [{"description": "RPG"}, {}],
            "metacritic": {"score": 93},
        }
        fake_steam(lambda url, params: FakeResponse(app_details(5, data)))

        details = steam.fetch_app_details(5)

        assert details == {
            "short_description": "Tom & Jerry",
            "screenshots": [{"thumbnail": "t1", "full": "f1"}],
            "release_date": "1 Jan, 2020",
            "coming_soon": False,
            "developers": ["Dev"],
            "publishers": ["Pub"],
            "genres": ["RPG"],
            "metacritic_score": 93,
            "store_url": "https://store.steampowered.com/app/5",
        }

    def test_missing_fields_have_defaults(self, fake_steam):
        fake_steam(lambda url, params: FakeResponse(app_details(5, {"name": "x"})))

        details = steam.fetch_app_details(5)

        assert details["short_description"] is None
        assert details["screenshots"] == []
        assert details["metacritic_score"] is None

    def test_unknown_game_returns_none(self, fake_steam):
        fake_steam(lambda url, params: FakeResponse(app_details(1, None, False)))

        assert steam.fetch_app_details(1) is None
