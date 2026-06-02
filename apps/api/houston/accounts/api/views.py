from __future__ import annotations

from django.conf import settings
from django.middleware.csrf import CsrfViewMiddleware
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from houston.accounts.api.serializers import (
    ApiErrorResponseSerializer,
    AuthResponseSerializer,
    BootstrapResponseSerializer,
    CsrfResponseSerializer,
    DetailResponseSerializer,
    DirectorInvitationAcceptErrorResponseSerializer,
    DirectorInvitationAcceptRequestSerializer,
    DirectorInvitationAcceptResponseSerializer,
    LoginRequestSerializer,
    RegistrationOwnerValidateRequestSerializer,
    RegistrationRequestSerializer,
    RegistrationResponseSerializer,
    SwitchEstablishmentRequestSerializer,
    ValidationErrorResponseSerializer,
)
from houston.accounts.authentication import (
    BearerAccessTokenAuthentication,
    OptionalBearerAccessTokenAuthentication,
)
from houston.accounts.selectors import build_bootstrap_payload
from houston.accounts.services import (
    AUTHENTICATION_FAILED_DETAIL,
    INVALID_CREDENTIALS_DETAIL,
    INVALID_REGISTRATION_INVITE_CODE_DETAIL,
    REGISTRATION_DUPLICATE_EMAIL_DETAIL,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    InvalidRegistrationInviteCodeError,
    InvalidSelectedEstablishmentError,
    RefreshTokenReuseError,
    RegistrationDuplicateEmailError,
    authenticate_user,
    clear_refresh_cookie,
    create_login_session,
    refresh_session,
    register_onboarding_owner,
    resolve_session_for_logout,
    revoke_session,
    set_refresh_cookie,
    switch_selected_establishment,
    validate_onboarding_owner_registration,
)
from houston.establishments.services import (
    EstablishmentInvitationAlreadyAcceptedError,
    EstablishmentInvitationExpiredError,
    InvalidEstablishmentInvitationError,
    accept_establishment_invitation,
)

_THROTTLED_OPENAPI_RESPONSE = OpenApiResponse(response=ApiErrorResponseSerializer)


class AuthRateLimitedMixin:
    """Applies ScopedRateThrottle when HOUSTON_AUTH_THROTTLE_ENABLED is true."""

    throttle_scope: str

    def get_throttles(self):
        if not settings.HOUSTON_AUTH_THROTTLE_ENABLED:
            return []
        return [ScopedRateThrottle()]


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


class LoginView(AuthRateLimitedMixin, APIView):
    authentication_classes = []
    permission_classes = []
    throttle_scope = settings.AUTH_THROTTLE_SCOPE_LOGIN

    @extend_schema(
        tags=["auth"],
        request=LoginRequestSerializer,
        responses={
            200: AuthResponseSerializer,
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            429: _THROTTLED_OPENAPI_RESPONSE,
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
            return _api_error_response(
                code="not_authenticated",
                detail=INVALID_CREDENTIALS_DETAIL,
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


class RegisterView(AuthRateLimitedMixin, APIView):
    authentication_classes = []
    permission_classes = []
    throttle_scope = settings.AUTH_THROTTLE_SCOPE_REGISTER

    @extend_schema(
        tags=["auth"],
        request=RegistrationRequestSerializer,
        responses={
            201: RegistrationResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            429: _THROTTLED_OPENAPI_RESPONSE,
        },
        description=(
            "Registers a new owner and provisions an organization, draft establishment, "
            "and onboarding session using a valid registration invite code. Requires a "
            "valid Django CSRF cookie and X-CSRFToken header."
        ),
    )
    def post(self, request):
        csrf_failure = _enforce_csrf(request)

        if csrf_failure is not None:
            return csrf_failure

        serializer = RegistrationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            bundle = register_onboarding_owner(
                request=request,
                **serializer.validated_data,
            )
        except InvalidRegistrationInviteCodeError:
            return Response(
                {
                    "detail": INVALID_REGISTRATION_INVITE_CODE_DETAIL,
                    "code": "invalid_invite_code",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except RegistrationDuplicateEmailError:
            return _registration_duplicate_email_response()

        response = Response(bundle.payload, status=status.HTTP_201_CREATED)
        set_refresh_cookie(
            response=response,
            raw_refresh_token=bundle.auth.refresh_token.raw_token,
            expires_at=bundle.auth.refresh_token.record.expires_at,
        )
        return response


class ValidateOwnerRegistrationView(AuthRateLimitedMixin, APIView):
    authentication_classes = []
    permission_classes = []
    throttle_scope = settings.AUTH_THROTTLE_SCOPE_REGISTER_VALIDATE

    @extend_schema(
        tags=["auth"],
        request=RegistrationOwnerValidateRequestSerializer,
        responses={
            204: OpenApiResponse(description="Owner registration fields are valid."),
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            429: _THROTTLED_OPENAPI_RESPONSE,
        },
        description=(
            "Validates owner registration fields without provisioning any records. "
            "Requires a valid Django CSRF cookie and X-CSRFToken header."
        ),
    )
    def post(self, request):
        csrf_failure = _enforce_csrf(request)

        if csrf_failure is not None:
            return csrf_failure

        serializer = RegistrationOwnerValidateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            validate_onboarding_owner_registration(
                invite_code=serializer.validated_data["invite_code"],
                email=serializer.validated_data["email"],
            )
        except InvalidRegistrationInviteCodeError:
            return Response(
                {
                    "detail": INVALID_REGISTRATION_INVITE_CODE_DETAIL,
                    "code": "invalid_invite_code",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except RegistrationDuplicateEmailError:
            return _registration_duplicate_email_response()

        return Response(status=status.HTTP_204_NO_CONTENT)


class DirectorInvitationAcceptView(AuthRateLimitedMixin, APIView):
    authentication_classes = []
    permission_classes = []
    throttle_scope = settings.AUTH_THROTTLE_SCOPE_INVITATION_ACCEPT

    @extend_schema(
        tags=["auth"],
        request=DirectorInvitationAcceptRequestSerializer,
        responses={
            201: DirectorInvitationAcceptResponseSerializer,
            400: OpenApiResponse(response=DirectorInvitationAcceptErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            429: _THROTTLED_OPENAPI_RESPONSE,
        },
        description=(
            "Accepts an establishment invitation, sets the account password, "
            "activates the user and membership, and creates an auth session. Requires "
            "a valid Django CSRF cookie and X-CSRFToken header."
        ),
    )
    def post(self, request, token: str):
        csrf_failure = _enforce_csrf(request)

        if csrf_failure is not None:
            return csrf_failure

        serializer = DirectorInvitationAcceptRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = accept_establishment_invitation(
                request=request,
                raw_token=token,
                password=serializer.validated_data["password"],
            )
        except EstablishmentInvitationExpiredError:
            return Response(
                {
                    "code": "invitation_expired",
                    "detail": "This invitation has expired.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except EstablishmentInvitationAlreadyAcceptedError:
            return Response(
                {
                    "code": "invitation_already_accepted",
                    "detail": "This invitation has already been accepted.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except InvalidEstablishmentInvitationError:
            return Response(
                {
                    "code": "invitation_invalid",
                    "detail": "This invitation is not valid.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        response = Response(result.payload, status=status.HTTP_201_CREATED)
        set_refresh_cookie(
            response=response,
            raw_refresh_token=result.auth.refresh_token.raw_token,
            expires_at=result.auth.refresh_token.record.expires_at,
        )
        return response


class RefreshView(AuthRateLimitedMixin, APIView):
    authentication_classes = []
    permission_classes = []
    throttle_scope = settings.AUTH_THROTTLE_SCOPE_REFRESH

    @extend_schema(
        tags=["auth"],
        request=None,
        responses={
            200: AuthResponseSerializer,
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            429: _THROTTLED_OPENAPI_RESPONSE,
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
            response = _api_error_response(
                code="not_authenticated",
                detail=AUTHENTICATION_FAILED_DETAIL,
                status=status.HTTP_401_UNAUTHORIZED,
            )
            clear_refresh_cookie(response=response)
            return response

        try:
            bundle = refresh_session(raw_refresh_token=raw_refresh_token)
        except (InvalidRefreshTokenError, RefreshTokenReuseError):
            response = _api_error_response(
                code="not_authenticated",
                detail=AUTHENTICATION_FAILED_DETAIL,
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
    authentication_classes = [OptionalBearerAccessTokenAuthentication]
    permission_classes = []

    @extend_schema(
        tags=["auth"],
        auth=[],
        request=None,
        responses={
            204: OpenApiResponse(description="Session revoked and refresh cookie cleared."),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
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
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
        description="Returns the authenticated bootstrap payload for the current bearer token.",
    )
    def get(self, request):
        return Response(build_bootstrap_payload(request.user, session=request.auth.session))


class SwitchEstablishmentView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["auth"],
        request=SwitchEstablishmentRequestSerializer,
        responses={
            200: BootstrapResponseSerializer,
            400: OpenApiResponse(response=ValidationErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
        description=(
            "Selects the active establishment for the current auth session. Requires "
            "a valid bearer access token and stores the selection on the backend "
            "UserSession."
        ),
    )
    def post(self, request):
        serializer = SwitchEstablishmentRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            payload = switch_selected_establishment(
                session=request.auth.session,
                establishment_id=serializer.validated_data["establishment_id"],
            )
        except InvalidSelectedEstablishmentError:
            return Response(
                {"detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(payload)


def _registration_duplicate_email_response() -> Response:
    return Response(
        {
            "detail": REGISTRATION_DUPLICATE_EMAIL_DETAIL,
            "code": "duplicate_email",
        },
        status=status.HTTP_400_BAD_REQUEST,
    )


def _api_error_response(*, code: str, detail: str, status: int) -> Response:
    return Response({"code": code, "detail": detail}, status=status)


def _enforce_csrf(request) -> Response | None:
    csrf_middleware = CsrfViewMiddleware(lambda csrf_request: None)
    failure_response = csrf_middleware.process_view(request._request, None, (), {})

    if failure_response is None:
        return None

    return _api_error_response(
        code="permission_denied",
        detail="CSRF validation failed.",
        status=status.HTTP_403_FORBIDDEN,
    )
