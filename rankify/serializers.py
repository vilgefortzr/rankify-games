from rest_framework import serializers
from .models import Collection, Game, CollectionGame


class CollectionSerializer(serializers.ModelSerializer):
    total_votes = serializers.IntegerField(read_only=True, default=0)
    games_count = serializers.IntegerField(read_only=True, default=0)
    top_game = serializers.SerializerMethodField()

    class Meta:
        model = Collection
        fields = ['id', 'title', 'genre', 'description',
                  'created_at', 'total_votes', 'games_count',
                  'top_game']

    def get_top_game(self, obj):
        top_games = getattr(obj, "top_games", [])
        return GameSerializer(top_games[0].game).data if top_games else None


class GameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Game
        fields = ['id', 'steam_id', 'title', 'img_url']


class CollectionGameSerializer(serializers.ModelSerializer):
    game = GameSerializer(read_only=True)
    votes_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = CollectionGame
        fields = ['id', 'game', 'votes_count']


class CollectionDetailSerializer(serializers.ModelSerializer):
    games = CollectionGameSerializer(source='collection_games', many=True, read_only=True)

    class Meta:
        model = Collection
        fields = ['id', 'title', 'genre', 'description', 'created_at', 'games']


class CollectionUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collection
        fields = ['id', 'title', 'genre', 'description']


class GameCollectionSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='collection.id', read_only=True)
    title = serializers.CharField(source='collection.title', read_only=True)
    genre = serializers.CharField(source='collection.genre', read_only=True)

    class Meta:
        model = CollectionGame
        fields = ['id', 'title', 'genre']


class GameDetailSerializer(serializers.ModelSerializer):
    game_collections = GameCollectionSerializer(source='in_collections', many=True, read_only=True)

    class Meta:
        model = Game
        fields = ['id', 'steam_id', 'title', 'img_url', 'game_collections']


class AddGameSerializer(serializers.Serializer):
    steam_id = serializers.IntegerField(min_value=1)

