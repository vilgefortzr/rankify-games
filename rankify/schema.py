from drf_spectacular.extensions import OpenApiViewExtension
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import serializers

from users.serializers import MeSerializer, RegisterSerializer

from .serializers import (
    AddGameSerializer,
    CollectionDetailSerializer,
    CollectionSerializer,
    CollectionUpdateSerializer,
    GameDetailSerializer,
    GameSerializer,
)


class ErrorBodySerializer(serializers.Serializer):
    status = serializers.IntegerField()
    code = serializers.CharField()
    message = serializers.CharField()
    details = serializers.JSONField(
        allow_null=True, help_text="Field errors for `400`, otherwise `null`."
    )


class ErrorSerializer(serializers.Serializer):
    error = ErrorBodySerializer()


class VoteResultSerializer(serializers.Serializer):
    game_id = serializers.IntegerField()
    votes_count = serializers.IntegerField()


class SteamResultSerializer(serializers.Serializer):
    steam_id = serializers.IntegerField()
    title = serializers.CharField()
    img_url = serializers.URLField()


class CollectionDoc(CollectionSerializer):
    top_game = GameSerializer(read_only=True, allow_null=True)

    class Meta(CollectionSerializer.Meta):
        ref_name = "Collection"


class CollectionDetailDoc(CollectionDetailSerializer):
    user_vote = serializers.IntegerField(
        read_only=True,
        allow_null=True,
        help_text="`collection_game_id` the current user voted for, or `null`.",
    )

    class Meta(CollectionDetailSerializer.Meta):
        ref_name = "CollectionDetail"


SEARCH = OpenApiParameter("search", str, description="Part of the title.")

ERROR_DESCRIPTIONS = {
    400: "Invalid data. `details` holds the errors per field.",
    401: "No token, or the token is invalid or expired.",
    403: "Authenticated, but not the collection's author or an admin.",
    404: "Collection not found.",
}


def errors(*codes):
    return {
        code: OpenApiResponse(ErrorSerializer, description=ERROR_DESCRIPTIONS[code])
        for code in codes
    }


def error_example(code, error_code, message, details=None):
    return OpenApiExample(
        f"{code} {error_code}",
        value={
            "error": {
                "status": code,
                "code": error_code,
                "message": message,
                "details": details,
            }
        },
        response_only=True,
        status_codes=[str(code)],
    )


INVALID = error_example(
    400, "invalid", "Invalid input.", {"genre": ['"Action" is not a valid choice.']}
)
NOT_AUTHENTICATED = error_example(
    401, "not_authenticated", "Authentication credentials were not provided."
)
NOT_AUTHOR = error_example(
    403, "permission_denied", "You don't have access to this resource."
)
NOT_FOUND = error_example(404, "not_found", "No Collection matches the given query.")


def document(view_path, **methods):
    class Extension(OpenApiViewExtension):
        target_class = view_path

        def view_replacement(self):
            @extend_schema_view(**methods)
            class Documented(self.target_class):
                pass

            return Documented

    Extension.__name__ = f"{view_path.rsplit('.', 1)[-1]}Schema"
    return Extension


document(
    "rankify.views.CollectionListView",
    get=extend_schema(
        summary="List collections",
        description="Public. Sorted by total votes, then by title.",
        parameters=[SEARCH],
        responses=CollectionDoc(many=True),
    ),
    post=extend_schema(
        summary="Create a collection",
        description="Requires a token. The current user becomes the author.",
        request=CollectionDoc,
        responses={201: CollectionDoc, **errors(400, 401)},
        examples=[
            OpenApiExample(
                "Request",
                value={
                    "title": "Best Mafia Game",
                    "genre": "action",
                    "description": "",
                },
                request_only=True,
            ),
            INVALID,
            NOT_AUTHENTICATED,
        ],
    ),
)

document(
    "rankify.views.CollectionDetailView",
    get=extend_schema(
        summary="Get a collection",
        description="Public. `author` is `null` for collections without an author.",
        responses={200: CollectionDetailDoc, **errors(404)},
        examples=[NOT_FOUND],
    ),
    patch=extend_schema(
        summary="Update a collection",
        description="Only the author or an admin. Send any of the fields.",
        request=CollectionUpdateSerializer,
        responses={200: CollectionUpdateSerializer, **errors(400, 401, 403, 404)},
        examples=[
            OpenApiExample("Request", value={"title": "New title"}, request_only=True),
            INVALID,
            NOT_AUTHENTICATED,
            NOT_AUTHOR,
            NOT_FOUND,
        ],
    ),
    delete=extend_schema(
        summary="Delete a collection",
        description="Only the author or an admin.",
        responses={204: None, **errors(401, 403, 404)},
        examples=[NOT_AUTHENTICATED, NOT_AUTHOR, NOT_FOUND],
    ),
)

document(
    "rankify.views.CollectionGameView",
    post=extend_schema(request=AddGameSerializer, responses={201: GameSerializer}),
)
document(
    "rankify.views.CollectionGameDetailView",
    delete=extend_schema(responses={204: None}),
)
document(
    "rankify.views.VoteView",
    post=extend_schema(request=None, responses={201: VoteResultSerializer}),
    delete=extend_schema(responses={204: None}),
)
document(
    "rankify.views.GameListView",
    get=extend_schema(parameters=[SEARCH], responses=GameSerializer(many=True)),
)
document(
    "rankify.views.GameDetailView",
    get=extend_schema(responses=GameDetailSerializer),
)
document(
    "rankify.views.SteamSearchView",
    get=extend_schema(parameters=[SEARCH], responses=SteamResultSerializer(many=True)),
)
document(
    "users.views.RegisterView",
    post=extend_schema(
        request=RegisterSerializer,
        responses={201: RegisterSerializer},
        examples=[
            OpenApiExample(
                "Request",
                value={
                    "username": "alice",
                    "first_name": "Alice",
                    "last_name": "",
                    "email": "alice@example.com",
                    "password": "Str0ngPassw0rd!",
                    "password_confirmation": "Str0ngPassw0rd!",
                },
                request_only=True,
            ),
        ],
    ),
)
document("users.views.MeView", get=extend_schema(responses=MeSerializer))
