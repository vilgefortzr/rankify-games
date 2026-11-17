import pytest

from rankify.models import Collection, CollectionGame, Vote

pytestmark = pytest.mark.django_db


def vote_url(collection_id, collection_game_id):
    return f"/api/v1/collections/{collection_id}/votes/{collection_game_id}/"


class TestVote:
    def test_user_can_vote(self, user_client, user, collection, collection_game):
        response = user_client.post(vote_url(collection.id, collection_game.id))

        assert response.status_code == 201
        assert response.json() == {
            "game_id": collection_game.game_id,
            "votes_count": 1,
        }
        assert Vote.objects.filter(collection_game=collection_game, author=user).exists()

    def test_anonymous_gets_401(self, api_client, collection, collection_game):
        response = api_client.post(vote_url(collection.id, collection_game.id))

        assert response.status_code == 401
        assert not Vote.objects.exists()

    def test_second_vote_in_same_collection_gets_409(
        self, user_client, collection, vote, other_collection_game
    ):
        response = user_client.post(vote_url(collection.id, other_collection_game.id))

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "vote_exists"
        assert Vote.objects.filter(author=vote.author).count() == 1

    def test_user_can_vote_in_different_collections(
        self, user_client, vote, ownerless_collection, other_game
    ):
        entry = CollectionGame.objects.create(
            collection=ownerless_collection, game=other_game
        )

        response = user_client.post(vote_url(ownerless_collection.id, entry.id))

        assert response.status_code == 201

    def test_different_users_votes_are_counted(
        self, user_client, other_client, collection, collection_game
    ):
        user_client.post(vote_url(collection.id, collection_game.id))
        response = other_client.post(vote_url(collection.id, collection_game.id))

        assert response.json()["votes_count"] == 2

    def test_missing_entry_gets_404(self, user_client, collection):
        response = user_client.post(vote_url(collection.id, 999_999))

        assert response.status_code == 404

    def test_entry_from_another_collection_gets_404(
        self, user_client, collection_game, ownerless_collection
    ):
        response = user_client.post(vote_url(ownerless_collection.id, collection_game.id))

        assert response.status_code == 404


class TestRemoveVote:
    def test_user_can_remove_own_vote(self, user_client, collection, vote):
        response = user_client.delete(vote_url(collection.id, vote.collection_game_id))

        assert response.status_code == 204
        assert not Vote.objects.filter(id=vote.id).exists()

    def test_cannot_remove_someone_elses_vote(self, other_client, collection, vote):
        response = other_client.delete(vote_url(collection.id, vote.collection_game_id))

        assert response.status_code == 404
        assert Vote.objects.filter(id=vote.id).exists()

    def test_no_vote_gets_404(self, user_client, collection, collection_game):
        response = user_client.delete(vote_url(collection.id, collection_game.id))

        assert response.status_code == 404

    def test_anonymous_gets_401(self, api_client, collection, vote):
        response = api_client.delete(vote_url(collection.id, vote.collection_game_id))

        assert response.status_code == 401
        assert Vote.objects.filter(id=vote.id).exists()

    def test_user_can_vote_again_after_removing(
        self, user_client, collection, vote, other_collection_game
    ):
        user_client.delete(vote_url(collection.id, vote.collection_game_id))

        response = user_client.post(vote_url(collection.id, other_collection_game.id))

        assert response.status_code == 201


def test_deleting_user_deletes_their_votes(vote, user):
    user.delete()

    assert not Vote.objects.filter(id=vote.id).exists()


def test_deleting_user_keeps_their_collections(collection, user):
    user.delete()

    collection = Collection.objects.get(id=collection.id)
    assert collection.author is None
