from __future__ import annotations

import logging
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime

from django.conf import settings
from django.contrib.auth import authenticate
from django.db import IntegrityError, transaction
from django.http import HttpRequest, HttpResponse
from django.utils import timezone

from houston.accounts import tokens
from houston.accounts.models import AccessToken, SessionRefreshToken, User, UserSession
from houston.accounts.selectors import build_bootstrap_payload
from houston.core.observability import build_refresh_token_reuse_log_context
from houston.establishments.models import (
    Establishment,
    EstablishmentMembership,
    OnboardingSession,
)
from houston.establishments.services import start_onboarding_session
from houston.organizations.models import Organization

logger = logging.getLogger(__name__)

INVALID_CREDENTIALS_DETAIL = "Invalid credentials."
AUTHENTICATION_FAILED_DETAIL = "Authentication failed."
INVALID_REGISTRATION_INVITE_CODE_DETAIL = "Invalid invitation code."
REGISTRATION_DUPLICATE_EMAIL_DETAIL = "An account with this email already exists."


class InvalidCredentialsError(Exception):
    pass


class InvalidRefreshTokenError(Exception):
    pass


class RefreshTokenReuseError(Exception):
    pass


class InvalidSelectedEstablishmentError(Exception):
    pass


class InvalidRegistrationInviteCodeError(Exception):
    pass


class RegistrationDuplicateEmailError(Exception):
    pass


@dataclass(frozen=True)
class RegistrationResult:
    organization: Organization
    establishment: Establishment
    user: User
    membership: EstablishmentMembership
    onboarding_session: OnboardingSession


@dataclass(frozen=True)
class RegistrationBundle:
    registration: RegistrationResult
    auth: AuthSessionBundle
    payload: dict


@dataclass(frozen=True)
class IssuedAccessToken:
    raw_token: str
    record: AccessToken


@dataclass(frozen=True)
class IssuedRefreshToken:
    raw_token: str
    record: SessionRefreshToken


@dataclass(frozen=True)
class AuthSessionBundle:
    session: UserSession
    access_token: IssuedAccessToken
    refresh_token: IssuedRefreshToken
    payload: dict


def is_valid_registration_invite_code(invite_code: str) -> bool:
    normalized_code = invite_code.strip()

    if not normalized_code:
        return False

    allowed_codes = settings.HOUSTON_REGISTRATION_INVITE_CODES

    if not allowed_codes:
        return False

    for candidate in allowed_codes:
        if secrets.compare_digest(normalized_code, candidate.strip()):
            return True

    return False


def validate_registration_invite_code(invite_code: str) -> None:
    if not is_valid_registration_invite_code(invite_code):
        raise InvalidRegistrationInviteCodeError


def validate_registration_email_available(email: str) -> None:
    normalized_email = User.normalize_email_value(email)

    if normalized_email is None:
        raise RegistrationDuplicateEmailError

    if User.objects.filter(email__iexact=normalized_email).exists():
        raise RegistrationDuplicateEmailError


def validate_onboarding_owner_registration(*, invite_code: str, email: str) -> None:
    validate_registration_invite_code(invite_code)
    validate_registration_email_available(email)


@transaction.atomic
def provision_onboarding_registration(
    *,
    invite_code: str,
    first_name: str,
    last_name: str,
    email: str,
    password: str,
    organization_name: str,
    establishment_name: str,
) -> RegistrationResult:
    validate_registration_invite_code(invite_code)
    validate_registration_email_available(email)
    normalized_email = User.normalize_email_value(email)
    assert normalized_email is not None

    organization = Organization.objects.create(
        name=organization_name.strip(),
        status=Organization.Status.ACTIVE,
    )
    establishment = Establishment.objects.create(
        name=establishment_name.strip(),
        organization=organization,
        status=Establishment.Status.DRAFT,
    )

    user = User(
        username=_build_registration_username(normalized_email),
        email=normalized_email,
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        identity_type=User.IdentityType.EMAIL,
        status=User.Status.ACTIVE,
    )
    user.set_password(password)

    try:
        user.save()
    except IntegrityError as exc:
        raise RegistrationDuplicateEmailError from exc

    membership = EstablishmentMembership.objects.create(
        user=user,
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    onboarding_session = start_onboarding_session(
        organization=organization,
        establishment=establishment,
        started_by=user,
    )

    return RegistrationResult(
        organization=organization,
        establishment=establishment,
        user=user,
        membership=membership,
        onboarding_session=onboarding_session,
    )


def register_onboarding_owner(
    *,
    request: HttpRequest,
    invite_code: str,
    first_name: str,
    last_name: str,
    email: str,
    password: str,
    organization_name: str,
    establishment_name: str,
) -> RegistrationBundle:
    registration = provision_onboarding_registration(
        invite_code=invite_code,
        first_name=first_name,
        last_name=last_name,
        email=email,
        password=password,
        organization_name=organization_name,
        establishment_name=establishment_name,
    )
    auth_bundle = create_login_session(request=request, user=registration.user)
    payload = auth_bundle.payload.copy()
    payload.update(
        {
            "establishment_id": registration.establishment.id,
            "onboarding_session_id": registration.onboarding_session.id,
        }
    )

    return RegistrationBundle(
        registration=registration,
        auth=auth_bundle,
        payload=payload,
    )


def authenticate_user(*, request: HttpRequest | None, identifier: str, password: str) -> User:
    user = authenticate(request=request, identifier=identifier, password=password)

    if user is None:
        raise InvalidCredentialsError

    return user


@transaction.atomic
def create_login_session(*, request: HttpRequest, user: User) -> AuthSessionBundle:
    session = create_user_session(request=request, user=user)
    access_token = issue_access_token(session=session)
    refresh_token = issue_refresh_token(session=session, family_id=session.refresh_token_family_id)

    return AuthSessionBundle(
        session=session,
        access_token=access_token,
        refresh_token=refresh_token,
        payload=build_auth_response_payload(session=session, access_token=access_token),
    )


def refresh_session(*, raw_refresh_token: str) -> AuthSessionBundle:
    refresh_token = validate_refresh_token(raw_refresh_token=raw_refresh_token)

    with transaction.atomic():
        mark_refresh_token_used(refresh_token)

        session = refresh_token.session
        session.last_used_at = timezone.now()
        session.refresh_expires_at = _build_refresh_expiry(
            now=session.last_used_at,
            session=session,
        )
        session.save(update_fields=["last_used_at", "refresh_expires_at", "updated_at"])

        access_token = issue_access_token(session=session)
        rotated_refresh_token = issue_refresh_token(
            session=session,
            family_id=refresh_token.family_id,
        )

        return AuthSessionBundle(
            session=session,
            access_token=access_token,
            refresh_token=rotated_refresh_token,
            payload=build_auth_response_payload(session=session, access_token=access_token),
        )


def build_auth_response_payload(
    *,
    session: UserSession,
    access_token: IssuedAccessToken,
) -> dict:
    payload = build_bootstrap_payload(
        session.user,
        session=session,
        autoselect_single_membership=True,
    )
    payload.update(
        {
            "access_token": access_token.raw_token,
            "access_token_expires_at": access_token.record.expires_at,
        }
    )
    return payload


def create_user_session(*, request: HttpRequest, user: User) -> UserSession:
    now = timezone.now()
    absolute_expires_at = now + settings.HOUSTON_AUTH_ABSOLUTE_SESSION_TTL
    refresh_expires_at = min(
        now + settings.HOUSTON_AUTH_REFRESH_TOKEN_TTL,
        absolute_expires_at,
    )

    return UserSession.objects.create(
        user=user,
        refresh_token_family_id=uuid.uuid4(),
        user_agent=_extract_user_agent(request),
        ip_metadata=_extract_client_ip(request),
        last_used_at=now,
        refresh_expires_at=refresh_expires_at,
        absolute_expires_at=absolute_expires_at,
    )


def issue_access_token(*, session: UserSession) -> IssuedAccessToken:
    now = timezone.now()

    def create_record(token_digest: str) -> AccessToken:
        return AccessToken.objects.create(
            session=session,
            token_digest=token_digest,
            expires_at=now + settings.HOUSTON_AUTH_ACCESS_TOKEN_TTL,
        )

    raw_token, record = _create_token_record(create_record)
    return IssuedAccessToken(raw_token=raw_token, record=record)


def issue_refresh_token(*, session: UserSession, family_id: uuid.UUID) -> IssuedRefreshToken:
    now = timezone.now()
    expires_at = _build_refresh_expiry(now=now, session=session)

    def create_record(token_digest: str) -> SessionRefreshToken:
        return SessionRefreshToken.objects.create(
            session=session,
            family_id=family_id,
            token_digest=token_digest,
            expires_at=expires_at,
        )

    raw_token, record = _create_token_record(create_record)
    session.refresh_token_family_id = family_id
    session.refresh_expires_at = expires_at
    session.last_used_at = now
    session.save(
        update_fields=[
            "refresh_token_family_id",
            "refresh_expires_at",
            "last_used_at",
            "updated_at",
        ]
    )
    return IssuedRefreshToken(raw_token=raw_token, record=record)


def validate_refresh_token(*, raw_refresh_token: str) -> SessionRefreshToken:
    refresh_token = (
        SessionRefreshToken.objects.select_related("session", "session__user")
        .filter(token_digest=tokens.digest_token(raw_refresh_token))
        .first()
    )

    if refresh_token is None:
        raise InvalidRefreshTokenError

    if _is_reused_refresh_token(refresh_token):
        _revoke_refresh_token_family_for_reuse(
            session_id=refresh_token.session_id,
            family_id=refresh_token.family_id,
        )
        logger.warning(
            "refresh_token_reuse_detected",
            extra=build_refresh_token_reuse_log_context(
                session_id=refresh_token.session_id,
                refresh_family_id=refresh_token.family_id,
                refresh_record_id=refresh_token.id,
                user_id=refresh_token.session.user_id,
            ),
        )
        raise RefreshTokenReuseError

    now = timezone.now()
    session = refresh_token.session

    if refresh_token.expires_at <= now:
        _mark_refresh_token_expired(refresh_token, now)
        raise InvalidRefreshTokenError

    if session.absolute_expires_at <= now or session.refresh_expires_at <= now:
        _mark_session_expired(session, now)
        raise InvalidRefreshTokenError

    if session.revoked_at is not None or session.status == UserSession.Status.REVOKED:
        raise InvalidRefreshTokenError

    if session.user.status != User.Status.ACTIVE:
        revoke_session(session=session)
        raise InvalidRefreshTokenError

    return refresh_token


def revoke_session(*, session: UserSession) -> None:
    now = timezone.now()

    if session.revoked_at is None or session.status != UserSession.Status.REVOKED:
        session.revoked_at = now
        session.status = UserSession.Status.REVOKED
        session.save(update_fields=["revoked_at", "status", "updated_at"])

    AccessToken.objects.filter(session=session, revoked_at__isnull=True).update(revoked_at=now)
    SessionRefreshToken.objects.filter(session=session, revoked_at__isnull=True).update(
        revoked_at=now,
        status=SessionRefreshToken.Status.REVOKED,
    )


def revoke_refresh_token_family(*, session: UserSession, family_id: uuid.UUID) -> None:
    revoke_session(session=session)
    SessionRefreshToken.objects.filter(session=session, family_id=family_id).update(
        revoked_at=timezone.now(),
        status=SessionRefreshToken.Status.REVOKED,
    )


def switch_selected_establishment(
    *,
    session: UserSession,
    establishment_id,
) -> dict:
    membership = (
        EstablishmentMembership.objects.filter(
            user=session.user,
            status=EstablishmentMembership.Status.ACTIVE,
            establishment_id=establishment_id,
            establishment__status=Establishment.Status.ACTIVE,
            establishment__organization__status=Organization.Status.ACTIVE,
        )
        .select_related("establishment")
        .first()
    )

    if membership is None:
        raise InvalidSelectedEstablishmentError

    session.selected_establishment = membership.establishment
    session.save(update_fields=["selected_establishment", "updated_at"])

    return build_bootstrap_payload(session.user, session=session)


def resolve_session_for_logout(
    *,
    auth_session: UserSession | None,
    raw_refresh_token: str | None,
) -> UserSession | None:
    if auth_session is not None:
        return auth_session

    if not raw_refresh_token:
        return None

    refresh_token = (
        SessionRefreshToken.objects.select_related("session")
        .filter(token_digest=tokens.digest_token(raw_refresh_token))
        .first()
    )
    return None if refresh_token is None else refresh_token.session


def set_refresh_cookie(
    *,
    response: HttpResponse,
    raw_refresh_token: str,
    expires_at: datetime,
) -> None:
    response.set_cookie(
        settings.HOUSTON_AUTH_REFRESH_COOKIE_NAME,
        raw_refresh_token,
        expires=expires_at,
        httponly=settings.HOUSTON_AUTH_REFRESH_COOKIE_HTTPONLY,
        secure=settings.HOUSTON_AUTH_REFRESH_COOKIE_SECURE,
        samesite=settings.HOUSTON_AUTH_REFRESH_COOKIE_SAMESITE,
        path=settings.HOUSTON_AUTH_REFRESH_COOKIE_PATH,
    )


def clear_refresh_cookie(*, response: HttpResponse) -> None:
    response.delete_cookie(
        settings.HOUSTON_AUTH_REFRESH_COOKIE_NAME,
        path=settings.HOUSTON_AUTH_REFRESH_COOKIE_PATH,
        samesite=settings.HOUSTON_AUTH_REFRESH_COOKIE_SAMESITE,
    )


def mark_refresh_token_used(refresh_token: SessionRefreshToken) -> None:
    now = timezone.now()
    refresh_token.used_at = now
    refresh_token.status = SessionRefreshToken.Status.USED
    refresh_token.save(update_fields=["used_at", "status", "updated_at"])


def _create_token_record(create_record):
    for _ in range(settings.HOUSTON_AUTH_TOKEN_GENERATION_MAX_ATTEMPTS):
        raw_token = tokens.generate_raw_token()
        token_digest = tokens.digest_token(raw_token)

        try:
            with transaction.atomic():
                return raw_token, create_record(token_digest)
        except IntegrityError:
            continue

    raise RuntimeError("Unable to generate a unique token digest.")


def _is_reused_refresh_token(refresh_token: SessionRefreshToken) -> bool:
    return (
        refresh_token.status
        in {
            SessionRefreshToken.Status.USED,
            SessionRefreshToken.Status.REVOKED,
        }
        or refresh_token.used_at is not None
        or refresh_token.revoked_at is not None
    )


def _revoke_refresh_token_family_for_reuse(*, session_id, family_id: uuid.UUID) -> None:
    now = timezone.now()

    with transaction.atomic():
        session = UserSession.objects.select_for_update().get(id=session_id)

        if session.revoked_at is None or session.status != UserSession.Status.REVOKED:
            session.revoked_at = now
            session.status = UserSession.Status.REVOKED
            session.save(update_fields=["revoked_at", "status", "updated_at"])

        AccessToken.objects.filter(session=session, revoked_at__isnull=True).update(revoked_at=now)
        SessionRefreshToken.objects.filter(session=session, family_id=family_id).update(
            revoked_at=now,
            status=SessionRefreshToken.Status.REVOKED,
        )


def _build_refresh_expiry(*, now: datetime, session: UserSession) -> datetime:
    return min(
        now + settings.HOUSTON_AUTH_REFRESH_TOKEN_TTL,
        session.absolute_expires_at,
    )


def _mark_refresh_token_expired(refresh_token: SessionRefreshToken, now: datetime) -> None:
    if refresh_token.status != SessionRefreshToken.Status.EXPIRED:
        refresh_token.status = SessionRefreshToken.Status.EXPIRED
        refresh_token.revoked_at = refresh_token.revoked_at or now
        refresh_token.save(update_fields=["status", "revoked_at", "updated_at"])


def _mark_session_expired(session: UserSession, now: datetime) -> None:
    if session.status != UserSession.Status.EXPIRED:
        session.status = UserSession.Status.EXPIRED
        session.revoked_at = session.revoked_at or now
        session.save(update_fields=["status", "revoked_at", "updated_at"])


def _extract_user_agent(request: HttpRequest) -> str:
    return request.META.get("HTTP_USER_AGENT", "")[:512]


def _extract_client_ip(request: HttpRequest) -> str | None:
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")

    if forwarded_for:
        return forwarded_for.split(",")[0].strip() or None

    remote_addr = request.META.get("REMOTE_ADDR")
    return remote_addr or None


def resolve_or_create_pending_user_for_invite(
    *,
    email: str,
    first_name: str,
    last_name: str,
    existing_user: User | None = None,
) -> User:
    normalized_email = User.normalize_email_value(email)
    if normalized_email is None:
        raise ValueError("A valid email is required.")

    if existing_user is not None:
        return existing_user

    user = User(
        username=_build_registration_username(normalized_email),
        email=normalized_email,
        first_name=first_name,
        last_name=last_name,
        identity_type=User.IdentityType.EMAIL,
        status=User.Status.PENDING,
    )
    user.set_unusable_password()

    try:
        with transaction.atomic():
            user.save()
    except IntegrityError:
        return User.objects.get(email__iexact=normalized_email)

    return user


def _build_registration_username(email: str) -> str:
    local_part = email.split("@", 1)[0].strip().lower() or "owner"
    candidate = local_part[:150]

    if not User.objects.filter(username=candidate).exists():
        return candidate

    suffix = uuid.uuid4().hex[:8]

    return f"{candidate[:141]}-{suffix}"
