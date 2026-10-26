from rest_framework import serializers
from .models import Collection, Game, Vote, CollectionGame


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
        top = next(iter(obj.collection_games.all()), None)
        return GameSerializer(top.game).data if top else None


class GameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Game
        fields = ['id', 'steam_id', 'title', 'img_url']


class CollectionGameSerializer(serializers.ModelSerializer):
    game = GameSerializer(read_only=True)
    votes_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = CollectionGame
        fields = ['game', 'votes_count']


class CollectionDetailSerializer(serializers.ModelSerializer):
    games = CollectionGameSerializer(source='collection_games', many=True, read_only=True)

    class Meta:
        model = Collection
        fields = ['id', 'title', 'genre', 'description', 'created_at', 'games']
