from __future__ import annotations

import secrets

from django.conf import settings
from django.utils.crypto import salted_hmac


def generate_raw_token() -> str:
    return secrets.token_urlsafe(settings.HOUSTON_AUTH_TOKEN_BYTES)


def digest_token(raw_token: str) -> str:
    return salted_hmac(
        settings.HOUSTON_AUTH_TOKEN_SALT,
        raw_token,
        secret=settings.HOUSTON_AUTH_TOKEN_PEPPER,
        algorithm="sha256",
    ).hexdigest()
