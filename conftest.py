import pytest
import requests
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from rankify.models import Collection, CollectionGame, Game, Vote

PASSWORD = "Str0ngPassw0rd!"


@pytest.fixture(autouse=True)
def empty_database(db):
    """Remove the demo data that migration 0003 seeds, so every test starts clean."""
    Collection.objects.all().delete()
    Game.objects.all().delete()


@pytest.fixture(autouse=True)
def fast_password_hasher(settings):
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@pytest.fixture(autouse=True)
def no_steam_network(monkeypatch):
    """Any real request to Steam fails, as if Steam were down."""

    def offline(*args, **kwargs):
        raise requests.ConnectionError("Network access is disabled in tests")

    monkeypatch.setattr("rankify.steam.requests.get", offline)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="alice", email="alice@example.com", password=PASSWORD
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        username="bob", email="bob@example.com", password=PASSWORD
    )


@pytest.fixture
def admin(db):
    return User.objects.create_user(
        username="admin", email="admin@example.com", password=PASSWORD, is_staff=True
    )


@pytest.fixture
def client_for():
    def make(user):
        client = APIClient()
        token = AccessToken.for_user(user)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return client

    return make


@pytest.fixture
def user_client(client_for, user):
    return client_for(user)


@pytest.fixture
def other_client(client_for, other_user):
    return client_for(other_user)


@pytest.fixture
def admin_client(client_for, admin):
    return client_for(admin)


@pytest.fixture
def collection(user):
    return Collection.objects.create(
        title="Best Witcher Game",
        genre="rpg",
        description="Which one is the best?",
        author=user,
    )


@pytest.fixture
def ownerless_collection(db):
    """Like the seed collections: no author, so only admins can edit it."""
    return Collection.objects.create(title="Ownerless", genre="action")


@pytest.fixture
def game(db):
    return Game.objects.create(steam_id=292030, title="The Witcher 3")


@pytest.fixture
def other_game(db):
    return Game.objects.create(steam_id=20920, title="The Witcher 2")


@pytest.fixture
def collection_game(collection, game):
    return CollectionGame.objects.create(collection=collection, game=game)


@pytest.fixture
def other_collection_game(collection, other_game):
    return CollectionGame.objects.create(collection=collection, game=other_game)


@pytest.fixture
def vote(collection_game, user):
    return Vote.objects.create(collection_game=collection_game, author=user)
