from __future__ import annotations

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from houston.accounts.models import User
from houston.establishments.models import (
    ACTIVITY_DESCRIPTION_MIN_LENGTH,
    ActivitySubject,
    Establishment,
    EstablishmentActivityDescription,
    EstablishmentMembership,
    OnboardingSession,
)
from houston.establishments.tests.taxonomy_helpers import create_business_unit
from houston.testing.auth import auth_headers, login
from houston.testing.factories import create_user
from houston.testing.onboarding import create_onboarding_session, create_ready_runtime

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


def invite_director_payload(
    *,
    email: str = "director@example.com",
    first_name: str = "Casey",
    last_name: str = "Director",
) -> dict:
    return {
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
    }


def test_director_invitation_creates_invited_director_membership(api_client):
    owner = create_user(username="director_invite_owner")
    session = create_onboarding_session(actor=owner)
    access_token = login(api_client, user=owner)

    response = api_client.post(
        f"/api/v1/onboarding-sessions/{session.id}/director-invitations/",
        invite_director_payload(),
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["membership"]["role"] == "director"
    assert body["membership"]["status"] == "invited"
    assert body["membership"]["user"]["email"] == "director@example.com"

    membership = EstablishmentMembership.objects.get(id=body["membership"]["id"])
    assert membership.role == EstablishmentMembership.Role.DIRECTOR
    assert membership.status == EstablishmentMembership.Status.INVITED
    assert membership.user.status == User.Status.PENDING
    assert body["invitation_token"]
    assert body["invitation_accept_path"] == f"/invitations/{body['invitation_token']}"


def test_director_invitation_rejects_duplicate_email(api_client):
    owner = create_user(username="director_invite_duplicate_owner")
    session = create_onboarding_session(actor=owner)
    access_token = login(api_client, user=owner)
    payload = invite_director_payload(email="duplicate@example.com")

    first_response = api_client.post(
        f"/api/v1/onboarding-sessions/{session.id}/director-invitations/",
        payload,
        format="json",
        **auth_headers(access_token),
    )
    second_response = api_client.post(
        f"/api/v1/onboarding-sessions/{session.id}/director-invitations/",
        payload,
        format="json",
        **auth_headers(access_token),
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 400
    assert second_response.json()["code"] == "director_invitation_duplicate"


def test_director_invitation_rejects_owner_email(api_client):
    owner = create_user(username="director_invite_owner_email")
    session = create_onboarding_session(actor=owner)
    access_token = login(api_client, user=owner)

    response = api_client.post(
        f"/api/v1/onboarding-sessions/{session.id}/director-invitations/",
        invite_director_payload(email=owner.email),
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "director_invitation_owner_not_allowed"


def test_manager_cannot_invite_director(api_client):
    owner = create_user(username="director_invite_owner_for_manager")
    session = create_onboarding_session(actor=owner)
    manager = create_user(username="director_invite_manager")
    EstablishmentMembership.objects.create(
        user=manager,
        establishment=session.establishment,
        role=EstablishmentMembership.Role.MANAGER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    access_token = login(api_client, user=manager)

    response = api_client.post(
        f"/api/v1/onboarding-sessions/{session.id}/director-invitations/",
        invite_director_payload(),
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 403


def test_staff_cannot_invite_director(api_client):
    owner = create_user(username="director_invite_owner_for_staff")
    session = create_onboarding_session(actor=owner)
    staff = create_user(username="director_invite_staff")
    EstablishmentMembership.objects.create(
        user=staff,
        establishment=session.establishment,
        role=EstablishmentMembership.Role.STAFF,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    access_token = login(api_client, user=staff)

    response = api_client.post(
        f"/api/v1/onboarding-sessions/{session.id}/director-invitations/",
        invite_director_payload(),
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 403


def test_mark_ready_fails_without_director(api_client):
    owner = create_user(username="mark_ready_no_director_owner")
    session = create_onboarding_session(actor=owner)
    establishment = session.establishment
    EstablishmentActivityDescription.objects.create(
        establishment=establishment,
        description="A" * ACTIVITY_DESCRIPTION_MIN_LENGTH,
        submitted_by=owner,
        validated_at=timezone.now(),
    )
    business_unit = create_business_unit(
        establishment=establishment,
        key="hotel",
        label="Hotel",
    )

    ActivitySubject.objects.create(
        establishment=establishment,
        business_unit=business_unit,
        normalized_name="proprete",
        label="Proprete",
        active=True,
    )
    access_token = login(api_client, user=owner)

    response = api_client.post(
        f"/api/v1/onboarding-sessions/{session.id}/mark-ready/",
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 400
    blocker_codes = {blocker["code"] for blocker in response.json()["blockers"]}
    assert "missing_active_or_invited_director" in blocker_codes


def test_mark_ready_and_activate_succeed_with_invited_director(api_client):
    owner = create_user(username="mark_ready_with_director_owner")
    session = create_onboarding_session(actor=owner)
    create_ready_runtime(session, owner)
    access_token = login(api_client, user=owner)

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

    assert mark_ready_response.status_code == 200
    assert activate_response.status_code == 200
    session.refresh_from_db()
    assert session.status == OnboardingSession.Status.ACTIVATED
    assert session.establishment.status == Establishment.Status.ACTIVE


def test_director_invitation_rejects_second_director_with_different_email(api_client):
    owner = create_user(username="multi_director_owner")
    session = create_onboarding_session(actor=owner)
    access_token = login(api_client, user=owner)

    first_response = api_client.post(
        f"/api/v1/onboarding-sessions/{session.id}/director-invitations/",
        invite_director_payload(email="first-director@example.com"),
        format="json",
        **auth_headers(access_token),
    )
    second_response = api_client.post(
        f"/api/v1/onboarding-sessions/{session.id}/director-invitations/",
        invite_director_payload(email="second-director@example.com"),
        format="json",
        **auth_headers(access_token),
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 400
    assert second_response.json()["code"] == "director_invitation_already_exists"
    assert (
        EstablishmentMembership.objects.filter(
            establishment=session.establishment,
            role=EstablishmentMembership.Role.DIRECTOR,
            status__in=[
                EstablishmentMembership.Status.INVITED,
                EstablishmentMembership.Status.ACTIVE,
            ],
        ).count()
        == 1
    )


def test_director_invitation_rejects_second_director_when_active_director_exists(api_client):
    owner = create_user(username="active_director_slot_owner")
    session = create_onboarding_session(actor=owner)
    establishment = session.establishment
    active_director = User.objects.create_user(
        username="active_director_slot_user",
        email="active-dir@example.com",
        password="secret",
        status=User.Status.ACTIVE,
    )
    EstablishmentMembership.objects.create(
        user=active_director,
        establishment=establishment,
        role=EstablishmentMembership.Role.DIRECTOR,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    access_token = login(api_client, user=owner)

    response = api_client.post(
        f"/api/v1/onboarding-sessions/{session.id}/director-invitations/",
        invite_director_payload(email="another-director@example.com"),
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "director_invitation_already_exists"


def test_director_invitation_succeeds_after_deactivated_director_with_new_email(api_client):
    owner = create_user(username="replace_deactivated_director_owner")
    session = create_onboarding_session(actor=owner)
    establishment = session.establishment
    former_director = User.objects.create_user(
        username="former_director_user",
        email="former-director@example.com",
        password="unused",
        status=User.Status.PENDING,
    )
    former_director.set_unusable_password()
    former_director.save(update_fields=["password"])
    EstablishmentMembership.objects.create(
        user=former_director,
        establishment=establishment,
        role=EstablishmentMembership.Role.DIRECTOR,
        status=EstablishmentMembership.Status.DEACTIVATED,
    )
    access_token = login(api_client, user=owner)

    response = api_client.post(
        f"/api/v1/onboarding-sessions/{session.id}/director-invitations/",
        invite_director_payload(email="new-director@example.com"),
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 201
    assert response.json()["membership"]["status"] == "invited"
    assert response.json()["membership"]["user"]["email"] == "new-director@example.com"
    assert (
        EstablishmentMembership.objects.filter(
            establishment=establishment,
            role=EstablishmentMembership.Role.DIRECTOR,
            status=EstablishmentMembership.Status.INVITED,
        ).count()
        == 1
    )
    former_membership = EstablishmentMembership.objects.get(
        user=former_director,
        establishment=establishment,
    )
    assert former_membership.status == EstablishmentMembership.Status.DEACTIVATED


def test_director_invitation_reactivates_deactivated_director_with_same_email(api_client):
    owner = create_user(username="reactivate_director_owner")
    session = create_onboarding_session(actor=owner)
    establishment = session.establishment
    former_director = User.objects.create_user(
        username="reactivate_director_user",
        email="reactivate-director@example.com",
        password="unused",
        status=User.Status.PENDING,
    )
    former_director.set_unusable_password()
    former_director.save(update_fields=["password"])
    deactivated_membership = EstablishmentMembership.objects.create(
        user=former_director,
        establishment=establishment,
        role=EstablishmentMembership.Role.DIRECTOR,
        status=EstablishmentMembership.Status.DEACTIVATED,
    )
    access_token = login(api_client, user=owner)

    response = api_client.post(
        f"/api/v1/onboarding-sessions/{session.id}/director-invitations/",
        invite_director_payload(
            email="reactivate-director@example.com",
            first_name="Reactivated",
            last_name="Director",
        ),
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 201
    assert response.json()["membership"]["id"] == str(deactivated_membership.id)
    assert response.json()["membership"]["status"] == "invited"

    deactivated_membership.refresh_from_db()
    former_director.refresh_from_db()
    assert deactivated_membership.status == EstablishmentMembership.Status.INVITED
    assert former_director.first_name == "Reactivated"
    assert former_director.last_name == "Director"
