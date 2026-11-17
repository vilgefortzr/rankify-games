import logging

from django.db.models import Count, Prefetch
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import APIException, NotFound, \
    ValidationError, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .exception_handler import ConflictError
from .models import Collection, CollectionGame, Game, Vote
from .serializers import (
    AddGameSerializer,
    CollectionDetailSerializer,
    CollectionSerializer,
    CollectionUpdateSerializer,
    GameDetailSerializer,
    GameSerializer,
)
from .steam import fetch_app_details, fetch_game, search_games

logger = logging.getLogger(__name__)


def check_can_edit(user, collection):
    if user != collection.author and not user.is_staff:
        logger.warning(
            "User %s was denied editing collection %s", user.id, collection.id
        )
        raise PermissionDenied("You don't have access to this resource.",
                               "permission_denied")

class SteamSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        term = request.query_params.get("search", "").strip()
        if not term:
            raise ValidationError({"search": ["Provide a search term."]})
        return Response(search_games(term))


class CollectionListView(APIView):
    def get(self, request):
        games = (
            CollectionGame.objects.select_related("game")
            .annotate(votes_count=Count("votes"))
            .order_by("-votes_count", "game__title")
        )
        collections = (
            Collection.objects.annotate(
                total_votes=Count("collection_games__votes", distinct=True),
                games_count=Count("collection_games", distinct=True),
            )
            .prefetch_related(
                Prefetch("collection_games", queryset=games[:1], to_attr="top_games")
            )
            .order_by("-total_votes", "title")
        )
        search = request.query_params.get("search")
        if search:
            collections = collections.filter(title__icontains=search)
        serializer = CollectionSerializer(collections, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = CollectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        collection = serializer.save(author=request.user)
        logger.info("User %s created collection %s", request.user.id, collection.id)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CollectionDetailView(APIView):
    def get(self, request, collection_id):
        games = (
            CollectionGame.objects.select_related("game")
            .annotate(votes_count=Count("votes"))
            .order_by("-votes_count", "game__title")
        )
        collection = get_object_or_404(
            Collection.objects.prefetch_related(
                Prefetch("collection_games", queryset=games)
            ).select_related("author"),
            id=collection_id,
        )
        serializer = CollectionDetailSerializer(collection, context={"request": request})
        return Response(serializer.data)

    def delete(self, request, collection_id):
        collection = get_object_or_404(Collection, id=collection_id)
        check_can_edit(request.user, collection)
        games_ids = [collection_game.game.id for collection_game
                 in CollectionGame.objects.filter(collection_id=collection_id)]
        collection.delete()
        Game.objects.filter(id__in=games_ids, in_collections__isnull=True).delete()
        logger.info("User %s deleted collection %s", request.user.id, collection_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def patch(self, request, collection_id):
        collection = get_object_or_404(Collection, id=collection_id)
        check_can_edit(request.user, collection)
        serializer = CollectionUpdateSerializer(
            collection, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        logger.info(
            "User %s updated collection %s: %s",
            request.user.id,
            collection_id,
            ", ".join(serializer.validated_data),
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class GameListView(APIView):
    def get(self, request):
        games = Game.objects.all()
        search = request.query_params.get("search")
        if search:
            games = games.filter(title__icontains=search)
        serializer = GameSerializer(games, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class GameDetailView(APIView):
    def get(self, request, steam_id):
        game_collections = CollectionGame.objects.select_related("collection")
        game = get_object_or_404(
            Game.objects.prefetch_related(
                Prefetch("in_collections", queryset=game_collections)
            ),
            steam_id=steam_id,
        )
        serializer = GameDetailSerializer(game)
        data = serializer.data
        try:
            data["steam"] = fetch_app_details(steam_id)
        except APIException:
            logger.warning("Showing game %s without Steam details", steam_id)
            data["steam"] = None
        return Response(data)


class CollectionGameView(APIView):
    def post(self, request, collection_id):
        collection = get_object_or_404(Collection, id=collection_id)
        check_can_edit(request.user, collection)
        serializer = AddGameSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        steam_id = serializer.validated_data["steam_id"]

        game = Game.objects.filter(steam_id=steam_id).first()
        if game is None:
            game_data = fetch_game(steam_id)
            if game_data is None:
                logger.info("Game %s not found on Steam", steam_id)
                raise NotFound("Game not found on Steam.", code="game_not_found")
            game, _ = Game.objects.get_or_create(steam_id=steam_id, defaults=game_data)
            logger.info("Loaded game %s (%s) from Steam", steam_id, game.title)

        _, created = CollectionGame.objects.get_or_create(
            collection=collection, game=game,
        )
        if not created:
            raise ConflictError(
                "This game is already in the collection.",
                code="game_already_in_collection",
            )

        logger.info(
            "User %s added game %s to collection %s",
            request.user.id,
            steam_id,
            collection_id,
        )
        return Response(GameSerializer(game).data, status=status.HTTP_201_CREATED)


class CollectionGameDetailView(APIView):
    def delete(self, request, collection_id, steam_id):
        collection_game = get_object_or_404(
            CollectionGame, collection_id=collection_id, game__steam_id=steam_id
        )
        check_can_edit(request.user, collection_game.collection)
        game = collection_game.game
        collection_game.delete()
        logger.info(
            "User %s removed game %s from collection %s",
            request.user.id,
            steam_id,
            collection_id,
        )

        if not CollectionGame.objects.filter(game=game).exists():
            game.delete()
            logger.info("Deleted game %s: it is not in any collection", steam_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class VoteView(APIView):
    def post(self, request, collection_id, collection_game_id):
        collection_game = get_object_or_404(
            CollectionGame, id=collection_game_id, collection_id=collection_id
        )
        if (Vote.objects.filter(author_id=request.user.id,
                                collection_game__collection=collection_game.collection)
                                .exists()):
            raise ConflictError(
                "You have already voted in this collection.",
                code="vote_exists",
            )
        Vote.objects.create(collection_game=collection_game, author=request.user)
        logger.info(
            "User %s voted for game %s in collection %s",
            request.user.id,
            collection_game.game.steam_id,
            collection_id,
        )
        votes_count = collection_game.votes.count()
        return Response(
            {
                "game_id": collection_game.game_id,
                "votes_count": votes_count,
            },
            status=status.HTTP_201_CREATED,
        )

    def delete(self, request, collection_id, collection_game_id):
        vote = get_object_or_404(Vote, collection_game_id=collection_game_id,
                                   collection_game__collection_id=collection_id,
                                   author=request.user)
        vote.delete()
        logger.info(
            "User %s removed their vote in collection %s", request.user.id, collection_id
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
