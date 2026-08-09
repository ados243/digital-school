from django.apps import AppConfig


class PedagogieConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pedagogie'

    def ready(self):
        from . import signals  # noqa: F401
