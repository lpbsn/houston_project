from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from houston.action_plans.constants import (
    EXECUTION_STATUS_IN_PROGRESS,
    EXECUTION_STATUS_PENDING_VALIDATION,
    EXECUTION_STATUS_SCHEDULED,
)
from houston.establishments.mama_nice_dataset_clock import (
    REFERENCE_SEED_KEY,
    assert_reference_compatible,
    first_frozen_public_event_start,
    in_progress_window,
    load_persisted_reference_at,
    non_terminal_runtime_errors,
    overdue_end_at,
    pending_on_time_window,
    resolve_seed_reference_at,
    use_reference_at,
)
from houston.establishments.mama_nice_dataset_constants import OBJECT_TYPE_CLOCK, SNAPSHOT
from houston.establishments.mama_nice_dataset_exceptions import MamaNiceDatasetError
from houston.establishments.models import MamaNiceSeedRecord
from houston.testing.factories import create_establishment


def _execution(*, status, start_at, end_at, title="exec"):
    return SimpleNamespace(
        id=title,
        status=status,
        start_at=start_at,
        end_at=end_at,
        title=title,
    )


def test_injected_clock_windows_never_use_reference_as_end():
    reference = SNAPSHOT + timedelta(hours=12)
    start, end = in_progress_window(reference_at=reference)
    assert start <= reference < end
    assert end != reference
    pending_start, pending_end = pending_on_time_window(reference_at=reference)
    assert pending_end > reference
    assert pending_end != reference
    assert pending_start <= reference
    late = overdue_end_at(days_late=3, reference_at=reference)
    assert late == reference - timedelta(days=3)
    assert late != reference


def test_reference_outside_public_event_window_fails_without_moving_events():
    limit = first_frozen_public_event_start()
    assert limit == datetime(2026, 9, 24, 9, 0, tzinfo=SNAPSHOT.tzinfo)
    assert_reference_compatible(SNAPSHOT)
    with pytest.raises(MamaNiceDatasetError, match="before the authored snapshot"):
        assert_reference_compatible(SNAPSHOT - timedelta(minutes=1))
    with pytest.raises(MamaNiceDatasetError, match="frozen public-event window"):
        assert_reference_compatible(limit)


@pytest.mark.django_db
def test_first_seed_persists_clock_and_resume_reuses_it():
    establishment = create_establishment(name="Mama clock persist", timezone="Europe/Paris")
    first = resolve_seed_reference_at(
        establishment=establishment,
        resume=False,
        as_of=SNAPSHOT,
        persist=True,
    )
    assert first == SNAPSHOT
    record = MamaNiceSeedRecord.objects.get(
        establishment=establishment,
        object_type=OBJECT_TYPE_CLOCK,
        seed_key=REFERENCE_SEED_KEY,
    )
    fingerprint = record.fingerprint
    assert load_persisted_reference_at(establishment) == SNAPSHOT

    resumed = resolve_seed_reference_at(
        establishment=establishment,
        resume=True,
        persist=True,
    )
    assert resumed == SNAPSHOT
    record.refresh_from_db()
    assert record.fingerprint == fingerprint
    assert MamaNiceSeedRecord.objects.filter(
        establishment=establishment,
        object_type=OBJECT_TYPE_CLOCK,
    ).count() == 1

    with pytest.raises(MamaNiceDatasetError, match="does not match"):
        resolve_seed_reference_at(
            establishment=establishment,
            resume=True,
            as_of=SNAPSHOT + timedelta(hours=1),
        )


@pytest.mark.django_db
def test_resume_without_persisted_clock_fails():
    establishment = create_establishment(name="Mama clock missing", timezone="Europe/Paris")
    with pytest.raises(MamaNiceDatasetError, match="cannot --resume"):
        resolve_seed_reference_at(establishment=establishment, resume=True)


def test_only_six_overdues_are_accepted_even_for_a_few_minutes():
    reference = SNAPSHOT
    overdues = [
        _execution(
            status=EXECUTION_STATUS_PENDING_VALIDATION,
            start_at=overdue_end_at(days_late=days, reference_at=reference) - timedelta(days=2),
            end_at=overdue_end_at(days_late=days, reference_at=reference),
            title=f"late-{days}",
        )
        for days in range(2, 8)
    ]
    start, end = in_progress_window(reference_at=reference)
    on_time = [
        _execution(
            status=EXECUTION_STATUS_IN_PROGRESS,
            start_at=start,
            end_at=end,
            title="in-progress",
        ),
        _execution(
            status=EXECUTION_STATUS_PENDING_VALIDATION,
            start_at=pending_on_time_window(reference_at=reference)[0],
            end_at=pending_on_time_window(reference_at=reference)[1],
            title="pending-on-time",
        ),
        _execution(
            status=EXECUTION_STATUS_SCHEDULED,
            start_at=reference + timedelta(hours=1),
            end_at=reference + timedelta(hours=3),
            title="scheduled",
        ),
    ]
    assert non_terminal_runtime_errors(
        executions=[*overdues, *on_time],
        reference_at=reference,
    ) == []

    extra = _execution(
        status=EXECUTION_STATUS_IN_PROGRESS,
        start_at=reference - timedelta(hours=1),
        end_at=reference - timedelta(minutes=5),
        title="almost-on-time",
    )
    errors = non_terminal_runtime_errors(
        executions=[*overdues, *on_time, extra],
        reference_at=reference,
    )
    assert any("overdue executions 7 != 6" in item or "extra overdue" in item for item in errors)

    equal_end = _execution(
        status=EXECUTION_STATUS_IN_PROGRESS,
        start_at=reference - timedelta(hours=1),
        end_at=reference,
        title="end-equals-reference",
    )
    equal_errors = non_terminal_runtime_errors(
        executions=[*overdues, equal_end],
        reference_at=reference,
    )
    assert any("must not equal reference_at" in item for item in equal_errors)


def test_operational_now_follows_injected_reference():
    from houston.establishments.mama_nice_dataset_clock import operational_now
    from houston.establishments.mama_nice_dataset_scenarios import overdue_execution_specs

    injected = SNAPSHOT + timedelta(hours=8)
    with use_reference_at(injected):
        assert operational_now() == injected
        specs = overdue_execution_specs()
        assert {item.days_late for item in specs} == set(range(2, 8))
        assert all(item.end_at < injected for item in specs)
        assert all(item.end_at != injected for item in specs)
