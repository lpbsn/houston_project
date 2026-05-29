from __future__ import annotations

import uuid

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from houston.accounts.models import User
from houston.establishments.models import (
    Establishment,
    EstablishmentMembership,
    OnboardingProposal,
    OnboardingSession,
    OperationalDomain,
    OperationalModule,
    RuntimeTag,
)
from houston.establishments.services import (
    create_ai_onboarding_proposal,
    create_manual_onboarding_proposal,
    create_template_onboarding_proposal,
)
from houston.establishments.tests.conftest import (
    HOTEL_HEBERGEMENT_DOMAIN_KEY,
    create_validated_proposal,
    valid_v2_payload,
)
from houston.organizations.models import Organization

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


def create_user(*, username: str, status: str = User.Status.ACTIVE) -> User:
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="secret",
        status=status,
    )


def ensure_csrf(api_client: APIClient) -> str:
    response = api_client.get("/api/v1/auth/csrf/")
    assert response.status_code == 200
    return api_client.cookies["csrftoken"].value


def login(api_client: APIClient, *, user: User) -> str:
    csrf_token = ensure_csrf(api_client)
    response = api_client.post(
        "/api/v1/auth/login/",
        {"identifier": user.email, "password": "secret"},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def auth_headers(access_token: str) -> dict:
    return {"HTTP_AUTHORIZATION": f"Bearer {access_token}"}


def create_onboarding_session(
    *,
    actor: User,
    role: str = EstablishmentMembership.Role.OWNER,
    establishment_status: str = Establishment.Status.DRAFT,
    organization_status: str = Organization.Status.ACTIVE,
) -> OnboardingSession:
    organization = Organization.objects.create(
        name=f"Proposal Group {uuid.uuid4().hex[:6]}",
        status=organization_status,
    )
    establishment = Establishment.objects.create(
        name=f"Proposal Site {uuid.uuid4().hex[:6]}",
        organization=organization,
        status=establishment_status,
    )
    session = OnboardingSession.objects.create(
        organization=organization,
        establishment=establishment,
        started_by=actor,
    )
    EstablishmentMembership.objects.create(
        user=actor,
        establishment=establishment,
        role=role,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    return session


def test_proposal_endpoints_require_authentication(api_client):
    session_id = uuid.uuid4()
    proposal_id = uuid.uuid4()

    responses = [
        api_client.get(f"/api/v1/onboarding-sessions/{session_id}/proposals/"),
        api_client.get(
            f"/api/v1/onboarding-sessions/{session_id}/proposals/{proposal_id}/",
        ),
        api_client.post(
            f"/api/v1/onboarding-sessions/{session_id}/proposals/ai-generate/",
            format="json",
        ),
        api_client.post(
            (
                f"/api/v1/onboarding-sessions/{session_id}/proposals/{proposal_id}/"
                "sections/operational_modules/decision/"
            ),
            {"decision": "accepted"},
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


def test_owner_can_list_and_retrieve_proposals(api_client):
    owner = create_user(username="proposal_api_owner")
    session = create_onboarding_session(actor=owner)
    proposal = create_manual_onboarding_proposal(
        session=session,
        actor=owner,
        payload=valid_v2_payload(),
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
    assert body["payload"]["schema_version"] == "onboarding_proposal_v2"
    assert "ai_usage_logs" not in body
    assert "provider" not in body


def test_manager_is_denied_for_proposal_commands(api_client):
    owner = create_user(username="proposal_api_manager_owner")
    manager = create_user(username="proposal_api_manager")
    session = create_onboarding_session(actor=owner)
    proposal = create_manual_onboarding_proposal(
        session=session,
        actor=owner,
        payload=valid_v2_payload(),
    )
    EstablishmentMembership.objects.create(
        user=manager,
        establishment=session.establishment,
        role=EstablishmentMembership.Role.MANAGER,
        status=EstablishmentMembership.Status.ACTIVE,
    )

    access_token = login(api_client, user=manager)
    response = api_client.post(
        (
            f"/api/v1/onboarding-sessions/{session.id}/proposals/{proposal.id}/"
            "sections/operational_modules/decision/"
        ),
        {"decision": "accepted"},
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 403


def test_staff_is_denied_for_proposal_commands(api_client):
    owner = create_user(username="proposal_api_staff_owner")
    staff = create_user(username="proposal_api_staff")
    session = create_onboarding_session(actor=owner)
    proposal = create_manual_onboarding_proposal(
        session=session,
        actor=owner,
        payload=valid_v2_payload(),
    )
    EstablishmentMembership.objects.create(
        user=staff,
        establishment=session.establishment,
        role=EstablishmentMembership.Role.STAFF,
        status=EstablishmentMembership.Status.ACTIVE,
    )

    access_token = login(api_client, user=staff)
    list_response = api_client.get(
        f"/api/v1/onboarding-sessions/{session.id}/proposals/",
        **auth_headers(access_token),
    )
    section_response = api_client.post(
        (
            f"/api/v1/onboarding-sessions/{session.id}/proposals/{proposal.id}/"
            "sections/operational_modules/decision/"
        ),
        {"decision": "accepted"},
        format="json",
        **auth_headers(access_token),
    )
    ai_generate_response = api_client.post(
        f"/api/v1/onboarding-sessions/{session.id}/proposals/ai-generate/",
        {"locale": "en-US"},
        format="json",
        **auth_headers(access_token),
    )

    assert list_response.status_code == 403
    assert section_response.status_code == 403
    assert ai_generate_response.status_code == 403


def test_foreign_and_mismatched_proposals_are_denied_safely(api_client):
    actor = create_user(username="proposal_api_foreign_actor")
    owner = create_user(username="proposal_api_foreign_owner")
    actor_session = create_onboarding_session(actor=actor)
    foreign_session = create_onboarding_session(actor=owner)
    foreign_proposal = create_manual_onboarding_proposal(
        session=foreign_session,
        actor=owner,
        payload=valid_v2_payload(),
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


def test_ai_generate_success_creates_ai_proposal_only(api_client, monkeypatch):
    owner = create_user(username="proposal_api_ai_owner")
    session = create_onboarding_session(actor=owner)

    def fake_run_ai_onboarding_interpretation(*, session, actor, locale):
        assert locale == "fr-FR"
        return create_ai_onboarding_proposal(
            session=session,
            actor=actor,
            payload=valid_v2_payload(),
        )

    monkeypatch.setattr(
        "houston.establishments.api.views.run_ai_onboarding_interpretation",
        fake_run_ai_onboarding_interpretation,
    )

    access_token = login(api_client, user=owner)
    response = api_client.post(
        f"/api/v1/onboarding-sessions/{session.id}/proposals/ai-generate/",
        {"locale": "fr-FR"},
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["proposal"]["source"] == OnboardingProposal.Source.AI_PROPOSED
    assert body["proposal"]["status"] == OnboardingProposal.Status.READY
    assert OperationalModule.objects.count() == 0
    assert OperationalDomain.objects.count() == 0
    session.establishment.refresh_from_db()
    assert session.establishment.status == Establishment.Status.DRAFT


def test_ai_generate_fallback_returns_template_without_leakage(api_client, monkeypatch, settings):
    settings.OPENAI_API_KEY = "sk-test-secret"
    owner = create_user(username="proposal_api_ai_fallback_owner")
    session = create_onboarding_session(actor=owner)

    def fake_run_ai_onboarding_interpretation(*, session, actor, locale):
        return create_template_onboarding_proposal(
            session=session,
            actor=actor,
            payload=valid_v2_payload(),
        )

    monkeypatch.setattr(
        "houston.establishments.api.views.run_ai_onboarding_interpretation",
        fake_run_ai_onboarding_interpretation,
    )

    access_token = login(api_client, user=owner)
    response = api_client.post(
        f"/api/v1/onboarding-sessions/{session.id}/proposals/ai-generate/",
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 201
    serialized = str(response.json())
    assert response.json()["proposal"]["source"] == OnboardingProposal.Source.TEMPLATE
    assert "sk-test-secret" not in serialized
    assert "raw_prompt" not in serialized
    assert "raw_provider_output" not in serialized
    assert OperationalModule.objects.count() == 0
    assert OperationalDomain.objects.count() == 0


def test_ai_generate_open_proposal_conflict(api_client):
    owner = create_user(username="proposal_api_ai_conflict_owner")
    session = create_onboarding_session(actor=owner)
    create_manual_onboarding_proposal(
        session=session,
        actor=owner,
        payload=valid_v2_payload(),
    )

    access_token = login(api_client, user=owner)
    response = api_client.post(
        f"/api/v1/onboarding-sessions/{session.id}/proposals/ai-generate/",
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 409


def test_section_decision_accepts_and_skips_sections(api_client):
    owner = create_user(username="proposal_api_decision_owner")
    session = create_onboarding_session(actor=owner)
    proposal = create_manual_onboarding_proposal(
        session=session,
        actor=owner,
        payload=valid_v2_payload(),
    )

    access_token = login(api_client, user=owner)
    module_response = api_client.post(
        (
            f"/api/v1/onboarding-sessions/{session.id}/proposals/{proposal.id}/"
            "sections/operational_modules/decision/"
        ),
        {"decision": "accepted"},
        format="json",
        **auth_headers(access_token),
    )
    units_response = api_client.post(
        (
            f"/api/v1/onboarding-sessions/{session.id}/proposals/{proposal.id}/"
            "sections/operational_units/decision/"
        ),
        {"decision": "skipped"},
        format="json",
        **auth_headers(access_token),
    )

    assert module_response.status_code == 200
    assert (
        module_response.json()["proposal"]["status"]
        == OnboardingProposal.Status.PARTIALLY_VALIDATED
    )
    assert units_response.status_code == 200
    assert units_response.json()["proposal"]["section_validation"]["operational_units"] == "skipped"


def test_required_section_skip_is_rejected(api_client):
    owner = create_user(username="proposal_api_required_skip_owner")
    session = create_onboarding_session(actor=owner)
    proposal = create_manual_onboarding_proposal(
        session=session,
        actor=owner,
        payload=valid_v2_payload(),
    )

    access_token = login(api_client, user=owner)
    response = api_client.post(
        (
            f"/api/v1/onboarding-sessions/{session.id}/proposals/{proposal.id}/"
            "sections/operational_modules/decision/"
        ),
        {"decision": "skipped"},
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 400
    assert response.json()["errors"][0]["code"] == "missing_required_section"
    assert OperationalModule.objects.count() == 0


def test_reject_does_not_mutate_runtime(api_client):
    owner = create_user(username="proposal_api_reject_owner")
    session = create_onboarding_session(actor=owner)
    proposal = create_manual_onboarding_proposal(
        session=session,
        actor=owner,
        payload=valid_v2_payload(),
    )

    access_token = login(api_client, user=owner)
    response = api_client.post(
        f"/api/v1/onboarding-sessions/{session.id}/proposals/{proposal.id}/reject/",
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 200
    assert response.json()["proposal"]["status"] == OnboardingProposal.Status.REJECTED
    assert OperationalModule.objects.count() == 0
    assert OperationalDomain.objects.count() == 0


def test_apply_requires_validated_proposal(api_client):
    owner = create_user(username="proposal_api_apply_unvalidated_owner")
    session = create_onboarding_session(actor=owner)
    proposal = create_manual_onboarding_proposal(
        session=session,
        actor=owner,
        payload=valid_v2_payload(),
    )

    access_token = login(api_client, user=owner)
    response = api_client.post(
        f"/api/v1/onboarding-sessions/{session.id}/proposals/{proposal.id}/apply/",
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 409
    assert OperationalModule.objects.count() == 0
    assert OperationalDomain.objects.count() == 0


def test_apply_mutates_runtime_without_activation(api_client):
    owner = create_user(username="proposal_api_apply_owner")
    session = create_onboarding_session(actor=owner)
    proposal = create_validated_proposal(session, owner)
    session.status = OnboardingSession.Status.READY_FOR_ACTIVATION
    session.ready_for_activation_at = timezone.now()
    session.save(update_fields=["status", "ready_for_activation_at", "updated_at"])

    access_token = login(api_client, user=owner)
    response = api_client.post(
        f"/api/v1/onboarding-sessions/{session.id}/proposals/{proposal.id}/apply/",
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["proposal"]["status"] == OnboardingProposal.Status.APPLIED
    assert body["session"]["status"] == OnboardingSession.Status.CONFIGURING_RUNTIME
    assert OperationalModule.objects.filter(key="hotel", active=True).exists()
    assert OperationalDomain.objects.filter(
        key=HOTEL_HEBERGEMENT_DOMAIN_KEY,
        active=True,
    ).exists()
    assert RuntimeTag.objects.filter(key="hvac", active=True).exists()
    session.refresh_from_db()
    session.establishment.refresh_from_db()
    assert session.ready_for_activation_at is None
    assert session.activated_at is None
    assert session.establishment.status == Establishment.Status.DRAFT


def test_apply_rejects_active_establishment_without_activation(api_client):
    owner = create_user(username="proposal_api_apply_active_owner")
    session = create_onboarding_session(actor=owner)
    proposal = create_validated_proposal(session, owner)
    session.establishment.status = Establishment.Status.ACTIVE
    session.establishment.save(update_fields=["status", "updated_at"])

    access_token = login(api_client, user=owner)
    response = api_client.post(
        f"/api/v1/onboarding-sessions/{session.id}/proposals/{proposal.id}/apply/",
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 409
    assert OperationalModule.objects.count() == 0


def test_activation_endpoint_does_not_activate_without_explicit_mark_ready(api_client):
    owner = create_user(username="proposal_api_activate_requires_ready_owner")
    session = create_onboarding_session(actor=owner)

    access_token = login(api_client, user=owner)
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
    assert session.activated_at is None
    assert session.establishment.status == Establishment.Status.DRAFT
