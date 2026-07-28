from __future__ import annotations

import uuid

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from houston.core.exceptions import DomainConflictError, DomainValidationError
from houston.establishments.models import (
    ACTIVITY_DESCRIPTION_MAX_LENGTH,
    ACTIVITY_DESCRIPTION_MIN_LENGTH,
    BusinessUnit,
    Establishment,
    EstablishmentActivityDescription,
    EstablishmentMembership,
    OnboardingDraft,
    OnboardingProposal,
    OnboardingSession,
)
from houston.establishments.onboarding_draft import (
    empty_onboarding_draft_payload,
    validate_onboarding_draft_payload,
)
from houston.establishments.services import (
    OnboardingDraftNotFoundError,
    OnboardingDraftValidationError,
    OnboardingRuntimeAlreadyMaterializedError,
    OnboardingSessionTerminalError,
    activate_onboarding_session,
    complete_onboarding_session,
    compute_activation_readiness,
    ensure_onboarding_draft_for_session,
    get_onboarding_draft,
    invite_director_during_onboarding,
    start_onboarding_session,
    upsert_onboarding_draft,
)
from houston.testing.auth import auth_headers, login
from houston.testing.factories import create_membership, create_user
from houston.testing.onboarding import create_onboarding_session, create_ready_runtime
from houston.testing.taxonomy import create_business_unit

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


def _valid_complete_payload(*, establishment_name: str) -> dict:
    bu_key = str(uuid.uuid4())
    subject_key = str(uuid.uuid4())
    return {
        "current_step": "team",
        "establishment": {
            "name": establishment_name,
            "description": "D" * ACTIVITY_DESCRIPTION_MIN_LENGTH,
        },
        "business_units": [
            {
                "client_key": bu_key,
                "catalog_key": "coworking",
                "specific_name": "Coworking Nord",
                "instance_description": "",
            }
        ],
        "activity_subjects": [
            {
                "client_key": subject_key,
                "business_unit_client_key": bu_key,
                "catalog_key": "coworking__proprete",
                "label": "",
                "description": "",
            }
        ],
        "team": {
            "director": {
                "email": f"director_{uuid.uuid4().hex[:8]}@example.com",
                "first_name": "Dir",
                "last_name": "Ector",
            },
            "members": [
                {
                    "email": f"manager_{uuid.uuid4().hex[:8]}@example.com",
                    "first_name": "Man",
                    "last_name": "Ager",
                    "role": "manager",
                    "business_unit_client_keys": [bu_key],
                }
            ],
        },
    }


def test_start_onboarding_session_creates_draft_skeleton(imported_catalog):
    owner = create_user(username="draft_start_owner")
    session = create_onboarding_session(actor=owner)
    # recreate via start to exercise service path on existing session
    started = start_onboarding_session(
        organization=session.organization,
        establishment=session.establishment,
        started_by=owner,
    )
    draft = get_onboarding_draft(session=started)
    assert draft.payload["current_step"] == "structure"
    assert draft.payload["business_units"] == []
    assert OnboardingDraft.objects.filter(onboarding_session=started).count() == 1


def test_ensure_skips_draft_when_business_unit_exists(imported_catalog):
    owner = create_user(username="draft_skip_bu_owner")
    session = create_onboarding_session(actor=owner)
    OnboardingDraft.objects.filter(onboarding_session=session).delete()
    create_business_unit(establishment=session.establishment, key="coworking")
    assert ensure_onboarding_draft_for_session(session=session) is None
    assert not OnboardingDraft.objects.filter(onboarding_session=session).exists()


def test_upsert_draft_soft_persists_incomplete(imported_catalog):
    owner = create_user(username="draft_upsert_owner")
    session = create_onboarding_session(actor=owner)
    payload = empty_onboarding_draft_payload()
    payload["establishment"] = {"name": "Temp Name", "description": ""}
    result = upsert_onboarding_draft(session=session, actor=owner, payload=payload)
    assert result["payload"]["establishment"]["name"] == "Temp Name"
    assert result["validation"]["is_ready_for_complete"] is False
    assert any(
        error["code"] == "invalid_activity_description_length"
        for error in result["validation"]["errors"]
    )


def test_draft_api_get_put_complete_happy_path(imported_catalog, api_client):
    owner = create_user(username="draft_api_owner")
    session = create_onboarding_session(actor=owner)
    access_token = login(api_client, user=owner)
    headers = auth_headers(access_token)

    get_response = api_client.get(
        f"/api/v1/onboarding-sessions/{session.id}/draft/",
        **headers,
    )
    assert get_response.status_code == 200
    assert get_response.json()["payload"]["current_step"] == "structure"

    payload = _valid_complete_payload(establishment_name=session.establishment.name)
    put_response = api_client.put(
        f"/api/v1/onboarding-sessions/{session.id}/draft/",
        {"payload": payload},
        format="json",
        **headers,
    )
    assert put_response.status_code == 200
    assert put_response.json()["validation"]["is_ready_for_complete"] is True

    complete_response = api_client.post(
        f"/api/v1/onboarding-sessions/{session.id}/complete/",
        format="json",
        **headers,
    )
    assert complete_response.status_code == 200, complete_response.content
    body = complete_response.json()
    assert body["activated"] is True
    assert body["idempotent"] is False

    session.refresh_from_db()
    assert session.status == OnboardingSession.Status.ACTIVATED
    assert session.establishment.status == Establishment.Status.ACTIVE
    assert not OnboardingDraft.objects.filter(onboarding_session=session).exists()
    assert BusinessUnit.objects.filter(establishment=session.establishment).count() == 1
    assert EstablishmentMembership.objects.filter(
        establishment=session.establishment,
        role=EstablishmentMembership.Role.DIRECTOR,
    ).exists()
    assert EstablishmentMembership.objects.filter(
        establishment=session.establishment,
        role=EstablishmentMembership.Role.MANAGER,
    ).exists()

    retry = api_client.post(
        f"/api/v1/onboarding-sessions/{session.id}/complete/",
        format="json",
        **headers,
    )
    assert retry.status_code == 200
    assert retry.json()["idempotent"] is True
    assert BusinessUnit.objects.filter(establishment=session.establishment).count() == 1


def test_complete_rejects_when_any_business_unit_exists(imported_catalog):
    owner = create_user(username="draft_complete_bu_owner")
    session = create_onboarding_session(actor=owner)
    bu = create_business_unit(
        establishment=session.establishment,
        key="coworking",
    )
    bu.active = False
    bu.save(update_fields=["active", "updated_at"])
    draft = get_onboarding_draft(session=session)
    draft.payload = _valid_complete_payload(establishment_name=session.establishment.name)
    draft.save(update_fields=["payload", "updated_at"])

    with pytest.raises(OnboardingRuntimeAlreadyMaterializedError):
        complete_onboarding_session(session=session, actor=owner)

    assert BusinessUnit.objects.filter(establishment=session.establishment).count() == 1


def test_complete_validation_failure_creates_no_runtime(imported_catalog):
    owner = create_user(username="draft_complete_invalid_owner")
    session = create_onboarding_session(actor=owner)
    draft = get_onboarding_draft(session=session)
    draft.payload = empty_onboarding_draft_payload()
    draft.save(update_fields=["payload", "updated_at"])

    with pytest.raises(OnboardingDraftValidationError):
        complete_onboarding_session(session=session, actor=owner)

    assert BusinessUnit.objects.filter(establishment=session.establishment).count() == 0
    assert session.establishment.status == Establishment.Status.DRAFT


def test_readiness_requires_description(imported_catalog):
    owner = create_user(username="draft_ready_desc_owner")
    session = create_onboarding_session(actor=owner)
    readiness = compute_activation_readiness(session=session)
    assert any(
        blocker["code"] == "missing_or_invalid_activity_description"
        for blocker in readiness["blockers"]
    )

    EstablishmentActivityDescription.objects.create(
        establishment=session.establishment,
        description="A" * ACTIVITY_DESCRIPTION_MIN_LENGTH,
        submitted_by=owner,
        validated_at=timezone.now(),
    )
    readiness = compute_activation_readiness(session=session)
    assert all(
        blocker["code"] != "missing_or_invalid_activity_description"
        for blocker in readiness["blockers"]
    )


def test_description_max_length_enforced():
    _payload, errors = validate_onboarding_draft_payload(
        {
            **empty_onboarding_draft_payload(),
            "establishment": {
                "name": "Site",
                "description": "A" * (ACTIVITY_DESCRIPTION_MAX_LENGTH + 1),
            },
        },
        mode="soft",
    )
    assert any(error["code"] == "invalid_activity_description_length" for error in errors)


def test_get_draft_404_when_missing(imported_catalog):
    owner = create_user(username="draft_missing_owner")
    session = create_onboarding_session(actor=owner)
    OnboardingDraft.objects.filter(onboarding_session=session).delete()
    with pytest.raises(OnboardingDraftNotFoundError):
        get_onboarding_draft(session=session)


def test_seed_onboarding_drafts_preserves_business_data_and_skips_runtime(imported_catalog):
    import importlib

    from django.apps import apps

    seed_module = importlib.import_module(
        "houston.establishments.migrations.0030_seed_onboarding_drafts"
    )

    owner = create_user(username="draft_mig_owner")
    eligible = create_onboarding_session(actor=owner)
    OnboardingDraft.objects.filter(onboarding_session=eligible).delete()
    OnboardingProposal.objects.create(
        onboarding_session=eligible,
        establishment=eligible.establishment,
        status=OnboardingProposal.Status.READY,
        payload={"schema_version": "onboarding_proposal_v4"},
        created_by=owner,
    )

    with_bu = create_onboarding_session(actor=create_user(username="draft_mig_bu"))
    OnboardingDraft.objects.filter(onboarding_session=with_bu).delete()
    bu = create_business_unit(establishment=with_bu.establishment, key="coworking")

    before_bu_count = BusinessUnit.objects.count()
    before_proposal_count = OnboardingProposal.objects.count()
    seed_module.seed_eligible_onboarding_drafts(apps, None)

    assert OnboardingDraft.objects.filter(onboarding_session=eligible).exists()
    eligible_draft = OnboardingDraft.objects.get(onboarding_session=eligible)
    assert eligible_draft.payload["business_units"] == []
    assert not OnboardingDraft.objects.filter(onboarding_session=with_bu).exists()
    assert BusinessUnit.objects.count() == before_bu_count
    assert BusinessUnit.objects.filter(id=bu.id).exists()
    assert OnboardingProposal.objects.count() == before_proposal_count


def _persist_valid_draft(
    *,
    session,
    director_email: str,
    director_first="Dir",
    director_last="Ector",
):
    payload = _valid_complete_payload(establishment_name=session.establishment.name)
    payload["team"]["director"] = {
        "email": director_email,
        "first_name": director_first,
        "last_name": director_last,
    }
    draft = get_onboarding_draft(session=session)
    draft.payload = payload
    draft.save(update_fields=["payload", "updated_at"])
    return draft, payload


def test_complete_skips_invite_when_invited_director_same_email(imported_catalog):
    owner = create_user(username="draft_skip_invited_owner")
    session = create_onboarding_session(actor=owner)
    director_email = f"Same.Director_{uuid.uuid4().hex[:8]}@Example.COM"
    invitation = invite_director_during_onboarding(
        session=session,
        actor=owner,
        email=director_email,
        first_name="Original",
        last_name="Name",
    )
    director_user = invitation.membership.user
    assert director_user.first_name == "Original"
    assert director_user.last_name == "Name"

    _persist_valid_draft(
        session=session,
        director_email=director_email.lower(),
        director_first="DraftFirst",
        director_last="DraftLast",
    )

    result = complete_onboarding_session(session=session, actor=owner)
    assert result["activated"] is True

    director_user.refresh_from_db()
    assert director_user.first_name == "Original"
    assert director_user.last_name == "Name"
    assert (
        EstablishmentMembership.objects.filter(
            establishment=session.establishment,
            role=EstablishmentMembership.Role.DIRECTOR,
            status__in=[
                EstablishmentMembership.Status.INVITED,
                EstablishmentMembership.Status.ACTIVE,
            ],
        )
        .exclude(user=owner)
        .count()
        == 1
    )


def test_complete_skips_invite_when_active_director_same_email(imported_catalog):
    owner = create_user(username="draft_skip_active_owner")
    session = create_onboarding_session(actor=owner)
    director_email = f"active_director_{uuid.uuid4().hex[:8]}@example.com"
    director = create_user(username=f"active_dir_{uuid.uuid4().hex[:8]}")
    director.email = director_email
    director.first_name = "KeepFirst"
    director.last_name = "KeepLast"
    director.save(update_fields=["email", "first_name", "last_name", "updated_at"])
    create_membership(
        establishment=session.establishment,
        user=director,
        role=EstablishmentMembership.Role.DIRECTOR,
        status=EstablishmentMembership.Status.ACTIVE,
    )

    _persist_valid_draft(
        session=session,
        director_email=director_email.upper(),
        director_first="OverwriteFirst",
        director_last="OverwriteLast",
    )

    result = complete_onboarding_session(session=session, actor=owner)
    assert result["activated"] is True

    director.refresh_from_db()
    assert director.first_name == "KeepFirst"
    assert director.last_name == "KeepLast"


def test_complete_rejects_different_director_email_with_no_materialization(
    imported_catalog, api_client
):
    owner = create_user(username="draft_diff_dir_owner")
    session = create_onboarding_session(actor=owner)
    invite_director_during_onboarding(
        session=session,
        actor=owner,
        email=f"existing_dir_{uuid.uuid4().hex[:8]}@example.com",
        first_name="Existing",
        last_name="Director",
    )
    draft, _payload = _persist_valid_draft(
        session=session,
        director_email=f"other_dir_{uuid.uuid4().hex[:8]}@example.com",
    )
    draft_id = draft.id
    before_memberships = EstablishmentMembership.objects.filter(
        establishment=session.establishment
    ).count()

    access_token = login(api_client, user=owner)
    response = api_client.post(
        f"/api/v1/onboarding-sessions/{session.id}/complete/",
        format="json",
        **auth_headers(access_token),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "director_invitation_already_exists"

    session.establishment.refresh_from_db()
    assert session.establishment.status == Establishment.Status.DRAFT
    assert BusinessUnit.objects.filter(establishment=session.establishment).count() == 0
    assert OnboardingDraft.objects.filter(id=draft_id).exists()
    assert (
        EstablishmentMembership.objects.filter(establishment=session.establishment).count()
        == before_memberships
    )


def test_get_draft_rejects_after_activation_and_deletes_on_legacy_activate(
    imported_catalog, api_client
):
    owner = create_user(username="draft_get_after_activate")
    session = create_onboarding_session(actor=owner)
    assert OnboardingDraft.objects.filter(onboarding_session=session).exists()

    create_ready_runtime(session, owner)
    session.status = OnboardingSession.Status.READY_FOR_ACTIVATION
    session.ready_for_activation_at = timezone.now()
    session.save(update_fields=["status", "ready_for_activation_at", "updated_at"])

    activated = activate_onboarding_session(session=session, actor=owner)
    assert activated["activated"] is True
    assert not OnboardingDraft.objects.filter(onboarding_session=session).exists()

    access_token = login(api_client, user=owner)
    get_response = api_client.get(
        f"/api/v1/onboarding-sessions/{session.id}/draft/",
        **auth_headers(access_token),
    )
    assert get_response.status_code == 409


def test_get_draft_has_no_side_effects(imported_catalog, api_client):
    owner = create_user(username="draft_get_readonly")
    session = create_onboarding_session(actor=owner)
    draft = get_onboarding_draft(session=session)
    before_updated_at = draft.updated_at
    before_payload = draft.payload

    access_token = login(api_client, user=owner)
    response = api_client.get(
        f"/api/v1/onboarding-sessions/{session.id}/draft/",
        **auth_headers(access_token),
    )
    assert response.status_code == 200

    draft.refresh_from_db()
    assert draft.updated_at == before_updated_at
    assert draft.payload == before_payload
    assert OnboardingDraft.objects.filter(onboarding_session=session).count() == 1


def test_activation_rollback_preserves_draft(imported_catalog, monkeypatch):
    owner = create_user(username="draft_rollback_owner")
    session = create_onboarding_session(actor=owner)
    _persist_valid_draft(
        session=session,
        director_email=f"rollback_dir_{uuid.uuid4().hex[:8]}@example.com",
    )
    draft_id = OnboardingDraft.objects.get(onboarding_session=session).id

    original_save = Establishment.save

    def failing_save(self, *args, **kwargs):
        if self.status == Establishment.Status.ACTIVE:
            raise RuntimeError("forced activation failure")
        return original_save(self, *args, **kwargs)

    monkeypatch.setattr(Establishment, "save", failing_save)

    with pytest.raises(RuntimeError, match="forced activation failure"):
        complete_onboarding_session(session=session, actor=owner)

    session.establishment.refresh_from_db()
    assert session.establishment.status == Establishment.Status.DRAFT
    assert OnboardingDraft.objects.filter(id=draft_id).exists()
    assert BusinessUnit.objects.filter(establishment=session.establishment).count() == 0


def test_complete_maps_domain_validation_error(imported_catalog, api_client, monkeypatch):
    owner = create_user(username="draft_domain_validation_owner")
    session = create_onboarding_session(actor=owner)
    _persist_valid_draft(
        session=session,
        director_email=f"domain_val_dir_{uuid.uuid4().hex[:8]}@example.com",
    )
    draft_id = OnboardingDraft.objects.get(onboarding_session=session).id
    before_memberships = EstablishmentMembership.objects.filter(
        establishment=session.establishment
    ).count()

    def raise_validation(*_args, **_kwargs):
        raise DomainValidationError(
            "Catalog activity subject does not belong to the business unit catalog.",
            code="catalog_subject_business_unit_mismatch",
        )

    monkeypatch.setattr(
        "houston.establishments.services.create_onboarding_business_unit",
        raise_validation,
    )

    access_token = login(api_client, user=owner)
    response = api_client.post(
        f"/api/v1/onboarding-sessions/{session.id}/complete/",
        format="json",
        **auth_headers(access_token),
    )
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "catalog_subject_business_unit_mismatch"

    session.establishment.refresh_from_db()
    assert session.establishment.status == Establishment.Status.DRAFT
    assert BusinessUnit.objects.filter(establishment=session.establishment).count() == 0
    assert OnboardingDraft.objects.filter(id=draft_id).exists()
    assert (
        EstablishmentMembership.objects.filter(establishment=session.establishment).count()
        == before_memberships
    )


def test_complete_maps_domain_conflict_error(imported_catalog, api_client, monkeypatch):
    owner = create_user(username="draft_domain_conflict_owner")
    session = create_onboarding_session(actor=owner)
    _persist_valid_draft(
        session=session,
        director_email=f"domain_conf_dir_{uuid.uuid4().hex[:8]}@example.com",
    )
    draft_id = OnboardingDraft.objects.get(onboarding_session=session).id
    before_memberships = EstablishmentMembership.objects.filter(
        establishment=session.establishment
    ).count()

    def raise_conflict(*_args, **_kwargs):
        raise DomainConflictError(
            "Catalog activity subject is inactive.",
            code="catalog_activity_subject_inactive",
        )

    monkeypatch.setattr(
        "houston.establishments.services.create_onboarding_business_unit",
        raise_conflict,
    )

    access_token = login(api_client, user=owner)
    response = api_client.post(
        f"/api/v1/onboarding-sessions/{session.id}/complete/",
        format="json",
        **auth_headers(access_token),
    )
    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "catalog_activity_subject_inactive"

    session.establishment.refresh_from_db()
    assert session.establishment.status == Establishment.Status.DRAFT
    assert BusinessUnit.objects.filter(establishment=session.establishment).count() == 0
    assert OnboardingDraft.objects.filter(id=draft_id).exists()
    assert (
        EstablishmentMembership.objects.filter(establishment=session.establishment).count()
        == before_memberships
    )


def test_get_onboarding_draft_service_rejects_activated_session(imported_catalog):
    owner = create_user(username="draft_service_activated")
    session = create_onboarding_session(actor=owner)
    session.status = OnboardingSession.Status.ACTIVATED
    session.activated_at = timezone.now()
    session.save(update_fields=["status", "activated_at", "updated_at"])
    session.establishment.status = Establishment.Status.ACTIVE
    session.establishment.save(update_fields=["status", "updated_at"])

    with pytest.raises(OnboardingSessionTerminalError):
        get_onboarding_draft(session=session)
