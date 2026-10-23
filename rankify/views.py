from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Collection
from .serializers import CollectionSerializer, CollectionDetailSerializer
from django.shortcuts import get_object_or_404
from django.db.models import Count


class CollectionListView(APIView):
    def get(self, request):
        collections = Collection.objects.annotate(
            total_votes=Count("collection_games__vote", distinct=True),
            games_count=Count("collection_games", distinct=True)
        ).order_by("-total_votes")
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
        collection = get_object_or_404(Collection, id=collection_id)
        serializer = CollectionDetailSerializer(collection)
        return Response(serializer.data)
