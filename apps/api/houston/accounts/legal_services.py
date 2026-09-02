from __future__ import annotations

from django.utils import timezone

from houston.accounts.legal_constants import (
    AI_CONSENT_REQUIRED_CODE,
    AI_CONSENT_REQUIRED_DETAIL,
    CURRENT_AI_CONSENT_VERSION,
    CURRENT_TERMS_VERSION,
    INVALID_AI_CONSENT_VERSION_CODE,
    INVALID_TERMS_VERSION_CODE,
    TERMS_ACCEPTANCE_REQUIRED_CODE,
    TERMS_ACCEPTANCE_REQUIRED_DETAIL,
)
from houston.accounts.models import User


class TermsAcceptanceRequiredError(Exception):
    code = TERMS_ACCEPTANCE_REQUIRED_CODE
    detail = TERMS_ACCEPTANCE_REQUIRED_DETAIL


class AiConsentRequiredError(Exception):
    code = AI_CONSENT_REQUIRED_CODE
    detail = AI_CONSENT_REQUIRED_DETAIL


class InvalidLegalVersionError(Exception):
    def __init__(self, *, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(detail)


def has_current_terms(user: User) -> bool:
    return (
        user.terms_version == CURRENT_TERMS_VERSION and user.terms_accepted_at is not None
    )


def has_current_ai_consent(user: User) -> bool:
    return (
        user.ai_consent_version == CURRENT_AI_CONSENT_VERSION
        and user.ai_processing_consented_at is not None
    )


def require_current_terms(*, user: User) -> None:
    if not has_current_terms(user):
        raise TermsAcceptanceRequiredError


def require_current_ai_consent(*, user: User) -> None:
    if not has_current_ai_consent(user):
        raise AiConsentRequiredError


def accept_current_terms(*, user: User, version: str) -> User:
    if version != CURRENT_TERMS_VERSION:
        raise InvalidLegalVersionError(
            code=INVALID_TERMS_VERSION_CODE,
            detail="This terms version is not current.",
        )
    user.terms_version = CURRENT_TERMS_VERSION
    user.terms_accepted_at = timezone.now()
    user.save(update_fields=["terms_version", "terms_accepted_at", "updated_at"])
    return user


def accept_current_ai_consent(*, user: User, version: str) -> User:
    if version != CURRENT_AI_CONSENT_VERSION:
        raise InvalidLegalVersionError(
            code=INVALID_AI_CONSENT_VERSION_CODE,
            detail="This AI consent version is not current.",
        )
    user.ai_consent_version = CURRENT_AI_CONSENT_VERSION
    user.ai_processing_consented_at = timezone.now()
    user.save(
        update_fields=["ai_consent_version", "ai_processing_consented_at", "updated_at"]
    )
    return user


def withdraw_ai_consent(*, user: User) -> User:
    user.ai_consent_version = None
    user.ai_processing_consented_at = None
    user.save(
        update_fields=["ai_consent_version", "ai_processing_consented_at", "updated_at"]
    )
    return user


def maybe_accept_terms_version(*, user: User, terms_version: str | None) -> None:
    if terms_version is None:
        return
    accept_current_terms(user=user, version=terms_version)


def clear_legal_fields(*, user: User) -> None:
    user.terms_version = None
    user.terms_accepted_at = None
    user.ai_consent_version = None
    user.ai_processing_consented_at = None


def grant_current_legal_defaults(*, user: User) -> User:
    now = timezone.now()
    user.terms_version = CURRENT_TERMS_VERSION
    user.terms_accepted_at = now
    user.ai_consent_version = CURRENT_AI_CONSENT_VERSION
    user.ai_processing_consented_at = now
    user.save(
        update_fields=[
            "terms_version",
            "terms_accepted_at",
            "ai_consent_version",
            "ai_processing_consented_at",
            "updated_at",
        ]
    )
    return user
