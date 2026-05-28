from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework import authentication, exceptions

from houston.accounts.models import AccessToken, User, UserSession
from houston.accounts.tokens import digest_token


@dataclass(frozen=True)
class AccessTokenAuthContext:
    session: UserSession
    access_token: AccessToken


class BearerAccessTokenAuthentication(authentication.BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        authorization_header = authentication.get_authorization_header(request).decode("utf-8")

        if not authorization_header:
            return None

        keyword, _, token = authorization_header.partition(" ")

        if keyword != self.keyword or not token:
            raise exceptions.AuthenticationFailed("Invalid access token.")

        access_token = (
            AccessToken.objects.select_related("session", "session__user")
            .filter(token_digest=digest_token(token))
            .first()
        )

        if access_token is None:
            raise exceptions.AuthenticationFailed("Invalid access token.")

        now = timezone.now()
        session = access_token.session
        user = session.user

        if access_token.revoked_at is not None or access_token.expires_at <= now:
            raise exceptions.AuthenticationFailed("Invalid access token.")

        if session.revoked_at is not None or session.status != UserSession.Status.ACTIVE:
            raise exceptions.AuthenticationFailed("Invalid access token.")

        if session.absolute_expires_at <= now:
            session.status = UserSession.Status.EXPIRED
            session.revoked_at = session.revoked_at or now
            session.save(update_fields=["status", "revoked_at", "updated_at"])
            raise exceptions.AuthenticationFailed("Invalid access token.")

        if user.status != User.Status.ACTIVE:
            raise exceptions.AuthenticationFailed("Invalid access token.")

        session.last_used_at = now
        session.save(update_fields=["last_used_at", "updated_at"])

        return user, AccessTokenAuthContext(session=session, access_token=access_token)

    def authenticate_header(self, request):
        return self.keyword


class OptionalBearerAccessTokenAuthentication(BearerAccessTokenAuthentication):
    def authenticate(self, request):
        try:
            return super().authenticate(request)
        except exceptions.AuthenticationFailed:
            return None


class BearerAccessTokenAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "houston.accounts.authentication.BearerAccessTokenAuthentication"
    name = "BearerAccessToken"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "opaque",
        }
