from django.contrib import admin
from .models import Collection, CollectionGame, Game, Vote

admin.site.register(Collection)
admin.site.register(CollectionGame)
admin.site.register(Game)
admin.site.register(Vote)
