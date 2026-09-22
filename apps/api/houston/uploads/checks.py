from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.checks import Error, register

from houston.uploads.private_storage import (
    PRIVATE_MEDIA_BACKEND_FILESYSTEM,
    PRIVATE_MEDIA_BACKEND_S3,
    SUPPORTED_PRIVATE_MEDIA_BACKENDS,
)

_S3_REQUIRED_SETTINGS = (
    "HOUSTON_S3_ENDPOINT_URL",
    "HOUSTON_S3_BUCKET",
    "HOUSTON_S3_ACCESS_KEY_ID",
    "HOUSTON_S3_SECRET_ACCESS_KEY",
    "HOUSTON_S3_REGION",
)

_CHAT_S3_REQUIRED_SETTINGS = (
    "HOUSTON_CHAT_S3_ENDPOINT_URL",
    "HOUSTON_CHAT_S3_BUCKET",
    "HOUSTON_CHAT_S3_ACCESS_KEY_ID",
    "HOUSTON_CHAT_S3_SECRET_ACCESS_KEY",
    "HOUSTON_CHAT_S3_REGION",
)

_ACTION_PLAN_S3_REQUIRED_SETTINGS = (
    "HOUSTON_ACTION_PLAN_S3_ENDPOINT_URL",
    "HOUSTON_ACTION_PLAN_S3_BUCKET",
    "HOUSTON_ACTION_PLAN_S3_ACCESS_KEY_ID",
    "HOUSTON_ACTION_PLAN_S3_SECRET_ACCESS_KEY",
    "HOUSTON_ACTION_PLAN_S3_REGION",
)


def _private_media_backend() -> str:
    backend = getattr(settings, "HOUSTON_PRIVATE_MEDIA_BACKEND", PRIVATE_MEDIA_BACKEND_FILESYSTEM)
    return (backend or PRIVATE_MEDIA_BACKEND_FILESYSTEM).strip().lower()


@register()
def check_private_media_backend(app_configs, **kwargs):
    if settings.DEBUG:
        return []

    backend = _private_media_backend()
    if backend not in SUPPORTED_PRIVATE_MEDIA_BACKENDS:
        return [
            Error(
                f"HOUSTON_PRIVATE_MEDIA_BACKEND is unsupported: {backend}",
                hint="Set HOUSTON_PRIVATE_MEDIA_BACKEND to 'filesystem' or 's3'.",
                id="uploads.E003",
            )
        ]
    return []


@register()
def check_private_media_root_configured(app_configs, **kwargs):
    if settings.DEBUG:
        return []
    if _private_media_backend() != PRIVATE_MEDIA_BACKEND_FILESYSTEM:
        return []

    media_root = (settings.HOUSTON_PRIVATE_MEDIA_ROOT or "").strip()
    if not media_root:
        return [
            Error(
                "HOUSTON_PRIVATE_MEDIA_ROOT is empty.",
                hint="Set HOUSTON_PRIVATE_MEDIA_ROOT to a writable private storage path.",
                id="uploads.E002",
            )
        ]
    return []


@register()
def check_private_media_root_writable(app_configs, **kwargs):
    if settings.DEBUG:
        return []
    if _private_media_backend() != PRIVATE_MEDIA_BACKEND_FILESYSTEM:
        return []

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


@register()
def check_private_media_s3_configured(app_configs, **kwargs):
    if settings.DEBUG:
        return []
    if _private_media_backend() != PRIVATE_MEDIA_BACKEND_S3:
        return []

    errors = []
    missing = [
        name
        for name in _S3_REQUIRED_SETTINGS
        if not (getattr(settings, name, "") or "").strip()
    ]
    if missing:
        errors.append(
            Error(
                "S3 private media settings are incomplete: " + ", ".join(missing),
                hint=(
                    "Set HOUSTON_S3_ENDPOINT_URL, HOUSTON_S3_BUCKET, "
                    "HOUSTON_S3_ACCESS_KEY_ID, HOUSTON_S3_SECRET_ACCESS_KEY, "
                    "and HOUSTON_S3_REGION. HOUSTON_S3_ADDRESSING_STYLE is optional."
                ),
                id="uploads.E004",
            )
        )
    chat_missing = [
        name
        for name in _CHAT_S3_REQUIRED_SETTINGS
        if not (getattr(settings, name, "") or "").strip()
    ]
    if chat_missing:
        errors.append(
            Error(
                "S3 chat media settings are incomplete: " + ", ".join(chat_missing),
                hint=(
                    "Set HOUSTON_CHAT_S3_ENDPOINT_URL, HOUSTON_CHAT_S3_BUCKET, "
                    "HOUSTON_CHAT_S3_ACCESS_KEY_ID, HOUSTON_CHAT_S3_SECRET_ACCESS_KEY, "
                    "and HOUSTON_CHAT_S3_REGION. HOUSTON_CHAT_S3_ADDRESSING_STYLE is optional."
                ),
                id="uploads.E007",
            )
        )
    action_plan_missing = [
        name
        for name in _ACTION_PLAN_S3_REQUIRED_SETTINGS
        if not (getattr(settings, name, "") or "").strip()
    ]
    if action_plan_missing:
        errors.append(
            Error(
                "S3 action-plan comment media settings are incomplete: "
                + ", ".join(action_plan_missing),
                hint=(
                    "Set HOUSTON_ACTION_PLAN_S3_ENDPOINT_URL, HOUSTON_ACTION_PLAN_S3_BUCKET, "
                    "HOUSTON_ACTION_PLAN_S3_ACCESS_KEY_ID, "
                    "HOUSTON_ACTION_PLAN_S3_SECRET_ACCESS_KEY, "
                    "and HOUSTON_ACTION_PLAN_S3_REGION. "
                    "HOUSTON_ACTION_PLAN_S3_ADDRESSING_STYLE is optional."
                ),
                id="uploads.E008",
            )
        )
    return errors


@register()
def check_observation_media_preview_windows(app_configs, **kwargs):
    cache_max_age = int(
        getattr(settings, "HOUSTON_OBSERVATION_MEDIA_PREVIEW_CACHE_MAX_AGE_SECONDS", 60)
    )
    bucket_seconds = int(
        getattr(settings, "HOUSTON_OBSERVATION_MEDIA_PREVIEW_URL_BUCKET_SECONDS", 60)
    )
    presign_ttl = int(getattr(settings, "HOUSTON_OBSERVATION_MEDIA_S3_PRESIGN_TTL_SECONDS", 120))
    errors = []
    if presign_ttl <= cache_max_age:
        errors.append(
            Error(
                "Observation media presign TTL must exceed Houston preview cache max-age (P > C).",
                hint=(
                    "Set HOUSTON_OBSERVATION_MEDIA_S3_PRESIGN_TTL_SECONDS greater than "
                    "HOUSTON_OBSERVATION_MEDIA_PREVIEW_CACHE_MAX_AGE_SECONDS."
                ),
                id="uploads.E005",
            )
        )
    if bucket_seconds < cache_max_age:
        errors.append(
            Error(
                "Preview URL bucket must be at least Houston cache max-age (W >= C).",
                hint=(
                    "Set HOUSTON_OBSERVATION_MEDIA_PREVIEW_URL_BUCKET_SECONDS "
                    ">= HOUSTON_OBSERVATION_MEDIA_PREVIEW_CACHE_MAX_AGE_SECONDS."
                ),
                id="uploads.E006",
            )
        )
    return errors
