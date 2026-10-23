from django.urls import path
from . import views

urlpatterns = [
    path("collections/", views.CollectionListView.as_view()),
    path("collections/<int:collection_id>/", views.CollectionDetailView.as_view()),
]
