from rest_framework import serializers
from .models import Collection, Game


class CollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collection
        fields = ['id', 'title', 'genre', 'description', 'created_at']


class CollectionDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collection
        fields = ['id', 'title', 'genre', 'description', 'created_at']
