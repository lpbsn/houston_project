from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.checks import Error, register


@register()
def check_private_media_root_writable(app_configs, **kwargs):
    media_root = Path(settings.HOUSTON_PRIVATE_MEDIA_ROOT)
    probe = media_root / ".write-check"

    try:
        media_root.mkdir(parents=True, exist_ok=True)
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError:
        return [
            Error(
                f"HOUSTON_PRIVATE_MEDIA_ROOT is not writable: {media_root}",
                hint=(
                    "Create the directory on the host (mkdir -p apps/api/private_media), "
                    "fix permissions (chmod), or on Linux use a docker-compose.override.yml "
                    'with user: "${UID}:${GID}" for api/celery. '
                    "A named volume for private_media is a last resort — see README."
                ),
                id="uploads.E001",
            )
        ]

    return []
