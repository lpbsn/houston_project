from __future__ import annotations

from django.conf import settings
from django.middleware.csrf import CsrfViewMiddleware, get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from houston.accounts.api.serializers import (
    REFRESH_TOKEN_TRANSPORT_BODY,
    REFRESH_TOKEN_TRANSPORT_COOKIE,
    AccountDeletionPreviewResponseSerializer,
    AccountDeletionRequestSerializer,
    ApiErrorResponseSerializer,
    AuthResponseSerializer,
    BootstrapResponseSerializer,
    CsrfResponseSerializer,
    DetailResponseSerializer,
    DirectorInvitationAcceptErrorResponseSerializer,
    DirectorInvitationAcceptRequestSerializer,
    DirectorInvitationAcceptResponseSerializer,
    EmailChangeConfirmRequestSerializer,
    EmailChangeConfirmResponseSerializer,
    EmailChangeRequestResponseSerializer,
    EmailChangeRequestSerializer,
    LegalVersionRequestSerializer,
    LoginRequestSerializer,
    LogoutRequestSerializer,
    PasswordChangeRequestSerializer,
    PasswordResetConfirmRequestSerializer,
    PasswordResetConfirmResponseSerializer,
    PasswordResetRequestResponseSerializer,
    PasswordResetRequestSerializer,
    RefreshRequestSerializer,
    SwitchEstablishmentRequestSerializer,
    UserProfileUpdateRequestSerializer,
    ValidationErrorResponseSerializer,
)
from houston.accounts.authentication import (
    BearerAccessTokenAuthentication,
    OptionalBearerAccessTokenAuthentication,
)
from houston.accounts.deletion_services import (
    InvalidAccountDeletionPasswordError,
    OrganizationClosureRequiredError,
    build_account_deletion_preview,
    delete_authenticated_account,
)
from houston.accounts.email_change_services import (
    EMAIL_CHANGE_DUPLICATE_DETAIL,
    EMAIL_CHANGE_UNAVAILABLE_DETAIL,
    EMAIL_CHANGE_UNCHANGED_DETAIL,
    INVALID_EMAIL_CHANGE_TOKEN_DETAIL,
    EmailChangeDuplicateError,
    EmailChangeUnavailableError,
    EmailChangeUnchangedError,
    InvalidEmailChangeCredentialsError,
    InvalidEmailChangeTokenError,
    confirm_email_change,
    request_email_change,
)
from houston.accounts.password_services import (
    INVALID_PASSWORD_RESET_TOKEN_DETAIL,
    PASSWORD_RESET_REQUEST_DETAIL,
    PASSWORD_RESET_UNAVAILABLE_DETAIL,
    PASSWORD_UNCHANGED_DETAIL,
    InvalidPasswordChangeCredentialsError,
    InvalidPasswordResetTokenError,
    PasswordRejectedError,
    PasswordResetUnavailableError,
    PasswordUnchangedError,
    change_password,
    confirm_password_reset,
    request_password_reset,
)
from houston.accounts.selectors import _serialize_user, build_bootstrap_payload
from houston.accounts.services import (
    AUTHENTICATION_FAILED_DETAIL,
    INVALID_CREDENTIALS_DETAIL,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    InvalidSelectedEstablishmentError,
    RefreshTokenReuseError,
    authenticate_user,
    clear_refresh_cookie,
    create_password_authenticated_session,
    refresh_session,
    resolve_session_for_logout,
    revoke_session,
    set_refresh_cookie,
    switch_selected_establishment,
    update_user_profile,
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
    permission_classes = [permissions.AllowAny]

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
    permission_classes = [permissions.AllowAny]
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
            bundle = create_password_authenticated_session(
                request=request,
                user=user,
                password=serializer.validated_data["password"],
            )
        except InvalidCredentialsError:
            return _api_error_response(
                code="not_authenticated",
                detail=INVALID_CREDENTIALS_DETAIL,
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return _build_auth_response(
            payload=bundle.payload,
            raw_refresh_token=bundle.refresh_token.raw_token,
            refresh_expires_at=bundle.refresh_token.record.expires_at,
            transport=transport,
        )



class DirectorInvitationAcceptView(AuthRateLimitedMixin, APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
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
            "The invitation bearer is sent in the JSON body, not in the URI. "
            "Owner invitations activate all compatible owner/invited memberships in the "
            "same organization. Cookie transport requires Django CSRF; body transport "
            "does not use cookies."
        ),
    )
    def post(self, request):
        serializer = DirectorInvitationAcceptRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        transport = serializer.validated_data.pop("refresh_token_transport")
        raw_token = serializer.validated_data.pop("token")
        terms_version = serializer.validated_data.pop("terms_version", None)
        version_error = _reject_invalid_terms_version(terms_version)
        if version_error is not None:
            return version_error

        csrf_failure = _enforce_csrf_for_transport(request, transport=transport)
        if csrf_failure is not None:
            return csrf_failure

        try:
            result = accept_establishment_invitation(
                request=request,
                raw_token=raw_token,
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

        terms_error = _apply_optional_terms(
            user=result.auth.session.user,
            payload=result.payload,
            terms_version=terms_version,
        )
        if terms_error is not None:
            return terms_error

        return _build_auth_response(
            payload=result.payload,
            raw_refresh_token=result.auth.refresh_token.raw_token,
            refresh_expires_at=result.auth.refresh_token.record.expires_at,
            transport=transport,
            response_status=status.HTTP_201_CREATED,
        )


class RefreshView(AuthRateLimitedMixin, APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
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
    permission_classes = [permissions.AllowAny]

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
        },
        description="Updates the authenticated user's personal profile fields.",
    )
    def patch(self, request):
        serializer = UserProfileUpdateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated = serializer.validated_data
        update_user_profile(
            user=request.user,
            first_name=validated.get("first_name"),
            last_name=validated.get("last_name"),
        )

        return Response(build_bootstrap_payload(request.user, session=request.auth.session))


class EmailChangeRequestView(AuthRateLimitedMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = settings.AUTH_THROTTLE_SCOPE_EMAIL_CHANGE

    @extend_schema(
        tags=["auth"],
        request=EmailChangeRequestSerializer,
        responses={
            200: EmailChangeRequestResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            409: OpenApiResponse(response=ApiErrorResponseSerializer),
            429: _THROTTLED_OPENAPI_RESPONSE,
            503: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
        description=(
            "Starts an email change. Requires the current password. The live email "
            "does not change until the token sent to the new address is confirmed."
        ),
    )
    def post(self, request):
        serializer = EmailChangeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = request_email_change(
                user=request.user,
                password=serializer.validated_data["password"],
                new_email=serializer.validated_data["new_email"],
            )
        except InvalidEmailChangeCredentialsError:
            return _api_error_response(
                code="invalid_credentials",
                detail=INVALID_CREDENTIALS_DETAIL,
                status=status.HTTP_403_FORBIDDEN,
            )
        except EmailChangeUnchangedError:
            return _api_error_response(
                code="email_change_unchanged",
                detail=EMAIL_CHANGE_UNCHANGED_DETAIL,
                status=status.HTTP_400_BAD_REQUEST,
            )
        except EmailChangeUnavailableError:
            return _api_error_response(
                code="email_change_unavailable",
                detail=EMAIL_CHANGE_UNAVAILABLE_DETAIL,
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except EmailChangeDuplicateError:
            return _api_error_response(
                code="email_change_duplicate",
                detail=EMAIL_CHANGE_DUPLICATE_DETAIL,
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            {
                "pending_email": result.pending_email,
                "expires_at": result.expires_at,
            }
        )


class EmailChangeConfirmView(AuthRateLimitedMixin, APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_scope = settings.AUTH_THROTTLE_SCOPE_EMAIL_CHANGE_CONFIRM

    @extend_schema(
        tags=["auth"],
        request=EmailChangeConfirmRequestSerializer,
        responses={
            200: EmailChangeConfirmResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            409: OpenApiResponse(response=ApiErrorResponseSerializer),
            429: _THROTTLED_OPENAPI_RESPONSE,
        },
        description=(
            "Confirms an email change with the token from the new inbox. "
            "The bearer is sent in the JSON body. Does not create a session."
        ),
    )
    def post(self, request):
        serializer = EmailChangeConfirmRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = confirm_email_change(raw_token=serializer.validated_data["token"])
        except InvalidEmailChangeTokenError:
            return _api_error_response(
                code="email_change_invalid",
                detail=INVALID_EMAIL_CHANGE_TOKEN_DETAIL,
                status=status.HTTP_400_BAD_REQUEST,
            )
        except EmailChangeDuplicateError:
            return _api_error_response(
                code="email_change_duplicate",
                detail=EMAIL_CHANGE_DUPLICATE_DETAIL,
                status=status.HTTP_409_CONFLICT,
            )

        return Response({"email": user.email})


class PasswordChangeView(AuthRateLimitedMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = settings.AUTH_THROTTLE_SCOPE_PASSWORD_CHANGE

    @extend_schema(
        tags=["auth"],
        request=PasswordChangeRequestSerializer,
        responses={
            204: OpenApiResponse(description="Password changed."),
            400: OpenApiResponse(response=ValidationErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            429: _THROTTLED_OPENAPI_RESPONSE,
        },
        description=(
            "Changes the authenticated user's password. Requires the current password. "
            "Revokes other sessions; the current session remains valid."
        ),
    )
    def post(self, request):
        serializer = PasswordChangeRequestSerializer(
            data=request.data,
            context={"user": request.user},
        )
        serializer.is_valid(raise_exception=True)
        try:
            change_password(
                user=request.user,
                current_password=serializer.validated_data["current_password"],
                new_password=serializer.validated_data["password"],
                current_session=request.auth.session,
            )
        except InvalidPasswordChangeCredentialsError:
            return _api_error_response(
                code="invalid_credentials",
                detail=INVALID_CREDENTIALS_DETAIL,
                status=status.HTTP_403_FORBIDDEN,
            )
        except PasswordUnchangedError:
            raise serializers.ValidationError({"password": [PASSWORD_UNCHANGED_DETAIL]}) from None
        except PasswordRejectedError as exc:
            raise serializers.ValidationError({"password": exc.messages}) from exc

        return Response(status=status.HTTP_204_NO_CONTENT)


class PasswordResetRequestView(AuthRateLimitedMixin, APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_scope = settings.AUTH_THROTTLE_SCOPE_PASSWORD_RESET

    @extend_schema(
        tags=["auth"],
        request=PasswordResetRequestSerializer,
        responses={
            200: PasswordResetRequestResponseSerializer,
            400: OpenApiResponse(response=ValidationErrorResponseSerializer),
            429: _THROTTLED_OPENAPI_RESPONSE,
            503: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
        description=(
            "Requests a password reset email. The HTTP response does not reveal whether "
            "the address belongs to an account."
        ),
    )
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            request_password_reset(email=serializer.validated_data["email"])
        except PasswordResetUnavailableError:
            return _api_error_response(
                code="password_reset_unavailable",
                detail=PASSWORD_RESET_UNAVAILABLE_DETAIL,
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response({"detail": PASSWORD_RESET_REQUEST_DETAIL})


class PasswordResetConfirmView(AuthRateLimitedMixin, APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_scope = settings.AUTH_THROTTLE_SCOPE_PASSWORD_RESET_CONFIRM

    @extend_schema(
        tags=["auth"],
        request=PasswordResetConfirmRequestSerializer,
        responses={
            200: PasswordResetConfirmResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            429: _THROTTLED_OPENAPI_RESPONSE,
        },
        description=(
            "Confirms a password reset with the token from the email. "
            "The bearer is sent in the JSON body. Does not create a session."
        ),
    )
    def post(self, request):
        serializer = PasswordResetConfirmRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            confirm_password_reset(
                raw_token=serializer.validated_data["token"],
                new_password=serializer.validated_data["password"],
            )
        except InvalidPasswordResetTokenError:
            return _api_error_response(
                code="password_reset_invalid",
                detail=INVALID_PASSWORD_RESET_TOKEN_DETAIL,
                status=status.HTTP_400_BAD_REQUEST,
            )
        except PasswordUnchangedError:
            raise serializers.ValidationError({"password": [PASSWORD_UNCHANGED_DETAIL]}) from None
        except PasswordRejectedError as exc:
            raise serializers.ValidationError({"password": exc.messages}) from exc

        return Response({"detail": "Password has been reset."})


class AccountDeletionPreviewView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["auth"],
        responses={
            200: AccountDeletionPreviewResponseSerializer,
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
        description=(
            "Returns account-deletion consequences for the authenticated user, "
            "including whether organization closure is required."
        ),
    )
    def get(self, request):
        return Response(build_account_deletion_preview(user=request.user))


class AccountDeletionView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["auth"],
        request=AccountDeletionRequestSerializer,
        responses={
            204: OpenApiResponse(
                description="Account deleted; cookie cleared for cookie transport."
            ),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            409: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
        description=(
            "Deletes the authenticated account after password confirmation. "
            "Last sole owners must confirm close_organizations. Cookie transport "
            "requires CSRF and clears the refresh cookie."
        ),
    )
    def post(self, request):
        serializer = AccountDeletionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        transport = serializer.validated_data["refresh_token_transport"]

        csrf_failure = _enforce_csrf_for_transport(request, transport=transport)
        if csrf_failure is not None:
            return csrf_failure

        try:
            delete_authenticated_account(
                user=request.user,
                password=serializer.validated_data["password"],
                close_organizations=serializer.validated_data["close_organizations"],
            )
        except InvalidAccountDeletionPasswordError as exc:
            return _api_error_response(
                code="invalid_credentials",
                detail=exc.detail,
                status=status.HTTP_403_FORBIDDEN,
            )
        except OrganizationClosureRequiredError as exc:
            return _api_error_response(
                code="organization_closure_required",
                detail=exc.detail,
                status=status.HTTP_409_CONFLICT,
            )

        response = Response(status=status.HTTP_204_NO_CONTENT)
        if transport == REFRESH_TOKEN_TRANSPORT_COOKIE:
            clear_refresh_cookie(response=response)
        return response


class TermsAcceptView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["auth"],
        request=LegalVersionRequestSerializer,
        responses={
            200: BootstrapResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
        description="Records acceptance of the current terms of use version.",
    )
    def post(self, request):
        serializer = LegalVersionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        from houston.accounts.legal_services import InvalidLegalVersionError, accept_current_terms

        try:
            accept_current_terms(user=request.user, version=serializer.validated_data["version"])
        except InvalidLegalVersionError as exc:
            from houston.accounts.api.legal_errors import legal_error_response

            return legal_error_response(exc)
        return Response(build_bootstrap_payload(user=request.user, session=request.auth.session))


class AiConsentAcceptView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["auth"],
        request=LegalVersionRequestSerializer,
        responses={
            200: BootstrapResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
        description="Records consent to the current OpenAI processing disclosure.",
    )
    def post(self, request):
        serializer = LegalVersionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        from houston.accounts.legal_services import (
            InvalidLegalVersionError,
            accept_current_ai_consent,
        )

        try:
            accept_current_ai_consent(
                user=request.user,
                version=serializer.validated_data["version"],
            )
        except InvalidLegalVersionError as exc:
            from houston.accounts.api.legal_errors import legal_error_response

            return legal_error_response(exc)
        return Response(build_bootstrap_payload(user=request.user, session=request.auth.session))


class AiConsentDeclineView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["auth"],
        request=LegalVersionRequestSerializer,
        responses={
            200: BootstrapResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
        description="Records an initial decline of the current OpenAI processing disclosure.",
    )
    def post(self, request):
        serializer = LegalVersionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        from houston.accounts.legal_services import (
            InvalidLegalVersionError,
            decline_current_ai_consent,
        )

        try:
            decline_current_ai_consent(
                user=request.user,
                version=serializer.validated_data["version"],
            )
        except InvalidLegalVersionError as exc:
            from houston.accounts.api.legal_errors import legal_error_response

            return legal_error_response(exc)
        return Response(build_bootstrap_payload(user=request.user, session=request.auth.session))


class AiConsentWithdrawView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["auth"],
        request=None,
        responses={
            200: BootstrapResponseSerializer,
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
        description="Withdraws OpenAI processing consent after a prior grant.",
    )
    def post(self, request):
        from houston.accounts.legal_services import withdraw_ai_consent

        withdraw_ai_consent(user=request.user)
        return Response(build_bootstrap_payload(user=request.user, session=request.auth.session))


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


def _api_error_response(*, code: str, detail: str, status: int) -> Response:
    return Response({"code": code, "detail": detail}, status=status)


def _reject_invalid_terms_version(terms_version: str | None) -> Response | None:
    from houston.accounts.legal_constants import (
        CURRENT_TERMS_VERSION,
        INVALID_TERMS_VERSION_CODE,
    )

    if terms_version is None or terms_version == CURRENT_TERMS_VERSION:
        return None
    return Response(
        {
            "code": INVALID_TERMS_VERSION_CODE,
            "detail": "This terms version is not current.",
        },
        status=status.HTTP_400_BAD_REQUEST,
    )


def _apply_optional_terms(*, user, payload: dict, terms_version: str | None) -> Response | None:
    from houston.accounts.legal_services import maybe_accept_terms_version

    maybe_accept_terms_version(user=user, terms_version=terms_version)
    user.refresh_from_db()
    payload["user"] = _serialize_user(user)
    return None


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
