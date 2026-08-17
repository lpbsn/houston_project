from __future__ import annotations

import importlib

import pytest
from django.core.management import call_command
from django.core.management.base import SystemCheckError
from django.test import override_settings
from rest_framework.test import APIClient

from config.settings import HOUSTON_NATIVE_WEBVIEW_ORIGINS, csrf_trusted_origins_from_client_origins

VALID_PRODUCTION_OVERRIDES = {
    "DEBUG": False,
    "SECRET_KEY": "production-secret-key-value-with-sufficient-length-and-entropy",
    "ALLOWED_HOSTS": ["example.railway.app"],
    "HOUSTON_CLIENT_ORIGINS": ["https://example.railway.app"],
    "CSRF_TRUSTED_ORIGINS": ["https://example.railway.app"],
    "CORS_ALLOWED_ORIGINS": ["https://example.railway.app"],
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


def test_production_deploy_check_rejects_empty_client_origins(valid_production_overrides):
    valid_production_overrides["HOUSTON_CLIENT_ORIGINS"] = []
    valid_production_overrides["CSRF_TRUSTED_ORIGINS"] = []
    valid_production_overrides["CORS_ALLOWED_ORIGINS"] = []
    with override_settings(**valid_production_overrides), pytest.raises(SystemCheckError):
        call_command("check", deploy=True)


def test_production_deploy_check_rejects_public_http_client_origin(valid_production_overrides):
    valid_production_overrides["HOUSTON_CLIENT_ORIGINS"] = ["http://evil.example.com"]
    valid_production_overrides["CSRF_TRUSTED_ORIGINS"] = ["http://evil.example.com"]
    valid_production_overrides["CORS_ALLOWED_ORIGINS"] = ["http://evil.example.com"]
    with override_settings(**valid_production_overrides), pytest.raises(SystemCheckError):
        call_command("check", deploy=True)


def test_production_deploy_check_rejects_local_http_csrf_without_exception(
    valid_production_overrides,
):
    valid_production_overrides["HOUSTON_CLIENT_ORIGINS"] = ["http://localhost:8080"]
    valid_production_overrides["CSRF_TRUSTED_ORIGINS"] = ["http://localhost:8080"]
    valid_production_overrides["CORS_ALLOWED_ORIGINS"] = ["http://localhost:8080"]
    valid_production_overrides["HOUSTON_ALLOW_INSECURE_LOCAL_CSRF_ORIGINS"] = False
    with override_settings(**valid_production_overrides), pytest.raises(SystemCheckError):
        call_command("check", deploy=True)


def test_production_deploy_check_allows_local_http_csrf_with_exception(valid_production_overrides):
    valid_production_overrides["ALLOWED_HOSTS"] = [
        "localhost",
        "127.0.0.1",
        "api",
        "gateway",
        "10.0.2.2",
    ]
    valid_production_overrides["HOUSTON_CLIENT_ORIGINS"] = ["http://localhost:8080"]
    valid_production_overrides["CSRF_TRUSTED_ORIGINS"] = ["http://localhost:8080"]
    valid_production_overrides["CORS_ALLOWED_ORIGINS"] = ["http://localhost:8080"]
    valid_production_overrides["HOUSTON_ALLOW_INSECURE_LOCAL_CSRF_ORIGINS"] = True
    valid_production_overrides["HOUSTON_ALLOW_LOCAL_ALLOWED_HOSTS"] = True
    with override_settings(**valid_production_overrides):
        call_command("check", deploy=True)


def test_csrf_trusted_origins_exclude_native_webview_origins():
    derived = csrf_trusted_origins_from_client_origins(
        [
            "https://example.railway.app",
            "http://localhost:5173",
            *sorted(HOUSTON_NATIVE_WEBVIEW_ORIGINS),
        ]
    )

    assert derived == ["https://example.railway.app", "http://localhost:5173"]
    assert HOUSTON_NATIVE_WEBVIEW_ORIGINS.isdisjoint(derived)


def test_production_deploy_check_allows_native_webview_origins(valid_production_overrides):
    native_origins = sorted(HOUSTON_NATIVE_WEBVIEW_ORIGINS)
    valid_production_overrides["HOUSTON_CLIENT_ORIGINS"] = [
        "https://example.railway.app",
        *native_origins,
    ]
    valid_production_overrides["CSRF_TRUSTED_ORIGINS"] = ["https://example.railway.app"]
    valid_production_overrides["CORS_ALLOWED_ORIGINS"] = [
        "https://example.railway.app",
        *native_origins,
    ]
    with override_settings(**valid_production_overrides):
        call_command("check", deploy=True)


def test_production_deploy_check_rejects_unknown_native_scheme(valid_production_overrides):
    valid_production_overrides["HOUSTON_CLIENT_ORIGINS"] = ["capacitor://evil.example"]
    valid_production_overrides["CSRF_TRUSTED_ORIGINS"] = []
    valid_production_overrides["CORS_ALLOWED_ORIGINS"] = ["capacitor://evil.example"]
    with override_settings(**valid_production_overrides), pytest.raises(SystemCheckError):
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


def test_production_deploy_check_rejects_android_emulator_host_without_exception(
    valid_production_overrides,
):
    valid_production_overrides["ALLOWED_HOSTS"] = ["10.0.2.2"]
    valid_production_overrides["HOUSTON_ALLOW_LOCAL_ALLOWED_HOSTS"] = False
    with override_settings(**valid_production_overrides), pytest.raises(SystemCheckError):
        call_command("check", deploy=True)


@pytest.mark.django_db
def test_allowed_hosts_accepts_android_emulator_loopback(settings):
    settings.ALLOWED_HOSTS = ["10.0.2.2"]
    response = APIClient().get("/api/v1/auth/csrf/", HTTP_HOST="10.0.2.2:8000")

    assert response.status_code == 200


def test_production_deploy_check_allows_local_allowed_hosts_with_exception(
    valid_production_overrides,
):
    valid_production_overrides["ALLOWED_HOSTS"] = [
        "localhost",
        "127.0.0.1",
        "api",
        "gateway",
        "10.0.2.2",
    ]
    valid_production_overrides["HOUSTON_ALLOW_LOCAL_ALLOWED_HOSTS"] = True
    valid_production_overrides["HOUSTON_CLIENT_ORIGINS"] = ["http://localhost:8080"]
    valid_production_overrides["CSRF_TRUSTED_ORIGINS"] = ["http://localhost:8080"]
    valid_production_overrides["CORS_ALLOWED_ORIGINS"] = ["http://localhost:8080"]
    valid_production_overrides["HOUSTON_ALLOW_INSECURE_LOCAL_CSRF_ORIGINS"] = True
    with override_settings(**valid_production_overrides):
        call_command("check", deploy=True)


def test_debug_mode_skips_production_security_checks():
    with override_settings(
        DEBUG=True,
        SECRET_KEY="replace-me-for-local-dev",
        HOUSTON_CLIENT_ORIGINS=[],
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
