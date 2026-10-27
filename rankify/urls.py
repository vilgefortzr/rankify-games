from django.urls import path
from . import views

urlpatterns = [
    path("collections/", views.CollectionListView.as_view()),
    path("collections/<int:collection_id>/", views.CollectionDetailView.as_view()),
    path("games/", views.GameListView.as_view()),
    path("games/<int:steam_id>/", views.GameDetailView.as_view()),
]
