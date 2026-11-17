import pytest

from rankify.models import Vote

pytestmark = pytest.mark.django_db


def test_str(collection, collection_game, vote):
    assert str(collection) == "Best Witcher Game"
    assert str(collection_game.game) == "The Witcher 3"
    assert str(collection_game) == "The Witcher 3 -> Best Witcher Game"
    assert str(vote) == "Vote for The Witcher 3 -> Best Witcher Game from alice"


def test_str_of_anonymous_vote(collection_game):
    vote = Vote.objects.create(collection_game=collection_game)

    assert str(vote) == "Vote for The Witcher 3 -> Best Witcher Game"
