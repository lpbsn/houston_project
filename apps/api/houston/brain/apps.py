from django.apps import AppConfig


class BrainConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "houston.brain"

    def ready(self) -> None:
        from houston.brain.worker_beat import register_worker_beat

        register_worker_beat()
