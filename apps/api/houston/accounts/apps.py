from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "houston.accounts"

    def ready(self) -> None:
        import houston.accounts.authentication  # noqa: F401
