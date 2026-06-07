from __future__ import annotations

import uuid

import pytest
from rest_framework.test import APIClient

from houston.accounts.models import User
from houston.establishments.catalog_import import sync_catalog_from_normalized_rows
from houston.establishments.models import (
    ActivitySubject,
    BusinessUnit,
    CatalogBusinessUnit,
    EstablishmentMembership,
    OnboardingProposal,
    OnboardingSession,
)
from houston.establishments.services import (
    OnboardingProposalValidationError,
    apply_onboarding_proposal,
    compute_activation_readiness,
    create_manual_onboarding_proposal,
    invite_director_during_onboarding,
    submit_manual_onboarding_proposal,
    update_onboarding_proposal_payload,
    validate_onboarding_proposal_payload,
)
from houston.establishments.tests.conftest import (
    MANUAL_V2_PROPOSAL_SCHEMA_VERSION,
    apply_validated_manual_v2_proposal,
    valid_manual_v2_payload,
)
from houston.establishments.tests.taxonomy_helpers import (
    assert_business_unit_scope_response,
    business_unit_scope_payload,
    create_business_unit,
)
from houston.establishments.tests.test_onboarding_proposal_api import (
    auth_headers,
    create_onboarding_session,
    create_user,
    ensure_csrf,
    login,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


@pytest.fixture
def imported_catalog():
    return sync_catalog_from_normalized_rows()


@pytest.fixture
def owner():
    return create_user(username=f"manual_v2_owner_{uuid.uuid4().hex[:8]}")


@pytest.fixture
def onboarding_session(owner):
    return create_onboarding_session(actor=owner)


def _invite_director(*, session: OnboardingSession, owner: User) -> None:
    invite_director_during_onboarding(
        session=session,
        actor=owner,
        email=f"director_{uuid.uuid4().hex[:6]}@example.com",
        first_name="Camille",
        last_name="Directeur",
    )


def test_manual_v2_creates_business_units(onboarding_session, owner, imported_catalog):
    apply_validated_manual_v2_proposal(session=onboarding_session, owner=owner)

    business_unit = BusinessUnit.objects.get(
        establishment=onboarding_session.establishment,
        key="coworking",
    )
    assert business_unit.label == "Coworking"
    assert business_unit.active is True


def test_manual_v2_persists_business_unit_description(onboarding_session, owner, imported_catalog):
    business_unit_client_key = str(uuid.uuid4())
    subject_client_key = str(uuid.uuid4())
    payload = valid_manual_v2_payload(
        business_units=[
            {
                "client_key": business_unit_client_key,
                "label": "Hébergement",
                "description": "  Chambres, étages et housekeeping  ",
                "unit_type": "dedicated",
                "catalog_key": "coworking",
            }
        ],
        activity_subjects=[
            {
                "client_key": subject_client_key,
                "label": "Propreté",
                "description": "",
                "business_unit_client_key": business_unit_client_key,
                "catalog_key": "coworking__proprete",
            }
        ],
    )

    proposal = create_manual_onboarding_proposal(
        session=onboarding_session,
        actor=owner,
        payload=payload,
    )
    submit_manual_onboarding_proposal(proposal=proposal, actor=owner)
    apply_onboarding_proposal(proposal=proposal, actor=owner)

    business_unit = BusinessUnit.objects.get(
        establishment=onboarding_session.establishment,
        key="hebergement",
    )
    assert business_unit.description == "Chambres, étages et housekeeping"


def test_manual_v2_persists_excluded_subject_keys(
    onboarding_session, owner, imported_catalog
):
    payload = valid_manual_v2_payload()
    business_unit_client_key = payload["business_units"][0]["client_key"]
    payload["excluded_catalog_subject_keys"] = {
        business_unit_client_key: ["wifi", "desk"],
    }

    proposal = create_manual_onboarding_proposal(
        session=onboarding_session,
        actor=owner,
        payload=payload,
    )

    assert proposal.payload["excluded_catalog_subject_keys"] == {
        business_unit_client_key: ["wifi", "desk"],
    }


def test_manual_v2_rejects_orphan_excluded_subject_keys(
    onboarding_session, owner, imported_catalog
):
    payload = valid_manual_v2_payload()
    payload["excluded_catalog_subject_keys"] = {
        str(uuid.uuid4()): ["wifi"],
    }

    with pytest.raises(OnboardingProposalValidationError) as exc_info:
        validate_onboarding_proposal_payload(payload)

    assert any(
        error.get("code") == "orphan_excluded_catalog_subject"
        for error in exc_info.value.errors
    )


def test_manual_v2_creates_activity_subjects(onboarding_session, owner, imported_catalog):
    apply_validated_manual_v2_proposal(session=onboarding_session, owner=owner)

    business_unit = BusinessUnit.objects.get(
        establishment=onboarding_session.establishment,
        key="coworking",
    )
    subject = ActivitySubject.objects.get(
        establishment=onboarding_session.establishment,
        business_unit=business_unit,
        normalized_name="proprete",
    )
    assert subject.label == "Propreté"
    assert subject.active is True


def test_catalog_selection_links_catalog_fk(onboarding_session, owner, imported_catalog):
    apply_validated_manual_v2_proposal(session=onboarding_session, owner=owner)

    business_unit = BusinessUnit.objects.get(
        establishment=onboarding_session.establishment,
        key="coworking",
    )
    catalog_business_unit = CatalogBusinessUnit.objects.get(key="coworking")
    assert business_unit.catalog_business_unit_id == catalog_business_unit.id
    assert business_unit.source == BusinessUnit.Source.CATALOG_SUGGESTION


def test_free_text_bu_without_catalog_fk(onboarding_session, owner):
    business_unit_client_key = str(uuid.uuid4())
    subject_client_key = str(uuid.uuid4())
    payload = valid_manual_v2_payload(
        business_units=[
            {
                "client_key": business_unit_client_key,
                "label": "Mon pôle custom",
                "description": "",
                "unit_type": "transversal",
                "catalog_key": None,
            }
        ],
        activity_subjects=[
            {
                "client_key": subject_client_key,
                "label": "Sujet libre",
                "description": "",
                "business_unit_client_key": business_unit_client_key,
                "catalog_key": None,
            }
        ],
    )

    apply_validated_manual_v2_proposal(
        session=onboarding_session,
        owner=owner,
        payload=payload,
    )

    business_unit = BusinessUnit.objects.get(
        establishment=onboarding_session.establishment,
        key="mon_pole_custom",
    )
    assert business_unit.catalog_business_unit_id is None
    assert business_unit.source == BusinessUnit.Source.MANUAL


def test_default_unit_type_is_suggestion_only(onboarding_session, owner, imported_catalog):
    business_unit_client_key = str(uuid.uuid4())
    subject_client_key = str(uuid.uuid4())
    payload = valid_manual_v2_payload(
        business_units=[
            {
                "client_key": business_unit_client_key,
                "label": "Maintenance",
                "description": "",
                "unit_type": "dedicated",
                "catalog_key": "maintenance",
            }
        ],
        activity_subjects=[
            {
                "client_key": subject_client_key,
                "label": "Intervention",
                "description": "",
                "business_unit_client_key": business_unit_client_key,
                "catalog_key": None,
            }
        ],
    )

    apply_validated_manual_v2_proposal(
        session=onboarding_session,
        owner=owner,
        payload=payload,
    )

    business_unit = BusinessUnit.objects.get(
        establishment=onboarding_session.establishment,
        key="maintenance",
    )
    catalog_row = CatalogBusinessUnit.objects.get(key="maintenance")
    assert catalog_row.default_unit_type == CatalogBusinessUnit.DefaultUnitType.TRANSVERSAL
    assert business_unit.unit_type == BusinessUnit.UnitType.DEDICATED


def test_client_key_stable_when_label_changes(onboarding_session, owner):
    business_unit_client_key = str(uuid.uuid4())
    subject_client_key = str(uuid.uuid4())
    payload = {
        "schema_version": MANUAL_V2_PROPOSAL_SCHEMA_VERSION,
        "business_units": [
            {
                "client_key": business_unit_client_key,
                "label": "Nom initial",
                "description": "",
                "unit_type": "dedicated",
                "catalog_key": None,
            }
        ],
        "activity_subjects": [
            {
                "client_key": subject_client_key,
                "label": "Sujet A",
                "description": "",
                "business_unit_client_key": business_unit_client_key,
                "catalog_key": None,
            }
        ],
    }
    validate_onboarding_proposal_payload(payload)

    payload["business_units"][0]["label"] = "Nom modifié"
    validate_onboarding_proposal_payload(payload)
    assert (
        payload["activity_subjects"][0]["business_unit_client_key"] == business_unit_client_key
    )


def test_remove_proposed_subject_before_submit(onboarding_session, owner):
    business_unit_client_key = str(uuid.uuid4())
    payload = {
        "schema_version": MANUAL_V2_PROPOSAL_SCHEMA_VERSION,
        "business_units": [
            {
                "client_key": business_unit_client_key,
                "label": "Pôle A",
                "description": "",
                "unit_type": "dedicated",
                "catalog_key": None,
            }
        ],
        "activity_subjects": [
            {
                "client_key": str(uuid.uuid4()),
                "label": "Sujet gardé",
                "description": "",
                "business_unit_client_key": business_unit_client_key,
                "catalog_key": None,
            },
            {
                "client_key": str(uuid.uuid4()),
                "label": "Sujet retiré",
                "description": "",
                "business_unit_client_key": business_unit_client_key,
                "catalog_key": None,
            },
        ],
    }
    proposal = create_manual_onboarding_proposal(
        session=onboarding_session,
        actor=owner,
        payload=payload,
    )
    payload["activity_subjects"] = [payload["activity_subjects"][0]]
    proposal = update_onboarding_proposal_payload(
        proposal=proposal,
        actor=owner,
        payload=payload,
    )
    proposal = submit_manual_onboarding_proposal(proposal=proposal, actor=owner)

    assert proposal.status == OnboardingProposal.Status.VALIDATED
    assert len(proposal.payload["activity_subjects"]) == 1


def test_activation_blocked_without_business_unit(onboarding_session, owner, imported_catalog):
    apply_validated_manual_v2_proposal(session=onboarding_session, owner=owner)
    _invite_director(session=onboarding_session, owner=owner)
    BusinessUnit.objects.filter(establishment=onboarding_session.establishment).update(
        active=False
    )

    readiness = compute_activation_readiness(session=onboarding_session)

    assert readiness["is_ready"] is False
    assert any(
        blocker["code"] == "missing_active_business_unit" for blocker in readiness["blockers"]
    )


def test_activation_blocked_bu_without_subject(onboarding_session, owner, imported_catalog):
    apply_validated_manual_v2_proposal(session=onboarding_session, owner=owner)
    _invite_director(session=onboarding_session, owner=owner)
    ActivitySubject.objects.filter(establishment=onboarding_session.establishment).update(
        active=False
    )

    readiness = compute_activation_readiness(session=onboarding_session)

    assert readiness["is_ready"] is False
    assert any(
        blocker["code"] == "business_units_without_active_subjects"
        for blocker in readiness["blockers"]
    )


def test_activation_ready_after_manual_v2_apply_and_director_invite(
    onboarding_session,
    owner,
    imported_catalog,
):
    apply_validated_manual_v2_proposal(session=onboarding_session, owner=owner)
    _invite_director(session=onboarding_session, owner=owner)

    readiness = compute_activation_readiness(session=onboarding_session)

    assert readiness["is_ready"] is True
    assert readiness["blockers"] == []
    assert "activation_mode" not in readiness


def test_activation_ready_with_manual_business_units_without_legacy_modules(
    onboarding_session,
    owner,
):
    business_unit = create_business_unit(
        establishment=onboarding_session.establishment,
        key="hotel",
        label="Hotel",
    )
    ActivitySubject.objects.create(
        establishment=onboarding_session.establishment,
        business_unit=business_unit,
        normalized_name="proprete",
        label="Propreté",
        active=True,
    )
    _invite_director(session=onboarding_session, owner=owner)

    readiness = compute_activation_readiness(session=onboarding_session)
    assert readiness["is_ready"] is True


def test_post_create_manual_v2_proposal_api(
    api_client,
    onboarding_session,
    owner,
    imported_catalog,
):
    access_token = login(api_client, user=owner)
    csrf_token = ensure_csrf(api_client)
    response = api_client.post(
        f"/api/v1/onboarding-sessions/{onboarding_session.id}/proposals/",
        {"payload": valid_manual_v2_payload()},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
        **auth_headers(access_token),
    )

    assert response.status_code == 201, response.json()
    body = response.json()
    assert body["proposal"]["payload"]["schema_version"] == MANUAL_V2_PROPOSAL_SCHEMA_VERSION


def test_director_cannot_create_manual_v2_proposal_on_draft(
    api_client,
    onboarding_session,
    owner,
    imported_catalog,
):
    director = create_user(username="manual_v2_director_blocked")
    EstablishmentMembership.objects.create(
        user=director,
        establishment=onboarding_session.establishment,
        role=EstablishmentMembership.Role.DIRECTOR,
        status=EstablishmentMembership.Status.ACTIVE,
    )

    access_token = login(api_client, user=director)
    csrf_token = ensure_csrf(api_client)
    response = api_client.post(
        f"/api/v1/onboarding-sessions/{onboarding_session.id}/proposals/",
        {"payload": valid_manual_v2_payload()},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
        **auth_headers(access_token),
    )

    assert response.status_code == 403


def test_submit_and_apply_manual_v2_proposal_api(
    api_client,
    onboarding_session,
    owner,
    imported_catalog,
):
    access_token = login(api_client, user=owner)
    csrf_token = ensure_csrf(api_client)

    create_response = api_client.post(
        f"/api/v1/onboarding-sessions/{onboarding_session.id}/proposals/",
        {"payload": valid_manual_v2_payload()},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
        **auth_headers(access_token),
    )
    proposal_id = create_response.json()["proposal"]["id"]

    submit_response = api_client.post(
        f"/api/v1/onboarding-sessions/{onboarding_session.id}/proposals/{proposal_id}/submit/",
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
        **auth_headers(access_token),
    )
    assert submit_response.status_code == 200
    assert submit_response.json()["proposal"]["status"] == "validated"

    apply_response = api_client.post(
        f"/api/v1/onboarding-sessions/{onboarding_session.id}/proposals/{proposal_id}/apply/",
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
        **auth_headers(access_token),
    )
    assert apply_response.status_code == 200
    assert BusinessUnit.objects.filter(
        establishment=onboarding_session.establishment,
        active=True,
    ).exists()


def test_invitation_manager_with_bu_scopes_after_manual_v2_apply(
    api_client,
    onboarding_session,
    owner,
    imported_catalog,
):
    apply_validated_manual_v2_proposal(session=onboarding_session, owner=owner)
    business_unit = BusinessUnit.objects.get(
        establishment=onboarding_session.establishment,
        key="coworking",
    )

    access_token = login(api_client, user=owner)
    csrf_token = ensure_csrf(api_client)
    response = api_client.post(
        f"/api/v1/establishments/{onboarding_session.establishment_id}/membership-invitations/",
        {
            "email": "manager@example.com",
            "first_name": "Marie",
            "last_name": "Manager",
            "role": EstablishmentMembership.Role.MANAGER,
            "scopes": [business_unit_scope_payload(business_unit)],
        },
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
        **auth_headers(access_token),
    )

    assert response.status_code == 201
    assert_business_unit_scope_response(response.json()["membership"], business_unit=business_unit)
