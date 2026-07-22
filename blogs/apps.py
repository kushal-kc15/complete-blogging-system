from django.apps import AppConfig


class BlogsConfig(AppConfig):
    name = 'blogs'

    def ready(self):
        # Register signal receivers (allauth social sign-up profile handling).
        from . import signals  # noqa: F401
