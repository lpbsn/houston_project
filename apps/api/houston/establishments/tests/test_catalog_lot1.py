from __future__ import annotations

from unittest.mock import MagicMock, patch

import importlib

import pytest
from django.db import IntegrityError

_migration_module = importlib.import_module("houston.establishments.migrations.0022_catalog_lot1")
_assert_no_custom_prefix_catalog_subject_keys = (
    _migration_module._assert_no_custom_prefix_catalog_subject_keys
)

from houston.establishments.catalog_import import sync_catalog_from_normalized_rows
from houston.establishments.catalog_preflight import CatalogImportError
from houston.establishments.catalog_source_normalization import (
    CatalogActivitySubjectRow,
    CatalogBusinessUnitRow,
)
from houston.establishments.catalog_subject_label_service import (
    CatalogSubjectLabelConflictError,
    CatalogSubjectLabelValidationError,
    _apply_catalog_activity_subject_label_update,
    update_catalog_activity_subject_label,
)
from houston.establishments.models import (
    ActivitySubject,
    BusinessUnit,
    CatalogActivitySubject,
    CatalogBusinessUnit,
)
from houston.establishments.taxonomy_normalization import normalize_activity_subject_name
from houston.testing.factories import create_establishment
from houston.testing.taxonomy import create_activity_subject, create_business_unit

pytestmark = pytest.mark.django_db


def _business_unit_row(
    *,
    key: str = "hotel",
    label: str = "Hôtel",
    unit_type: str = "dedicated",
) -> CatalogBusinessUnitRow:
    return CatalogBusinessUnitRow(
        key=key,
        label=label,
        unit_type=unit_type,
        description="",
        sort_order=10,
    )


def _activity_subject_row(
    *,
    key: str = "hotel__menage",
    label: str = "Ménage",
    business_unit_key: str = "hotel",
) -> CatalogActivitySubjectRow:
    return CatalogActivitySubjectRow(
        key=key,
        label=label,
        catalog_business_unit_key=business_unit_key,
        description="",
        sort_order=10,
    )


def _link_runtime_business_unit(*, catalog_key: str) -> BusinessUnit:
    establishment = create_establishment()
    catalog_business_unit = CatalogBusinessUnit.objects.get(key=catalog_key)
    return BusinessUnit.objects.create(
        establishment=establishment,
        key=catalog_key,
        label=catalog_business_unit.label,
        catalog_business_unit=catalog_business_unit,
        source=BusinessUnit.Source.CATALOG_SUGGESTION,
        active=True,
    )


def _link_runtime_activity_subject(
    *,
    business_unit: BusinessUnit,
    catalog_key: str,
) -> ActivitySubject:
    catalog_subject = CatalogActivitySubject.objects.get(key=catalog_key)
    return ActivitySubject.objects.create(
        establishment=business_unit.establishment,
        business_unit=business_unit,
        normalized_name=normalize_activity_subject_name(catalog_subject.label),
        label=catalog_subject.label,
        catalog_activity_subject=catalog_subject,
        source=ActivitySubject.Source.CATALOG_SUGGESTION,
        active=True,
    )


def test_catalog_import_rejects_duplicate_business_unit_key(imported_catalog):
    rows = (
        _business_unit_row(key="hotel", label="Hôtel"),
        _business_unit_row(key="hotel", label="Hôtel duplicate"),
    )
    with pytest.raises(CatalogImportError) as exc_info:
        sync_catalog_from_normalized_rows(
            business_unit_rows=rows,
            activity_subject_rows=(),
        )
    assert exc_info.value.code == "duplicate_catalog_key"


def test_catalog_import_rejects_duplicate_subject_key(imported_catalog):
    rows = (
        _activity_subject_row(key="hotel__menage", label="Ménage"),
        _activity_subject_row(key="hotel__menage", label="Ménage duplicate"),
    )
    with pytest.raises(CatalogImportError) as exc_info:
        sync_catalog_from_normalized_rows(
            business_unit_rows=(_business_unit_row(),),
            activity_subject_rows=rows,
        )
    assert exc_info.value.code == "duplicate_catalog_key"


def test_catalog_unit_type_change_rejected_when_referenced(imported_catalog):
    _link_runtime_business_unit(catalog_key="maintenance")
    rows = (
        _business_unit_row(key="maintenance", label="Maintenance", unit_type="dedicated"),
    )
    with pytest.raises(CatalogImportError) as exc_info:
        sync_catalog_from_normalized_rows(
            business_unit_rows=rows,
            activity_subject_rows=(),
        )
    assert exc_info.value.code == "catalog_immutable_field"
    assert CatalogBusinessUnit.objects.get(key="maintenance").unit_type == "transversal"


def test_catalog_import_rejects_subject_business_unit_change_when_referenced(imported_catalog):
    business_unit = _link_runtime_business_unit(catalog_key="hotel")
    _link_runtime_activity_subject(business_unit=business_unit, catalog_key="hotel__menage")

    rows = (
        _business_unit_row(),
        _business_unit_row(key="coworking", label="Coworking"),
        _activity_subject_row(
            key="hotel__menage",
            label="Ménage",
            business_unit_key="coworking",
        ),
    )
    with pytest.raises(CatalogImportError) as exc_info:
        sync_catalog_from_normalized_rows(
            business_unit_rows=rows[:2],
            activity_subject_rows=rows[2:],
        )
    assert exc_info.value.code == "catalog_subject_immutable_business_unit"
    subject = CatalogActivitySubject.objects.get(key="hotel__menage")
    assert subject.catalog_business_unit.key == "hotel"


def test_catalog_import_missing_existing_key_is_noop(imported_catalog):
    orphan = CatalogBusinessUnit.objects.create(
        key="orphan_catalog_bu",
        label="Orphan",
        unit_type=CatalogBusinessUnit.DefaultUnitType.DEDICATED,
        description="keep-me",
        active=False,
        sort_order=999,
    )

    sync_catalog_from_normalized_rows(
        business_unit_rows=(_business_unit_row(),),
        activity_subject_rows=(_activity_subject_row(),),
    )

    orphan.refresh_from_db()
    assert orphan.label == "Orphan"
    assert orphan.description == "keep-me"
    assert orphan.active is False
    assert orphan.sort_order == 999


def test_catalog_import_is_atomic_on_preflight_failure(imported_catalog):
    _link_runtime_business_unit(catalog_key="maintenance")
    before_label = CatalogBusinessUnit.objects.get(key="hotel").label
    before_count = CatalogBusinessUnit.objects.count()

    rows = (
        _business_unit_row(key="hotel", label="Hôtel modifié"),
        _business_unit_row(key="maintenance", label="Maintenance", unit_type="dedicated"),
    )
    with pytest.raises(CatalogImportError):
        sync_catalog_from_normalized_rows(
            business_unit_rows=rows,
            activity_subject_rows=(),
        )

    assert CatalogBusinessUnit.objects.count() == before_count
    assert CatalogBusinessUnit.objects.get(key="hotel").label == before_label


def test_catalog_import_label_change_uses_label_service(imported_catalog):
    business_unit = _link_runtime_business_unit(catalog_key="hotel")
    _link_runtime_activity_subject(business_unit=business_unit, catalog_key="hotel__menage")

    with patch(
        "houston.establishments.catalog_import._apply_catalog_activity_subject_label_update",
        wraps=_apply_catalog_activity_subject_label_update,
    ) as label_update:
        sync_catalog_from_normalized_rows(
            business_unit_rows=(_business_unit_row(),),
            activity_subject_rows=(
                _activity_subject_row(key="hotel__menage", label="Housekeeping"),
            ),
        )

    label_update.assert_called_once_with(
        catalog_activity_subject_key="hotel__menage",
        new_label="Housekeeping",
    )


def test_catalog_import_label_change_propagates_runtime_subject_label_and_normalized_name(
    imported_catalog,
):
    business_unit = _link_runtime_business_unit(catalog_key="hotel")
    runtime_subject = _link_runtime_activity_subject(
        business_unit=business_unit,
        catalog_key="hotel__menage",
    )

    sync_catalog_from_normalized_rows(
        business_unit_rows=(_business_unit_row(),),
        activity_subject_rows=(
            _activity_subject_row(key="hotel__menage", label="Housekeeping"),
        ),
    )

    runtime_subject.refresh_from_db()
    assert CatalogActivitySubject.objects.get(key="hotel__menage").label == "Housekeeping"
    assert runtime_subject.label == "Housekeeping"
    assert runtime_subject.normalized_name == normalize_activity_subject_name("Housekeeping")


def test_catalog_subject_custom_prefix_rejected_by_database_constraint(imported_catalog):
    hotel = CatalogBusinessUnit.objects.get(key="hotel")
    with pytest.raises(IntegrityError):
        CatalogActivitySubject.objects.bulk_create(
            [
                CatalogActivitySubject(
                    key="custom--reserved",
                    label="Reserved",
                    catalog_business_unit=hotel,
                    active=True,
                )
            ]
        )


def test_catalog_subject_label_update_propagates_normalized_name(imported_catalog):
    business_unit = _link_runtime_business_unit(catalog_key="hotel")
    runtime_subject = _link_runtime_activity_subject(
        business_unit=business_unit,
        catalog_key="hotel__menage",
    )

    update_catalog_activity_subject_label(
        catalog_activity_subject_key="hotel__menage",
        new_label="Housekeeping",
    )

    runtime_subject.refresh_from_db()
    assert runtime_subject.label == "Housekeeping"
    assert runtime_subject.normalized_name == normalize_activity_subject_name("Housekeeping")


def test_catalog_subject_label_update_rejected_on_collision(imported_catalog):
    business_unit = _link_runtime_business_unit(catalog_key="hotel")
    _link_runtime_activity_subject(business_unit=business_unit, catalog_key="hotel__menage")
    create_activity_subject(
        establishment=business_unit.establishment,
        business_unit=business_unit,
        label="Housekeeping",
    )

    with pytest.raises(CatalogSubjectLabelConflictError) as exc_info:
        update_catalog_activity_subject_label(
            catalog_activity_subject_key="hotel__menage",
            new_label="Housekeeping",
        )
    assert exc_info.value.code == "catalog_subject_label_conflict"
    assert CatalogActivitySubject.objects.get(key="hotel__menage").label == "Ménage"


def test_catalog_subject_label_update_is_atomic(imported_catalog):
    business_unit = _link_runtime_business_unit(catalog_key="hotel")
    catalog_subject = CatalogActivitySubject.objects.get(key="hotel__menage")
    first_subject = _link_runtime_activity_subject(
        business_unit=business_unit,
        catalog_key="hotel__menage",
    )
    create_activity_subject(
        establishment=business_unit.establishment,
        business_unit=business_unit,
        label="Housekeeping",
    )

    with pytest.raises(CatalogSubjectLabelConflictError):
        update_catalog_activity_subject_label(
            catalog_activity_subject_key="hotel__menage",
            new_label="Housekeeping",
        )

    catalog_subject.refresh_from_db()
    first_subject.refresh_from_db()
    assert catalog_subject.label == "Ménage"
    assert first_subject.label == "Ménage"


def test_catalog_subject_label_update_rejects_empty_normalized_name(imported_catalog):
    with pytest.raises(CatalogSubjectLabelValidationError) as exc_info:
        update_catalog_activity_subject_label(
            catalog_activity_subject_key="hotel__menage",
            new_label="   ",
        )
    assert exc_info.value.code == "invalid_normalized_name"

    with pytest.raises(CatalogSubjectLabelValidationError):
        update_catalog_activity_subject_label(
            catalog_activity_subject_key="hotel__menage",
            new_label="!!!",
        )


def test_catalog_subject_label_update_handles_concurrent_collision(imported_catalog):
    business_unit = _link_runtime_business_unit(catalog_key="hotel")
    runtime_subject = _link_runtime_activity_subject(
        business_unit=business_unit,
        catalog_key="hotel__menage",
    )
    original_save = ActivitySubject.save
    save_calls = {"count": 0}

    def flaky_save(self, *args, **kwargs):
        save_calls["count"] += 1
        if save_calls["count"] == 1:
            raise IntegrityError("simulated concurrent normalized_name collision")
        return original_save(self, *args, **kwargs)

    with patch.object(ActivitySubject, "save", flaky_save):
        with pytest.raises(CatalogSubjectLabelConflictError):
            update_catalog_activity_subject_label(
                catalog_activity_subject_key="hotel__menage",
                new_label="Balcon",
            )

    runtime_subject.refresh_from_db()
    assert CatalogActivitySubject.objects.get(key="hotel__menage").label == "Ménage"
    assert runtime_subject.label == "Ménage"


def test_catalog_custom_prefix_migration_rejects_existing_invalid_row():
    mock_model = MagicMock()
    mock_model.objects.filter.return_value.order_by.return_value.values_list.return_value = [
        "custom--legacy"
    ]
    mock_apps = MagicMock()
    mock_apps.get_model.return_value = mock_model

    with pytest.raises(RuntimeError, match="custom--legacy"):
        _assert_no_custom_prefix_catalog_subject_keys(mock_apps, None)
