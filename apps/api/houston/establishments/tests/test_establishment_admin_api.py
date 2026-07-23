from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from rest_framework.test import APIClient

from houston.accounts.models import User, UserSession
from houston.action_plans.constants import (
    EXECUTION_STATUS_CANCELED,
    EXECUTION_STATUS_DONE,
    EXECUTION_STATUS_IN_PROGRESS,
    EXECUTION_STATUS_PENDING_VALIDATION,
    EXECUTION_STATUS_SCHEDULED,
)
from houston.action_plans.tests.helpers import create_execution
from houston.establishments.establishment_admin_selectors import (
    observation_weekly_average_window,
)
from houston.establishments.models import (
    Establishment,
    EstablishmentMembership,
)
from houston.observations.models import Observation
from houston.organizations.models import Organization
from houston.signals.models import Signal
from houston.testing.auth import auth_headers, login
from houston.testing.factories import create_membership, create_user
from houston.testing.pipeline import create_observation
from houston.testing.taxonomy import (
    create_activity_subject,
    create_business_unit,
    create_membership_with_business_unit_scope,
    create_signal_v3_for_membership,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


def _admin_path(establishment_id, suffix: str = "overview/") -> str:
    return f"/api/v1/establishments/{establishment_id}/admin/{suffix}"


def _selected_establishment_id(user: User):
    session = UserSession.objects.filter(user=user).order_by("-created_at").first()
    assert session is not None
    return session.selected_establishment_id


def _setup_two_active_establishments():
    organization = Organization.objects.create(
        name=f"Org {uuid.uuid4().hex[:6]}",
        status=Organization.Status.ACTIVE,
    )
    owner = create_user(username=f"owner_{uuid.uuid4().hex[:6]}")
    est_a = Establishment.objects.create(
        name="Hotel A",
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )
    est_b = Establishment.objects.create(
        name="Hotel B",
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )
    create_membership(
        establishment=est_a,
        user=owner,
        role=EstablishmentMembership.Role.OWNER,
    )
    create_membership(
        establishment=est_b,
        user=owner,
        role=EstablishmentMembership.Role.OWNER,
    )
    return owner, organization, est_a, est_b


def test_owner_reads_other_active_establishment_without_switching(api_client):
    owner, _organization, est_a, est_b = _setup_two_active_establishments()
    access_token = login(api_client, user=owner)
    session = UserSession.objects.filter(user=owner).order_by("-created_at").first()
    assert session is not None
    session.selected_establishment = est_a
    session.save(update_fields=["selected_establishment", "updated_at"])
    before = est_a.id

    response = api_client.get(
        _admin_path(est_b.id),
        **auth_headers(access_token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(est_b.id)
    assert body["name"] == "Hotel B"
    assert "metrics" in body
    assert "operational_config" in body
    assert _selected_establishment_id(owner) == before


def test_director_path_ok_cross_est_forbidden(api_client):
    owner, _organization, est_a, est_b = _setup_two_active_establishments()
    director = create_user(username=f"dir_{uuid.uuid4().hex[:6]}")
    create_membership(
        establishment=est_a,
        user=director,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    access_token = login(api_client, user=director)

    ok = api_client.get(_admin_path(est_a.id), **auth_headers(access_token))
    assert ok.status_code == 200

    forbidden = api_client.get(_admin_path(est_b.id), **auth_headers(access_token))
    assert forbidden.status_code == 403
    assert forbidden.json()["code"] == "establishment_admin_forbidden"
    del owner


def test_manager_staff_forbidden_and_draft_not_found(api_client, imported_catalog):
    del imported_catalog
    owner, organization, est_a, _est_b = _setup_two_active_establishments()
    draft = Establishment.objects.create(
        name="Draft Hotel",
        organization=organization,
        status=Establishment.Status.DRAFT,
    )
    create_membership(
        establishment=draft,
        user=owner,
        role=EstablishmentMembership.Role.OWNER,
    )
    manager = create_user(username=f"mgr_{uuid.uuid4().hex[:6]}")
    manager_membership = create_membership(
        establishment=est_a,
        user=manager,
        role=EstablishmentMembership.Role.MANAGER,
    )
    bu = create_business_unit(establishment=est_a, key="mgr_pole", label="Mgr pole")
    create_membership_with_business_unit_scope(
        membership=manager_membership,
        business_unit=bu,
    )
    access_token = login(api_client, user=manager)
    assert (
        api_client.get(_admin_path(est_a.id), **auth_headers(access_token)).status_code
        == 403
    )

    owner_token = login(api_client, user=owner)
    draft_response = api_client.get(
        _admin_path(draft.id),
        **auth_headers(owner_token),
    )
    assert draft_response.status_code == 404


def test_overview_metrics_and_operational_config(api_client, imported_catalog):
    del imported_catalog
    owner, _organization, est_a, _est_b = _setup_two_active_establishments()
    owner_membership = EstablishmentMembership.objects.get(
        user=owner,
        establishment=est_a,
    )
    bu = create_business_unit(establishment=est_a, key="cuisine", label="Cuisine")
    subject = create_activity_subject(
        establishment=est_a,
        business_unit=bu,
        label="Stock",
    )

    create_signal_v3_for_membership(
        owner_membership,
        affected_business_unit=bu,
        responsible_business_unit=bu,
        activity_subject=subject,
        status=Signal.Status.OPEN,
        title="Open signal",
    )
    create_signal_v3_for_membership(
        owner_membership,
        affected_business_unit=bu,
        responsible_business_unit=bu,
        activity_subject=subject,
        status=Signal.Status.IN_PROGRESS,
        title="Progress signal",
    )
    create_signal_v3_for_membership(
        owner_membership,
        affected_business_unit=bu,
        responsible_business_unit=bu,
        activity_subject=subject,
        status=Signal.Status.RESOLVED,
        title="Resolved signal",
    )

    for status, title in [
        (EXECUTION_STATUS_SCHEDULED, "Scheduled"),
        (EXECUTION_STATUS_IN_PROGRESS, "In progress"),
        (EXECUTION_STATUS_PENDING_VALIDATION, "Pending"),
        (EXECUTION_STATUS_DONE, "Done"),
        (EXECUTION_STATUS_CANCELED, "Canceled"),
    ]:
        create_execution(
            owner_membership,
            business_unit=bu,
            title=title,
            status=status,
        )

    window_start, window_end = observation_weekly_average_window()
    inside = window_start + timedelta(days=3)
    current_week = window_end + timedelta(days=1)

    for submitted_at, origin in [
        (inside, Observation.Origin.DIRECT_REPORT),
        (inside, Observation.Origin.DIRECT_REPORT),
        (inside, Observation.Origin.ACTION_PLAN_TASK),
        (current_week, Observation.Origin.DIRECT_REPORT),
    ]:
        observation = create_observation(membership=owner_membership)
        observation.origin = origin
        observation.submitted_at = submitted_at
        observation.save(update_fields=["origin", "submitted_at", "updated_at"])

    access_token = login(api_client, user=owner)
    response = api_client.get(_admin_path(est_a.id), **auth_headers(access_token))
    assert response.status_code == 200
    metrics = response.json()["metrics"]
    assert metrics["signals_open"] == 1
    assert metrics["signals_in_progress"] == 1
    assert metrics["action_plans_in_progress"] == 2
    assert metrics["action_plans_scheduled"] == 1
    assert metrics["observations_weekly_average"] == 0.3

    config = response.json()["operational_config"]
    assert config["status"] == "configured"
    assert config["active_business_unit_count"] == 1
    assert config["active_activity_subject_count"] == 1
    assert config["active_business_units_without_subjects_count"] == 0


def test_operational_config_needs_attention_without_subjects(api_client, imported_catalog):
    del imported_catalog
    owner, _organization, est_a, _est_b = _setup_two_active_establishments()
    create_business_unit(establishment=est_a, key="orphan", label="Orphan pole")
    access_token = login(api_client, user=owner)
    response = api_client.get(_admin_path(est_a.id), **auth_headers(access_token))
    assert response.status_code == 200
    assert response.json()["operational_config"]["status"] == "needs_attention"


def test_memberships_exclude_owner_and_refuse_owner_mutations(api_client, imported_catalog):
    del imported_catalog
    owner, _organization, est_a, _est_b = _setup_two_active_establishments()
    director = create_user(username=f"dir_{uuid.uuid4().hex[:6]}")
    director_membership = create_membership(
        establishment=est_a,
        user=director,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    owner_membership = EstablishmentMembership.objects.get(
        user=owner,
        establishment=est_a,
    )
    access_token = login(api_client, user=owner)
    before = _selected_establishment_id(owner)

    listed = api_client.get(
        _admin_path(est_a.id, "memberships/"),
        **auth_headers(access_token),
    )
    assert listed.status_code == 200
    ids = {row["id"] for row in listed.json()["results"]}
    assert str(director_membership.id) in ids
    assert str(owner_membership.id) not in ids

    invite_owner = api_client.post(
        _admin_path(est_a.id, "membership-invitations/"),
        {
            "email": f"owner_invite_{uuid.uuid4().hex[:6]}@example.com",
            "first_name": "Own",
            "last_name": "Er",
            "role": "owner",
        },
        format="json",
        **auth_headers(access_token),
    )
    assert invite_owner.status_code in {400, 403}

    deactivate_owner = api_client.post(
        _admin_path(est_a.id, f"memberships/{owner_membership.id}/deactivate/"),
        **auth_headers(access_token),
    )
    assert deactivate_owner.status_code == 403
    assert deactivate_owner.json()["code"] == "establishment_admin_owner_forbidden"
    assert _selected_establishment_id(owner) == before


def test_director_cannot_manage_director_or_invite_director(api_client, imported_catalog):
    del imported_catalog
    owner, _organization, est_a, _est_b = _setup_two_active_establishments()
    director = create_user(username=f"dir_{uuid.uuid4().hex[:6]}")
    other_director = create_user(username=f"dir2_{uuid.uuid4().hex[:6]}")
    create_membership(
        establishment=est_a,
        user=director,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    other = create_membership(
        establishment=est_a,
        user=other_director,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    access_token = login(api_client, user=director)

    invite = api_client.post(
        _admin_path(est_a.id, "membership-invitations/"),
        {
            "email": f"dir_invite_{uuid.uuid4().hex[:6]}@example.com",
            "first_name": "New",
            "last_name": "Dir",
            "role": "director",
        },
        format="json",
        **auth_headers(access_token),
    )
    assert invite.status_code == 403

    patch = api_client.patch(
        _admin_path(est_a.id, f"memberships/{other.id}/"),
        {"role": "manager"},
        format="json",
        **auth_headers(access_token),
    )
    assert patch.status_code == 403

    deactivate = api_client.post(
        _admin_path(est_a.id, f"memberships/{other.id}/deactivate/"),
        **auth_headers(access_token),
    )
    assert deactivate.status_code == 403
    del owner


def test_org_owner_with_local_director_keeps_owner_admin_powers(
    api_client, imported_catalog
):
    del imported_catalog
    organization = Organization.objects.create(
        name=f"Org {uuid.uuid4().hex[:6]}",
        status=Organization.Status.ACTIVE,
    )
    actor = create_user(username=f"org_owner_dir_{uuid.uuid4().hex[:6]}")
    est_a = Establishment.objects.create(
        name="Hotel A",
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )
    est_b = Establishment.objects.create(
        name="Hotel B",
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )
    create_membership(
        establishment=est_a,
        user=actor,
        role=EstablishmentMembership.Role.OWNER,
    )
    actor_director_on_b = create_membership(
        establishment=est_b,
        user=actor,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    other_director = create_user(username=f"dir_other_{uuid.uuid4().hex[:6]}")
    other_director_membership = create_membership(
        establishment=est_b,
        user=other_director,
        role=EstablishmentMembership.Role.DIRECTOR,
    )

    other_org = Organization.objects.create(
        name=f"Other {uuid.uuid4().hex[:6]}",
        status=Organization.Status.ACTIVE,
    )
    foreign_owner = create_user(username=f"foreign_owner_{uuid.uuid4().hex[:6]}")
    foreign_est = Establishment.objects.create(
        name="Foreign Hotel",
        organization=other_org,
        status=Establishment.Status.ACTIVE,
    )
    create_membership(
        establishment=foreign_est,
        user=foreign_owner,
        role=EstablishmentMembership.Role.OWNER,
    )

    access_token = login(api_client, user=actor)
    session = UserSession.objects.filter(user=actor).order_by("-created_at").first()
    assert session is not None
    session.selected_establishment = est_a
    session.save(update_fields=["selected_establishment", "updated_at"])

    invite = api_client.post(
        _admin_path(est_b.id, "membership-invitations/"),
        {
            "email": f"dir_invite_{uuid.uuid4().hex[:6]}@example.com",
            "first_name": "New",
            "last_name": "Dir",
            "role": "director",
        },
        format="json",
        **auth_headers(access_token),
    )
    assert invite.status_code == 201
    invited_membership_id = invite.json()["membership"]["id"]

    manage = api_client.post(
        _admin_path(
            est_b.id, f"memberships/{other_director_membership.id}/deactivate/"
        ),
        **auth_headers(access_token),
    )
    assert manage.status_code == 200
    other_director_membership.refresh_from_db()
    assert other_director_membership.status == EstablishmentMembership.Status.DEACTIVATED

    deactivate_invited = api_client.post(
        _admin_path(est_b.id, f"memberships/{invited_membership_id}/deactivate/"),
        **auth_headers(access_token),
    )
    assert deactivate_invited.status_code == 200

    deactivate_last = api_client.post(
        _admin_path(est_b.id, f"memberships/{actor_director_on_b.id}/deactivate/"),
        **auth_headers(access_token),
    )
    assert deactivate_last.status_code == 409
    assert deactivate_last.json()["code"] == "director_coverage_invariant"
    actor_director_on_b.refresh_from_db()
    assert actor_director_on_b.status == EstablishmentMembership.Status.ACTIVE

    foreign_token = login(api_client, user=foreign_owner)
    foreign_forbidden = api_client.get(
        _admin_path(est_b.id),
        **auth_headers(foreign_token),
    )
    assert foreign_forbidden.status_code == 403
    assert foreign_forbidden.json()["code"] == "establishment_admin_forbidden"


def test_membership_other_establishment_not_found(api_client, imported_catalog):
    del imported_catalog
    owner, _organization, est_a, est_b = _setup_two_active_establishments()
    staff = create_user(username=f"staff_{uuid.uuid4().hex[:6]}")
    staff_membership = create_membership(
        establishment=est_b,
        user=staff,
        role=EstablishmentMembership.Role.STAFF,
    )
    bu = create_business_unit(establishment=est_b, key="staff_pole", label="Staff pole")
    create_membership_with_business_unit_scope(
        membership=staff_membership,
        business_unit=bu,
    )
    access_token = login(api_client, user=owner)

    response = api_client.get(
        _admin_path(est_a.id, f"memberships/{staff_membership.id}/"),
        **auth_headers(access_token),
    )
    assert response.status_code == 404


def test_admin_mutations_do_not_change_selected_establishment(api_client, imported_catalog):
    del imported_catalog
    owner, _organization, est_a, est_b = _setup_two_active_establishments()
    bu = create_business_unit(establishment=est_a, key="salle", label="Salle")
    create_activity_subject(establishment=est_a, business_unit=bu, label="Service")
    access_token = login(api_client, user=owner)
    session = UserSession.objects.filter(user=owner).order_by("-created_at").first()
    assert session is not None
    session.selected_establishment = est_b
    session.save(update_fields=["selected_establishment", "updated_at"])
    before = est_b.id

    invite = api_client.post(
        _admin_path(est_a.id, "membership-invitations/"),
        {
            "email": f"staff_{uuid.uuid4().hex[:6]}@example.com",
            "first_name": "Sta",
            "last_name": "Ff",
            "role": "staff",
            "scopes": [{"scope_type": "business_unit", "scope_id": str(bu.id)}],
        },
        format="json",
        **auth_headers(access_token),
    )
    assert invite.status_code == 201
    assert _selected_establishment_id(owner) == before

    membership_id = invite.json()["membership"]["id"]
    deactivate = api_client.post(
        _admin_path(est_a.id, f"memberships/{membership_id}/deactivate/"),
        **auth_headers(access_token),
    )
    assert deactivate.status_code == 200
    assert _selected_establishment_id(owner) == before


def test_team_memberships_endpoint_unchanged_session_bound(api_client):
    owner, _organization, est_a, est_b = _setup_two_active_establishments()
    access_token = login(api_client, user=owner)
    session = UserSession.objects.filter(user=owner).order_by("-created_at").first()
    assert session is not None
    session.selected_establishment = est_a
    session.save(update_fields=["selected_establishment", "updated_at"])

    ok = api_client.get(
        f"/api/v1/establishments/{est_a.id}/memberships/",
        **auth_headers(access_token),
    )
    assert ok.status_code == 200

    other = api_client.get(
        f"/api/v1/establishments/{est_b.id}/memberships/",
        **auth_headers(access_token),
    )
    assert other.status_code == 404


def test_filter_options_path_scoped_poles(api_client, imported_catalog):
    del imported_catalog
    owner, _organization, est_a, est_b = _setup_two_active_establishments()
    create_business_unit(establishment=est_a, key="pole_a", label="Pole A")
    create_business_unit(establishment=est_b, key="pole_b", label="Pole B")
    access_token = login(api_client, user=owner)
    response = api_client.get(
        _admin_path(est_a.id, "memberships/filter-options/"),
        **auth_headers(access_token),
    )
    assert response.status_code == 200
    body = response.json()
    assert "owner" not in body["roles"]
    labels = {row["label"] for row in body["business_units"]}
    assert "Pole A" in labels
    assert "Pole B" not in labels
