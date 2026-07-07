from __future__ import annotations

import importlib

import pytest
from django.core.management import call_command
from django.core.management.base import SystemCheckError
from django.test import override_settings

VALID_PRODUCTION_OVERRIDES = {
    "DEBUG": False,
    "SECRET_KEY": "production-secret-key-value-with-sufficient-length-and-entropy",
    "ALLOWED_HOSTS": ["example.railway.app"],
    "CSRF_TRUSTED_ORIGINS": ["https://example.railway.app"],
    "_HOUSTON_AUTH_TOKEN_PEPPER_ENV": "production-pepper-value-distinct-from-secret",
    "HOUSTON_AUTH_TOKEN_PEPPER": "production-pepper-value-distinct-from-secret",
    "HOUSTON_AUTH_TOKEN_SALT": "production-auth-token-salt",
    "HOUSTON_CHAT_WS_TICKET_SALT": "production-chat-ws-salt",
    "HOUSTON_REALTIME_WS_TICKET_SALT": "production-realtime-ws-salt",
    "OPENAI_API_KEY": "sk-production-test",
    "HOUSTON_AI_OBSERVATION_PROVIDER": "openai",
    "HOUSTON_AI_TRANSCRIPTION_PROVIDER": "openai",
    "HOUSTON_ENABLE_API_DOCS": False,
    "HOUSTON_ALLOW_INSECURE_LOCAL_CSRF_ORIGINS": False,
    "HOUSTON_ALLOW_LOCAL_ALLOWED_HOSTS": False,
    "HOUSTON_PRIVATE_MEDIA_ROOT": "/tmp/houston-private-media-test",
    "CSRF_COOKIE_SECURE": True,
    "SESSION_COOKIE_SECURE": True,
    "SECURE_SSL_REDIRECT": False,
}


@pytest.fixture
def valid_production_overrides():
    return dict(VALID_PRODUCTION_OVERRIDES)


def test_production_deploy_check_passes_with_valid_configuration(valid_production_overrides):
    with override_settings(**valid_production_overrides):
        call_command("check", deploy=True)


def test_production_deploy_check_rejects_local_secret_placeholder(valid_production_overrides):
    valid_production_overrides["SECRET_KEY"] = "replace-me-for-local-dev"
    with override_settings(**valid_production_overrides), pytest.raises(SystemCheckError):
        call_command("check", deploy=True)


def test_production_deploy_check_rejects_empty_csrf_origins(valid_production_overrides):
    valid_production_overrides["CSRF_TRUSTED_ORIGINS"] = []
    with override_settings(**valid_production_overrides), pytest.raises(SystemCheckError):
        call_command("check", deploy=True)


def test_production_deploy_check_rejects_public_http_csrf_origin(valid_production_overrides):
    valid_production_overrides["CSRF_TRUSTED_ORIGINS"] = ["http://evil.example.com"]
    with override_settings(**valid_production_overrides), pytest.raises(SystemCheckError):
        call_command("check", deploy=True)


def test_production_deploy_check_rejects_local_http_csrf_without_exception(
    valid_production_overrides,
):
    valid_production_overrides["CSRF_TRUSTED_ORIGINS"] = ["http://localhost:8080"]
    valid_production_overrides["HOUSTON_ALLOW_INSECURE_LOCAL_CSRF_ORIGINS"] = False
    with override_settings(**valid_production_overrides), pytest.raises(SystemCheckError):
        call_command("check", deploy=True)


def test_production_deploy_check_allows_local_http_csrf_with_exception(valid_production_overrides):
    valid_production_overrides["ALLOWED_HOSTS"] = ["localhost", "127.0.0.1", "api", "gateway"]
    valid_production_overrides["CSRF_TRUSTED_ORIGINS"] = ["http://localhost:8080"]
    valid_production_overrides["HOUSTON_ALLOW_INSECURE_LOCAL_CSRF_ORIGINS"] = True
    valid_production_overrides["HOUSTON_ALLOW_LOCAL_ALLOWED_HOSTS"] = True
    with override_settings(**valid_production_overrides):
        call_command("check", deploy=True)


def test_production_deploy_check_rejects_missing_explicit_pepper(valid_production_overrides):
    valid_production_overrides["_HOUSTON_AUTH_TOKEN_PEPPER_ENV"] = ""
    valid_production_overrides["HOUSTON_AUTH_TOKEN_PEPPER"] = (
        "production-pepper-value-distinct-from-secret"
    )
    with override_settings(**valid_production_overrides), pytest.raises(SystemCheckError):
        call_command("check", deploy=True)


def test_production_deploy_check_rejects_pepper_equal_to_secret(valid_production_overrides):
    valid_production_overrides["SECRET_KEY"] = "shared-secret-value"
    valid_production_overrides["_HOUSTON_AUTH_TOKEN_PEPPER_ENV"] = "shared-secret-value"
    valid_production_overrides["HOUSTON_AUTH_TOKEN_PEPPER"] = "shared-secret-value"
    with override_settings(**valid_production_overrides), pytest.raises(SystemCheckError):
        call_command("check", deploy=True)


def test_production_deploy_check_rejects_default_auth_salts(valid_production_overrides):
    valid_production_overrides["HOUSTON_AUTH_TOKEN_SALT"] = "houston.auth.token"
    with override_settings(**valid_production_overrides), pytest.raises(SystemCheckError):
        call_command("check", deploy=True)


def test_production_deploy_check_rejects_openai_without_api_key(valid_production_overrides):
    valid_production_overrides["OPENAI_API_KEY"] = ""
    with override_settings(**valid_production_overrides), pytest.raises(SystemCheckError):
        call_command("check", deploy=True)


def test_production_deploy_check_allows_local_allowed_hosts_with_exception(
    valid_production_overrides,
):
    valid_production_overrides["ALLOWED_HOSTS"] = ["localhost", "127.0.0.1", "api", "gateway"]
    valid_production_overrides["HOUSTON_ALLOW_LOCAL_ALLOWED_HOSTS"] = True
    valid_production_overrides["CSRF_TRUSTED_ORIGINS"] = ["http://localhost:8080"]
    valid_production_overrides["HOUSTON_ALLOW_INSECURE_LOCAL_CSRF_ORIGINS"] = True
    with override_settings(**valid_production_overrides):
        call_command("check", deploy=True)


def test_debug_mode_skips_production_security_checks():
    with override_settings(
        DEBUG=True,
        SECRET_KEY="replace-me-for-local-dev",
        CSRF_TRUSTED_ORIGINS=[],
        _HOUSTON_AUTH_TOKEN_PEPPER_ENV="",
        HOUSTON_AUTH_TOKEN_PEPPER="replace-me-for-local-dev",
        HOUSTON_AUTH_TOKEN_SALT="houston.auth.token",
        OPENAI_API_KEY="",
    ):
        call_command("check", deploy=True)


def _collect_route_patterns(urlpatterns, prefix: str = "") -> list[str]:
    routes: list[str] = []
    for pattern in urlpatterns:
        route = prefix + str(getattr(pattern, "pattern", pattern))
        if hasattr(pattern, "url_patterns"):
            routes.extend(_collect_route_patterns(pattern.url_patterns, route))
        else:
            routes.append(route)
    return routes


def test_api_docs_routes_disabled_by_default_in_production(valid_production_overrides):
    from config import urls as urls_module

    valid_production_overrides["HOUSTON_ENABLE_API_DOCS"] = False
    with override_settings(**valid_production_overrides, ROOT_URLCONF="config.urls"):
        importlib.reload(urls_module)
        routes = _collect_route_patterns(urls_module.urlpatterns)
        assert not any("api/docs" in route for route in routes)
        assert not any("api/schema" in route for route in routes)
    importlib.reload(urls_module)
