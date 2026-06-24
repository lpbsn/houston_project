from __future__ import annotations

import uuid

import pytest
from rest_framework.test import APIClient

from houston.establishments.services import create_manual_onboarding_proposal
from houston.establishments.tests.conftest import valid_manual_v2_payload
from houston.establishments.tests.taxonomy_helpers import (
    business_unit_scope_payload,
    create_business_unit,
)
from houston.testing.auth import auth_headers, login
from houston.testing.factories import create_user
from houston.testing.onboarding import create_onboarding_session

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("imported_catalog")]

_MINIMAL_DESCRIPTION = {"description": "A" * 80}
_MINIMAL_PROPOSAL = {"payload": valid_manual_v2_payload()}
_MINIMAL_DIRECTOR_INVITE = {
    "email": "director@example.com",
    "first_name": "Dir",
    "last_name": "Ector",
}


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


@pytest.fixture
def foreign_access():
    actor = create_user(username=f"iso_actor_{uuid.uuid4().hex[:8]}")
    foreign_actor = create_user(username=f"iso_foreign_{uuid.uuid4().hex[:8]}")
    create_onboarding_session(actor=actor)
    foreign_session = create_onboarding_session(actor=foreign_actor)
    foreign_proposal = create_manual_onboarding_proposal(
        session=foreign_session,
        actor=foreign_actor,
        payload=valid_manual_v2_payload(),
    )
    foreign_business_unit = create_business_unit(
        establishment=foreign_session.establishment,
        key="iso_bu",
        label="Isolation BU",
    )
    return {
        "actor": actor,
        "foreign_session": foreign_session,
        "foreign_proposal": foreign_proposal,
        "foreign_business_unit": foreign_business_unit,
        "token": None,
    }


@pytest.fixture
def actor_token(api_client, foreign_access):
    foreign_access["token"] = login(api_client, user=foreign_access["actor"])
    return foreign_access["token"]


def _session_url(session_id: uuid.UUID, suffix: str = "") -> str:
    base = f"/api/v1/onboarding-sessions/{session_id}/"
    if suffix:
        return f"{base}{suffix}"
    return base


@pytest.mark.parametrize(
    "suffix",
    [
        "",
        "runtime-config/",
        "activation-summary/",
        "proposals/",
    ],
)
def test_foreign_onboarding_session_get_endpoints_return_404(
    api_client,
    foreign_access,
    actor_token,
    suffix,
):
    session = foreign_access["foreign_session"]
    response = api_client.get(
        _session_url(session.id, suffix),
        **auth_headers(actor_token),
    )
    assert response.status_code == 404


@pytest.mark.parametrize(
    ("method", "suffix", "payload"),
    [
        ("patch", "description/", _MINIMAL_DESCRIPTION),
        ("post", "director-invitations/", _MINIMAL_DIRECTOR_INVITE),
        ("post", "mark-ready/", {}),
        ("post", "activate/", {}),
        ("post", "proposals/", _MINIMAL_PROPOSAL),
    ],
)
def test_foreign_onboarding_session_mutations_return_404(
    api_client,
    foreign_access,
    actor_token,
    method,
    suffix,
    payload,
):
    session = foreign_access["foreign_session"]
    url = _session_url(session.id, suffix)
    request = getattr(api_client, method)
    response = request(url, payload, format="json", **auth_headers(actor_token))
    assert response.status_code == 404


@pytest.mark.parametrize(
    "action_suffix",
    [
        "submit/",
        "reject/",
        "apply/",
    ],
)
def test_foreign_onboarding_proposal_mutations_return_404(
    api_client,
    foreign_access,
    actor_token,
    action_suffix,
):
    session = foreign_access["foreign_session"]
    proposal = foreign_access["foreign_proposal"]
    url = _session_url(session.id, f"proposals/{proposal.id}/{action_suffix}")
    response = api_client.post(url, {}, format="json", **auth_headers(actor_token))
    assert response.status_code == 404


def test_foreign_onboarding_proposal_detail_returns_404(
    api_client,
    foreign_access,
    actor_token,
):
    session = foreign_access["foreign_session"]
    proposal = foreign_access["foreign_proposal"]
    response = api_client.get(
        _session_url(session.id, f"proposals/{proposal.id}/"),
        **auth_headers(actor_token),
    )
    assert response.status_code == 404


def test_foreign_establishment_membership_invitation_returns_404(
    api_client,
    foreign_access,
    actor_token,
):
    foreign_establishment_id = foreign_access["foreign_session"].establishment_id
    response = api_client.post(
        f"/api/v1/establishments/{foreign_establishment_id}/membership-invitations/",
        {
            "email": "staff@example.com",
            "first_name": "Staff",
            "last_name": "Member",
            "role": "staff",
            "scopes": [business_unit_scope_payload(foreign_access["foreign_business_unit"])],
        },
        format="json",
        **auth_headers(actor_token),
    )
    assert response.status_code == 404


def test_mismatched_proposal_id_on_actor_session_returns_404(
    api_client,
    foreign_access,
    actor_token,
):
    actor_session = create_onboarding_session(actor=foreign_access["actor"])
    foreign_proposal = foreign_access["foreign_proposal"]
    response = api_client.get(
        _session_url(actor_session.id, f"proposals/{foreign_proposal.id}/"),
        **auth_headers(actor_token),
    )
    assert response.status_code == 404
