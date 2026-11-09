from django.db.models import Count, Prefetch
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import APIException, NotFound, ValidationError
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


class SteamSearchView(APIView):
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
        serializer.save()
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
            ),
            id=collection_id,
        )
        serializer = CollectionDetailSerializer(collection)
        return Response(serializer.data)

    def delete(self, request, collection_id):
        collection = get_object_or_404(Collection, id=collection_id)
        games_ids = [collection_game.game.id for collection_game
                 in CollectionGame.objects.filter(collection_id=collection_id)]
        collection.delete()
        Game.objects.filter(id__in=games_ids, in_collections__isnull=True).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def patch(self, request, collection_id):
        collection = get_object_or_404(Collection, id=collection_id)
        serializer = CollectionUpdateSerializer(
            collection, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
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
            data["steam"] = None
        return Response(data)


class CollectionGameView(APIView):
    def post(self, request, collection_id):
        collection = get_object_or_404(Collection, id=collection_id)
        serializer = AddGameSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        steam_id = serializer.validated_data["steam_id"]

        game = Game.objects.filter(steam_id=steam_id).first()
        if game is None:
            game_data = fetch_game(steam_id)
            if game_data is None:
                raise NotFound("Game not found on Steam.", code="game_not_found")
            game, _ = Game.objects.get_or_create(steam_id=steam_id, defaults=game_data)

        _, created = CollectionGame.objects.get_or_create(
            collection=collection, game=game
        )
        if not created:
            raise ConflictError(
                "This game is already in the collection.",
                code="game_already_in_collection",
            )

        return Response(GameSerializer(game).data, status=status.HTTP_201_CREATED)


class CollectionGameDetailView(APIView):
    def delete(self, request, collection_id, steam_id):
        collection_game = get_object_or_404(
            CollectionGame, collection_id=collection_id, game__steam_id=steam_id
        )
        game = collection_game.game
        collection_game.delete()

        if not CollectionGame.objects.filter(game=game).exists():
            game.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class VoteView(APIView):
    def post(self, request, collection_id, collection_game_id):
        collection_game = get_object_or_404(
            CollectionGame, id=collection_game_id, collection_id=collection_id
        )
        Vote.objects.create(collection_game=collection_game)
        votes_count = collection_game.votes.count()
        return Response(
            {
                "game_id": collection_game.game_id,
                "votes_count": votes_count,
            },
            status=status.HTTP_201_CREATED,
        )

    def delete(self, request, collection_id, collection_game_id):
        collection_game = get_object_or_404(
            CollectionGame, id=collection_game_id, collection_id=collection_id
        )
        vote = collection_game.votes.first()
        if vote is None:
            raise NotFound("This game has no votes yet.", code="game_has_no_votes")
        vote.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
