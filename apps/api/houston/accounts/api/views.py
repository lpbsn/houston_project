from __future__ import annotations

from django.conf import settings
from django.middleware.csrf import CsrfViewMiddleware
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from houston.accounts.api.serializers import (
    AuthResponseSerializer,
    BootstrapResponseSerializer,
    CsrfResponseSerializer,
    DetailResponseSerializer,
    LoginRequestSerializer,
)
from houston.accounts.authentication import BearerAccessTokenAuthentication
from houston.accounts.selectors import build_bootstrap_payload
from houston.accounts.services import (
    AUTHENTICATION_FAILED_DETAIL,
    INVALID_CREDENTIALS_DETAIL,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    RefreshTokenReuseError,
    authenticate_user,
    clear_refresh_cookie,
    create_login_session,
    refresh_session,
    resolve_session_for_logout,
    revoke_session,
    set_refresh_cookie,
)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfCookieView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        tags=["auth"],
        responses=CsrfResponseSerializer,
        description="Ensures the Django CSRF cookie exists for subsequent auth mutations.",
    )
    def get(self, request):
        return Response({"detail": "CSRF cookie set."})


class LoginView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        tags=["auth"],
        request=LoginRequestSerializer,
        responses={
            200: AuthResponseSerializer,
            401: OpenApiResponse(response=DetailResponseSerializer),
            403: OpenApiResponse(response=DetailResponseSerializer),
        },
        description=(
            "Logs in with an email or username identifier. Requires a valid Django CSRF "
            "cookie and X-CSRFToken header."
        ),
    )
    def post(self, request):
        csrf_failure = _enforce_csrf(request)

        if csrf_failure is not None:
            return csrf_failure

        serializer = LoginRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = authenticate_user(
                request=request,
                identifier=serializer.validated_data["identifier"],
                password=serializer.validated_data["password"],
            )
        except InvalidCredentialsError:
            return Response(
                {"detail": INVALID_CREDENTIALS_DETAIL},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        bundle = create_login_session(request=request, user=user)
        response = Response(bundle.payload)
        set_refresh_cookie(
            response=response,
            raw_refresh_token=bundle.refresh_token.raw_token,
            expires_at=bundle.refresh_token.record.expires_at,
        )
        return response


class RefreshView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        tags=["auth"],
        request=None,
        responses={
            200: AuthResponseSerializer,
            401: OpenApiResponse(response=DetailResponseSerializer),
            403: OpenApiResponse(response=DetailResponseSerializer),
        },
        description=(
            "Rotates the HttpOnly refresh token cookie and issues a new opaque access token. "
            "Requires a valid CSRF cookie and X-CSRFToken header. The refresh token is read "
            "from the houston_refresh_token HttpOnly cookie."
        ),
    )
    def post(self, request):
        csrf_failure = _enforce_csrf(request)

        if csrf_failure is not None:
            return csrf_failure

        raw_refresh_token = request.COOKIES.get(settings.HOUSTON_AUTH_REFRESH_COOKIE_NAME)

        if not raw_refresh_token:
            response = Response(
                {"detail": AUTHENTICATION_FAILED_DETAIL},
                status=status.HTTP_401_UNAUTHORIZED,
            )
            clear_refresh_cookie(response=response)
            return response

        try:
            bundle = refresh_session(raw_refresh_token=raw_refresh_token)
        except (InvalidRefreshTokenError, RefreshTokenReuseError):
            response = Response(
                {"detail": AUTHENTICATION_FAILED_DETAIL},
                status=status.HTTP_401_UNAUTHORIZED,
            )
            clear_refresh_cookie(response=response)
            return response

        response = Response(bundle.payload)
        set_refresh_cookie(
            response=response,
            raw_refresh_token=bundle.refresh_token.raw_token,
            expires_at=bundle.refresh_token.record.expires_at,
        )
        return response


class LogoutView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = []

    @extend_schema(
        tags=["auth"],
        request=None,
        responses={
            204: OpenApiResponse(description="Session revoked and refresh cookie cleared."),
            403: OpenApiResponse(response=DetailResponseSerializer),
        },
        description=(
            "Revokes the current session, preferring the bearer access token when available "
            "and otherwise falling back to the refresh token cookie. Requires CSRF and clears "
            "the houston_refresh_token HttpOnly cookie."
        ),
    )
    def post(self, request):
        csrf_failure = _enforce_csrf(request)

        if csrf_failure is not None:
            return csrf_failure

        raw_refresh_token = request.COOKIES.get(settings.HOUSTON_AUTH_REFRESH_COOKIE_NAME)
        auth_session = None if request.auth is None else request.auth.session
        session = resolve_session_for_logout(
            auth_session=auth_session,
            raw_refresh_token=raw_refresh_token,
        )

        if session is not None:
            revoke_session(session=session)

        response = Response(status=status.HTTP_204_NO_CONTENT)
        clear_refresh_cookie(response=response)
        return response


class BootstrapView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["auth"],
        responses={
            200: BootstrapResponseSerializer,
            401: OpenApiResponse(response=DetailResponseSerializer),
        },
        description="Returns the authenticated bootstrap payload for the current bearer token.",
    )
    def get(self, request):
        return Response(build_bootstrap_payload(request.user))


def _enforce_csrf(request) -> Response | None:
    csrf_middleware = CsrfViewMiddleware(lambda csrf_request: None)
    failure_response = csrf_middleware.process_view(request._request, None, (), {})

    if failure_response is None:
        return None

    return Response(
        {"detail": "CSRF validation failed."},
        status=status.HTTP_403_FORBIDDEN,
    )
