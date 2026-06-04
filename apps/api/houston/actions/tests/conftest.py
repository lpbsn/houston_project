from __future__ import annotations

import uuid

import pytest
from django.utils import timezone

from houston.establishments.models import EstablishmentMembership, MembershipScope
from houston.establishments.tests.conftest import TEST_PASSWORD
from houston.establishments.tests.test_permissions import build_membership
from houston.signals.models import Signal
from houston.signals.tests.conftest import auth_headers, create_taxonomy, login

__all__ = [
    "auth_headers",
    "login",
    "build_api_membership",
    "build_api_membership_on_establishment",
    "action_url",
    "actions_url",
    "execution_feed_url",
    "create_signal_for_membership",
    "assign_domain_scope",
    "create_action_payload",
    "api_client",
]


def build_api_membership(**kwargs) -> EstablishmentMembership:
    membership = build_membership(**kwargs)
    membership.user.set_password(TEST_PASSWORD)
    membership.user.save(update_fields=["password"])
    return membership


def build_api_membership_on_establishment(
    establishment_membership: EstablishmentMembership,
    *,
    role=EstablishmentMembership.Role.STAFF,
) -> EstablishmentMembership:
    from houston.accounts.models import User

    user = User.objects.create_user(
        username=f"user_{uuid.uuid4().hex[:8]}",
        password=TEST_PASSWORD,
        status=User.Status.ACTIVE,
    )
    return EstablishmentMembership.objects.create(
        user=user,
        establishment=establishment_membership.establishment,
        role=role,
        status=EstablishmentMembership.Status.ACTIVE,
    )


def action_url(establishment_id, action_id, suffix: str = "") -> str:
    base = f"/api/v1/establishments/{establishment_id}/actions/{action_id}/"
    return base + suffix.lstrip("/")


def actions_url(establishment_id) -> str:
    return f"/api/v1/establishments/{establishment_id}/actions/"


def execution_feed_url(establishment_id) -> str:
    return f"/api/v1/establishments/{establishment_id}/execution-feed/"


def create_signal_for_membership(membership, *, status: str = Signal.Status.OPEN) -> Signal:
    module, domain, subject = create_taxonomy(membership.establishment)
    now = timezone.now()
    return Signal.objects.create(
        establishment=membership.establishment,
        operational_module=module,
        operational_domain=domain,
        operational_subject=subject,
        title="Signal title",
        structured_summary="Summary",
        status=status,
        last_activity_at=now,
    )


def assign_domain_scope(membership, domain) -> None:
    MembershipScope.objects.create(
        membership=membership,
        operational_domain=domain,
    )


def create_action_payload(
    *,
    membership: EstablishmentMembership,
    assigned_to: EstablishmentMembership | None = None,
    signal: Signal | None = None,
    module_key: str | None = None,
    domain_key: str | None = None,
    subject_key: str | None = None,
) -> dict:
    module, domain, subject = create_taxonomy(membership.establishment)
    due = timezone.now() + timezone.timedelta(days=1)
    payload = {
        "title": "Clean area",
        "instruction": "Mop the floor near the entrance.",
        "assigned_to": str((assigned_to or membership).id),
        "due_at": due.isoformat(),
        "module_key": module_key or module.key,
        "domain_key": domain_key or domain.key,
        "subject_key": subject_key or subject.key,
    }
    if signal is not None:
        payload["signal"] = str(signal.id)
    return payload


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient

    return APIClient(enforce_csrf_checks=True)
