from django.test import override_settings


def test_home_page_renders(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"Houston" in response.content


def test_health_endpoint_returns_ok(client):
    response = client.get("/api/v1/health/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_client_requirements_defaults_to_no_android_force_update(client):
    response = client.get("/api/v1/client-requirements/")

    assert response.status_code == 200
    assert response.json() == {"android_min_supported_version_code": 0}


@override_settings(HOUSTON_ANDROID_MIN_SUPPORTED_VERSION_CODE=4)
def test_client_requirements_exposes_configured_android_min_version(client):
    response = client.get("/api/v1/client-requirements/")

    assert response.status_code == 200
    assert response.json() == {"android_min_supported_version_code": 4}
