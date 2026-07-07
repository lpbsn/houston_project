from django.apps import AppConfig


class UploadsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "houston.uploads"

    def ready(self) -> None:
        from . import checks  # noqa: F401
