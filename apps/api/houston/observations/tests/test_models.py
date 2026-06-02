from __future__ import annotations

import uuid

import pytest
from django.utils import timezone
from houston.accounts.models import User
from houston.establishments.models import Establishment, EstablishmentMembership
from houston.observations.models import Observation, ObservationProcessing
from houston.organizations.models import Organization

pytestmark = pytest.mark.django_db


def _active_establishment() -> Establishment:
    organization = Organization.objects.create(
        name=f"Org {uuid.uuid4().hex[:6]}",
        status=Organization.Status.ACTIVE,
    )
    return Establishment.objects.create(
        name="Test Hotel",
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )


def _membership(establishment: Establishment) -> EstablishmentMembership:
    user = User.objects.create_user(
        username=f"user_{uuid.uuid4().hex[:8]}",
        email=f"{uuid.uuid4().hex[:8]}@example.com",
        password="secret-password-12",
        status=User.Status.ACTIVE,
    )
    return EstablishmentMembership.objects.create(
        user=user,
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
        status=EstablishmentMembership.Status.ACTIVE,
    )


def test_observation_stores_raw_text_not_exposed_field_name():
    establishment = _active_establishment()
    membership = _membership(establishment)
    now = timezone.now()
    observation = Observation.objects.create(
        establishment=establishment,
        submitted_by_membership=membership,
        raw_text="Chambre 204 nécessite un contrôle de propreté.",
        submitted_at=now,
    )
    ObservationProcessing.objects.create(
        observation=observation,
        status=ObservationProcessing.Status.QUEUED,
        queued_at=now,
    )

    observation.refresh_from_db()
    assert observation.raw_text.startswith("Chambre")
    assert not hasattr(observation, "text")
