from __future__ import annotations

from rest_framework import status
from rest_framework.response import Response

from houston.accounts.legal_services import (
    AiConsentRequiredError,
    InvalidLegalVersionError,
    TermsAcceptanceRequiredError,
)

_LEGAL_ERRORS = (TermsAcceptanceRequiredError, AiConsentRequiredError, InvalidLegalVersionError)


def legal_error_response(exc: Exception) -> Response | None:
    if isinstance(exc, InvalidLegalVersionError):
        return Response(
            {"code": exc.code, "detail": exc.detail},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if isinstance(exc, _LEGAL_ERRORS):
        return Response(
            {"code": exc.code, "detail": exc.detail},
            status=status.HTTP_403_FORBIDDEN,
        )
    return None
