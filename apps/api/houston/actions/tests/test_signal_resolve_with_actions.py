from __future__ import annotations

import pytest
from django.utils import timezone

from houston.actions.services import accept_action, create_action
from houston.actions.tests.conftest import (
    build_api_membership,
    build_api_membership_on_establishment,
    create_signal_for_membership,
    create_taxonomy,
)
from houston.establishments.models import EstablishmentMembership
from houston.signals.models import Signal
from houston.signals.tests.conftest import auth_headers, login, signal_detail_url

pytestmark = pytest.mark.django_db


def test_resolve_signal_blocked_with_active_linked_action(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    signal = create_signal_for_membership(owner, status=Signal.Status.IN_PROGRESS)
    module, domain, subject = create_taxonomy(owner.establishment)
    action = create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Linked",
        instruction="Work",
        assigned_to_id=staff.id,
        due_at=timezone.now() + timezone.timedelta(days=1),
        module_key=module.key,
        domain_key=domain.key,
        subject_key=subject.key,
        signal_id=signal.id,
    )
    accept_action(action=action)

    token = login(api_client, user=owner.user)
    response = api_client.post(
        signal_detail_url(owner.establishment_id, signal.id) + "resolve/",
        **auth_headers(token),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "business_conflict"
