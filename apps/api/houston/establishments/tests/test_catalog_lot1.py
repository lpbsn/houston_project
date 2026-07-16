from __future__ import annotations

import importlib
import threading
import time
from unittest.mock import MagicMock, patch

import pytest
from django.db import IntegrityError, close_old_connections, connection, transaction

from houston.establishments.business_unit_identity import normalize_generic_activity_subject_name
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
    return create_business_unit(
        establishment=establishment,
        key=catalog_key,
        label=catalog_business_unit.label,
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
        catalog_activity_subject=catalog_subject,
        normalized_name=normalize_generic_activity_subject_name(catalog_subject.label),
        label="",
        description="",
        routing_key=catalog_subject.key,
        source=ActivitySubject.Source.CATALOG_SUGGESTION,
        active=True,
    )




def _require_postgresql() -> None:
    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL-only concurrency test")


def _session_has_ungranted_lock(*, pid: int) -> bool:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT EXISTS (SELECT 1 FROM pg_locks WHERE pid = %s AND NOT granted)",
            [pid],
        )
        return cursor.fetchone()[0]


def _wait_until_session_waiting_for_lock(*, pid: int) -> None:
    for _ in range(500):
        if _session_has_ungranted_lock(pid=pid):
            return
        time.sleep(0.01)
    raise AssertionError(f"Expected PostgreSQL session {pid} to block on a lock")

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




@pytest.mark.django_db(transaction=True)
def test_catalog_bu_lock_blocks_concurrent_business_unit_reference(imported_catalog):
    _require_postgresql()

    establishment = create_establishment()
    catalog_bu = CatalogBusinessUnit.objects.get(key="maintenance")
    catalog_locked = threading.Event()
    runtime_attempting = threading.Event()
    runtime_finished = threading.Event()
    runtime_error: list[BaseException] = []
    runtime_pid: dict[str, int | None] = {"value": None}

    def runtime_txn() -> None:
        close_old_connections()
        try:
            assert catalog_locked.wait(timeout=5)
            runtime_pid["value"] = connection.cursor().connection.info.backend_pid
            runtime_attempting.set()
            with transaction.atomic():
                create_business_unit(
                    establishment=establishment,
                    key="maintenance",
                    label=catalog_bu.label,
                )
            runtime_finished.set()
        except BaseException as exc:
            runtime_error.append(exc)
        finally:
            close_old_connections()

    runtime_thread = threading.Thread(target=runtime_txn)
    runtime_thread.start()

    try:
        with transaction.atomic():
            CatalogBusinessUnit.objects.select_for_update().get(key="maintenance")
            catalog_locked.set()
            assert runtime_attempting.wait(timeout=5)
            assert runtime_pid["value"] is not None
            _wait_until_session_waiting_for_lock(pid=runtime_pid["value"])
            assert not runtime_finished.is_set()
    finally:
        runtime_thread.join(timeout=10)

    assert not runtime_error
    assert runtime_finished.is_set()
    assert BusinessUnit.objects.filter(catalog_business_unit_id=catalog_bu.id).count() == 1


@pytest.mark.django_db(transaction=True)
def test_catalog_subject_lock_blocks_concurrent_activity_subject_reference(imported_catalog):
    _require_postgresql()

    establishment = create_establishment()
    catalog_bu = CatalogBusinessUnit.objects.get(key="hotel")
    runtime_bu = create_business_unit(
        establishment=establishment,
        key="hotel",
        label=catalog_bu.label,
    )
    catalog_as = CatalogActivitySubject.objects.get(key="hotel__menage")
    catalog_locked = threading.Event()
    runtime_attempting = threading.Event()
    runtime_finished = threading.Event()
    runtime_error: list[BaseException] = []
    runtime_pid: dict[str, int | None] = {"value": None}

    def runtime_txn() -> None:
        close_old_connections()
        try:
            assert catalog_locked.wait(timeout=5)
            runtime_pid["value"] = connection.cursor().connection.info.backend_pid
            runtime_attempting.set()
            with transaction.atomic():
                ActivitySubject.objects.create(
                    establishment=establishment,
                    business_unit=runtime_bu,
                    catalog_activity_subject=catalog_as,
                    normalized_name=normalize_generic_activity_subject_name(catalog_as.label),
                    label="",
                    description="",
                    routing_key=catalog_as.key,
                    source=ActivitySubject.Source.CATALOG_SUGGESTION,
                    active=True,
                )
            runtime_finished.set()
        except BaseException as exc:
            runtime_error.append(exc)
        finally:
            close_old_connections()

    runtime_thread = threading.Thread(target=runtime_txn)
    runtime_thread.start()

    try:
        with transaction.atomic():
            CatalogActivitySubject.objects.select_for_update(of=("self",)).get(
                key="hotel__menage"
            )
            catalog_locked.set()
            assert runtime_attempting.wait(timeout=5)
            assert runtime_pid["value"] is not None
            _wait_until_session_waiting_for_lock(pid=runtime_pid["value"])
            assert not runtime_finished.is_set()
    finally:
        runtime_thread.join(timeout=10)

    assert not runtime_error
    assert runtime_finished.is_set()
    assert (
        ActivitySubject.objects.filter(catalog_activity_subject_id=catalog_as.id).count() == 1
    )

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


def test_catalog_import_does_not_deactivate_absent_keys(imported_catalog):
    hotel = CatalogBusinessUnit.objects.get(key="hotel")
    menage = CatalogActivitySubject.objects.get(key="hotel__menage")
    assert hotel.active is True
    assert menage.active is True

    sync_catalog_from_normalized_rows(
        business_unit_rows=(
            _business_unit_row(key="restaurant", label="Restaurant"),
        ),
        activity_subject_rows=(
            _activity_subject_row(
                key="restaurant__stock",
                label="Stock",
                business_unit_key="restaurant",
            ),
        ),
    )

    hotel.refresh_from_db()
    menage.refresh_from_db()
    assert hotel.active is True
    assert menage.active is True


def test_catalog_import_new_key_creates_new_definition_without_modifying_old_key(
    imported_catalog,
):
    hotel_before = CatalogBusinessUnit.objects.get(key="hotel")
    hotel_snapshot = (
        hotel_before.label,
        hotel_before.description,
        hotel_before.unit_type,
        hotel_before.active,
        hotel_before.sort_order,
    )
    before_count = CatalogBusinessUnit.objects.count()

    sync_catalog_from_normalized_rows(
        business_unit_rows=(
            _business_unit_row(
                key="spa_wellness",
                label="Spa Wellness",
                unit_type="dedicated",
            ),
        ),
        activity_subject_rows=(),
    )

    hotel_after = CatalogBusinessUnit.objects.get(key="hotel")
    assert (
        hotel_after.label,
        hotel_after.description,
        hotel_after.unit_type,
        hotel_after.active,
        hotel_after.sort_order,
    ) == hotel_snapshot
    assert CatalogBusinessUnit.objects.count() == before_count + 1
    created = CatalogBusinessUnit.objects.get(key="spa_wellness")
    assert created.label == "Spa Wellness"
    assert created.active is True


def test_catalog_import_missing_referenced_key_is_noop(imported_catalog):
    business_unit = _link_runtime_business_unit(catalog_key="hotel")
    subject = _link_runtime_activity_subject(
        business_unit=business_unit,
        catalog_key="hotel__menage",
    )
    catalog_bu = CatalogBusinessUnit.objects.get(key="hotel")
    catalog_subject = CatalogActivitySubject.objects.get(key="hotel__menage")
    bu_snapshot = (
        catalog_bu.label,
        catalog_bu.description,
        catalog_bu.active,
        catalog_bu.sort_order,
    )
    subject_snapshot = (
        catalog_subject.label,
        catalog_subject.description,
        catalog_subject.active,
        catalog_subject.sort_order,
        catalog_subject.catalog_business_unit_id,
    )

    sync_catalog_from_normalized_rows(
        business_unit_rows=(
            _business_unit_row(key="restaurant", label="Restaurant"),
        ),
        activity_subject_rows=(
            _activity_subject_row(
                key="restaurant__stock",
                label="Stock",
                business_unit_key="restaurant",
            ),
        ),
    )

    catalog_bu.refresh_from_db()
    catalog_subject.refresh_from_db()
    business_unit.refresh_from_db()
    subject.refresh_from_db()
    assert (
        catalog_bu.label,
        catalog_bu.description,
        catalog_bu.active,
        catalog_bu.sort_order,
    ) == bu_snapshot
    assert (
        catalog_subject.label,
        catalog_subject.description,
        catalog_subject.active,
        catalog_subject.sort_order,
        catalog_subject.catalog_business_unit_id,
    ) == subject_snapshot
    assert business_unit.catalog_business_unit_id == catalog_bu.id
    assert subject.catalog_activity_subject_id == catalog_subject.id


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
    assert runtime_subject.label == ""
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
    assert runtime_subject.label == ""
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
    assert first_subject.label == ""


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
    assert runtime_subject.label == ""


def test_catalog_custom_prefix_migration_rejects_existing_invalid_row():
    migration_module = importlib.import_module(
        "houston.establishments.migrations.0022_catalog_lot1"
    )
    assert_fn = migration_module._assert_no_custom_prefix_catalog_subject_keys

    mock_model = MagicMock()
    mock_model.objects.filter.return_value.order_by.return_value.values_list.return_value = [
        "custom--legacy"
    ]
    mock_apps = MagicMock()
    mock_apps.get_model.return_value = mock_model

    with pytest.raises(RuntimeError, match="custom--legacy"):
        assert_fn(mock_apps, None)
