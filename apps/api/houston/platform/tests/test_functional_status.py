from __future__ import annotations

from types import SimpleNamespace

import pytest

from houston.establishments.models import Establishment, OnboardingSession
from houston.platform.onboarding_status import (
    FUNCTIONAL_ACTIVATED,
    FUNCTIONAL_ERROR,
    FUNCTIONAL_IN_PROGRESS,
    FUNCTIONAL_READY_TO_COMPLETE,
    FUNCTIONAL_WAITING_ACCEPTANCE,
    derive_onboarding_functional_status,
)

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("establishment_status", "session_status", "last_error_code", "readiness", "expected"),
    [
        (
            Establishment.Status.ACTIVE,
            OnboardingSession.Status.FAILED,
            "boom",
            {"is_ready": False, "blockers": [{"code": "missing_active_owner_or_director"}]},
            FUNCTIONAL_ACTIVATED,
        ),
        (
            Establishment.Status.DRAFT,
            OnboardingSession.Status.ACTIVATED,
            "boom",
            {"is_ready": True, "blockers": []},
            FUNCTIONAL_ACTIVATED,
        ),
        (
            Establishment.Status.DRAFT,
            OnboardingSession.Status.STARTED,
            "boom",
            {"is_ready": True, "blockers": []},
            FUNCTIONAL_ERROR,
        ),
        (
            Establishment.Status.DRAFT,
            OnboardingSession.Status.FAILED,
            "",
            {"is_ready": True, "blockers": []},
            FUNCTIONAL_ERROR,
        ),
        (
            Establishment.Status.DRAFT,
            OnboardingSession.Status.STARTED,
            "",
            {"is_ready": True, "blockers": []},
            FUNCTIONAL_READY_TO_COMPLETE,
        ),
        (
            Establishment.Status.DRAFT,
            OnboardingSession.Status.STARTED,
            "",
            {
                "is_ready": False,
                "blockers": [{"code": "missing_active_owner_or_director"}],
            },
            FUNCTIONAL_WAITING_ACCEPTANCE,
        ),
        (
            Establishment.Status.DRAFT,
            OnboardingSession.Status.STARTED,
            "",
            {
                "is_ready": False,
                "blockers": [
                    {"code": "missing_active_owner_or_director"},
                    {"code": "missing_active_business_unit"},
                ],
            },
            FUNCTIONAL_IN_PROGRESS,
        ),
        (
            Establishment.Status.DRAFT,
            OnboardingSession.Status.STARTED,
            "",
            None,
            FUNCTIONAL_IN_PROGRESS,
        ),
    ],
)
def test_derive_onboarding_functional_status_table(
    establishment_status,
    session_status,
    last_error_code,
    readiness,
    expected,
):
    establishment = SimpleNamespace(status=establishment_status)
    session = SimpleNamespace(status=session_status, last_error_code=last_error_code)
    assert (
        derive_onboarding_functional_status(
            establishment=establishment,
            session=session,
            readiness=readiness,
        )
        == expected
    )


def test_derive_onboarding_functional_status_none_session():
    establishment = SimpleNamespace(status=Establishment.Status.DRAFT)
    assert (
        derive_onboarding_functional_status(
            establishment=establishment,
            session=None,
            readiness={"is_ready": True, "blockers": []},
        )
        is None
    )
