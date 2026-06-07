from __future__ import annotations

import uuid

import pytest
from django.utils import timezone

from houston.establishments.models import (
    ActivitySubject,
    BusinessUnit,
    EstablishmentMembership,
    MembershipScope,
)
from houston.establishments.tests.conftest import TEST_PASSWORD
from houston.establishments.tests.taxonomy_helpers import (
    create_membership_with_business_unit_scope,
)
from houston.establishments.tests.test_permissions import build_membership
from houston.signals.models import Signal
from houston.signals.tests.conftest import auth_headers, login

__all__ = [
    "auth_headers",
    "login",
    "build_api_membership",
    "build_api_membership_on_establishment",
    "action_url",
    "actions_url",
    "execution_feed_url",
    "create_signal_v3_for_membership",
    "assign_business_unit_scope",
    "create_linked_action_payload",
    "create_free_action_payload",
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


def assign_business_unit_scope(
    membership: EstablishmentMembership,
    business_unit: BusinessUnit,
) -> MembershipScope:
    return create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=business_unit,
    )


def create_signal_v3_for_membership(
    membership: EstablishmentMembership,
    *,
    affected_business_unit: BusinessUnit,
    responsible_business_unit: BusinessUnit,
    activity_subject: ActivitySubject,
    status: str = Signal.Status.OPEN,
    title: str = "Signal title",
    location_text: str = "chambre 102",
) -> Signal:
    now = timezone.now()
    return Signal.objects.create(
        establishment=membership.establishment,
        affected_business_unit=affected_business_unit,
        responsible_business_unit=responsible_business_unit,
        activity_subject=activity_subject,
        title=title,
        structured_summary="Summary",
        location_text=location_text,
        status=status,
        last_activity_at=now,
    )


def create_linked_action_payload(
    *,
    membership: EstablishmentMembership,
    signal: Signal,
    assigned_to: EstablishmentMembership | None = None,
    title: str = "Clean area",
    instruction: str = "Mop the floor near the entrance.",
) -> dict:
    due = timezone.now() + timezone.timedelta(days=1)
    return {
        "title": title,
        "instruction": instruction,
        "assigned_to": str((assigned_to or membership).id),
        "due_at": due.isoformat(),
        "signal": str(signal.id),
    }


def create_free_action_payload(
    *,
    membership: EstablishmentMembership,
    responsible_business_unit: BusinessUnit,
    assigned_to: EstablishmentMembership | None = None,
    title: str = "Routine check",
    instruction: str = "Inspect the storage area.",
) -> dict:
    due = timezone.now() + timezone.timedelta(days=1)
    return {
        "title": title,
        "instruction": instruction,
        "assigned_to": str((assigned_to or membership).id),
        "due_at": due.isoformat(),
        "signal": None,
        "responsible_business_unit_id": str(responsible_business_unit.id),
    }


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient

    return APIClient(enforce_csrf_checks=True)
