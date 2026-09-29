from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from houston.core.feed_hardening_baseline import (
    QueryDiagnostic,
    _assert_pr5d_materialization_only_effect,
    _delete_feed_baseline_dataset,
    _explain_summary,
    _query_attribution,
    _snapshot_delta,
    _visible_same_day_materialization_window,
    resolve_feed_baseline_profile,
)
from houston.notifications.models import Notification


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("establishments", "establishments must be positive"),
        ("signals_per_establishment", "signals_per_establishment must be at least 30"),
        ("executions_per_establishment", "executions_per_establishment must be at least 30"),
    ],
)
def test_explicit_zero_reaches_baseline_profile_validation(field, message):
    with pytest.raises(ValueError, match=message):
        resolve_feed_baseline_profile("smoke", **{field: 0})


@pytest.mark.django_db
def test_delete_feed_baseline_dataset_deletes_notifications_once(monkeypatch):
    delete_calls = 0
    original_filter = Notification.objects.filter

    def counting_filter(*args, **kwargs):
        queryset = original_filter(*args, **kwargs)
        original_delete = queryset.delete

        def counting_delete(*delete_args, **delete_kwargs):
            nonlocal delete_calls
            delete_calls += 1
            return original_delete(*delete_args, **delete_kwargs)

        queryset.delete = counting_delete
        return queryset

    monkeypatch.setattr(Notification.objects, "filter", counting_filter)

    _delete_feed_baseline_dataset()

    assert delete_calls == 1


def test_query_attribution_groups_every_recorded_shape():
    queries = [
        QueryDiagnostic(
            sql=(
                'SELECT "action_plans_actionplanexecution"."id" '
                'FROM "action_plans_actionplanexecution" '
                'WHERE "action_plans_actionplanexecution"."availability_notified_at" IS NULL '
                'AND "action_plans_actionplanexecution"."visible_from" <= %s'
            ),
            params=(),
            elapsed_ms=2.0,
        ),
        QueryDiagnostic(
            sql='INSERT INTO "action_plans_actionplanexecutionlifecycleevent" DEFAULT VALUES',
            params=(),
            elapsed_ms=1.0,
        ),
        QueryDiagnostic(sql="COMMIT", params=None, elapsed_ms=0.5),
    ]

    attribution = _query_attribution(queries)

    assert sum(row["count"] for row in attribution) == len(queries)
    assert {
        (row["owner"], row["role"])
        for row in attribution
    } == {
        ("action_plans.lifecycle_promotion", "availability_candidates"),
        ("action_plans.lifecycle_events", "lifecycle_events"),
        ("django_transaction", "transaction_control"),
    }


def test_snapshot_delta_keeps_exact_non_zero_side_effects():
    before = {"executions": 2, "events": {"created": 1, "started": 1}}
    after = {"executions": 3, "events": {"created": 2, "started": 1}}

    assert _snapshot_delta(before, after) == {
        "executions": 1,
        "events": {"created": 1},
    }


@pytest.mark.parametrize(
    "local_hour",
    [0, 6, 8, 22, 23],
)
def test_materialization_window_is_visible_on_the_same_local_day(local_hour):
    tz = ZoneInfo("Europe/Paris")
    now = datetime(2026, 9, 29, local_hour, 15, tzinfo=tz)
    start_at, end_at = _visible_same_day_materialization_window(now, tz)
    start = datetime.combine(now.date(), start_at, tzinfo=tz)
    end = datetime.combine(now.date(), end_at, tzinfo=tz)

    assert end - start == timedelta(hours=2)
    assert start - timedelta(hours=1) <= now


def test_materialization_only_rejects_a_noop_effect():
    with pytest.raises(RuntimeError, match="without materializing"):
        _assert_pr5d_materialization_only_effect(
            {"side_effect_delta": {"executions": 0, "materialized_schedules": 0}}
        )


def test_explain_summary_exposes_planning_executor_and_buffers():
    plan = [
        {
            "Planning Time": 1.25,
            "Execution Time": 2.5,
            "Plan": {
                "Actual Rows": 3,
                "Shared Hit Blocks": 4,
                "Shared Read Blocks": 5,
                "Temp Read Blocks": 6,
                "Temp Written Blocks": 7,
            },
        }
    ]

    assert _explain_summary(plan) == {
        "planning_ms": 1.25,
        "executor_ms": 2.5,
        "rows": 3,
        "shared_hit_blocks": 4,
        "shared_read_blocks": 5,
        "shared_dirtied_blocks": 0,
        "shared_written_blocks": 0,
        "temp_read_blocks": 6,
        "temp_written_blocks": 7,
    }
