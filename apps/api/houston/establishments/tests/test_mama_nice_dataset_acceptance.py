from datetime import datetime, timedelta

from houston.establishments.mama_nice_dataset_acceptance import (
    TOTAL_EXECUTION_COUNT,
    authored_calendar_specs,
    runtime_calendar_elapsed_specs,
    runtime_calendar_remaining_specs,
)
from houston.establishments.mama_nice_dataset_constants import (
    FUTURE_BY_MONTH,
    FUTURE_EXECUTION_COUNT,
    HISTORICAL_EXECUTION_COUNT,
    PARIS_TZ,
    SNAPSHOT,
)


def test_canonical_calendar_specs_are_independent_of_reference_clock():
    specs = authored_calendar_specs()
    assert len(specs) == FUTURE_EXECUTION_COUNT
    assert HISTORICAL_EXECUTION_COUNT + len(specs) == TOTAL_EXECUTION_COUNT
    months = {
        (item.start_at.astimezone(PARIS_TZ).year, item.start_at.astimezone(PARIS_TZ).month)
        for item in specs
    }
    assert {(year, month) for year, month in FUTURE_BY_MONTH} <= months
    assert len(runtime_calendar_elapsed_specs(reference_at=SNAPSHOT)) == 0
    assert len(runtime_calendar_remaining_specs(reference_at=SNAPSHOT)) == FUTURE_EXECUTION_COUNT


def test_runtime_projection_moves_elapsed_calendar_rows_without_calling_them_futures():
    reference_at = datetime(2026, 9, 23, 15, 30, tzinfo=SNAPSHOT.tzinfo)
    elapsed = runtime_calendar_elapsed_specs(reference_at=reference_at)
    remaining = runtime_calendar_remaining_specs(reference_at=reference_at)
    assert elapsed
    assert all(SNAPSHOT < item.start_at <= reference_at for item in elapsed)
    assert all(item.start_at > reference_at for item in remaining)
    assert len(elapsed) + len(remaining) == FUTURE_EXECUTION_COUNT
    assert {authored_id(item) for item in elapsed}.isdisjoint(
        {authored_id(item) for item in remaining}
    )
    expected_elapsed = HISTORICAL_EXECUTION_COUNT + len(elapsed)
    expected_remaining = len(remaining)
    assert expected_elapsed + expected_remaining == TOTAL_EXECUTION_COUNT
    assert expected_elapsed != HISTORICAL_EXECUTION_COUNT
    assert expected_remaining != FUTURE_EXECUTION_COUNT


def authored_id(item) -> str:
    from houston.establishments.mama_nice_dataset_acceptance import authored_calendar_identity

    return authored_calendar_identity(item)


def test_later_reference_does_not_change_canonical_180():
    later = SNAPSHOT + timedelta(hours=16)
    assert len(authored_calendar_specs()) == FUTURE_EXECUTION_COUNT
    assert len(runtime_calendar_remaining_specs(reference_at=later)) < FUTURE_EXECUTION_COUNT
