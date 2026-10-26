from rest_framework import serializers
from .models import Collection, Game, Vote, CollectionGame


class CollectionSerializer(serializers.ModelSerializer):
    total_votes = serializers.IntegerField(read_only=True, default=0)
    games_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Collection
        fields = ['id', 'title', 'genre', 'description', 'created_at', 'total_votes', 'games_count']


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
