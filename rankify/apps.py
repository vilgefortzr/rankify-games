from django.apps import AppConfig


class RankifyConfig(AppConfig):
    name = "rankify"

    def ready(self):
        from . import schema  # noqa: F401  registers the OpenAPI descriptions
