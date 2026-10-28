from django.db import migrations

STEAM_IMG = "https://cdn.akamai.steamstatic.com/steam/apps/{}/header.jpg"

# назва, жанр, опис, [(steam_id, назва гри, кількість голосів), ...]
DATA = [
    ("Best The Witcher Game", "rpg", "Яка частина Відьмака найкраща", [
        (292030, "The Witcher 3: Wild Hunt", 42),
        (20920, "The Witcher 2: Assassins of Kings", 17),
        (20900, "The Witcher: Enhanced Edition", 9),
    ]),
    ("Best Assassin's Creed Game", "action", "Яка частина Assassin's Creed найкраща", [
        (33230, "Assassin's Creed II", 38),
        (242050, "Assassin's Creed IV Black Flag", 29),
        (582160, "Assassin's Creed Origins", 21),
        (812140, "Assassin's Creed Odyssey", 14),
        (911400, "Assassin's Creed III Remastered", 6),
    ]),
    ("Best Mafia Game", "action", "Яка частина Mafia найкраща", [
        (1030840, "Mafia: Definitive Edition", 31),
        (1030830, "Mafia II: Definitive Edition", 24),
        (360430, "Mafia III: Definitive Edition", 8),
    ]),
    ("Best Soulslike", "rpg", "Найкраща гра в жанрі soulslike", [
        (1245620, "ELDEN RING", 47),
        (374320, "DARK SOULS III", 33),
        (814380, "Sekiro: Shadows Die Twice", 26),
        (1627720, "Lies of P", 12),
    ]),
    ("Best FromSoftware Game", "rpg", "Найкраща гра від FromSoftware", [
        (1245620, "ELDEN RING", 67),
        (374320, "DARK SOULS III", 36),
        (814380, "Sekiro: Shadows Die Twice", 68),
        (570940, "DARK SOULS: REMASTERED", 30),
        (335300, "DARK SOULS II: Scholar of the First Sin", 22),
    ]),
    ("Best Roguelike Game", "roguelike", "Найкраща roguelike-гра", [
        (1145360, "Hades", 44),
        (588650, "Dead Cells", 27),
        (367520, "Hollow Knight", 45),
        (250900, "The Binding of Isaac: Rebirth", 15),
        (1030300, "Hollow Knight: Silksong", 48),
    ]),
]


def seed(apps, schema_editor):
    Collection = apps.get_model("rankify", "Collection")
    Game = apps.get_model("rankify", "Game")
    CollectionGame = apps.get_model("rankify", "CollectionGame")
    Vote = apps.get_model("rankify", "Vote")

    for title, genre, description, games in DATA:
        collection, _ = Collection.objects.get_or_create(
            title=title,
            defaults={"genre": genre, "description": description},
        )
        for steam_id, game_title, votes in games:
            game, _ = Game.objects.get_or_create(
                steam_id=steam_id,
                defaults={"title": game_title, "img_url": STEAM_IMG.format(steam_id)},
            )
            collection_game, created = CollectionGame.objects.get_or_create(
                collection=collection, game=game
            )
            if created:
                Vote.objects.bulk_create(
                    [Vote(collection_game=collection_game) for _ in range(votes)]
                )


def unseed(apps, schema_editor):
    Collection = apps.get_model("rankify", "Collection")
    Game = apps.get_model("rankify", "Game")

    Collection.objects.filter(title__in=[row[0] for row in DATA]).delete()
    steam_ids = {steam_id for *_, games in DATA for steam_id, _, _ in games}
    Game.objects.filter(steam_id__in=steam_ids, collectiongame__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('rankify', '0002_remove_collectiongame_votes_vote'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
