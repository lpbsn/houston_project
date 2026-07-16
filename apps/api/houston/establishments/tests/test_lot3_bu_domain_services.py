from __future__ import annotations

from unittest.mock import patch

import pytest
from django.db import IntegrityError, transaction

from houston.core.exceptions import (
    DomainConflictError,
    DomainNotFoundError,
    DomainValidationError,
)
from houston.establishments.business_unit_domain_service import (
    _create_business_unit_core,
    _lock_catalog_activity_subjects,
    create_onboarding_business_unit,
    create_runtime_business_unit,
    reactivate_business_unit,
    update_business_unit_specific_name,
)
from houston.establishments.business_unit_identity import (
    build_free_activity_subject_row,
    preflight_activity_subject_rows,
)
from houston.establishments.models import (
    ActivitySubject,
    BusinessUnit,
    CatalogActivitySubject,
    CatalogBusinessUnit,
    EstablishmentMembership,
    MembershipScope,
)
from houston.testing.factories import (
    create_establishment,
    create_membership,
)

pytestmark = pytest.mark.django_db


def _catalog(key: str) -> CatalogBusinessUnit:
    return CatalogBusinessUnit.objects.get(key=key)


def test_create_business_unit_core_does_not_seed_subjects_and_dual_writes_legacy(
    imported_catalog,
):
    establishment = create_establishment()
    restaurant = _catalog("restaurant")

    business_unit = _create_business_unit_core(
        establishment=establishment,
        catalog_business_unit=restaurant,
        specific_name="Food Court",
        instance_description="Ground floor",
    )

    assert business_unit.specific_name == "Food Court"
    assert business_unit.normalized_specific_name == "food_court"
    assert business_unit.routing_key.startswith("restaurant--food-court--")
    assert business_unit.instance_description == "Ground floor"
    assert business_unit.catalog_business_unit_id == restaurant.id
    assert business_unit.catalog_business_unit.unit_type == restaurant.unit_type
    assert not ActivitySubject.objects.filter(business_unit=business_unit).exists()


def test_core_creates_distinct_routing_keys_for_same_catalog(imported_catalog):
    establishment = create_establishment()
    restaurant = _catalog("restaurant")

    food_court = _create_business_unit_core(
        establishment=establishment,
        catalog_business_unit=restaurant,
        specific_name="Food Court",
    )
    rooftop = _create_business_unit_core(
        establishment=establishment,
        catalog_business_unit=restaurant,
        specific_name="Rooftop",
    )

    assert food_court.routing_key != rooftop.routing_key


def test_runtime_seeds_all_active_catalog_subjects_with_derived_establishment(
    imported_catalog,
):
    establishment = create_establishment()
    restaurant = _catalog("restaurant")
    expected_keys = set(
        CatalogActivitySubject.objects.filter(
            catalog_business_unit=restaurant,
            active=True,
        ).values_list("key", flat=True)
    )

    business_unit = create_runtime_business_unit(
        establishment=establishment,
        catalog_business_unit=restaurant,
        specific_name="Food Court",
    )

    subjects = ActivitySubject.objects.filter(business_unit=business_unit)
    assert set(subjects.values_list("routing_key", flat=True)) == expected_keys
    assert set(subjects.values_list("establishment_id", flat=True)) == {
        establishment.id
    }
    assert all(
        subject.label == ""
        and subject.description == ""
        and subject.catalog_activity_subject_id is not None
        for subject in subjects.select_related("catalog_activity_subject")
    )


def test_onboarding_materializes_only_explicit_subjects(imported_catalog):
    establishment = create_establishment()
    restaurant = _catalog("restaurant")

    business_unit = create_onboarding_business_unit(
        establishment=establishment,
        catalog_business_unit=restaurant,
        specific_name="Rooftop",
        generic_activity_subject_keys=["restaurant__stock"],
        free_activity_subjects=[{"label": "Terrasse VIP", "description": "Private"}],
    )

    subjects = ActivitySubject.objects.filter(business_unit=business_unit).order_by(
        "routing_key"
    )
    assert subjects.count() == 2
    assert set(subjects.values_list("normalized_name", flat=True)) == {
        "stock",
        "terrasse_vip",
    }
    assert subjects.filter(routing_key="restaurant__stock").exists()
    assert subjects.filter(routing_key__startswith="custom--terrasse-vip--").exists()


def test_create_rejects_name_reserved_by_inactive_business_unit(imported_catalog):
    establishment = create_establishment()
    restaurant = _catalog("restaurant")
    existing = _create_business_unit_core(
        establishment=establishment,
        catalog_business_unit=restaurant,
        specific_name="Food Court",
    )
    BusinessUnit.objects.filter(id=existing.id).update(active=False)

    with pytest.raises(DomainConflictError) as exc_info:
        create_runtime_business_unit(
            establishment=establishment,
            catalog_business_unit=restaurant,
            specific_name="Food Court",
        )

    assert exc_info.value.code == "duplicate_specific_name"
    assert BusinessUnit.objects.filter(establishment=establishment).count() == 1


def test_create_rejects_duplicate_transversal_catalog_instance(imported_catalog):
    establishment = create_establishment()
    maintenance = _catalog("maintenance")
    _create_business_unit_core(
        establishment=establishment,
        catalog_business_unit=maintenance,
        specific_name="Maintenance A",
    )

    with pytest.raises(DomainConflictError) as exc_info:
        _create_business_unit_core(
            establishment=establishment,
            catalog_business_unit=maintenance,
            specific_name="Maintenance B",
        )

    assert exc_info.value.code == "duplicate_transversal_catalog_instance"


def test_create_rejects_inactive_catalog_business_unit(imported_catalog):
    establishment = create_establishment()
    restaurant = _catalog("restaurant")
    CatalogBusinessUnit.objects.filter(id=restaurant.id).update(active=False)

    with pytest.raises(DomainConflictError) as exc_info:
        _create_business_unit_core(
            establishment=establishment,
            catalog_business_unit=restaurant,
            specific_name="Food Court",
        )

    assert exc_info.value.code == "catalog_business_unit_inactive"


def test_onboarding_rejects_inactive_catalog_subject_and_rolls_back(imported_catalog):
    establishment = create_establishment()
    restaurant = _catalog("restaurant")
    CatalogActivitySubject.objects.filter(key="restaurant__stock").update(active=False)

    with pytest.raises(DomainConflictError) as exc_info:
        create_onboarding_business_unit(
            establishment=establishment,
            catalog_business_unit=restaurant,
            specific_name="Food Court",
            generic_activity_subject_keys=["restaurant__stock"],
        )

    assert exc_info.value.code == "catalog_activity_subject_inactive"
    assert not BusinessUnit.objects.filter(establishment=establishment).exists()


def test_onboarding_rejects_catalog_subject_from_another_business_unit(
    imported_catalog,
):
    establishment = create_establishment()
    restaurant = _catalog("restaurant")
    hotel_subject = CatalogActivitySubject.objects.filter(
        catalog_business_unit__key="hotel"
    ).first()
    assert hotel_subject is not None

    with pytest.raises(DomainValidationError) as exc_info:
        create_onboarding_business_unit(
            establishment=establishment,
            catalog_business_unit=restaurant,
            specific_name="Food Court",
            generic_activity_subject_keys=[hotel_subject.key],
        )

    assert exc_info.value.code == "catalog_subject_business_unit_mismatch"
    assert not BusinessUnit.objects.filter(establishment=establishment).exists()


def test_onboarding_rejects_inactive_foreign_catalog_subject_as_mismatch(
    imported_catalog,
):
    establishment = create_establishment()
    restaurant = _catalog("restaurant")
    hotel_subject = CatalogActivitySubject.objects.filter(
        catalog_business_unit__key="hotel"
    ).first()
    assert hotel_subject is not None
    CatalogActivitySubject.objects.filter(id=hotel_subject.id).update(active=False)

    with pytest.raises(DomainValidationError) as exc_info:
        create_onboarding_business_unit(
            establishment=establishment,
            catalog_business_unit=restaurant,
            specific_name="Food Court",
            generic_activity_subject_keys=[hotel_subject.key],
        )

    assert exc_info.value.code == "catalog_subject_business_unit_mismatch"
    assert not BusinessUnit.objects.filter(establishment=establishment).exists()


def test_lock_catalog_activity_subjects_scopes_keys_to_catalog(imported_catalog):
    restaurant = _catalog("restaurant")
    hotel_subject = CatalogActivitySubject.objects.filter(
        catalog_business_unit__key="hotel"
    ).first()
    assert hotel_subject is not None

    with transaction.atomic():
        subjects = _lock_catalog_activity_subjects(
            catalog_business_unit=restaurant,
            keys=[hotel_subject.key],
        )

    assert subjects == []


def test_onboarding_rejects_duplicate_generic_keys_and_rolls_back(imported_catalog):
    establishment = create_establishment()
    restaurant = _catalog("restaurant")

    with pytest.raises(DomainConflictError) as exc_info:
        create_onboarding_business_unit(
            establishment=establishment,
            catalog_business_unit=restaurant,
            specific_name="Food Court",
            generic_activity_subject_keys=[
                "restaurant__stock",
                "restaurant__stock",
            ],
        )

    assert exc_info.value.code == "duplicate_generic_catalog_subject_key"
    assert not BusinessUnit.objects.filter(establishment=establishment).exists()
    assert not ActivitySubject.objects.filter(establishment=establishment).exists()


def test_onboarding_rejects_empty_free_label_and_rolls_back(imported_catalog):
    establishment = create_establishment()
    restaurant = _catalog("restaurant")

    with pytest.raises(DomainValidationError) as exc_info:
        create_onboarding_business_unit(
            establishment=establishment,
            catalog_business_unit=restaurant,
            specific_name="Food Court",
            free_activity_subjects=[{"label": "   "}],
        )

    assert exc_info.value.code == "invalid_free_activity_subject_label"
    assert not BusinessUnit.objects.filter(establishment=establishment).exists()


def test_preflight_rejects_normalized_name_and_routing_key_collisions(
    imported_catalog,
):
    establishment = create_establishment()
    restaurant = _catalog("restaurant")
    business_unit = _create_business_unit_core(
        establishment=establishment,
        catalog_business_unit=restaurant,
        specific_name="Food Court",
    )
    first = build_free_activity_subject_row(
        business_unit=business_unit,
        label="Stock",
    )
    second = build_free_activity_subject_row(
        business_unit=business_unit,
        label="Stock!",
    )

    with pytest.raises(DomainConflictError) as normalized_exc:
        preflight_activity_subject_rows(
            business_unit=business_unit,
            rows=[first, second],
        )
    assert normalized_exc.value.code == "duplicate_activity_subject_normalized_name"

    second.normalized_name = "other"
    second.routing_key = first.routing_key
    with pytest.raises(DomainConflictError) as routing_exc:
        preflight_activity_subject_rows(
            business_unit=business_unit,
            rows=[first, second],
        )
    assert routing_exc.value.code == "duplicate_activity_subject_routing_key"


def test_residual_bulk_integrity_error_becomes_domain_conflict(
    imported_catalog,
):
    establishment = create_establishment()
    restaurant = _catalog("restaurant")

    with patch(
        "houston.establishments.business_unit_domain_service.ActivitySubject.objects.bulk_create",
        side_effect=IntegrityError("forced"),
    ):
        with pytest.raises(DomainConflictError) as exc_info:
            create_onboarding_business_unit(
                establishment=establishment,
                catalog_business_unit=restaurant,
                specific_name="Food Court",
                generic_activity_subject_keys=["restaurant__stock"],
            )

    assert exc_info.value.code == "activity_subject_identity_conflict"
    assert not BusinessUnit.objects.filter(establishment=establishment).exists()


def test_rename_updates_normalized_name_and_preserves_routing_key(imported_catalog):
    establishment = create_establishment()
    restaurant = _catalog("restaurant")
    business_unit = _create_business_unit_core(
        establishment=establishment,
        catalog_business_unit=restaurant,
        specific_name="Food Court",
    )
    initial_routing_key = business_unit.routing_key

    renamed = update_business_unit_specific_name(
        establishment_id=establishment.id,
        business_unit_id=business_unit.id,
        specific_name="Rooftop",
    )

    assert renamed.specific_name == "Rooftop"
    assert renamed.normalized_specific_name == "rooftop"
    assert renamed.routing_key == initial_routing_key


def test_rename_rejects_duplicate_specific_name(imported_catalog):
    establishment = create_establishment()
    restaurant = _catalog("restaurant")
    first = _create_business_unit_core(
        establishment=establishment,
        catalog_business_unit=restaurant,
        specific_name="Food Court",
    )
    second = _create_business_unit_core(
        establishment=establishment,
        catalog_business_unit=restaurant,
        specific_name="Rooftop",
    )

    with pytest.raises(DomainConflictError) as exc_info:
        update_business_unit_specific_name(
            establishment_id=establishment.id,
            business_unit_id=second.id,
            specific_name=first.specific_name,
        )

    assert exc_info.value.code == "duplicate_specific_name"


def test_reactivate_preserves_identity_subjects_and_membership_scopes(
    imported_catalog,
):
    establishment = create_establishment()
    restaurant = _catalog("restaurant")
    business_unit = create_onboarding_business_unit(
        establishment=establishment,
        catalog_business_unit=restaurant,
        specific_name="Food Court",
        generic_activity_subject_keys=["restaurant__stock"],
    )
    membership = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
    )
    MembershipScope.objects.create(
        membership=membership,
        business_unit=business_unit,
    )
    identity = (
        business_unit.id,
        business_unit.specific_name,
        business_unit.normalized_specific_name,
        business_unit.routing_key,
    )
    subject_ids = set(
        ActivitySubject.objects.filter(business_unit=business_unit).values_list(
            "id", flat=True
        )
    )
    BusinessUnit.objects.filter(id=business_unit.id).update(active=False)

    reactivated = reactivate_business_unit(
        establishment_id=establishment.id,
        business_unit_id=business_unit.id,
    )

    assert reactivated.active is True
    assert (
        reactivated.id,
        reactivated.specific_name,
        reactivated.normalized_specific_name,
        reactivated.routing_key,
    ) == identity
    assert set(
        ActivitySubject.objects.filter(business_unit=business_unit).values_list(
            "id", flat=True
        )
    ) == subject_ids
    assert MembershipScope.objects.filter(
        membership=membership,
        business_unit=business_unit,
    ).count() == 1


def test_reactivate_not_found_wrong_establishment_and_already_active(imported_catalog):
    establishment = create_establishment()
    other_establishment = create_establishment()
    restaurant = _catalog("restaurant")
    business_unit = _create_business_unit_core(
        establishment=establishment,
        catalog_business_unit=restaurant,
        specific_name="Food Court",
    )

    with pytest.raises(DomainNotFoundError):
        reactivate_business_unit(
            establishment_id=other_establishment.id,
            business_unit_id=business_unit.id,
        )

    with pytest.raises(DomainConflictError) as exc_info:
        reactivate_business_unit(
            establishment_id=establishment.id,
            business_unit_id=business_unit.id,
        )
    assert exc_info.value.code == "business_unit_already_active"


def test_catalog_activity_subjects_locked_in_deterministic_order(imported_catalog):
    restaurant = _catalog("restaurant")
    CatalogActivitySubject.objects.filter(
        catalog_business_unit=restaurant,
    ).update(sort_order=0)

    with transaction.atomic():
        subjects = _lock_catalog_activity_subjects(
            catalog_business_unit=restaurant,
        )

    keys = [subject.key for subject in subjects]
    assert keys == sorted(keys)
