import pytest

from rankify.models import CollectionGame, Game

pytestmark = pytest.mark.django_db


def games_url(collection_id):
    return f"/api/v1/collections/{collection_id}/games/"


def game_in_collection_url(collection_id, steam_id):
    return f"/api/v1/collections/{collection_id}/games/{steam_id}/"


@pytest.fixture
def steam_game(monkeypatch):
    def fake_fetch_game(steam_id):
        return {"title": "Cyberpunk 2077", "img_url": f"https://img/{steam_id}.jpg"}

    monkeypatch.setattr("rankify.views.fetch_game", fake_fetch_game)


@pytest.fixture
def steam_unknown_game(monkeypatch):
    monkeypatch.setattr("rankify.views.fetch_game", lambda steam_id: None)


class TestAddGameToCollection:
    def test_author_adds_game_from_steam(self, user_client, collection, steam_game):
        response = user_client.post(
            games_url(collection.id), {"steam_id": 1091500}, format="json"
        )

        assert response.status_code == 201
        assert response.json()["title"] == "Cyberpunk 2077"
        assert CollectionGame.objects.filter(
            collection=collection, game__steam_id=1091500
        ).exists()

    def test_known_game_is_reused_without_steam(self, user_client, collection, game):
        response = user_client.post(
            games_url(collection.id), {"steam_id": game.steam_id}, format="json"
        )

        assert response.status_code == 201
        assert Game.objects.filter(steam_id=game.steam_id).count() == 1

    def test_admin_can_add_to_any_collection(
        self, admin_client, ownerless_collection, game
    ):
        response = admin_client.post(
            games_url(ownerless_collection.id), {"steam_id": game.steam_id}, format="json"
        )

        assert response.status_code == 201

    def test_other_user_gets_403(self, other_client, collection, game):
        response = other_client.post(
            games_url(collection.id), {"steam_id": game.steam_id}, format="json"
        )

        assert response.status_code == 403
        assert not CollectionGame.objects.filter(collection=collection).exists()

    def test_anonymous_gets_401(self, api_client, collection, game):
        response = api_client.post(
            games_url(collection.id), {"steam_id": game.steam_id}, format="json"
        )

        assert response.status_code == 401

    def test_duplicate_game_gets_409(self, user_client, collection, collection_game):
        response = user_client.post(
            games_url(collection.id),
            {"steam_id": collection_game.game.steam_id},
            format="json",
        )

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "game_already_in_collection"

    def test_game_unknown_to_steam_gets_404(
        self, user_client, collection, steam_unknown_game
    ):
        response = user_client.post(
            games_url(collection.id), {"steam_id": 1}, format="json"
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "game_not_found"

    def test_steam_unavailable_gets_503(self, user_client, collection):
        response = user_client.post(
            games_url(collection.id), {"steam_id": 1091500}, format="json"
        )

        assert response.status_code == 503
        assert response.json()["error"]["code"] == "steam_unavailable"

    @pytest.mark.parametrize("steam_id", [0, -5, "abc", None])
    def test_invalid_steam_id_gets_400(self, user_client, collection, steam_id):
        response = user_client.post(
            games_url(collection.id), {"steam_id": steam_id}, format="json"
        )

        assert response.status_code == 400
        assert "steam_id" in response.json()["error"]["details"]

    def test_missing_collection_gets_404(self, user_client):
        response = user_client.post(games_url(999_999), {"steam_id": 1}, format="json")

        assert response.status_code == 404


class TestRemoveGameFromCollection:
    def test_author_removes_game(self, user_client, collection, collection_game):
        steam_id = collection_game.game.steam_id

        response = user_client.delete(game_in_collection_url(collection.id, steam_id))

        assert response.status_code == 204
        assert not CollectionGame.objects.filter(id=collection_game.id).exists()
        assert not Game.objects.filter(steam_id=steam_id).exists()

    def test_game_used_in_another_collection_is_kept(
        self, user_client, collection, collection_game, ownerless_collection
    ):
        game = collection_game.game
        CollectionGame.objects.create(collection=ownerless_collection, game=game)

        user_client.delete(game_in_collection_url(collection.id, game.steam_id))

        assert Game.objects.filter(id=game.id).exists()

    def test_other_user_gets_403(self, other_client, collection, collection_game):
        url = game_in_collection_url(collection.id, collection_game.game.steam_id)

        response = other_client.delete(url)

        assert response.status_code == 403
        assert CollectionGame.objects.filter(id=collection_game.id).exists()

    def test_anonymous_gets_401(self, api_client, collection, collection_game):
        url = game_in_collection_url(collection.id, collection_game.game.steam_id)

        assert api_client.delete(url).status_code == 401

    def test_game_not_in_collection_gets_404(self, user_client, collection):
        response = user_client.delete(game_in_collection_url(collection.id, 123))

        assert response.status_code == 404


class TestGamesCatalogue:
    def test_list_games(self, api_client, game, other_game):
        response = api_client.get("/api/v1/games/", {"search": "witcher 3"})

        assert response.status_code == 200
        assert [g["steam_id"] for g in response.json()] == [game.steam_id]

    def test_game_detail_with_steam_details(self, api_client, collection_game, monkeypatch):
        monkeypatch.setattr(
            "rankify.views.fetch_app_details",
            lambda steam_id: {"short_description": "A game"},
        )

        response = api_client.get(f"/api/v1/games/{collection_game.game.steam_id}/")

        data = response.json()
        assert response.status_code == 200
        assert data["steam"] == {"short_description": "A game"}
        assert data["game_collections"][0]["id"] == collection_game.collection_id

    def test_game_detail_when_steam_is_down(self, api_client, game):
        response = api_client.get(f"/api/v1/games/{game.steam_id}/")

        assert response.status_code == 200
        assert response.json()["steam"] is None

    def test_missing_game_gets_404(self, api_client):
        assert api_client.get("/api/v1/games/999999/").status_code == 404


class TestSteamSearch:
    url = "/api/v1/steam/games/"

    def test_authenticated_user_can_search(self, user_client, monkeypatch):
        results = [{"steam_id": 1, "title": "Witcher", "img_url": "https://img/1.jpg"}]
        monkeypatch.setattr("rankify.views.search_games", lambda term: results)

        response = user_client.get(self.url, {"search": "witcher"})

        assert response.status_code == 200
        assert response.json() == results

    def test_anonymous_gets_401(self, api_client):
        assert api_client.get(self.url, {"search": "witcher"}).status_code == 401

    def test_empty_search_gets_400(self, user_client):
        response = user_client.get(self.url, {"search": "   "})

        assert response.status_code == 400
        assert "search" in response.json()["error"]["details"]

    def test_steam_unavailable_gets_503(self, user_client):
        response = user_client.get(self.url, {"search": "witcher"})

        assert response.status_code == 503
