from __future__ import annotations

import os
from dataclasses import dataclass

from houston.accounts.legal_services import grant_current_legal_defaults
from houston.accounts.models import User
from houston.core.dev_guards import assert_local_dev_environment
from houston.establishments.business_unit_domain_service import create_onboarding_business_unit
from houston.establishments.mama_nice_dataset_constants import (
    BU_DESCRIPTIONS,
    CATALOG_KEYS,
    ESTABLISHMENT_DESCRIPTION,
    LOCAL_ESTABLISHMENT_NAME,
    LOCAL_GOVERNANCE_DIRECTOR_EMAIL,
    LOCAL_ORG_NAME,
    LOCAL_OWNER_EMAIL,
    LOCAL_TIMEZONE,
    OWNER_PASSWORD_ENV,
)
from houston.establishments.mama_nice_dataset_exceptions import MamaNiceDatasetError
from houston.establishments.mama_nice_dataset_manifest import load_mama_nice_manifest
from houston.establishments.models import (
    CatalogActivitySubject,
    CatalogBusinessUnit,
    Establishment,
    EstablishmentActivityDescription,
    EstablishmentMembership,
)
from houston.organizations.models import Organization


@dataclass
class BootstrapResult:
    establishment: Establishment
    created: bool


def _require_password(env_name: str) -> str:
    password = os.environ.get(env_name, "").strip()
    if not password:
        raise MamaNiceDatasetError([f"{env_name} must be set and is never stored in git"])
    return password


def _get_or_create_user(*, email: str, first_name: str, last_name: str, password: str) -> User:
    user = User.objects.filter(email__iexact=email).first()
    if user is None:
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            status=User.Status.ACTIVE,
        )
    else:
        user.set_password(password)
        user.status = User.Status.ACTIVE
        user.first_name = first_name
        user.last_name = last_name
        user.save()
    grant_current_legal_defaults(user=user)
    return user


def bootstrap_mama_nice_dataset(*, confirm: bool) -> BootstrapResult:
    assert_local_dev_environment()
    if not confirm:
        raise MamaNiceDatasetError(["bootstrap requires --confirm"])
    owner_password = _require_password(OWNER_PASSWORD_ENV)
    owner = _get_or_create_user(
        email=LOCAL_OWNER_EMAIL,
        first_name="Leonard",
        last_name="Boisson",
        password=owner_password,
    )
    organization, _ = Organization.objects.get_or_create(
        name=LOCAL_ORG_NAME,
        defaults={"status": Organization.Status.ACTIVE},
    )
    establishment = Establishment.objects.filter(
        organization=organization,
        name=LOCAL_ESTABLISHMENT_NAME,
    ).first()
    created = establishment is None
    if establishment is None:
        establishment = Establishment.objects.create(
            organization=organization,
            name=LOCAL_ESTABLISHMENT_NAME,
            timezone=LOCAL_TIMEZONE,
            status=Establishment.Status.DRAFT,
            chat_enabled=False,
        )
    owner_membership = EstablishmentMembership.objects.filter(
        establishment=establishment,
        user=owner,
    ).first()
    if owner_membership is None:
        EstablishmentMembership.objects.create(
            user=owner,
            establishment=establishment,
            role=EstablishmentMembership.Role.OWNER,
            status=EstablishmentMembership.Status.ACTIVE,
        )
    director = _get_or_create_user(
        email=LOCAL_GOVERNANCE_DIRECTOR_EMAIL,
        first_name="Director",
        last_name="Gouvernance",
        password=owner_password,
    )
    if not EstablishmentMembership.objects.filter(
        establishment=establishment,
        user=director,
    ).exists():
        EstablishmentMembership.objects.create(
            user=director,
            establishment=establishment,
            role=EstablishmentMembership.Role.DIRECTOR,
            status=EstablishmentMembership.Status.ACTIVE,
        )
    _ensure_business_units(establishment)
    EstablishmentActivityDescription.objects.update_or_create(
        establishment=establishment,
        defaults={
            "description": ESTABLISHMENT_DESCRIPTION,
            "source": EstablishmentActivityDescription.Source.MANUAL,
            "submitted_by": owner,
        },
    )
    establishment.status = Establishment.Status.ACTIVE
    establishment.chat_enabled = True
    establishment.timezone = LOCAL_TIMEZONE
    establishment.save(update_fields=["status", "chat_enabled", "timezone", "updated_at"])
    return BootstrapResult(establishment=establishment, created=created)


def _ensure_business_units(establishment: Establishment) -> None:
    manifest = load_mama_nice_manifest()
    subjects_by_pole: dict[str, list[str]] = {key: [] for key in CATALOG_KEYS}
    for subject in manifest["catalog_lock"]["activity_subjects"]:
        pole, _rest = subject.split("__", 1)
        subjects_by_pole[pole].append(subject)
    labels = {
        "hotel": "Hôtel",
        "petit_dejeuner": "Petit déjeuner",
        "restaurant": "Restaurant",
        "maintenance": "Maintenance",
        "communication": "Communication",
        "evenements_privatisations": "Événements & privatisations",
        "rh": "RH",
    }
    for key in CATALOG_KEYS:
        catalog = CatalogBusinessUnit.objects.get(key=key)
        existing = establishment.business_units.filter(catalog_business_unit=catalog).first()
        if existing is not None:
            if existing.instance_description != BU_DESCRIPTIONS[key]:
                existing.instance_description = BU_DESCRIPTIONS[key]
                existing.save(update_fields=["instance_description", "updated_at"])
            continue
        create_onboarding_business_unit(
            establishment=establishment,
            catalog_business_unit=catalog,
            specific_name=labels[key],
            instance_description=BU_DESCRIPTIONS[key],
            generic_activity_subject_keys=subjects_by_pole[key],
        )
        CatalogActivitySubject.objects.filter(key__in=subjects_by_pole[key]).count()
