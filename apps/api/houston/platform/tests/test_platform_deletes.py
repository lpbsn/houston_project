from __future__ import annotations

from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from houston.accounts.models import User
from houston.establishments.models import Establishment, EstablishmentMembership
from houston.organizations.models import Organization
from houston.platform.delete_services import delete_platform_establishment
from houston.platform.exceptions import PlatformLifecycleDenied
from houston.platform.models import PlatformLifecycleEvent
from houston.testing.auth import auth_headers, login
from houston.testing.factories import create_user
from houston.testing.platform import grant_operator

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


def _start_draft(api_client, token):
    created = api_client.post(
        "/api/v1/platform/onboardings/",
        {"organization_name": "Delete Org", "establishment_name": "Delete Site"},
        format="json",
        **auth_headers(token),
    )
    assert created.status_code == 201
    return created.json()


def test_delete_eligibility_failure_inside_mutate_rolls_back_and_audits_denied():
    operator = create_user(username="plat_del_atomic_op")
    grant_operator(operator)
    organization = Organization.objects.create(name="Atomic Org")
    establishment = Establishment.objects.create(
        name="Atomic Site",
        organization=organization,
        status=Establishment.Status.DRAFT,
    )

    def boom(locked):
        Organization.objects.create(name="partial-delete-side-effect")
        return ["establishment_not_draft"]

    with patch(
        "houston.platform.delete_services.establishment_delete_blocking_reasons",
        side_effect=boom,
    ):
        with pytest.raises(PlatformLifecycleDenied) as exc:
            delete_platform_establishment(
                operator=operator,
                establishment=establishment,
                justification="attempted cleanup",
            )
    assert exc.value.code == "establishment_not_deletable"
    assert Establishment.objects.filter(pk=establishment.pk).exists()
    assert Organization.objects.filter(name="partial-delete-side-effect").count() == 0
    event = PlatformLifecycleEvent.objects.get(action="delete_establishment")
    assert event.result == PlatformLifecycleEvent.Result.DENIED
    assert event.error_code == "establishment_not_deletable"


def test_delete_denied_when_establishment_no_longer_draft_does_not_use_can_delete_hint(
    api_client,
):
    operator = create_user(username="plat_del_status_op")
    grant_operator(operator)
    token = login(api_client, user=operator)
    body = _start_draft(api_client, token)
    establishment_id = body["establishment_id"]

    hint = api_client.get(
        f"/api/v1/platform/establishments/{establishment_id}/",
        **auth_headers(token),
    )
    assert hint.status_code == 200
    assert hint.json()["can_delete"] is True

    establishment = Establishment.objects.get(pk=establishment_id)
    establishment.status = Establishment.Status.ACTIVE
    establishment.save(update_fields=["status", "updated_at"])

    detail = api_client.get(
        f"/api/v1/platform/establishments/{establishment_id}/",
        **auth_headers(token),
    )
    assert detail.status_code == 200
    assert detail.json()["can_delete"] is False

    denied = api_client.post(
        f"/api/v1/platform/establishments/{establishment_id}/delete/",
        {"justification": "stale can_delete hint"},
        format="json",
        **auth_headers(token),
    )
    assert denied.status_code == 409
    assert denied.json()["code"] == "establishment_not_deletable"
    assert Establishment.objects.filter(pk=establishment_id).exists()
    event = PlatformLifecycleEvent.objects.get(action="delete_establishment")
    assert event.result == PlatformLifecycleEvent.Result.DENIED


def test_deleting_establishment_does_not_delete_users(api_client):
    operator = create_user(username="plat_del_users_op")
    grant_operator(operator)
    token = login(api_client, user=operator)
    body = _start_draft(api_client, token)
    establishment_id = body["establishment_id"]
    member = create_user(username="kept_after_est_delete")
    EstablishmentMembership.objects.create(
        user=member,
        establishment_id=establishment_id,
        role=EstablishmentMembership.Role.STAFF,
        status=EstablishmentMembership.Status.ACTIVE,
    )

    deleted = api_client.post(
        f"/api/v1/platform/establishments/{establishment_id}/delete/",
        {"justification": "abandoned draft"},
        format="json",
        **auth_headers(token),
    )
    assert deleted.status_code == 204
    assert not Establishment.objects.filter(pk=establishment_id).exists()
    assert User.objects.filter(pk=member.pk).exists()
    assert User.objects.filter(pk=operator.pk).exists()
