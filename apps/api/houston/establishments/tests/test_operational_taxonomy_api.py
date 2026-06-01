from __future__ import annotations

import uuid

import pytest
from rest_framework.test import APIClient

from houston.accounts.models import User
from houston.establishments.models import (
    Establishment,
    EstablishmentMembership,
    OperationalDomain,
    OperationalModule,
    OperationalSubject,
)
from houston.establishments.tests.conftest import TEST_PASSWORD
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


def create_establishment(*, name: str = "Taxonomy Hotel") -> Establishment:
    organization = Organization.objects.create(
        name=f"{name} Group {uuid.uuid4().hex[:6]}",
        status=Organization.Status.ACTIVE,
    )
    return Establishment.objects.create(
        name=name,
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )


def create_membership(
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


def taxonomy_url(establishment_id) -> str:
    return f"/api/v1/establishments/{establishment_id}/operational-taxonomy/"


def test_owner_can_read_operational_taxonomy_tree(api_client):
    establishment = create_establishment()
    owner = create_user(username="taxonomy_owner")
    create_membership(
        user=owner,
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )

    module = OperationalModule.objects.create(
        establishment=establishment,
        key="hotel",
        label="Hôtel",
        active=True,
    )
    domain = OperationalDomain.objects.create(
        establishment=establishment,
        operational_module=module,
        key="housekeeping",
        label="Entretien",
        active=True,
    )
    subject = OperationalSubject.objects.create(
        establishment=establishment,
        operational_domain=domain,
        key="room_cleaning",
        label="Propreté chambre",
        active=True,
    )
    inactive_domain = OperationalDomain.objects.create(
        establishment=establishment,
        operational_module=module,
        key="inactive_domain",
        label="Inactive",
        active=False,
    )
    OperationalSubject.objects.create(
        establishment=establishment,
        operational_domain=inactive_domain,
        key="inactive_subject",
        label="Inactive subject",
        active=True,
    )

    token = login(api_client, user=owner)
    response = api_client.get(
        taxonomy_url(establishment.id),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["modules"]) == 1
    assert body["modules"][0]["id"] == str(module.id)
    assert len(body["modules"][0]["domains"]) == 1
    assert body["modules"][0]["domains"][0]["id"] == str(domain.id)
    assert len(body["modules"][0]["domains"][0]["subjects"]) == 1
    assert body["modules"][0]["domains"][0]["subjects"][0]["id"] == str(subject.id)


def test_director_can_read_operational_taxonomy_tree(api_client):
    establishment = create_establishment()
    director = create_user(username="taxonomy_director")
    create_membership(
        user=director,
        establishment=establishment,
        role=EstablishmentMembership.Role.DIRECTOR,
    )

    token = login(api_client, user=director)
    response = api_client.get(
        taxonomy_url(establishment.id),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 200


@pytest.mark.parametrize(
    "role",
    [EstablishmentMembership.Role.MANAGER, EstablishmentMembership.Role.STAFF],
)
def test_manager_and_staff_cannot_read_operational_taxonomy(api_client, role):
    establishment = create_establishment()
    actor = create_user(username=f"taxonomy_{role}")
    create_membership(user=actor, establishment=establishment, role=role)

    token = login(api_client, user=actor)
    response = api_client.get(
        taxonomy_url(establishment.id),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 403


def test_unassigned_domains_returned_separately(api_client):
    establishment = create_establishment()
    owner = create_user(username="taxonomy_unassigned")
    create_membership(
        user=owner,
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )

    orphan_domain = OperationalDomain.objects.create(
        establishment=establishment,
        operational_module=None,
        key="orphan",
        label="Domaine orphelin",
        active=True,
    )

    token = login(api_client, user=owner)
    response = api_client.get(
        taxonomy_url(establishment.id),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["unassigned_domains"]) == 1
    assert body["unassigned_domains"][0]["id"] == str(orphan_domain.id)
