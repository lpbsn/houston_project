from __future__ import annotations

import uuid

import pytest
from rest_framework.test import APIClient

from houston.establishments.catalog_import import sync_catalog_from_normalized_rows
from houston.establishments.models import (
    ActivitySubject,
    BusinessUnit,
    EstablishmentMembership,
    OnboardingProposal,
)
from houston.establishments.services import create_manual_onboarding_proposal
from houston.establishments.tests.conftest import valid_manual_v2_payload
from houston.testing.auth import auth_headers, login
from houston.testing.factories import create_user
from houston.testing.onboarding import create_onboarding_session

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


@pytest.fixture(autouse=True)
def imported_catalog():
    return sync_catalog_from_normalized_rows()


def test_proposal_endpoints_require_authentication(api_client):
    session_id = uuid.uuid4()
    proposal_id = uuid.uuid4()
    responses = [
        api_client.get(f"/api/v1/onboarding-sessions/{session_id}/proposals/"),
        api_client.get(
            f"/api/v1/onboarding-sessions/{session_id}/proposals/{proposal_id}/",
        ),
        api_client.post(
            f"/api/v1/onboarding-sessions/{session_id}/proposals/{proposal_id}/submit/",
            format="json",
        ),
        api_client.post(
            f"/api/v1/onboarding-sessions/{session_id}/proposals/{proposal_id}/reject/",
            format="json",
        ),
        api_client.post(
            f"/api/v1/onboarding-sessions/{session_id}/proposals/{proposal_id}/apply/",
            format="json",
        ),
    ]
    assert {response.status_code for response in responses} == {401}


def test_owner_can_list_and_retrieve_v3_proposals(api_client):
    owner = create_user(username="proposal_api_owner")
    session = create_onboarding_session(actor=owner)
    proposal = create_manual_onboarding_proposal(
        session=session,
        actor=owner,
        payload=valid_manual_v2_payload(),
    )

    access_token = login(api_client, user=owner)
    list_response = api_client.get(
        f"/api/v1/onboarding-sessions/{session.id}/proposals/",
        **auth_headers(access_token),
    )
    detail_response = api_client.get(
        f"/api/v1/onboarding-sessions/{session.id}/proposals/{proposal.id}/",
        **auth_headers(access_token),
    )

    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [str(proposal.id)]
    assert detail_response.status_code == 200
    body = detail_response.json()
    assert body["id"] == str(proposal.id)
    assert body["source"] == OnboardingProposal.Source.MANUAL
    assert body["payload"]["schema_version"] == "onboarding_proposal_v3"


def test_manager_and_staff_are_denied_for_proposal_endpoints(api_client):
    owner = create_user(username="proposal_api_non_owner")
    manager = create_user(username="proposal_api_manager")
    staff = create_user(username="proposal_api_staff")
    session = create_onboarding_session(actor=owner)
    proposal = create_manual_onboarding_proposal(
        session=session,
        actor=owner,
        payload=valid_manual_v2_payload(),
    )
    EstablishmentMembership.objects.create(
        user=manager,
        establishment=session.establishment,
        role=EstablishmentMembership.Role.MANAGER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    EstablishmentMembership.objects.create(
        user=staff,
        establishment=session.establishment,
        role=EstablishmentMembership.Role.STAFF,
        status=EstablishmentMembership.Status.ACTIVE,
    )

    for actor in (manager, staff):
        access_token = login(api_client, user=actor)
        list_response = api_client.get(
            f"/api/v1/onboarding-sessions/{session.id}/proposals/",
            **auth_headers(access_token),
        )
        submit_response = api_client.post(
            f"/api/v1/onboarding-sessions/{session.id}/proposals/{proposal.id}/submit/",
            format="json",
            **auth_headers(access_token),
        )
        assert list_response.status_code == 403
        assert submit_response.status_code == 403


def test_foreign_session_and_mismatched_proposal_are_denied(api_client):
    actor = create_user(username="proposal_api_foreign_actor")
    owner = create_user(username="proposal_api_foreign_owner")
    actor_session = create_onboarding_session(actor=actor)
    foreign_session = create_onboarding_session(actor=owner)
    foreign_proposal = create_manual_onboarding_proposal(
        session=foreign_session,
        actor=owner,
        payload=valid_manual_v2_payload(),
    )

    access_token = login(api_client, user=actor)
    foreign_response = api_client.get(
        f"/api/v1/onboarding-sessions/{foreign_session.id}/proposals/",
        **auth_headers(access_token),
    )
    mismatched_response = api_client.get(
        f"/api/v1/onboarding-sessions/{actor_session.id}/proposals/{foreign_proposal.id}/",
        **auth_headers(access_token),
    )
    assert foreign_response.status_code == 404
    assert mismatched_response.status_code == 404


def test_reject_does_not_mutate_runtime(api_client):
    owner = create_user(username="proposal_api_reject_owner")
    session = create_onboarding_session(actor=owner)
    proposal = create_manual_onboarding_proposal(
        session=session,
        actor=owner,
        payload=valid_manual_v2_payload(),
    )

    access_token = login(api_client, user=owner)
    response = api_client.post(
        f"/api/v1/onboarding-sessions/{session.id}/proposals/{proposal.id}/reject/",
        format="json",
        **auth_headers(access_token),
    )
    assert response.status_code == 200
    assert response.json()["proposal"]["status"] == OnboardingProposal.Status.REJECTED
    assert BusinessUnit.objects.filter(establishment=session.establishment).count() == 0
    assert ActivitySubject.objects.filter(establishment=session.establishment).count() == 0


def test_apply_requires_validated_proposal(api_client):
    owner = create_user(username="proposal_api_apply_unvalidated_owner")
    session = create_onboarding_session(actor=owner)
    proposal = create_manual_onboarding_proposal(
        session=session,
        actor=owner,
        payload=valid_manual_v2_payload(),
    )

    access_token = login(api_client, user=owner)
    response = api_client.post(
        f"/api/v1/onboarding-sessions/{session.id}/proposals/{proposal.id}/apply/",
        format="json",
        **auth_headers(access_token),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "invalid_onboarding_proposal_state"
