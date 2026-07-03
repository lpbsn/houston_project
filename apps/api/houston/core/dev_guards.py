from __future__ import annotations

from django.conf import settings

LOCAL_POSTGRES_HOSTS = frozenset({"postgres", "localhost", "127.0.0.1"})


class LocalDevEnvironmentError(RuntimeError):
    """Raised when a local-dev-only operation runs outside a safe environment."""


def assert_local_dev_environment() -> None:
    host = str(settings.DATABASES["default"]["HOST"]).strip().lower()
    if host not in LOCAL_POSTGRES_HOSTS:
        raise LocalDevEnvironmentError(
            f"Refusing to run: POSTGRES_HOST={host!r} is not a local dev host "
            f"({', '.join(sorted(LOCAL_POSTGRES_HOSTS))})."
        )
    if not settings.DEBUG:
        raise LocalDevEnvironmentError(
            "Refusing to run: DJANGO_DEBUG must be True for local-dev-only operations."
        )
