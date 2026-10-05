from __future__ import annotations

from uuid import UUID

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from houston.core.dev_guards import LocalDevEnvironmentError
from houston.establishments.mama_nice_dataset_bootstrap import _ensure_business_units
from houston.establishments.mama_nice_dataset_compiler import CompiledCorpus
from houston.establishments.mama_nice_dataset_constants import (
    LOCAL_ORG_NAME,
    PROD_ESTABLISHMENT_ID,
    SNAPSHOT,
    STAGING_ESTABLISHMENT_ID,
)
from houston.establishments.mama_nice_dataset_exceptions import MamaNiceDatasetError
from houston.establishments.mama_nice_dataset_preflight import (
    preflight_mama_nice_production,
    preflight_mama_nice_staging,
)
from houston.establishments.mama_nice_dataset_replay import SeedResult, seed_mama_nice_dataset
from houston.establishments.models import BusinessUnit, Establishment, EstablishmentMembership
from houston.organizations.models import Organization
from houston.testing.factories import create_membership, create_user


def _staging_establishment(*, organization_name: str = LOCAL_ORG_NAME) -> Establishment:
    organization = Organization.objects.create(
        name=organization_name,
        status=Organization.Status.ACTIVE,
    )
    return Establishment.objects.create(
        id=STAGING_ESTABLISHMENT_ID,
        name="Mama Shelter Nice",
        organization=organization,
        status=Establishment.Status.ACTIVE,
        timezone="Europe/Paris",
    )


def _governance(
    establishment: Establishment,
    *,
    owner_status: str = EstablishmentMembership.Status.ACTIVE,
    director_status: str = EstablishmentMembership.Status.ACTIVE,
    extra_director: bool = False,
) -> None:
    create_membership(
        establishment=establishment,
        user=create_user(username="mama_nice_owner"),
        role=EstablishmentMembership.Role.OWNER,
        status=owner_status,
    )
    create_membership(
        establishment=establishment,
        user=create_user(username="mama_nice_director"),
        role=EstablishmentMembership.Role.DIRECTOR,
        status=director_status,
    )
    if extra_director:
        create_membership(
            establishment=establishment,
            user=create_user(username="mama_nice_director_2"),
            role=EstablishmentMembership.Role.DIRECTOR,
            status=EstablishmentMembership.Status.ACTIVE,
        )


def _patch_compile(monkeypatch) -> None:
    monkeypatch.setattr(
        "houston.establishments.mama_nice_dataset_replay.compile_mama_nice_dataset",
        lambda: CompiledCorpus(),
    )


def test_production_preflight_rejects_staging_establishment():
    with pytest.raises(MamaNiceDatasetError, match="production seed must target"):
        preflight_mama_nice_production(establishment_id=STAGING_ESTABLISHMENT_ID)


def test_staging_preflight_rejects_other_establishment_id():
    with pytest.raises(MamaNiceDatasetError, match="staging seed must target"):
        preflight_mama_nice_staging(establishment_id=PROD_ESTABLISHMENT_ID)


@pytest.mark.django_db
def test_staging_preflight_requires_existing_establishment():
    with pytest.raises(MamaNiceDatasetError, match="staging establishment was not found"):
        preflight_mama_nice_staging(establishment_id=STAGING_ESTABLISHMENT_ID)


@pytest.mark.django_db
def test_staging_preflight_requires_demo_spore_org():
    _staging_establishment(organization_name="Other Org")
    with pytest.raises(MamaNiceDatasetError, match=r"diverges from \[DEMO\] SPORE"):
        preflight_mama_nice_staging(establishment_id=STAGING_ESTABLISHMENT_ID)


@pytest.mark.django_db
def test_staging_preflight_requires_exactly_one_active_owner():
    establishment = _staging_establishment()
    _governance(establishment, owner_status=EstablishmentMembership.Status.DEACTIVATED)
    with pytest.raises(MamaNiceDatasetError, match="exactly one active OWNER; found 0"):
        preflight_mama_nice_staging(establishment_id=STAGING_ESTABLISHMENT_ID)


@pytest.mark.django_db
def test_staging_preflight_requires_exactly_one_active_director():
    establishment = _staging_establishment()
    _governance(establishment, extra_director=True)
    with pytest.raises(MamaNiceDatasetError, match="exactly one active DIRECTOR; found 2"):
        preflight_mama_nice_staging(establishment_id=STAGING_ESTABLISHMENT_ID)


@pytest.mark.django_db
def test_staging_preflight_accepts_locked_target_and_keeps_catalog_descriptions(imported_catalog):
    del imported_catalog
    establishment = _staging_establishment()
    _governance(establishment)
    _ensure_business_units(establishment)
    hotel = BusinessUnit.objects.get(
        establishment=establishment,
        catalog_business_unit__key="hotel",
    )
    original = hotel.instance_description

    result = preflight_mama_nice_staging(establishment_id=STAGING_ESTABLISHMENT_ID)

    assert result.establishment.id == UUID(STAGING_ESTABLISHMENT_ID)
    assert result.organization.name == LOCAL_ORG_NAME
    assert result.owner_membership.role == EstablishmentMembership.Role.OWNER
    assert result.owner_membership.status == EstablishmentMembership.Status.ACTIVE
    assert result.governance_director.role == EstablishmentMembership.Role.DIRECTOR
    assert result.governance_director.status == EstablishmentMembership.Status.ACTIVE

    hotel.instance_description = "diverged"
    hotel.save(update_fields=["instance_description", "updated_at"])
    with pytest.raises(MamaNiceDatasetError, match="instance_description diverges"):
        preflight_mama_nice_staging(establishment_id=STAGING_ESTABLISHMENT_ID)
    hotel.refresh_from_db()
    assert hotel.instance_description == "diverged"
    hotel.instance_description = original
    hotel.save(update_fields=["instance_description", "updated_at"])


def test_seed_rejects_local_and_staging():
    with pytest.raises(MamaNiceDatasetError, match="mutually exclusive"):
        seed_mama_nice_dataset(
            establishment_id=STAGING_ESTABLISHMENT_ID,
            dry_run=True,
            confirm=False,
            resume=False,
            local=True,
            staging=True,
        )


def test_seed_staging_requires_establishment_id():
    with pytest.raises(MamaNiceDatasetError, match="required for staging"):
        seed_mama_nice_dataset(
            establishment_id=None,
            dry_run=True,
            confirm=False,
            resume=False,
            staging=True,
        )


def test_local_seed_still_asserts_local_dev_environment(monkeypatch):
    _patch_compile(monkeypatch)

    def _guard() -> None:
        raise LocalDevEnvironmentError("blocked")

    monkeypatch.setattr(
        "houston.establishments.mama_nice_dataset_replay.assert_local_dev_environment",
        _guard,
    )
    with pytest.raises(LocalDevEnvironmentError, match="blocked"):
        seed_mama_nice_dataset(
            establishment_id=None,
            dry_run=True,
            confirm=False,
            resume=False,
            local=True,
        )


def test_production_seed_still_rejects_staging_establishment(monkeypatch):
    _patch_compile(monkeypatch)
    result = seed_mama_nice_dataset(
        establishment_id=STAGING_ESTABLISHMENT_ID,
        dry_run=True,
        confirm=False,
        resume=False,
    )
    assert any("production seed must target" in message for message in result.errors)


@pytest.mark.django_db
def test_staging_seed_skips_local_guard_and_reuses_replay(imported_catalog, monkeypatch):
    del imported_catalog
    establishment = _staging_establishment()
    _governance(establishment)
    _ensure_business_units(establishment)
    _patch_compile(monkeypatch)
    guarded: list[str] = []
    replayed: list[UUID] = []

    def _guard() -> None:
        guarded.append("local")

    def _replay(**kwargs) -> None:
        replayed.append(kwargs["preflight"].establishment.id)

    monkeypatch.setattr(
        "houston.establishments.mama_nice_dataset_replay.assert_local_dev_environment",
        _guard,
    )
    monkeypatch.setattr(
        "houston.establishments.mama_nice_dataset_replay.resolve_seed_reference_at",
        lambda **_kwargs: SNAPSHOT,
    )
    monkeypatch.setattr(
        "houston.establishments.mama_nice_dataset_replay._replay",
        _replay,
    )

    result = seed_mama_nice_dataset(
        establishment_id=STAGING_ESTABLISHMENT_ID,
        dry_run=False,
        confirm=True,
        resume=False,
        staging=True,
    )

    assert guarded == []
    assert replayed == [UUID(STAGING_ESTABLISHMENT_ID)]
    assert result.establishment_id == UUID(STAGING_ESTABLISHMENT_ID)
    assert result.dry_run is False


def test_seed_command_exposes_staging_and_keeps_modes_exclusive(monkeypatch):
    captured: dict[str, object] = {}

    def _fake(**kwargs) -> SeedResult:
        captured.update(kwargs)
        return SeedResult(dry_run=True, resume=False)

    monkeypatch.setattr(
        "houston.establishments.management.commands.seed_mama_nice_dataset.seed_mama_nice_dataset",
        _fake,
    )
    call_command(
        "seed_mama_nice_dataset",
        "--staging",
        "--dry-run",
        f"--establishment-id={STAGING_ESTABLISHMENT_ID}",
    )
    assert captured["staging"] is True
    assert captured["local"] is False
    assert captured["establishment_id"] == STAGING_ESTABLISHMENT_ID


def test_seed_command_rejects_local_and_staging():
    with pytest.raises(CommandError, match="mutually exclusive"):
        call_command(
            "seed_mama_nice_dataset",
            "--local",
            "--staging",
            "--dry-run",
            f"--establishment-id={STAGING_ESTABLISHMENT_ID}",
        )
