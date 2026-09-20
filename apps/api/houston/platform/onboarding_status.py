from __future__ import annotations

from houston.establishments.models import Establishment, OnboardingSession

FUNCTIONAL_ACTIVATED = "activated"
FUNCTIONAL_ERROR = "error"
FUNCTIONAL_READY_TO_COMPLETE = "ready_to_complete"
FUNCTIONAL_WAITING_ACCEPTANCE = "waiting_acceptance"
FUNCTIONAL_IN_PROGRESS = "in_progress"

_WAITING_ONLY = frozenset({"missing_active_owner_or_director"})


def derive_onboarding_functional_status(
    *,
    establishment: Establishment,
    session: OnboardingSession | None,
    readiness: dict | None,
) -> str | None:
    if session is None:
        return None
    if (
        establishment.status == Establishment.Status.ACTIVE
        or session.status == OnboardingSession.Status.ACTIVATED
    ):
        return FUNCTIONAL_ACTIVATED
    if session.status == OnboardingSession.Status.FAILED or bool(session.last_error_code):
        return FUNCTIONAL_ERROR
    if readiness is None:
        return FUNCTIONAL_IN_PROGRESS
    if readiness.get("is_ready"):
        return FUNCTIONAL_READY_TO_COMPLETE
    blocker_codes = {item.get("code") for item in readiness.get("blockers") or []}
    if blocker_codes and blocker_codes <= _WAITING_ONLY:
        return FUNCTIONAL_WAITING_ACCEPTANCE
    return FUNCTIONAL_IN_PROGRESS
