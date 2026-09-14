from __future__ import annotations

import uuid

from django.test import RequestFactory, override_settings
from houston.observations.media_access import build_observation_media_preview_url

_PRODUCTION_PROXY = override_settings(
    DEBUG=False,
    ALLOWED_HOSTS=["app.spore-os.com"],
    SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https"),
)


def _preview_url(**request_meta: str) -> str:
    request = RequestFactory().get("/", **request_meta)
    return build_observation_media_preview_url(
        request=request,
        establishment_id=uuid.uuid4(),
        media_id=uuid.uuid4(),
    )


@_PRODUCTION_PROXY
def test_preview_url_uses_https_when_forwarded_proto_is_https():
    url = _preview_url(
        HTTP_HOST="app.spore-os.com",
        HTTP_X_FORWARDED_PROTO="https",
    )

    assert url.startswith("https://app.spore-os.com/")
    assert "/preview/" in url
    assert "token=" in url


@_PRODUCTION_PROXY
def test_preview_url_stays_http_when_forwarded_proto_is_absent():
    url = _preview_url(HTTP_HOST="app.spore-os.com")

    assert url.startswith("http://app.spore-os.com/")
