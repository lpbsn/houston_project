from __future__ import annotations

from django.conf import settings


def test_database_settings_expose_connection_pooling_options():
    database_settings = settings.DATABASES["default"]

    assert database_settings["CONN_MAX_AGE"] == settings.HOUSTON_DB_CONN_MAX_AGE
    assert database_settings["CONN_HEALTH_CHECKS"] == settings.HOUSTON_DB_CONN_HEALTH_CHECKS
    assert isinstance(settings.HOUSTON_DB_CONN_MAX_AGE, int)
    assert isinstance(settings.HOUSTON_DB_CONN_HEALTH_CHECKS, bool)


def test_auth_session_last_used_update_interval_is_configured():
    assert settings.HOUSTON_AUTH_SESSION_LAST_USED_UPDATE_INTERVAL_SECONDS >= 0
