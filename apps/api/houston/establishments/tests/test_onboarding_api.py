from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from django.db import close_old_connections
from django.utils import timezone
from rest_framework.test import APIClient

from houston.accounts.models import User
from houston.ai.models import AIUsageLog
from houston.establishments.models import (
    ACTIVITY_DESCRIPTION_MIN_LENGTH,
    ActivitySubject,
    BusinessUnit,
    Establishment,
    EstablishmentActivityDescription,
    EstablishmentMembership,
    OnboardingSession,
    OperationalUnit,
)
from houston.organizations.models import Organization
from houston.testing.auth import auth_headers, login
from houston.testing.factories import create_user
from houston.testing.onboarding import create_onboarding_session, create_ready_runtime
from houston.testing.taxonomy import create_membership_with_business_unit_scope

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


def test_create_onboarding_session_success_for_owner(api_client):
    actor = create_user(username="onboarding_owner")
    organization = Organization.objects.create(name="Nice Group")
    establishment = Establishment.objects.create(
        name="Draft Site",
        organization=organization,
        status=Establishment.Status.DRAFT,
    )
    EstablishmentMembership.objects.create(
        user=actor,
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.ACTIVE,
    )

    access_token = login(api_client, user=actor)
    response = api_client.post(
        "/api/v1/onboarding-sessions/",
        {"establishment_id": str(establishment.id)},
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["created"] is True
    assert body["session"]["establishment"]["id"] == str(establishment.id)
    assert body["session"]["source_mode"] == OnboardingSession.SourceMode.MANUAL
    assert OnboardingSession.objects.filter(establishment=establishment).count() == 1


def test_director_cannot_start_onboarding_session_on_draft_establishment(api_client):
    actor = create_user(username="onboarding_director_blocked")
    organization = Organization.objects.create(name="Nice Group")
    establishment = Establishment.objects.create(
        name="Draft Site",
        organization=organization,
        status=Establishment.Status.DRAFT,
    )
    EstablishmentMembership.objects.create(
        user=actor,
        establishment=establishment,
        role=EstablishmentMembership.Role.DIRECTOR,
        status=EstablishmentMembership.Status.ACTIVE,
    )

    access_token = login(api_client, user=actor)
    response = api_client.post(
        "/api/v1/onboarding-sessions/",
        {"establishment_id": str(establishment.id)},
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 403
    assert OnboardingSession.objects.filter(establishment=establishment).count() == 0


def test_create_onboarding_session_allows_template_and_returns_existing_session(
    api_client,
):
    actor = create_user(username="onboarding_template_owner")
    organization = Organization.objects.create(name="Nice Group")
    establishment = Establishment.objects.create(
        name="Draft Site",
        organization=organization,
        status=Establishment.Status.DRAFT,
    )
    EstablishmentMembership.objects.create(
        user=actor,
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.ACTIVE,
    )

    access_token = login(api_client, user=actor)
    first_response = api_client.post(
        "/api/v1/onboarding-sessions/",
        {
            "establishment_id": str(establishment.id),
            "source_mode": OnboardingSession.SourceMode.TEMPLATE,
        },
        format="json",
        **auth_headers(access_token),
    )
    second_response = api_client.post(
        "/api/v1/onboarding-sessions/",
        {
            "establishment_id": str(establishment.id),
            "source_mode": OnboardingSession.SourceMode.TEMPLATE,
        },
        format="json",
        **auth_headers(access_token),
    )

    assert first_response.status_code == 201
    assert first_response.json()["session"]["source_mode"] == OnboardingSession.SourceMode.TEMPLATE
    assert second_response.status_code == 200
    assert second_response.json()["created"] is False
    assert second_response.json()["session"]["id"] == first_response.json()["session"]["id"]


@pytest.mark.django_db(transaction=True)
def test_concurrent_create_onboarding_session_is_idempotent():
    actor = create_user(username="onboarding_concurrent_owner")
    organization = Organization.objects.create(name="Concurrent Group")
    establishment = Establishment.objects.create(
        name="Concurrent Draft Site",
        organization=organization,
        status=Establishment.Status.DRAFT,
    )
    EstablishmentMembership.objects.create(
        user=actor,
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.ACTIVE,
    )

    def create_session(_: int) -> int:
        close_old_connections()
        try:
            client = APIClient(enforce_csrf_checks=True)
            access_token = login(client, user=actor)
            response = client.post(
                "/api/v1/onboarding-sessions/",
                {"establishment_id": str(establishment.id)},
                format="json",
                **auth_headers(access_token),
            )
            return response.status_code
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(create_session, range(2)))

    assert all(status in {200, 201} for status in statuses)
    assert OnboardingSession.objects.filter(establishment=establishment).count() == 1


def test_create_onboarding_session_rejects_ai_source_mode(api_client):
    actor = create_user(username="onboarding_ai_owner")
    session = create_onboarding_session(actor=actor)
    session.delete()

    access_token = login(api_client, user=actor)
    response = api_client.post(
        "/api/v1/onboarding-sessions/",
        {
            "establishment_id": str(session.establishment_id),
            "source_mode": OnboardingSession.SourceMode.AI,
        },
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 400
    assert not OnboardingSession.objects.filter(establishment=session.establishment).exists()


def test_onboarding_session_endpoints_require_authentication(api_client):
    response = api_client.get(f"/api/v1/onboarding-sessions/{uuid.uuid4()}/")

    assert response.status_code == 401


def test_retrieve_onboarding_session_success_and_excludes_runtime_config(api_client):
    actor = create_user(username="onboarding_detail_owner")
    session = create_onboarding_session(actor=actor)

    access_token = login(api_client, user=actor)
    response = api_client.get(
        f"/api/v1/onboarding-sessions/{session.id}/",
        **auth_headers(access_token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(session.id)
    assert body["organization"]["id"] == str(session.organization_id)
    assert body["establishment"]["id"] == str(session.establishment_id)
    assert "runtime_config" not in body


def test_foreign_onboarding_session_returns_not_found(api_client):
    actor = create_user(username="onboarding_foreign_actor")
    foreign_actor = create_user(username="onboarding_foreign_owner")
    foreign_session = create_onboarding_session(actor=foreign_actor)

    access_token = login(api_client, user=actor)
    response = api_client.get(
        f"/api/v1/onboarding-sessions/{foreign_session.id}/",
        **auth_headers(access_token),
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Not found."}


@pytest.mark.parametrize(
    ("membership_status", "organization_status", "establishment_status"),
    [
        (
            EstablishmentMembership.Status.DEACTIVATED,
            Organization.Status.ACTIVE,
            Establishment.Status.DRAFT,
        ),
        (
            EstablishmentMembership.Status.ACTIVE,
            Organization.Status.SUSPENDED,
            Establishment.Status.DRAFT,
        ),
        (
            EstablishmentMembership.Status.ACTIVE,
            Organization.Status.ACTIVE,
            Establishment.Status.DEACTIVATED,
        ),
    ],
)
def test_invalid_onboarding_access_state_is_denied_safely(
    api_client,
    membership_status,
    organization_status,
    establishment_status,
):
    actor = create_user(username=f"invalid_state_{uuid.uuid4().hex[:6]}")
    session = create_onboarding_session(
        actor=actor,
        membership_status=membership_status,
        organization_status=organization_status,
        establishment_status=establishment_status,
    )

    access_token = login(api_client, user=actor)
    response = api_client.get(
        f"/api/v1/onboarding-sessions/{session.id}/",
        **auth_headers(access_token),
    )

    assert response.status_code == 404


def test_draft_onboarding_membership_remains_excluded_from_bootstrap(api_client):
    actor = create_user(username="draft_bootstrap_owner")
    session = create_onboarding_session(actor=actor)

    access_token = login(api_client, user=actor)
    response = api_client.get(
        "/api/v1/auth/bootstrap/",
        **auth_headers(access_token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["memberships"] == []
    assert body["active_membership"] is None
    assert len(body["pending_onboarding_memberships"]) == 1
    pending = body["pending_onboarding_memberships"][0]
    assert pending["establishment_id"] == str(session.establishment_id)
    assert pending["role"] == EstablishmentMembership.Role.OWNER
    assert pending["can_continue_onboarding"] is True
    assert pending["onboarding_session_id"] == str(session.id)


def test_description_patch_accepts_valid_description(api_client):
    actor = create_user(username="description_owner")
    session = create_onboarding_session(actor=actor)

    access_token = login(api_client, user=actor)
    response = api_client.patch(
        f"/api/v1/onboarding-sessions/{session.id}/description/",
        {"description": f" {'A' * ACTIVITY_DESCRIPTION_MIN_LENGTH} "},
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["session"]["status"] == OnboardingSession.Status.DESCRIPTION_SUBMITTED
    assert body["activity_description"]["description"] == "A" * ACTIVITY_DESCRIPTION_MIN_LENGTH
    field_names = {field.name for field in Establishment._meta.fields}
    assert "activity_description" not in field_names


def test_description_patch_rejects_too_short_description(api_client):
    actor = create_user(username="description_short_owner")
    session = create_onboarding_session(actor=actor)

    access_token = login(api_client, user=actor)
    response = api_client.patch(
        f"/api/v1/onboarding-sessions/{session.id}/description/",
        {"description": "A" * (ACTIVITY_DESCRIPTION_MIN_LENGTH - 1)},
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 400
    assert not EstablishmentActivityDescription.objects.filter(
        establishment=session.establishment,
    ).exists()


def test_description_patch_rejects_terminal_session(api_client):
    actor = create_user(username="description_terminal_owner")
    session = create_onboarding_session(
        actor=actor,
        session_status=OnboardingSession.Status.CANCELED,
    )

    access_token = login(api_client, user=actor)
    response = api_client.patch(
        f"/api/v1/onboarding-sessions/{session.id}/description/",
        {"description": "A" * ACTIVITY_DESCRIPTION_MIN_LENGTH},
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "onboarding_session_terminal"


def test_manager_cannot_mutate_onboarding_description(api_client):
    actor = create_user(username="description_manager")
    session = create_onboarding_session(
        actor=actor,
        role=EstablishmentMembership.Role.MANAGER,
    )

    access_token = login(api_client, user=actor)
    response = api_client.patch(
        f"/api/v1/onboarding-sessions/{session.id}/description/",
        {"description": "A" * ACTIVITY_DESCRIPTION_MIN_LENGTH},
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 403


def test_runtime_config_get_returns_same_establishment_active_data_only(api_client):
    actor = create_user(username="runtime_config_owner")
    session = create_onboarding_session(actor=actor)
    establishment = session.establishment
    foreign_establishment = Establishment.objects.create(
        name="Foreign",
        organization=session.organization,
        status=Establishment.Status.DRAFT,
    )
    business_unit = BusinessUnit.objects.create(
        establishment=establishment,
        key="hotel",
        label="Hotel",
    )
    foreign_business_unit = BusinessUnit.objects.create(
        establishment=foreign_establishment,
        key="restaurant",
        label="Restaurant",
    )
    ActivitySubject.objects.create(
        establishment=establishment,
        business_unit=business_unit,
        normalized_name="proprete",
        label="Proprete",
    )
    ActivitySubject.objects.create(
        establishment=foreign_establishment,
        business_unit=foreign_business_unit,
        normalized_name="foreign",
        label="Foreign",
    )
    OperationalUnit.objects.create(
        establishment=establishment,
        key="lobby",
        label="Lobby",
    )

    access_token = login(api_client, user=actor)
    response = api_client.get(
        f"/api/v1/onboarding-sessions/{session.id}/runtime-config/",
        **auth_headers(access_token),
    )

    assert response.status_code == 200
    body = response.json()
    assert [item["key"] for item in body["active_business_units"]] == ["hotel"]
    assert [item["key"] for item in body["optional_units"]] == ["lobby"]


def test_activation_summary_returns_readiness_blockers_and_access_flags(api_client):
    actor = create_user(username="summary_owner")
    session = create_onboarding_session(actor=actor)

    access_token = login(api_client, user=actor)
    response = api_client.get(
        f"/api/v1/onboarding-sessions/{session.id}/activation-summary/",
        **auth_headers(access_token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["readiness"]["is_ready"] is False
    assert body["access"]["can_activate"] is True
    assert body["effective_can_activate"] is False
    assert "active_business_units" in body
    assert {blocker["code"] for blocker in body["blockers"]} == {
        "missing_active_business_unit",
        "missing_active_or_invited_director",
    }


def test_activation_summary_returns_effective_can_activate_when_ready(api_client):
    actor = create_user(username="summary_ready_owner")
    session = create_onboarding_session(actor=actor)
    create_ready_runtime(session, actor)

    access_token = login(api_client, user=actor)
    response = api_client.get(
        f"/api/v1/onboarding-sessions/{session.id}/activation-summary/",
        **auth_headers(access_token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["readiness"]["is_ready"] is True
    assert body["access"]["can_activate"] is True
    assert body["effective_can_activate"] is True
    assert len(body["active_business_units"]) == 1
    assert body["active_business_units"][0]["key"] == "coworking"


def test_mark_ready_success_does_not_activate_establishment(api_client):
    actor = create_user(username="mark_ready_owner")
    session = create_onboarding_session(actor=actor)
    create_ready_runtime(session, actor)

    access_token = login(api_client, user=actor)
    response = api_client.post(
        f"/api/v1/onboarding-sessions/{session.id}/mark-ready/",
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["session"]["status"] == OnboardingSession.Status.READY_FOR_ACTIVATION
    assert body["activation_summary"]["effective_can_activate"] is True

    session.refresh_from_db()
    session.establishment.refresh_from_db()
    assert session.ready_for_activation_at is not None
    assert session.activated_at is None
    assert session.establishment.status == Establishment.Status.DRAFT


def test_mark_ready_blocked_when_readiness_fails(api_client):
    actor = create_user(username="mark_ready_blocked_owner")
    session = create_onboarding_session(actor=actor)

    access_token = login(api_client, user=actor)
    response = api_client.post(
        f"/api/v1/onboarding-sessions/{session.id}/mark-ready/",
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "activation_readiness_failed"
    assert response.json()["blockers"]
    session.refresh_from_db()
    assert session.status == OnboardingSession.Status.STARTED
    assert session.ready_for_activation_at is None


def test_manager_cannot_mark_ready_even_when_readiness_passes(api_client):
    owner = create_user(username="mark_ready_owner_for_manager_case")
    session = create_onboarding_session(actor=owner)
    business_unit = create_ready_runtime(session, owner)
    manager = create_user(username="mark_ready_manager")
    manager_membership = EstablishmentMembership.objects.create(
        user=manager,
        establishment=session.establishment,
        role=EstablishmentMembership.Role.MANAGER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    create_membership_with_business_unit_scope(
        membership=manager_membership,
        business_unit=business_unit,
    )

    access_token = login(api_client, user=manager)
    response = api_client.post(
        f"/api/v1/onboarding-sessions/{session.id}/mark-ready/",
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 403
    session.refresh_from_db()
    assert session.status == OnboardingSession.Status.STARTED
    assert session.establishment.status == Establishment.Status.DRAFT


def test_activate_success_transitions_ready_session_and_establishment(api_client):
    actor = create_user(username="activate_owner")
    session = create_onboarding_session(actor=actor)
    create_ready_runtime(session, actor)

    access_token = login(api_client, user=actor)
    mark_ready_response = api_client.post(
        f"/api/v1/onboarding-sessions/{session.id}/mark-ready/",
        format="json",
        **auth_headers(access_token),
    )
    assert mark_ready_response.status_code == 200
    session.refresh_from_db()
    ready_at = session.ready_for_activation_at

    response = api_client.post(
        f"/api/v1/onboarding-sessions/{session.id}/activate/",
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["session"]["status"] == OnboardingSession.Status.ACTIVATED
    assert body["session"]["activated_at"] is not None
    assert body["activation_summary"]["establishment"]["status"] == Establishment.Status.ACTIVE
    session.refresh_from_db()
    session.establishment.refresh_from_db()
    assert session.ready_for_activation_at == ready_at
    assert session.activated_at is not None
    assert session.establishment.status == Establishment.Status.ACTIVE
    assert AIUsageLog.objects.count() == 0


def test_activate_is_idempotent_for_same_activated_session(api_client):
    actor = create_user(username="activate_idempotent_owner")
    session = create_onboarding_session(actor=actor)
    create_ready_runtime(session, actor)

    access_token = login(api_client, user=actor)
    mark_ready_response = api_client.post(
        f"/api/v1/onboarding-sessions/{session.id}/mark-ready/",
        format="json",
        **auth_headers(access_token),
    )
    assert mark_ready_response.status_code == 200
    first_response = api_client.post(
        f"/api/v1/onboarding-sessions/{session.id}/activate/",
        format="json",
        **auth_headers(access_token),
    )
    assert first_response.status_code == 200
    session.refresh_from_db()
    activated_at = session.activated_at

    second_response = api_client.post(
        f"/api/v1/onboarding-sessions/{session.id}/activate/",
        format="json",
        **auth_headers(access_token),
    )

    assert second_response.status_code == 200
    assert second_response.json()["session"]["status"] == OnboardingSession.Status.ACTIVATED
    session.refresh_from_db()
    assert session.activated_at == activated_at


def test_activate_blocked_when_readiness_fails(api_client):
    actor = create_user(username="activate_blocked_owner")
    session = create_onboarding_session(actor=actor)
    session.status = OnboardingSession.Status.READY_FOR_ACTIVATION
    session.ready_for_activation_at = timezone.now()
    session.save(update_fields=["status", "ready_for_activation_at", "updated_at"])

    access_token = login(api_client, user=actor)
    response = api_client.post(
        f"/api/v1/onboarding-sessions/{session.id}/activate/",
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "activation_readiness_failed"
    assert response.json()["blockers"]
    session.refresh_from_db()
    session.establishment.refresh_from_db()
    assert session.status == OnboardingSession.Status.READY_FOR_ACTIVATION
    assert session.establishment.status == Establishment.Status.DRAFT


def test_activate_conflicts_when_session_is_not_marked_ready(api_client):
    actor = create_user(username="activate_not_ready_owner")
    session = create_onboarding_session(actor=actor)
    create_ready_runtime(session, actor)

    access_token = login(api_client, user=actor)
    response = api_client.post(
        f"/api/v1/onboarding-sessions/{session.id}/activate/",
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "invalid_onboarding_activation_state"
    session.refresh_from_db()
    session.establishment.refresh_from_db()
    assert session.status == OnboardingSession.Status.STARTED
    assert session.establishment.status == Establishment.Status.DRAFT


def test_activate_conflicts_when_ready_timestamp_is_missing(api_client):
    actor = create_user(username="activate_missing_ready_timestamp_owner")
    session = create_onboarding_session(actor=actor)
    create_ready_runtime(session, actor)
    session.status = OnboardingSession.Status.READY_FOR_ACTIVATION
    session.ready_for_activation_at = None
    session.save(update_fields=["status", "ready_for_activation_at", "updated_at"])

    access_token = login(api_client, user=actor)
    response = api_client.post(
        f"/api/v1/onboarding-sessions/{session.id}/activate/",
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "invalid_onboarding_activation_state"
    session.refresh_from_db()
    assert session.status == OnboardingSession.Status.READY_FOR_ACTIVATION


def test_activate_conflicts_when_establishment_is_already_active(api_client):
    actor = create_user(username="activate_already_active_owner")
    session = create_onboarding_session(actor=actor)
    create_ready_runtime(session, actor)
    session.status = OnboardingSession.Status.READY_FOR_ACTIVATION
    session.ready_for_activation_at = timezone.now()
    session.save(update_fields=["status", "ready_for_activation_at", "updated_at"])
    session.establishment.status = Establishment.Status.ACTIVE
    session.establishment.save(update_fields=["status", "updated_at"])

    access_token = login(api_client, user=actor)
    response = api_client.post(
        f"/api/v1/onboarding-sessions/{session.id}/activate/",
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 404
    session.refresh_from_db()
    assert session.status == OnboardingSession.Status.READY_FOR_ACTIVATION
    assert session.activated_at is None


def test_manager_cannot_activate_even_when_readiness_passes(api_client):
    owner = create_user(username="activate_owner_for_manager_case")
    session = create_onboarding_session(actor=owner)
    business_unit = create_ready_runtime(session, owner)
    manager = create_user(username="activate_manager")
    manager_membership = EstablishmentMembership.objects.create(
        user=manager,
        establishment=session.establishment,
        role=EstablishmentMembership.Role.MANAGER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    create_membership_with_business_unit_scope(
        membership=manager_membership,
        business_unit=business_unit,
    )
    session.status = OnboardingSession.Status.READY_FOR_ACTIVATION
    session.ready_for_activation_at = timezone.now()
    session.save(update_fields=["status", "ready_for_activation_at", "updated_at"])

    access_token = login(api_client, user=manager)
    response = api_client.post(
        f"/api/v1/onboarding-sessions/{session.id}/activate/",
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 403
    session.refresh_from_db()
    session.establishment.refresh_from_db()
    assert session.status == OnboardingSession.Status.READY_FOR_ACTIVATION
    assert session.establishment.status == Establishment.Status.DRAFT


def test_foreign_actor_cannot_activate_onboarding_session(api_client):
    owner = create_user(username="activate_foreign_owner")
    foreign_actor = create_user(username="activate_foreign_actor")
    session = create_onboarding_session(actor=owner)
    create_ready_runtime(session, owner)
    session.status = OnboardingSession.Status.READY_FOR_ACTIVATION
    session.ready_for_activation_at = timezone.now()
    session.save(update_fields=["status", "ready_for_activation_at", "updated_at"])

    access_token = login(api_client, user=foreign_actor)
    response = api_client.post(
        f"/api/v1/onboarding-sessions/{session.id}/activate/",
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 404
    session.refresh_from_db()
    session.establishment.refresh_from_db()
    assert session.status == OnboardingSession.Status.READY_FOR_ACTIVATION
    assert session.establishment.status == Establishment.Status.DRAFT


def _add_staff_membership(*, session: OnboardingSession) -> User:
    staff = create_user(username=f"onboarding_staff_{uuid.uuid4().hex[:6]}")
    EstablishmentMembership.objects.create(
        user=staff,
        establishment=session.establishment,
        role=EstablishmentMembership.Role.STAFF,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    return staff


def test_staff_cannot_access_onboarding_session_reads(api_client):
    owner = create_user(username="onboarding_staff_read_owner")
    session = create_onboarding_session(actor=owner)
    staff = _add_staff_membership(session=session)

    access_token = login(api_client, user=staff)
    for path in (
        f"/api/v1/onboarding-sessions/{session.id}/",
        f"/api/v1/onboarding-sessions/{session.id}/runtime-config/",
        f"/api/v1/onboarding-sessions/{session.id}/activation-summary/",
    ):
        response = api_client.get(path, **auth_headers(access_token))
        assert response.status_code == 404


def test_staff_cannot_submit_activity_description(api_client):
    owner = create_user(username="onboarding_staff_description_owner")
    session = create_onboarding_session(actor=owner)
    staff = _add_staff_membership(session=session)

    access_token = login(api_client, user=staff)
    response = api_client.patch(
        f"/api/v1/onboarding-sessions/{session.id}/description/",
        {"description": "A" * ACTIVITY_DESCRIPTION_MIN_LENGTH},
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 403


def test_staff_cannot_mark_ready_or_activate(api_client):
    owner = create_user(username="onboarding_staff_activate_owner")
    session = create_onboarding_session(actor=owner)
    create_ready_runtime(session, owner)
    staff = _add_staff_membership(session=session)
    session.status = OnboardingSession.Status.READY_FOR_ACTIVATION
    session.ready_for_activation_at = timezone.now()
    session.save(update_fields=["status", "ready_for_activation_at", "updated_at"])

    access_token = login(api_client, user=staff)
    mark_ready_response = api_client.post(
        f"/api/v1/onboarding-sessions/{session.id}/mark-ready/",
        format="json",
        **auth_headers(access_token),
    )
    activate_response = api_client.post(
        f"/api/v1/onboarding-sessions/{session.id}/activate/",
        format="json",
        **auth_headers(access_token),
    )

    assert mark_ready_response.status_code == 403
    assert activate_response.status_code == 403
    session.refresh_from_db()
    session.establishment.refresh_from_db()
    assert session.establishment.status == Establishment.Status.DRAFT
