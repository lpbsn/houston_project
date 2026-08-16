from __future__ import annotations

from datetime import timedelta

import pytest
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from houston.accounts import tokens as auth_tokens
from houston.accounts.models import User
from houston.establishments.models import (
    EstablishmentInvitation,
    EstablishmentMembership,
    MembershipScope,
)
from houston.establishments.tests.membership_api_helpers import (
    auth_headers,
    create_membership,
    create_user,
    ensure_csrf,
    login,
)
from houston.establishments.tests.taxonomy_helpers import (
    business_unit_scope_payload,
    create_business_unit,
    create_membership_with_business_unit_scope,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


def _invite_staff(*, api_client, owner, establishment, business_unit, email: str):
    access_token = login(api_client, identifier=owner.email)
    csrf_token = ensure_csrf(api_client)
    response = api_client.post(
        f"/api/v1/establishments/{establishment.id}/membership-invitations/",
        {
            "email": email,
            "first_name": "Invited",
            "last_name": "Staff",
            "role": EstablishmentMembership.Role.STAFF,
            "scopes": [business_unit_scope_payload(business_unit)],
        },
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
        **auth_headers(access_token),
    )
    assert response.status_code == 201, response.json()
    return response.json(), access_token


def test_membership_detail_exposes_invitation_fields_without_token(api_client):
    owner = create_user(username="owner_detail_invite")
    owner_membership = create_membership(
        user=owner,
        role=EstablishmentMembership.Role.OWNER,
        name="Nice",
    )
    establishment = owner_membership.establishment
    business_unit = create_business_unit(establishment=establishment, key="cuisine")

    invite_body, access_token = _invite_staff(
        api_client=api_client,
        owner=owner,
        establishment=establishment,
        business_unit=business_unit,
        email="pending-staff@example.com",
    )
    membership_id = invite_body["membership"]["id"]

    detail = api_client.get(
        f"/api/v1/establishments/{establishment.id}/memberships/{membership_id}/",
        **auth_headers(access_token),
    )
    assert detail.status_code == 200
    body = detail.json()
    assert body["last_invited_at"] is not None
    assert body["pending_invitation"] is not None
    assert body["pending_invitation"]["is_expired"] is False
    assert body["pending_invitation"]["expires_at"]
    assert body["permission_hints"]["can_reinvite"] is True
    assert "invitation_token" not in body
    assert "invitation_accept_path" not in body


@override_settings(HOUSTON_INVITATION_EMAIL_ENABLED=False)
def test_reinvite_revokes_previous_token_and_returns_disabled_email_status(api_client):
    owner = create_user(username="owner_reinvite")
    owner_membership = create_membership(
        user=owner,
        role=EstablishmentMembership.Role.OWNER,
        name="Nice",
    )
    establishment = owner_membership.establishment
    business_unit = create_business_unit(establishment=establishment, key="cuisine")

    invite_body, access_token = _invite_staff(
        api_client=api_client,
        owner=owner,
        establishment=establishment,
        business_unit=business_unit,
        email="reinvite-staff@example.com",
    )
    membership_id = invite_body["membership"]["id"]
    old_token = invite_body["invitation_token"]
    old_digest = auth_tokens.digest_token(old_token)

    csrf_token = ensure_csrf(api_client)
    reinvite = api_client.post(
        f"/api/v1/establishments/{establishment.id}/memberships/{membership_id}/reinvite/",
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
        **auth_headers(access_token),
    )
    assert reinvite.status_code == 200, reinvite.json()
    body = reinvite.json()
    assert body["email_scheduling_status"] == "disabled"
    assert body["invitation_token"]
    assert body["invitation_token"] != old_token
    assert body["invitation_accept_path"] == f"/invitations/{body['invitation_token']}"
    assert body["membership"]["permission_hints"]["can_reinvite"] is True
    assert body["membership"]["last_invited_at"] is not None
    assert body["membership"]["pending_invitation"] is not None

    old_invitation = EstablishmentInvitation.objects.get(token_digest=old_digest)
    assert old_invitation.revoked_at is not None

    accept = api_client.post(
        f"/api/v1/invitations/{old_token}/accept/",
        {
            "password": "SecurePass123!",
            "password_confirmation": "SecurePass123!",
            "refresh_token_transport": "cookie",
        },
        format="json",
        HTTP_X_CSRFTOKEN=ensure_csrf(api_client),
    )
    assert accept.status_code in {400, 404, 409}


@override_settings(HOUSTON_INVITATION_EMAIL_ENABLED=True)
def test_reinvite_reports_requested_when_email_enabled(api_client):
    owner = create_user(username="owner_reinvite_email")
    owner_membership = create_membership(
        user=owner,
        role=EstablishmentMembership.Role.OWNER,
        name="Nice",
    )
    establishment = owner_membership.establishment
    business_unit = create_business_unit(establishment=establishment, key="cuisine")

    invite_body, access_token = _invite_staff(
        api_client=api_client,
        owner=owner,
        establishment=establishment,
        business_unit=business_unit,
        email="reinvite-email@example.com",
    )
    membership_id = invite_body["membership"]["id"]

    csrf_token = ensure_csrf(api_client)
    reinvite = api_client.post(
        f"/api/v1/establishments/{establishment.id}/memberships/{membership_id}/reinvite/",
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
        **auth_headers(access_token),
    )
    assert reinvite.status_code == 200
    assert reinvite.json()["email_scheduling_status"] == "requested"


def test_reinvite_conflict_for_active_membership(api_client):
    owner = create_user(username="owner_reinvite_active")
    owner_membership = create_membership(
        user=owner,
        role=EstablishmentMembership.Role.OWNER,
        name="Nice",
    )
    staff = EstablishmentMembership.objects.create(
        user=create_user(username="active_staff_reinvite"),
        establishment=owner_membership.establishment,
        role=EstablishmentMembership.Role.STAFF,
        status=EstablishmentMembership.Status.ACTIVE,
    )

    access_token = login(api_client, identifier=owner.email)
    csrf_token = ensure_csrf(api_client)
    response = api_client.post(
        (
            f"/api/v1/establishments/{owner_membership.establishment_id}/memberships/"
            f"{staff.id}/reinvite/"
        ),
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
        **auth_headers(access_token),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "membership_reinvite_conflict"


def test_reinvite_forbidden_for_staff_actor(api_client):
    owner = create_user(username="owner_for_staff_actor")
    owner_membership = create_membership(
        user=owner,
        role=EstablishmentMembership.Role.OWNER,
        name="Nice",
    )
    establishment = owner_membership.establishment
    business_unit = create_business_unit(establishment=establishment, key="cuisine")
    invite_body, _ = _invite_staff(
        api_client=api_client,
        owner=owner,
        establishment=establishment,
        business_unit=business_unit,
        email="target-for-staff@example.com",
    )

    staff_actor = create_user(username="staff_cannot_reinvite")
    staff_membership = EstablishmentMembership.objects.create(
        user=staff_actor,
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    MembershipScope.objects.create(
        membership=staff_membership,
        business_unit=business_unit,
    )

    access_token = login(api_client, identifier=staff_actor.email)
    csrf_token = ensure_csrf(api_client)
    response = api_client.post(
        (
            f"/api/v1/establishments/{establishment.id}/memberships/"
            f"{invite_body['membership']['id']}/reinvite/"
        ),
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
        **auth_headers(access_token),
    )
    assert response.status_code == 403


def test_reinvite_not_found_for_foreign_membership(api_client):
    owner = create_user(username="owner_reinvite_404")
    owner_membership = create_membership(
        user=owner,
        role=EstablishmentMembership.Role.OWNER,
        name="Nice",
    )
    foreign = create_membership(
        user=create_user(username="foreign_invited", status=User.Status.PENDING),
        role=EstablishmentMembership.Role.STAFF,
        name="Cannes",
        membership_status=EstablishmentMembership.Status.INVITED,
    )

    access_token = login(api_client, identifier=owner.email)
    csrf_token = ensure_csrf(api_client)
    response = api_client.post(
        (
            f"/api/v1/establishments/{owner_membership.establishment_id}/memberships/"
            f"{foreign.id}/reinvite/"
        ),
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
        **auth_headers(access_token),
    )
    assert response.status_code == 404


def test_sequential_reinvite_keeps_only_last_invitation_valid(api_client):
    owner = create_user(username="owner_sequential_reinvite")
    owner_membership = create_membership(
        user=owner,
        role=EstablishmentMembership.Role.OWNER,
        name="Nice",
    )
    establishment = owner_membership.establishment
    business_unit = create_business_unit(establishment=establishment, key="cuisine")
    invite_body, access_token = _invite_staff(
        api_client=api_client,
        owner=owner,
        establishment=establishment,
        business_unit=business_unit,
        email="sequential@example.com",
    )
    membership_id = invite_body["membership"]["id"]
    first_token = invite_body["invitation_token"]

    csrf_token = ensure_csrf(api_client)
    second = api_client.post(
        f"/api/v1/establishments/{establishment.id}/memberships/{membership_id}/reinvite/",
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
        **auth_headers(access_token),
    )
    assert second.status_code == 200
    second_token = second.json()["invitation_token"]

    csrf_token = ensure_csrf(api_client)
    third = api_client.post(
        f"/api/v1/establishments/{establishment.id}/memberships/{membership_id}/reinvite/",
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
        **auth_headers(access_token),
    )
    assert third.status_code == 200
    third_token = third.json()["invitation_token"]

    assert first_token != second_token != third_token
    live = EstablishmentInvitation.objects.filter(
        membership_id=membership_id,
        accepted_at__isnull=True,
        revoked_at__isnull=True,
    )
    assert live.count() == 1
    assert live.get().token_digest == auth_tokens.digest_token(third_token)


def test_detail_marks_pending_invitation_expired(api_client):
    owner = create_user(username="owner_expired_invite")
    owner_membership = create_membership(
        user=owner,
        role=EstablishmentMembership.Role.OWNER,
        name="Nice",
    )
    pending_user = create_user(
        username="expired_invitee",
        status=User.Status.PENDING,
    )
    membership = EstablishmentMembership.objects.create(
        user=pending_user,
        establishment=owner_membership.establishment,
        role=EstablishmentMembership.Role.STAFF,
        status=EstablishmentMembership.Status.INVITED,
    )
    EstablishmentInvitation.objects.create(
        membership=membership,
        token_digest=auth_tokens.digest_token("expired-raw-token"),
        expires_at=timezone.now() - timedelta(hours=1),
    )

    access_token = login(api_client, identifier=owner.email)
    detail = api_client.get(
        (
            f"/api/v1/establishments/{owner_membership.establishment_id}/memberships/"
            f"{membership.id}/"
        ),
        **auth_headers(access_token),
    )
    assert detail.status_code == 200
    body = detail.json()
    assert body["pending_invitation"]["is_expired"] is True
    assert body["permission_hints"]["can_reinvite"] is True


@override_settings(HOUSTON_INVITATION_EMAIL_ENABLED=True)
def test_manager_out_of_scope_cannot_reinvite(api_client, monkeypatch):
    owner = create_user(username="owner_mgr_oos_reinvite")
    owner_membership = create_membership(
        user=owner,
        role=EstablishmentMembership.Role.OWNER,
        name="Nice",
    )
    establishment = owner_membership.establishment
    actor_unit = create_business_unit(establishment=establishment, key="housekeeping")
    target_unit = create_business_unit(establishment=establishment, key="security")

    invite_body, _ = _invite_staff(
        api_client=api_client,
        owner=owner,
        establishment=establishment,
        business_unit=target_unit,
        email="oos-staff@example.com",
    )
    membership_id = invite_body["membership"]["id"]

    manager = create_user(username="manager_oos_reinvite")
    manager_membership = EstablishmentMembership.objects.create(
        user=manager,
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    create_membership_with_business_unit_scope(
        membership=manager_membership,
        business_unit=actor_unit,
    )

    before = list(
        EstablishmentInvitation.objects.filter(membership_id=membership_id)
        .order_by("id")
        .values_list("id", "token_digest", "revoked_at")
    )
    scheduled: list[object] = []
    monkeypatch.setattr(
        "houston.establishments.invitation_email.schedule_establishment_invitation_email",
        lambda **kwargs: scheduled.append(kwargs) or "requested",
    )

    access_token = login(api_client, identifier=manager.email)
    detail = api_client.get(
        f"/api/v1/establishments/{establishment.id}/memberships/{membership_id}/",
        **auth_headers(access_token),
    )
    assert detail.status_code == 200
    assert detail.json()["permission_hints"]["can_reinvite"] is False

    csrf_token = ensure_csrf(api_client)
    response = api_client.post(
        f"/api/v1/establishments/{establishment.id}/memberships/{membership_id}/reinvite/",
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
        **auth_headers(access_token),
    )
    assert response.status_code == 403
    assert response.json()["code"] == "membership_management_forbidden"

    after = list(
        EstablishmentInvitation.objects.filter(membership_id=membership_id)
        .order_by("id")
        .values_list("id", "token_digest", "revoked_at")
    )
    assert after == before
    assert scheduled == []


@override_settings(HOUSTON_INVITATION_EMAIL_ENABLED=False)
def test_manager_in_scope_can_reinvite(api_client):
    owner = create_user(username="owner_mgr_in_scope_reinvite")
    owner_membership = create_membership(
        user=owner,
        role=EstablishmentMembership.Role.OWNER,
        name="Nice",
    )
    establishment = owner_membership.establishment
    business_unit = create_business_unit(establishment=establishment, key="housekeeping")

    invite_body, _ = _invite_staff(
        api_client=api_client,
        owner=owner,
        establishment=establishment,
        business_unit=business_unit,
        email="in-scope-staff@example.com",
    )
    membership_id = invite_body["membership"]["id"]
    old_token = invite_body["invitation_token"]

    manager = create_user(username="manager_in_scope_reinvite")
    manager_membership = EstablishmentMembership.objects.create(
        user=manager,
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    create_membership_with_business_unit_scope(
        membership=manager_membership,
        business_unit=business_unit,
    )

    access_token = login(api_client, identifier=manager.email)
    detail = api_client.get(
        f"/api/v1/establishments/{establishment.id}/memberships/{membership_id}/",
        **auth_headers(access_token),
    )
    assert detail.status_code == 200
    assert detail.json()["permission_hints"]["can_reinvite"] is True

    csrf_token = ensure_csrf(api_client)
    reinvite = api_client.post(
        f"/api/v1/establishments/{establishment.id}/memberships/{membership_id}/reinvite/",
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
        **auth_headers(access_token),
    )
    assert reinvite.status_code == 200, reinvite.json()
    body = reinvite.json()
    assert body["invitation_token"]
    assert body["invitation_token"] != old_token
    assert body["membership"]["permission_hints"]["can_reinvite"] is True


@override_settings(HOUSTON_INVITATION_EMAIL_ENABLED=False)
def test_director_can_reinvite(api_client):
    owner = create_user(username="owner_for_director_reinvite")
    owner_membership = create_membership(
        user=owner,
        role=EstablishmentMembership.Role.OWNER,
        name="Nice",
    )
    establishment = owner_membership.establishment
    business_unit = create_business_unit(establishment=establishment, key="cuisine")

    invite_body, _ = _invite_staff(
        api_client=api_client,
        owner=owner,
        establishment=establishment,
        business_unit=business_unit,
        email="director-reinvite-staff@example.com",
    )
    membership_id = invite_body["membership"]["id"]
    old_token = invite_body["invitation_token"]

    director = create_user(username="director_reinvite")
    EstablishmentMembership.objects.create(
        user=director,
        establishment=establishment,
        role=EstablishmentMembership.Role.DIRECTOR,
        status=EstablishmentMembership.Status.ACTIVE,
    )

    access_token = login(api_client, identifier=director.email)
    csrf_token = ensure_csrf(api_client)
    reinvite = api_client.post(
        f"/api/v1/establishments/{establishment.id}/memberships/{membership_id}/reinvite/",
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
        **auth_headers(access_token),
    )
    assert reinvite.status_code == 200, reinvite.json()
    assert reinvite.json()["invitation_token"] != old_token
