import pytest

from rankify.models import Collection, CollectionGame, Game, Vote

LIST_URL = "/api/v1/collections/"


def detail_url(collection_id):
    return f"/api/v1/collections/{collection_id}/"


def error_code(response):
    return response.json()["error"]["code"]


pytestmark = pytest.mark.django_db


class TestListCollections:
    def test_anonymous_can_list(self, api_client, collection):
        response = api_client.get(LIST_URL)

        assert response.status_code == 200
        assert collection.id in [item["id"] for item in response.json()]

    def test_search_filters_by_title(self, api_client, collection, ownerless_collection):
        response = api_client.get(LIST_URL, {"search": "witcher game"})

        assert response.status_code == 200
        assert [item["id"] for item in response.json()] == [collection.id]

    def test_includes_vote_stats_and_top_game(
        self, api_client, collection, collection_game, other_collection_game, vote
    ):
        response = api_client.get(LIST_URL, {"search": collection.title})

        item = response.json()[0]
        assert item["total_votes"] == 1
        assert item["games_count"] == 2
        assert item["top_game"]["steam_id"] == collection_game.game.steam_id


class TestCreateCollection:
    payload = {"title": "Best Mafia Game", "genre": "action", "description": "?"}

    def test_authenticated_user_creates_collection_as_author(self, user_client, user):
        response = user_client.post(LIST_URL, self.payload, format="json")

        assert response.status_code == 201
        assert response.json()["title"] == "Best Mafia Game"
        assert Collection.objects.get(id=response.json()["id"]).author == user

    def test_description_is_optional(self, user_client):
        response = user_client.post(
            LIST_URL, {"title": "No description", "genre": "rpg"}, format="json"
        )

        assert response.status_code == 201
        assert response.json()["description"] == ""

    def test_anonymous_gets_401(self, api_client):
        response = api_client.post(LIST_URL, self.payload, format="json")

        assert response.status_code == 401
        assert error_code(response) == "not_authenticated"
        assert not Collection.objects.filter(title="Best Mafia Game").exists()

    def test_invalid_token_gets_401(self, api_client):
        api_client.credentials(HTTP_AUTHORIZATION="Bearer not-a-real-token")

        response = api_client.post(LIST_URL, self.payload, format="json")

        assert response.status_code == 401
        assert error_code(response) == "token_not_valid"

    @pytest.mark.parametrize(
        "payload, field",
        [
            ({"genre": "rpg"}, "title"),
            ({"title": "No genre"}, "genre"),
            ({"title": "Bad genre", "genre": "not-a-genre"}, "genre"),
            ({"title": "x" * 101, "genre": "rpg"}, "title"),
        ],
    )
    def test_invalid_data_gets_400_with_field_errors(self, user_client, payload, field):
        response = user_client.post(LIST_URL, payload, format="json")

        assert response.status_code == 400
        assert field in response.json()["error"]["details"]

    def test_author_cannot_be_set_from_request(self, user_client, user, other_user):
        payload = {**self.payload, "author": other_user.id}

        response = user_client.post(LIST_URL, payload, format="json")

        assert response.status_code == 201
        assert Collection.objects.get(id=response.json()["id"]).author == user


class TestRetrieveCollection:
    def test_anonymous_gets_details(self, api_client, collection, collection_game):
        response = api_client.get(detail_url(collection.id))

        data = response.json()
        assert response.status_code == 200
        assert data["title"] == collection.title
        assert data["author"] == {"id": collection.author.id, "username": "alice"}
        assert data["games"][0]["game"]["steam_id"] == collection_game.game.steam_id
        assert data["user_vote"] is None

    def test_shows_current_user_vote(self, user_client, collection, vote):
        response = user_client.get(detail_url(collection.id))

        assert response.json()["user_vote"] == vote.collection_game_id

    def test_games_are_sorted_by_votes(
        self, api_client, collection, collection_game, other_collection_game, other_user
    ):
        Vote.objects.create(collection_game=other_collection_game, author=other_user)

        response = api_client.get(detail_url(collection.id))

        games = response.json()["games"]
        assert [g["id"] for g in games] == [other_collection_game.id, collection_game.id]
        assert games[0]["votes_count"] == 1

    def test_ownerless_collection_has_null_author(self, api_client, ownerless_collection):
        response = api_client.get(detail_url(ownerless_collection.id))

        assert response.status_code == 200
        assert response.json()["author"] is None

    def test_missing_collection_gets_404(self, api_client):
        response = api_client.get(detail_url(999_999))

        assert response.status_code == 404


class TestUpdateCollection:
    def test_author_can_update(self, user_client, collection):
        response = user_client.patch(
            detail_url(collection.id), {"title": "Renamed"}, format="json"
        )

        assert response.status_code == 200
        assert response.json()["title"] == "Renamed"
        collection.refresh_from_db()
        assert collection.title == "Renamed"

    def test_admin_can_update_any_collection(self, admin_client, collection):
        response = admin_client.patch(
            detail_url(collection.id), {"genre": "action"}, format="json"
        )

        assert response.status_code == 200
        collection.refresh_from_db()
        assert collection.genre == "action"

    def test_other_user_gets_403(self, other_client, collection):
        response = other_client.patch(
            detail_url(collection.id), {"title": "Hacked"}, format="json"
        )

        assert response.status_code == 403
        assert error_code(response) == "permission_denied"
        collection.refresh_from_db()
        assert collection.title == "Best Witcher Game"

    def test_only_admin_can_update_ownerless_collection(
        self, user_client, admin_client, ownerless_collection
    ):
        url = detail_url(ownerless_collection.id)

        assert user_client.patch(url, {"title": "x"}, format="json").status_code == 403
        assert admin_client.patch(url, {"title": "x"}, format="json").status_code == 200

    def test_anonymous_gets_401(self, api_client, collection):
        response = api_client.patch(
            detail_url(collection.id), {"title": "x"}, format="json"
        )

        assert response.status_code == 401

    def test_invalid_data_gets_400(self, user_client, collection):
        response = user_client.patch(
            detail_url(collection.id), {"genre": "not-a-genre"}, format="json"
        )

        assert response.status_code == 400
        assert "genre" in response.json()["error"]["details"]

    def test_missing_collection_gets_404(self, user_client):
        response = user_client.patch(detail_url(999_999), {"title": "x"}, format="json")

        assert response.status_code == 404


class TestDeleteCollection:
    def test_author_can_delete(self, user_client, collection):
        response = user_client.delete(detail_url(collection.id))

        assert response.status_code == 204
        assert not Collection.objects.filter(id=collection.id).exists()

    def test_deleting_removes_games_not_used_elsewhere(
        self, user_client, collection, collection_game, other_collection_game,
        ownerless_collection,
    ):
        shared_game = other_collection_game.game
        CollectionGame.objects.create(collection=ownerless_collection, game=shared_game)

        user_client.delete(detail_url(collection.id))

        assert not Game.objects.filter(id=collection_game.game_id).exists()
        assert Game.objects.filter(id=shared_game.id).exists()

    def test_admin_can_delete_any_collection(self, admin_client, collection):
        response = admin_client.delete(detail_url(collection.id))

        assert response.status_code == 204

    def test_other_user_gets_403(self, other_client, collection):
        response = other_client.delete(detail_url(collection.id))

        assert response.status_code == 403
        assert Collection.objects.filter(id=collection.id).exists()

    def test_anonymous_gets_401(self, api_client, collection):
        response = api_client.delete(detail_url(collection.id))

        assert response.status_code == 401
        assert Collection.objects.filter(id=collection.id).exists()

    def test_missing_collection_gets_404(self, user_client):
        response = user_client.delete(detail_url(999_999))

        assert response.status_code == 404
