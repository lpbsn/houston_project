from __future__ import annotations

from django.conf import settings
from django.middleware.csrf import CsrfViewMiddleware, get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from houston.accounts.api.serializers import (
    REFRESH_TOKEN_TRANSPORT_BODY,
    REFRESH_TOKEN_TRANSPORT_COOKIE,
    ApiErrorResponseSerializer,
    AuthResponseSerializer,
    BootstrapResponseSerializer,
    CsrfResponseSerializer,
    DetailResponseSerializer,
    DirectorInvitationAcceptErrorResponseSerializer,
    DirectorInvitationAcceptRequestSerializer,
    DirectorInvitationAcceptResponseSerializer,
    LoginRequestSerializer,
    LogoutRequestSerializer,
    RefreshRequestSerializer,
    RegistrationOwnerValidateRequestSerializer,
    RegistrationRequestSerializer,
    RegistrationResponseSerializer,
    SwitchEstablishmentRequestSerializer,
    UserProfileUpdateRequestSerializer,
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
    ProfileDuplicateEmailError,
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
    update_user_profile,
    validate_onboarding_owner_registration,
)
from houston.establishments.services import (
    EstablishmentInvitationAlreadyAcceptedError,
    EstablishmentInvitationExpiredError,
    InvalidEstablishmentInvitationError,
    OrganizationalOwnerInvariantConflictError,
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
        description=(
            "Ensures the Django CSRF cookie exists and returns csrf_token for "
            "subsequent auth mutations."
        ),
    )
    def get(self, request):
        return Response(
            {
                "detail": "CSRF cookie set.",
                "csrf_token": get_token(request),
            }
        )


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
            "Logs in with an email or username identifier. Cookie transport requires "
            "Django CSRF and returns the refresh token only as an HttpOnly cookie. Body "
            "transport omits cookies and returns the refresh token in JSON."
        ),
    )
    def post(self, request):
        serializer = LoginRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        transport = serializer.validated_data["refresh_token_transport"]

        csrf_failure = _enforce_csrf_for_transport(request, transport=transport)
        if csrf_failure is not None:
            return csrf_failure

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
        return _build_auth_response(
            payload=bundle.payload,
            raw_refresh_token=bundle.refresh_token.raw_token,
            refresh_expires_at=bundle.refresh_token.record.expires_at,
            transport=transport,
        )


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
            "and onboarding session using a valid registration invite code. Cookie "
            "transport requires Django CSRF; body transport does not use cookies."
        ),
    )
    def post(self, request):
        serializer = RegistrationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        transport = serializer.validated_data.pop("refresh_token_transport")

        csrf_failure = _enforce_csrf_for_transport(request, transport=transport)
        if csrf_failure is not None:
            return csrf_failure

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

        return _build_auth_response(
            payload=bundle.payload,
            raw_refresh_token=bundle.auth.refresh_token.raw_token,
            refresh_expires_at=bundle.auth.refresh_token.record.expires_at,
            transport=transport,
            response_status=status.HTTP_201_CREATED,
        )


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
            "Validates owner registration fields without provisioning any records."
        ),
    )
    def post(self, request):
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
            409: OpenApiResponse(response=DirectorInvitationAcceptErrorResponseSerializer),
            429: _THROTTLED_OPENAPI_RESPONSE,
        },
        description=(
            "Accepts an establishment invitation, sets the account password, "
            "activates the user and membership, and creates an auth session. "
            "Owner invitations activate all compatible owner/invited memberships in the "
            "same organization. Cookie transport requires Django CSRF; body transport "
            "does not use cookies."
        ),
    )
    def post(self, request, token: str):
        serializer = DirectorInvitationAcceptRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        transport = serializer.validated_data.pop("refresh_token_transport")

        csrf_failure = _enforce_csrf_for_transport(request, transport=transport)
        if csrf_failure is not None:
            return csrf_failure

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
        except OrganizationalOwnerInvariantConflictError as exc:
            return Response(
                {
                    "code": "organizational_owner_invariant_conflict",
                    "detail": str(exc),
                },
                status=status.HTTP_409_CONFLICT,
            )

        return _build_auth_response(
            payload=result.payload,
            raw_refresh_token=result.auth.refresh_token.raw_token,
            refresh_expires_at=result.auth.refresh_token.record.expires_at,
            transport=transport,
            response_status=status.HTTP_201_CREATED,
        )


class RefreshView(AuthRateLimitedMixin, APIView):
    authentication_classes = []
    permission_classes = []
    throttle_scope = settings.AUTH_THROTTLE_SCOPE_REFRESH

    @extend_schema(
        tags=["auth"],
        request=RefreshRequestSerializer,
        responses={
            200: AuthResponseSerializer,
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            429: _THROTTLED_OPENAPI_RESPONSE,
        },
        description=(
            "Rotates a refresh token and issues a new opaque access token. Cookie transport "
            "reads and rotates the HttpOnly cookie and requires CSRF. Body transport reads "
            "the explicit request field, returns the rotated token in JSON, and never "
            "consults or modifies cookies."
        ),
    )
    def post(self, request):
        serializer = RefreshRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        transport = serializer.validated_data["refresh_token_transport"]

        csrf_failure = _enforce_csrf_for_transport(request, transport=transport)
        if csrf_failure is not None:
            return csrf_failure

        if transport == REFRESH_TOKEN_TRANSPORT_COOKIE:
            raw_refresh_token = request.COOKIES.get(settings.HOUSTON_AUTH_REFRESH_COOKIE_NAME)
        else:
            raw_refresh_token = serializer.validated_data["refresh_token"]

        if not raw_refresh_token:
            return _auth_failure_response(
                code="not_authenticated",
                detail=AUTHENTICATION_FAILED_DETAIL,
                status=status.HTTP_401_UNAUTHORIZED,
                transport=transport,
            )

        try:
            bundle = refresh_session(raw_refresh_token=raw_refresh_token)
        except (InvalidRefreshTokenError, RefreshTokenReuseError):
            return _auth_failure_response(
                code="not_authenticated",
                detail=AUTHENTICATION_FAILED_DETAIL,
                status=status.HTTP_401_UNAUTHORIZED,
                transport=transport,
            )

        return _build_auth_response(
            payload=bundle.payload,
            raw_refresh_token=bundle.refresh_token.raw_token,
            refresh_expires_at=bundle.refresh_token.record.expires_at,
            transport=transport,
        )


class LogoutView(APIView):
    authentication_classes = [OptionalBearerAccessTokenAuthentication]
    permission_classes = []

    @extend_schema(
        tags=["auth"],
        auth=[],
        request=LogoutRequestSerializer,
        responses={
            204: OpenApiResponse(
                description="Session revoked; cookie cleared only for cookie transport."
            ),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
        description=(
            "Revokes the current session, preferring a valid bearer access token. Cookie "
            "transport requires CSRF and may fall back to and clear its refresh cookie. Body "
            "transport may fall back to its explicit refresh token and never consults or "
            "modifies cookies."
        ),
    )
    def post(self, request):
        serializer = LogoutRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        transport = serializer.validated_data["refresh_token_transport"]

        csrf_failure = _enforce_csrf_for_transport(request, transport=transport)
        if csrf_failure is not None:
            return csrf_failure

        if transport == REFRESH_TOKEN_TRANSPORT_COOKIE:
            raw_refresh_token = request.COOKIES.get(settings.HOUSTON_AUTH_REFRESH_COOKIE_NAME)
        else:
            raw_refresh_token = serializer.validated_data.get("refresh_token")
        auth_session = None if request.auth is None else request.auth.session
        session = resolve_session_for_logout(
            auth_session=auth_session,
            raw_refresh_token=raw_refresh_token,
        )

        if session is not None:
            revoke_session(session=session)

        response = Response(status=status.HTTP_204_NO_CONTENT)
        if transport == REFRESH_TOKEN_TRANSPORT_COOKIE:
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


class UserProfileView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["auth"],
        request=UserProfileUpdateRequestSerializer,
        responses={
            200: BootstrapResponseSerializer,
            400: OpenApiResponse(response=ValidationErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            409: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
        description="Updates the authenticated user's personal profile fields.",
    )
    def patch(self, request):
        serializer = UserProfileUpdateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated = serializer.validated_data
        try:
            update_user_profile(
                user=request.user,
                first_name=validated.get("first_name"),
                last_name=validated.get("last_name"),
                email=validated.get("email"),
            )
        except ProfileDuplicateEmailError:
            return Response(
                {
                    "code": "profile_duplicate_email",
                    "detail": "An account with this email already exists.",
                },
                status=status.HTTP_409_CONFLICT,
            )

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


def _build_auth_response(
    *,
    payload: dict,
    raw_refresh_token: str,
    refresh_expires_at,
    transport: str,
    response_status: int = status.HTTP_200_OK,
) -> Response:
    response_payload = payload.copy()
    if transport == REFRESH_TOKEN_TRANSPORT_BODY:
        response_payload["refresh_token"] = raw_refresh_token
        response_payload["refresh_token_expires_at"] = refresh_expires_at

    response = Response(response_payload, status=response_status)
    if transport == REFRESH_TOKEN_TRANSPORT_COOKIE:
        set_refresh_cookie(
            response=response,
            raw_refresh_token=raw_refresh_token,
            expires_at=refresh_expires_at,
        )
    return response


def _auth_failure_response(*, code: str, detail: str, status: int, transport: str) -> Response:
    response = _api_error_response(code=code, detail=detail, status=status)
    if transport == REFRESH_TOKEN_TRANSPORT_COOKIE:
        clear_refresh_cookie(response=response)
    return response


def _enforce_csrf_for_transport(request, *, transport: str) -> Response | None:
    if transport == REFRESH_TOKEN_TRANSPORT_BODY:
        return None
    return _enforce_csrf(request)


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
