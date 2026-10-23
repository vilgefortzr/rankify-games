from rest_framework import serializers
from .models import Collection, Game, Vote


class CollectionSerializer(serializers.ModelSerializer):
    total_votes = serializers.IntegerField(read_only=True, default=0)
    games_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Collection
        fields = ['id', 'title', 'genre', 'description', 'created_at', 'total_votes', 'games_count']


class CollectionDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collection
        fields = ['id', 'title', 'genre', 'description', 'created_at']
