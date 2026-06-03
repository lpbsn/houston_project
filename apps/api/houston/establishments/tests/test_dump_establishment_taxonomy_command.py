from __future__ import annotations

import json
import uuid
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from houston.establishments.models import (
    Establishment,
    OperationalDomain,
    OperationalModule,
    OperationalSubject,
    OperationalUnit,
)
from houston.organizations.models import Organization

pytestmark = pytest.mark.django_db


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


def test_dump_establishment_taxonomy_prints_active_tree():
    establishment = create_establishment()
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
    OperationalSubject.objects.create(
        establishment=establishment,
        operational_domain=domain,
        key="room_cleaning",
        label="Propreté chambre",
        active=True,
    )
    OperationalUnit.objects.create(
        establishment=establishment,
        key="kitchen",
        label="Cuisine",
        active=True,
    )
    inactive_module = OperationalModule.objects.create(
        establishment=establishment,
        key="inactive_module",
        label="Inactive module",
        active=False,
    )
    inactive_domain = OperationalDomain.objects.create(
        establishment=establishment,
        operational_module=inactive_module,
        key="inactive_domain",
        label="Inactive domain",
        active=False,
    )
    OperationalSubject.objects.create(
        establishment=establishment,
        operational_domain=inactive_domain,
        key="inactive_subject",
        label="Inactive subject",
        active=True,
    )
    OperationalUnit.objects.create(
        establishment=establishment,
        key="inactive_unit",
        label="Inactive unit",
        active=False,
    )

    out = StringIO()
    call_command("dump_establishment_taxonomy", str(establishment.id), stdout=out)
    output = out.getvalue()

    assert "Establishment: Taxonomy Hotel" in output
    assert "[module] hotel — Hôtel" in output
    assert "[domain] housekeeping — Entretien" in output
    assert "[subject] room_cleaning — Propreté chambre" in output
    assert "unit kitchen — Cuisine" in output
    assert "inactive_module" not in output
    assert "inactive_domain" not in output
    assert "inactive_subject" not in output
    assert "inactive_unit" not in output


def test_dump_establishment_taxonomy_includes_unassigned_domains():
    establishment = create_establishment(name="Unassigned Hotel")
    domain = OperationalDomain.objects.create(
        establishment=establishment,
        operational_module=None,
        key="legacy_domain",
        label="Legacy domain",
        active=True,
    )
    OperationalSubject.objects.create(
        establishment=establishment,
        operational_domain=domain,
        key="legacy_subject",
        label="Legacy subject",
        active=True,
    )

    out = StringIO()
    call_command("dump_establishment_taxonomy", str(establishment.id), stdout=out)
    output = out.getvalue()

    assert "[unassigned domain] legacy_domain — Legacy domain" in output
    assert "[subject] legacy_subject — Legacy subject" in output


def test_dump_establishment_taxonomy_empty_taxonomy():
    establishment = create_establishment(name="Empty Hotel")

    out = StringIO()
    call_command("dump_establishment_taxonomy", str(establishment.id), stdout=out)
    output = out.getvalue()

    assert "Establishment: Empty Hotel" in output
    assert "(no active operational taxonomy)" in output


def test_dump_establishment_taxonomy_raises_when_establishment_missing():
    missing_id = uuid.uuid4()

    with pytest.raises(CommandError, match="Establishment not found"):
        call_command("dump_establishment_taxonomy", str(missing_id))


def test_dump_establishment_taxonomy_raises_on_invalid_uuid():
    with pytest.raises(CommandError, match="Invalid establishment UUID"):
        call_command("dump_establishment_taxonomy", "not-a-uuid")


def test_dump_establishment_taxonomy_json_output():
    establishment = create_establishment(name="JSON Hotel")
    module = OperationalModule.objects.create(
        establishment=establishment,
        key="restaurant",
        label="Restaurant",
        active=True,
    )
    domain = OperationalDomain.objects.create(
        establishment=establishment,
        operational_module=module,
        key="bar",
        label="Bar",
        active=True,
    )
    OperationalSubject.objects.create(
        establishment=establishment,
        operational_domain=domain,
        key="stocks",
        label="Stocks",
        active=True,
    )
    OperationalUnit.objects.create(
        establishment=establishment,
        key="rooms",
        label="Rooms",
        active=True,
    )

    out = StringIO()
    call_command(
        "dump_establishment_taxonomy",
        str(establishment.id),
        "--json",
        stdout=out,
    )
    payload = json.loads(out.getvalue())

    assert payload["establishment_name"] == "JSON Hotel"
    assert len(payload["modules"]) == 1
    assert payload["modules"][0]["key"] == "restaurant"
    assert payload["modules"][0]["domains"][0]["key"] == "bar"
    assert payload["modules"][0]["domains"][0]["subjects"][0]["key"] == "stocks"
    assert payload["units"][0]["key"] == "rooms"
    assert payload["unassigned_domains"] == []
