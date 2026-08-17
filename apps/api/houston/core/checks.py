from __future__ import annotations

from urllib.parse import urlparse

from django.conf import settings
from django.core.checks import Error, register

_FORBIDDEN_SECRET_KEYS = frozenset(
    {
        "",
        "replace-me-for-local-dev",
        "replace-me-for-local-prod-test",
    }
)
_DEFAULT_AUTH_TOKEN_SALT = "houston.auth.token"
_DEFAULT_CHAT_WS_TICKET_SALT = "houston.chat.ws_ticket"
_DEFAULT_REALTIME_WS_TICKET_SALT = "houston.realtime.ws_ticket"
_LOCAL_ALLOWED_HOSTS = frozenset({"localhost", "127.0.0.1", "api", "gateway", "10.0.2.2"})
_LOCAL_CSRF_HOSTNAMES = frozenset({"localhost", "127.0.0.1"})


def _production_gate_active() -> bool:
    return not settings.DEBUG


def _error(message: str, *, hint: str, check_id: str) -> Error:
    return Error(message, hint=hint, id=check_id)


@register()
def check_production_secret_key(app_configs, **kwargs):
    if not _production_gate_active():
        return []

    secret_key = (settings.SECRET_KEY or "").strip()
    if secret_key in _FORBIDDEN_SECRET_KEYS:
        return [
            _error(
                "DJANGO_SECRET_KEY is missing or uses a local development placeholder.",
                hint=(
                    "Set DJANGO_SECRET_KEY to a long random value before running with "
                    "DJANGO_DEBUG=0. Generate one with: openssl rand -hex 32"
                ),
                check_id="core.E001",
            )
        ]
    return []


@register()
def check_production_allowed_hosts(app_configs, **kwargs):
    if not _production_gate_active():
        return []

    hosts = [host.strip().lower() for host in settings.ALLOWED_HOSTS if host.strip()]
    if not hosts:
        return [
            _error(
                "DJANGO_ALLOWED_HOSTS is empty.",
                hint="Set DJANGO_ALLOWED_HOSTS to the public Railway domain(s).",
                check_id="core.E002",
            )
        ]

    if set(hosts).issubset(_LOCAL_ALLOWED_HOSTS) and not settings.HOUSTON_ALLOW_LOCAL_ALLOWED_HOSTS:
        return [
            _error(
                "DJANGO_ALLOWED_HOSTS is local-only, which is not allowed for production.",
                hint=(
                    "Set DJANGO_ALLOWED_HOSTS to the public Railway domain. "
                    "For local prod-test only, set HOUSTON_ALLOW_LOCAL_ALLOWED_HOSTS=1."
                ),
                check_id="core.E003",
            )
        ]
    return []


@register()
def check_production_csrf_origins(app_configs, **kwargs):
    if not _production_gate_active():
        return []

    origins = [origin.strip() for origin in settings.HOUSTON_CLIENT_ORIGINS if origin.strip()]
    if not origins:
        return [
            _error(
                "HOUSTON_CLIENT_ORIGINS is empty.",
                hint=(
                    "Set HOUSTON_CLIENT_ORIGINS to the public HTTPS origin(s), "
                    "for example https://<railway-domain>."
                ),
                check_id="core.E004",
            )
        ]

    errors: list[Error] = []
    for origin in origins:
        parsed = urlparse(origin)
        if not parsed.scheme or not parsed.netloc:
            errors.append(
                _error(
                    f"HOUSTON_CLIENT_ORIGINS contains an invalid origin: {origin!r}.",
                    hint="Use full origins such as https://example.railway.app.",
                    check_id="core.E005",
                )
            )
            continue

        hostname = (parsed.hostname or "").lower()
        if origin in settings.HOUSTON_NATIVE_WEBVIEW_ORIGINS:
            continue
        if parsed.scheme == "https":
            continue

        if parsed.scheme == "http" and hostname in _LOCAL_CSRF_HOSTNAMES:
            if settings.HOUSTON_ALLOW_INSECURE_LOCAL_CSRF_ORIGINS:
                continue
            errors.append(
                _error(
                    f"HOUSTON_CLIENT_ORIGINS uses HTTP for local origin {origin!r}.",
                    hint=(
                        "Use HTTPS in production. For local prod-test only, set "
                        "HOUSTON_ALLOW_INSECURE_LOCAL_CSRF_ORIGINS=1."
                    ),
                    check_id="core.E006",
                )
            )
            continue

        errors.append(
            _error(
                f"HOUSTON_CLIENT_ORIGINS must use HTTPS in production: {origin!r}.",
                hint=(
                    "Public HTTP origins are forbidden. Use https://<railway-domain> "
                    "or a documented local exception for localhost only."
                ),
                check_id="core.E007",
            )
        )
    return errors


@register()
def check_production_auth_secrets(app_configs, **kwargs):
    if not _production_gate_active():
        return []

    errors: list[Error] = []
    pepper_env = (getattr(settings, "_HOUSTON_AUTH_TOKEN_PEPPER_ENV", None) or "").strip()
    secret_key = (settings.SECRET_KEY or "").strip()
    pepper_value = (settings.HOUSTON_AUTH_TOKEN_PEPPER or "").strip()

    if not pepper_env:
        errors.append(
            _error(
                "HOUSTON_AUTH_TOKEN_PEPPER is not set explicitly.",
                hint=(
                    "Set HOUSTON_AUTH_TOKEN_PEPPER to a dedicated random value distinct "
                    "from DJANGO_SECRET_KEY."
                ),
                check_id="core.E008",
            )
        )
    elif pepper_value in _FORBIDDEN_SECRET_KEYS or pepper_value == secret_key:
        errors.append(
            _error(
                (
                    "HOUSTON_AUTH_TOKEN_PEPPER is missing, uses a placeholder, "
                    "or equals DJANGO_SECRET_KEY."
                ),
                hint=(
                    "Generate a dedicated pepper with openssl rand -hex 32 and set "
                    "HOUSTON_AUTH_TOKEN_PEPPER independently from DJANGO_SECRET_KEY."
                ),
                check_id="core.E009",
            )
        )

    salt_checks = (
        (
            "HOUSTON_AUTH_TOKEN_SALT",
            settings.HOUSTON_AUTH_TOKEN_SALT,
            _DEFAULT_AUTH_TOKEN_SALT,
            "core.E010",
        ),
        (
            "HOUSTON_CHAT_WS_TICKET_SALT",
            settings.HOUSTON_CHAT_WS_TICKET_SALT,
            _DEFAULT_CHAT_WS_TICKET_SALT,
            "core.E011",
        ),
        (
            "HOUSTON_REALTIME_WS_TICKET_SALT",
            settings.HOUSTON_REALTIME_WS_TICKET_SALT,
            _DEFAULT_REALTIME_WS_TICKET_SALT,
            "core.E012",
        ),
    )
    for env_name, value, default_value, check_id in salt_checks:
        normalized = (value or "").strip()
        if not normalized or normalized == default_value:
            errors.append(
                _error(
                    f"{env_name} is missing or uses the development default.",
                    hint=f"Set {env_name} to a dedicated random value before production.",
                    check_id=check_id,
                )
            )
    return errors


@register()
def check_production_openai_configuration(app_configs, **kwargs):
    if not _production_gate_active():
        return []

    openai_api_key = (settings.OPENAI_API_KEY or "").strip()
    providers = (
        settings.HOUSTON_AI_OBSERVATION_PROVIDER,
        settings.HOUSTON_AI_TRANSCRIPTION_PROVIDER,
        settings.HOUSTON_AI_ANALYTICS_PATTERN_PROVIDER,
    )
    if any(provider.strip().lower() == "openai" for provider in providers) and not openai_api_key:
        return [
            _error(
                "OPENAI_API_KEY is required when an OpenAI provider is active.",
                hint=(
                    "Set OPENAI_API_KEY on api-web and celery-worker, or switch providers "
                    "away from openai for non-production environments only."
                ),
                check_id="core.E013",
            )
        ]
    return []
