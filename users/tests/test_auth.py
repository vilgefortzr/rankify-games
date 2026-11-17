import pytest
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken

from conftest import PASSWORD

pytestmark = pytest.mark.django_db

REGISTER_URL = "/api/v1/auth/register/"
LOGIN_URL = "/api/v1/auth/login/"
REFRESH_URL = "/api/v1/auth/token/refresh/"
ME_URL = "/api/v1/auth/me/"


def details(response):
    return response.json()["error"]["details"]


@pytest.fixture
def registration_data():
    return {
        "username": "carol",
        "first_name": "Carol",
        "last_name": "",
        "email": "carol@example.com",
        "password": PASSWORD,
        "password_confirmation": PASSWORD,
    }


class TestRegister:
    def test_creates_user_with_hashed_password(self, api_client, registration_data):
        response = api_client.post(REGISTER_URL, registration_data, format="json")

        assert response.status_code == 201
        user = User.objects.get(username="carol")
        assert user.password != PASSWORD
        assert user.check_password(PASSWORD)

    def test_response_never_contains_passwords(self, api_client, registration_data):
        response = api_client.post(REGISTER_URL, registration_data, format="json")

        data = response.json()
        assert set(data) == {"id", "username", "first_name", "last_name", "email"}

    def test_first_and_last_name_are_optional(self, api_client, registration_data):
        del registration_data["first_name"], registration_data["last_name"]

        response = api_client.post(REGISTER_URL, registration_data, format="json")

        assert response.status_code == 201

    @pytest.mark.parametrize(
        "field", ["username", "email", "password", "password_confirmation"]
    )
    def test_required_fields(self, api_client, registration_data, field):
        del registration_data[field]

        response = api_client.post(REGISTER_URL, registration_data, format="json")

        assert response.status_code == 400
        assert field in details(response)

    @pytest.mark.parametrize(
        "changes, field",
        [
            ({"email": "not-an-email"}, "email"),
            ({"username": "x" * 151}, "username"),
            ({"password_confirmation": "Different1!"}, "password_confirmation"),
            ({"password": "short", "password_confirmation": "short"}, "password"),
            ({"password": "12345678901", "password_confirmation": "12345678901"}, "password"),
            ({"password": "password123", "password_confirmation": "password123"}, "password"),
            ({"password": "carol123", "password_confirmation": "carol123"}, "password"),
        ],
        ids=[
            "bad-email",
            "username-too-long",
            "passwords-dont-match",
            "password-too-short",
            "password-numeric",
            "password-common",
            "password-similar-to-username",
        ],
    )
    def test_invalid_data_gets_400(self, api_client, registration_data, changes, field):
        response = api_client.post(
            REGISTER_URL, {**registration_data, **changes}, format="json"
        )

        assert response.status_code == 400
        assert field in details(response)
        assert not User.objects.filter(username=registration_data["username"]).exists()

    @pytest.mark.parametrize("field", ["username", "email"])
    def test_duplicate_username_or_email_gets_400(
        self, api_client, registration_data, user, field
    ):
        registration_data[field] = getattr(user, field)

        response = api_client.post(REGISTER_URL, registration_data, format="json")

        assert response.status_code == 400
        assert field in details(response)


class TestLogin:
    def test_returns_access_and_refresh_tokens(self, api_client, user):
        response = api_client.post(
            LOGIN_URL, {"username": "alice", "password": PASSWORD}, format="json"
        )

        assert response.status_code == 200
        assert set(response.json()) == {"access", "refresh"}

    def test_wrong_password_gets_401(self, api_client, user):
        response = api_client.post(
            LOGIN_URL, {"username": "alice", "password": "wrong"}, format="json"
        )

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "no_active_account"

    def test_missing_fields_get_400(self, api_client):
        response = api_client.post(LOGIN_URL, {}, format="json")

        assert response.status_code == 400

    def test_access_token_from_login_works(self, api_client, user):
        tokens = api_client.post(
            LOGIN_URL, {"username": "alice", "password": PASSWORD}, format="json"
        ).json()
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        response = api_client.get(ME_URL)

        assert response.status_code == 200
        assert response.json()["username"] == "alice"


class TestRefresh:
    def test_returns_new_access_token(self, api_client, user):
        refresh = RefreshToken.for_user(user)

        response = api_client.post(REFRESH_URL, {"refresh": str(refresh)}, format="json")

        assert response.status_code == 200
        assert "access" in response.json()

    def test_invalid_refresh_token_gets_401(self, api_client):
        response = api_client.post(REFRESH_URL, {"refresh": "garbage"}, format="json")

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "token_not_valid"

    def test_access_token_cannot_be_used_as_refresh(self, api_client, user):
        access = RefreshToken.for_user(user).access_token

        response = api_client.post(REFRESH_URL, {"refresh": str(access)}, format="json")

        assert response.status_code == 401


class TestMe:
    def test_returns_current_user(self, user_client, user):
        response = user_client.get(ME_URL)

        assert response.status_code == 200
        assert response.json() == {
            "id": user.id,
            "username": "alice",
            "first_name": "",
            "last_name": "",
            "email": "alice@example.com",
            "is_staff": False,
        }

    def test_admin_flag(self, admin_client):
        assert admin_client.get(ME_URL).json()["is_staff"] is True

    def test_anonymous_gets_401(self, api_client):
        response = api_client.get(ME_URL)

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "not_authenticated"

    def test_refresh_token_cannot_be_used_as_access(self, api_client, user):
        refresh = RefreshToken.for_user(user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh}")

        assert api_client.get(ME_URL).status_code == 401
