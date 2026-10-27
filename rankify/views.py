from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError, NotFound
from .models import Collection, CollectionGame, Game
from .serializers import CollectionSerializer, CollectionDetailSerializer, GameSerializer, GameDetailSerializer, \
    AddGameSerializer
from django.shortcuts import get_object_or_404
from django.db.models import Count, Prefetch, Model
from .steam import fetch_app_details, search_games


class SteamSearchView(APIView):
    def get(self, request):
        term = request.query_params.get("search", "").strip()
        if not term:
            raise ValidationError({"search": ["Вкажіть пошуковий запит."]})
        return Response(search_games(term))


class CollectionListView(APIView):
    def get(self, request):
        games = (
            CollectionGame.objects
            .select_related("game")
            .annotate(votes_count=Count("votes"))
            .order_by("-votes_count", "game__title")
        )
        collections = (Collection.objects.annotate(
            total_votes=Count("collection_games__votes", distinct=True),
            games_count=Count("collection_games", distinct=True)
        ).prefetch_related(
            Prefetch(
                "collection_games", queryset=games))
            .order_by("-total_votes"))
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
        games = (CollectionGame.objects
                 .select_related('game')
                 .annotate(votes_count=Count('votes'))
                 .order_by("-votes_count")
                 )
        collection = get_object_or_404(
            Collection.objects.prefetch_related(
                Prefetch("collection_games", queryset=games)
            ), id=collection_id
        )
        serializer = CollectionDetailSerializer(collection)
        return Response(serializer.data)

    def delete(self, request, collection_id):
        collection = get_object_or_404(Collection, id=collection_id)
        collection.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def patch(self, request, collection_id):
        collection = get_object_or_404(Collection, id=collection_id)
        serializer = CollectionDetailSerializer(collection, data=request.data, partial=True)
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
        game = get_object_or_404(Game.objects.prefetch_related(
            Prefetch("in_collections", queryset=game_collections)), steam_id=steam_id)
        serializer = GameDetailSerializer(game)
        data = serializer.data
        try:
            data["steam"] = fetch_app_details(steam_id)
        except SteamUnavailableError:
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
            details = fetch_app_details(steam_id)
            if details is None:
                raise NotFound("Гру не знайдено у Steam.")
            game = Game.objects.create(
                steam_id=steam_id,
                title=details["name"],
                img_url=details["header_image"],
            )

        if CollectionGame.objects.filter(collection=collection, game=game).exists():
            raise ConflictError("Гра вже є в цій колекції.")

        CollectionGame.objects.create(collection=collection, game=game)
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





