from django.db import models


class Game(models.Model):
    steam_id = models.PositiveIntegerField(unique=True)
    title = models.CharField(max_length=200, blank=True)
    img_url = models.CharField(max_length=300, blank=True)

    def __str__(self):
        return self.title


class Collection(models.Model):
    GENRES = [
        ("action", "Action"),
        ("adventure", "Adventure"),
        ("rpg", "RPG"),
        ("shooter", "Shooter"),
        ("strategy", "Strategy"),
        ("simulation", "Simulation"),
        ("sports", "Sports"),
        ("racing", "Racing"),
        ("fighting", "Fighting"),
        ("platformer", "Platformer"),
        ("puzzle", "Puzzle"),
        ("horror", "Horror"),
        ("survival", "Survival"),
        ("open_world", "Open World"),
        ("roguelike", "Roguelike"),
        ("indie", "Indie"),
        ("other", "Other"),
    ]

    title = models.CharField(max_length=100)
    genre = models.CharField(max_length=30, choices=GENRES)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class CollectionGame(models.Model):
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE, related_name='collection_games')
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    votes = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["collection", "game"], name='unique_game')]
