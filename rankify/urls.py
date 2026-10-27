from django.urls import path
from . import views

urlpatterns = [
    path("collections/", views.CollectionListView.as_view()),
    path("collections/<int:collection_id>/", views.CollectionDetailView.as_view()),
    path("games/", views.GameListView.as_view()),
    path("games/<int:steam_id>/", views.GameDetailView.as_view()),
    path("collections/<int:collection_id>/games/", views.CollectionGameView.as_view()),
    path("collections/<int:collection_id>/games/<int:steam_id>/", views.CollectionGameDetailView.as_view()),
    path("steam/games/", views.SteamSearchView.as_view()),
    path("collections/<int:collection_id>/votes/<int:collection_game_id>", views.VoteView.as_view()),

]
