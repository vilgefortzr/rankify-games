import logging

import pytest

from conftest import PASSWORD

pytestmark = pytest.mark.django_db


def messages(caplog, level):
    return [r.getMessage() for r in caplog.records if r.levelno == level]


def test_creating_collection_is_logged(user_client, user, caplog):
    caplog.set_level(logging.INFO, logger="rankify")

    response = user_client.post(
        "/api/v1/collections/", {"title": "New", "genre": "rpg"}, format="json"
    )

    assert f"User {user.id} created collection {response.json()['id']}" in messages(
        caplog, logging.INFO
    )


def test_permission_denied_is_logged_as_warning(
    other_client, other_user, collection, caplog
):
    other_client.patch(
        f"/api/v1/collections/{collection.id}/", {"title": "x"}, format="json"
    )

    assert (
        f"User {other_user.id} was denied editing collection {collection.id}"
        in messages(caplog, logging.WARNING)
    )


def test_registration_log_has_no_password_or_email(api_client, caplog):
    caplog.set_level(logging.DEBUG)

    api_client.post(
        "/api/v1/auth/register/",
        {
            "username": "carol",
            "email": "carol@example.com",
            "password": PASSWORD,
            "password_confirmation": PASSWORD,
        },
        format="json",
    )

    assert any("Registered user" in m for m in messages(caplog, logging.INFO))
    assert PASSWORD not in caplog.text
    assert "carol@example.com" not in caplog.text


def test_login_log_has_no_password_or_tokens(api_client, user, caplog):
    caplog.set_level(logging.DEBUG)

    tokens = api_client.post(
        "/api/v1/auth/login/",
        {"username": "alice", "password": PASSWORD},
        format="json",
    ).json()

    assert PASSWORD not in caplog.text
    assert tokens["access"] not in caplog.text
    assert tokens["refresh"] not in caplog.text


def test_steam_failure_is_logged_as_warning(user_client, caplog):
    user_client.get("/api/v1/steam/games/", {"search": "witcher"})

    assert any("Steam request" in m for m in messages(caplog, logging.WARNING))


def test_unhandled_error_is_logged_and_returns_500(api_client, monkeypatch, caplog):
    def broken(self, request):
        raise RuntimeError("boom")

    monkeypatch.setattr("rankify.views.GameListView.get", broken)
    api_client.raise_request_exception = False

    response = api_client.get("/api/v1/games/")

    assert response.status_code == 500
    error = next(r for r in caplog.records if r.name == "rankify.exception_handler")
    assert error.levelno == logging.ERROR
    assert error.exc_info[0] is RuntimeError
