from __future__ import annotations

import uuid

import pytest
from rest_framework.test import APIClient

from houston.accounts.models import User
from houston.establishments.models import (
    ActivitySubject,
    BusinessUnit,
    Establishment,
    EstablishmentMembership,
)
from houston.establishments.tests.conftest import TEST_PASSWORD
from houston.establishments.tests.taxonomy_helpers import (
    create_business_unit,
    create_establishment,
    create_membership_with_business_unit_scope,
)
from houston.organizations.models import Organization

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


def create_user(*, username: str) -> User:
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password=TEST_PASSWORD,
        status=User.Status.ACTIVE,
    )


def login(api_client: APIClient, *, user: User) -> str:
    csrf = api_client.get("/api/v1/auth/csrf/").cookies["csrftoken"].value
    response = api_client.post(
        "/api/v1/auth/login/",
        {"identifier": user.email, "password": TEST_PASSWORD},
        format="json",
        HTTP_X_CSRFTOKEN=csrf,
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def auth_headers(access_token: str) -> dict:
    return {"HTTP_AUTHORIZATION": f"Bearer {access_token}"}


def business_units_url(establishment_id) -> str:
    return f"/api/v1/establishments/{establishment_id}/business-units/"


def business_unit_detail_url(establishment_id, business_unit_id) -> str:
    return f"/api/v1/establishments/{establishment_id}/business-units/{business_unit_id}/"


def business_unit_deactivate_url(establishment_id, business_unit_id) -> str:
    return (
        f"/api/v1/establishments/{establishment_id}/business-units/{business_unit_id}/deactivate/"
    )


def activity_subjects_url(establishment_id, business_unit_id) -> str:
    return (
        f"/api/v1/establishments/{establishment_id}/business-units/{business_unit_id}/"
        "activity-subjects/"
    )


def activity_subject_deactivate_url(establishment_id, activity_subject_id) -> str:
    return (
        f"/api/v1/establishments/{establishment_id}/activity-subjects/"
        f"{activity_subject_id}/deactivate/"
    )


def create_membership_for_user(
    *,
    user: User,
    establishment: Establishment,
    role: str,
) -> EstablishmentMembership:
    return EstablishmentMembership.objects.create(
        user=user,
        establishment=establishment,
        role=role,
        status=EstablishmentMembership.Status.ACTIVE,
    )


def setup_active_establishment_with_runtime(*, owner_username: str = "runtime_owner"):
    establishment = create_establishment()
    owner = create_user(username=owner_username)
    create_membership_for_user(
        user=owner,
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    hotel = create_business_unit(
        establishment=establishment,
        key="hotel",
        label="Hôtel",
    )
    maintenance = create_business_unit(
        establishment=establishment,
        key="maintenance",
        label="Maintenance",
        unit_type=BusinessUnit.UnitType.TRANSVERSAL,
    )
    create_activity_subject(
        establishment=establishment,
        business_unit=hotel,
        label="Propreté chambre",
    )
    create_activity_subject(
        establishment=establishment,
        business_unit=maintenance,
        label="Climatisation",
    )
    return establishment, owner, hotel, maintenance


def create_activity_subject(
    *,
    establishment: Establishment,
    business_unit: BusinessUnit,
    label: str,
) -> ActivitySubject:
    from houston.establishments.taxonomy_normalization import normalize_activity_subject_name

    return ActivitySubject.objects.create(
        establishment=establishment,
        business_unit=business_unit,
        normalized_name=normalize_activity_subject_name(label),
        label=label,
        source=ActivitySubject.Source.MANUAL,
        active=True,
    )


def test_owner_can_create_update_and_deactivate_runtime_taxonomy(api_client):
    establishment, owner, hotel, maintenance = setup_active_establishment_with_runtime()
    access_token = login(api_client, user=owner)

    create_response = api_client.post(
        business_units_url(establishment.id),
        {"label": "Restaurant", "description": "Service restauration"},
        format="json",
        **auth_headers(access_token),
    )
    assert create_response.status_code == 201
    restaurant_id = create_response.json()["id"]
    assert create_response.json()["description"] == "Service restauration"

    patch_response = api_client.patch(
        business_unit_detail_url(establishment.id, restaurant_id),
        {"description": "Restauration et bar"},
        format="json",
        **auth_headers(access_token),
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["description"] == "Restauration et bar"

    subject_response = api_client.post(
        activity_subjects_url(establishment.id, restaurant_id),
        {"label": "Cuisine"},
        format="json",
        **auth_headers(access_token),
    )
    assert subject_response.status_code == 201
    subject_id = subject_response.json()["id"]

    second_subject_response = api_client.post(
        activity_subjects_url(establishment.id, restaurant_id),
        {"label": "Service"},
        format="json",
        **auth_headers(access_token),
    )
    assert second_subject_response.status_code == 201

    deactivate_subject_response = api_client.post(
        activity_subject_deactivate_url(establishment.id, subject_id),
        format="json",
        **auth_headers(access_token),
    )
    assert deactivate_subject_response.status_code == 200
    assert (
        ActivitySubject.objects.get(id=subject_id).active is False
    )

    deactivate_bu_response = api_client.post(
        business_unit_deactivate_url(establishment.id, restaurant_id),
        format="json",
        **auth_headers(access_token),
    )
    assert deactivate_bu_response.status_code == 200
    restaurant = BusinessUnit.objects.get(id=restaurant_id)
    assert restaurant.active is False
    assert ActivitySubject.objects.filter(id=subject_id, active=False).exists()


def test_director_has_same_runtime_mutation_rights(api_client):
    establishment, owner, hotel, _maintenance = setup_active_establishment_with_runtime()
    director = create_user(username="runtime_director")
    create_membership_for_user(
        user=director,
        establishment=establishment,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    access_token = login(api_client, user=director)

    response = api_client.patch(
        business_unit_detail_url(establishment.id, hotel.id),
        {"description": "Description director"},
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 200
    assert response.json()["description"] == "Description director"


@pytest.mark.parametrize("role", ["manager", "staff"])
def test_manager_and_staff_cannot_mutate_runtime_config(api_client, role):
    establishment, owner, hotel, _maintenance = setup_active_establishment_with_runtime()
    actor = create_user(username=f"runtime_{role}")
    create_membership_for_user(user=actor, establishment=establishment, role=role)
    access_token = login(api_client, user=actor)

    response = api_client.patch(
        business_unit_detail_url(establishment.id, hotel.id),
        {"description": "Forbidden"},
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 403


def test_mutations_are_scoped_to_active_membership_establishment(api_client):
    establishment, owner, hotel, _maintenance = setup_active_establishment_with_runtime()
    other_establishment = create_establishment(name="Other Hotel")
    access_token = login(api_client, user=owner)

    response = api_client.patch(
        business_unit_detail_url(other_establishment.id, hotel.id),
        {"description": "Cross tenant"},
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 404


def test_cannot_deactivate_last_active_business_unit(api_client):
    establishment = create_establishment()
    owner = create_user(username="runtime_last_bu_owner")
    create_membership_for_user(
        user=owner,
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    only_bu = create_business_unit(establishment=establishment, key="solo", label="Solo")
    create_activity_subject(
        establishment=establishment,
        business_unit=only_bu,
        label="Unique sujet",
    )
    access_token = login(api_client, user=owner)

    response = api_client.post(
        business_unit_deactivate_url(establishment.id, only_bu.id),
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "last_active_business_unit"
    assert BusinessUnit.objects.get(id=only_bu.id).active is True


def test_cannot_deactivate_last_active_activity_subject(api_client):
    establishment, owner, hotel, _maintenance = setup_active_establishment_with_runtime()
    access_token = login(api_client, user=owner)
    subject = ActivitySubject.objects.filter(business_unit=hotel, active=True).get()

    response = api_client.post(
        activity_subject_deactivate_url(establishment.id, subject.id),
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "last_active_activity_subject"
    assert ActivitySubject.objects.get(id=subject.id).active is True


def test_cannot_deactivate_business_unit_with_active_membership_scope(api_client):
    establishment, owner, hotel, maintenance = setup_active_establishment_with_runtime()
    manager = create_user(username="runtime_scope_manager")
    manager_membership = create_membership_for_user(
        user=manager,
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
    )
    create_membership_with_business_unit_scope(
        membership=manager_membership,
        business_unit=maintenance,
    )
    access_token = login(api_client, user=owner)

    response = api_client.post(
        business_unit_deactivate_url(establishment.id, maintenance.id),
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "business_unit_has_membership_scopes"
    assert BusinessUnit.objects.get(id=maintenance.id).active is True


def test_deactivate_business_unit_cascades_subjects(api_client):
    establishment, owner, hotel, maintenance = setup_active_establishment_with_runtime()
    access_token = login(api_client, user=owner)

    response = api_client.post(
        business_unit_deactivate_url(establishment.id, maintenance.id),
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 200
    assert BusinessUnit.objects.get(id=maintenance.id).active is False
    assert ActivitySubject.objects.filter(business_unit=maintenance, active=False).exists()


def test_recreate_same_label_reactivates_existing_business_unit(api_client):
    establishment, owner, hotel, _maintenance = setup_active_establishment_with_runtime()
    access_token = login(api_client, user=owner)

    deactivate_response = api_client.post(
        business_unit_deactivate_url(establishment.id, hotel.id),
        format="json",
        **auth_headers(access_token),
    )
    assert deactivate_response.status_code == 200

    recreate_response = api_client.post(
        business_units_url(establishment.id),
        {"label": "Hôtel", "description": "Réactivé"},
        format="json",
        **auth_headers(access_token),
    )

    assert recreate_response.status_code == 201
    assert recreate_response.json()["id"] == str(hotel.id)
    hotel.refresh_from_db()
    assert hotel.active is True
    assert hotel.description == "Réactivé"


def test_draft_establishment_runtime_mutations_return_forbidden(api_client):
    organization = Organization.objects.create(
        name=f"Draft Org {uuid.uuid4().hex[:6]}",
        status=Organization.Status.ACTIVE,
    )
    establishment = Establishment.objects.create(
        name="Draft Hotel",
        organization=organization,
        status=Establishment.Status.DRAFT,
    )
    owner = create_user(username="runtime_draft_owner")
    create_membership_for_user(
        user=owner,
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    access_token = login(api_client, user=owner)

    response = api_client.post(
        business_units_url(establishment.id),
        {"label": "Restaurant"},
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 403
