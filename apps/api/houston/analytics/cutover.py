"""Idempotent Analytics journal cutover: baseline + current-episode terminal events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from django.db import connection as default_connection
from django.utils import timezone

from houston.action_plans.constants import (
    EXECUTION_LIFECYCLE_EVENT_CANCELED,
    EXECUTION_LIFECYCLE_EVENT_HISTORY_BASELINE,
    EXECUTION_LIFECYCLE_EVENT_MARKED_DONE,
    EXECUTION_LIFECYCLE_EVENT_VALIDATED,
    EXECUTION_STATUS_CANCELED,
    EXECUTION_STATUS_DONE,
    EXECUTION_STATUS_PENDING_VALIDATION,
)
from houston.action_plans.models import ActionPlanExecution, ActionPlanExecutionLifecycleEvent
from houston.analytics.models import AnalyticsHistoryCoverage
from houston.signals.constants import (
    SIGNAL_LIFECYCLE_EVENT_ARCHIVED,
    SIGNAL_LIFECYCLE_EVENT_CANCELED,
    SIGNAL_LIFECYCLE_EVENT_HISTORY_BASELINE,
    SIGNAL_LIFECYCLE_EVENT_RESOLVED,
)
from houston.signals.models import Signal, SignalLifecycleEvent

_END_AT_ISO_EXPR = (
    "CASE WHEN {alias}.end_at IS NULL THEN NULL "
    "ELSE to_char({alias}.end_at AT TIME ZONE 'UTC', "
    """'YYYY-MM-DD"T"HH24:MI:SS.US') || '+00:00' END"""
)


@dataclass(frozen=True)
class _CutoverTables:
    signals: str
    signal_events: str
    executions: str
    execution_events: str


def apply_analytics_history_cutover(*, now: datetime | None = None) -> datetime:
    """Persist ``history_reliable_from`` once and insert baselines + current terminals.

    Idempotent on ``(object, event_type, occurred_at)`` and one baseline per object.
    """
    occurred_at = now or timezone.now()
    coverage, _created = AnalyticsHistoryCoverage.objects.get_or_create(
        singleton_key=AnalyticsHistoryCoverage.SINGLETON_KEY,
        defaults={"reliable_from": occurred_at},
    )
    reliable_from = coverage.reliable_from
    _execute_history_cutover_inserts(default_connection, reliable_from=reliable_from)
    return reliable_from


def reset_history_reliable_from(*, now: datetime | None = None) -> datetime:
    """Overwrite the coverage singleton. Does not insert journal baselines."""
    occurred_at = now or timezone.now()
    coverage, _created = AnalyticsHistoryCoverage.objects.update_or_create(
        singleton_key=AnalyticsHistoryCoverage.SINGLETON_KEY,
        defaults={"reliable_from": occurred_at},
    )
    return coverage.reliable_from


def _require_postgresql(connection) -> None:
    if connection.vendor != "postgresql":
        raise RuntimeError("Analytics history cutover requires PostgreSQL.")


def _quoted_table(connection, model) -> str:
    return connection.ops.quote_name(model._meta.db_table)


def _execute_history_cutover_inserts(connection, *, reliable_from: datetime) -> None:
    _require_postgresql(connection)
    tables = _CutoverTables(
        signals=_quoted_table(connection, Signal),
        signal_events=_quoted_table(connection, SignalLifecycleEvent),
        executions=_quoted_table(connection, ActionPlanExecution),
        execution_events=_quoted_table(connection, ActionPlanExecutionLifecycleEvent),
    )
    with connection.cursor() as cursor:
        for sql, params in _history_cutover_insert_statements(tables, reliable_from=reliable_from):
            cursor.execute(sql, params)


def _history_cutover_insert_statements(
    tables: _CutoverTables, *, reliable_from: datetime
) -> list[tuple[str, list]]:
    end_at_exec = _END_AT_ISO_EXPR.format(alias="e")
    return [
        (
            f"""
            INSERT INTO {tables.signal_events} (
                id, created_at, updated_at, signal_id, establishment_id,
                event_type, actor_membership_id, occurred_at, metadata_safe
            )
            SELECT
                gen_random_uuid(),
                now(),
                now(),
                s.id,
                s.establishment_id,
                '{SIGNAL_LIFECYCLE_EVENT_HISTORY_BASELINE}',
                NULL,
                %s,
                jsonb_build_object('to_status', s.status)
            FROM {tables.signals} s
            WHERE NOT EXISTS (
                SELECT 1
                FROM {tables.signal_events} existing
                WHERE existing.signal_id = s.id
                  AND existing.event_type = '{SIGNAL_LIFECYCLE_EVENT_HISTORY_BASELINE}'
            )
            """,
            [reliable_from],
        ),
        (
            f"""
            INSERT INTO {tables.execution_events} (
                id, created_at, updated_at, action_plan_execution_id,
                establishment_id, event_type, actor_membership_id,
                occurred_at, metadata_safe
            )
            SELECT
                gen_random_uuid(),
                now(),
                now(),
                e.id,
                e.establishment_id,
                '{EXECUTION_LIFECYCLE_EVENT_HISTORY_BASELINE}',
                NULL,
                %s,
                jsonb_build_object(
                    'to_status', e.status,
                    'end_at', {end_at_exec}
                )
            FROM {tables.executions} e
            WHERE NOT EXISTS (
                SELECT 1
                FROM {tables.execution_events} existing
                WHERE existing.action_plan_execution_id = e.id
                  AND existing.event_type = '{EXECUTION_LIFECYCLE_EVENT_HISTORY_BASELINE}'
            )
            """,
            [reliable_from],
        ),
        *_signal_terminal_statements(tables),
        *_execution_terminal_statements(tables, end_at_exec=end_at_exec),
    ]


def _signal_terminal_statements(tables: _CutoverTables) -> list[tuple[str, list]]:
    terminals = (
        ("resolved", "resolved_at", SIGNAL_LIFECYCLE_EVENT_RESOLVED),
        ("canceled", "canceled_at", SIGNAL_LIFECYCLE_EVENT_CANCELED),
        ("archived", "archived_at", SIGNAL_LIFECYCLE_EVENT_ARCHIVED),
    )
    statements = []
    for status, timestamp_field, event_type in terminals:
        statements.append(
            (
                f"""
                INSERT INTO {tables.signal_events} (
                    id, created_at, updated_at, signal_id, establishment_id,
                    event_type, actor_membership_id, occurred_at, metadata_safe
                )
                SELECT
                    gen_random_uuid(),
                    now(),
                    now(),
                    s.id,
                    s.establishment_id,
                    '{event_type}',
                    NULL,
                    s.{timestamp_field},
                    jsonb_build_object('to_status', '{status}')
                FROM {tables.signals} s
                WHERE s.status = '{status}'
                  AND s.{timestamp_field} IS NOT NULL
                  AND NOT EXISTS (
                    SELECT 1
                    FROM {tables.signal_events} existing
                    WHERE existing.signal_id = s.id
                      AND existing.event_type = '{event_type}'
                      AND existing.occurred_at = s.{timestamp_field}
                  )
                """,
                [],
            )
        )
    return statements


def _execution_terminal_statements(
    tables: _CutoverTables, *, end_at_exec: str
) -> list[tuple[str, list]]:
    return [
        (
            f"""
            INSERT INTO {tables.execution_events} (
                id, created_at, updated_at, action_plan_execution_id,
                establishment_id, event_type, actor_membership_id,
                occurred_at, metadata_safe
            )
            SELECT
                gen_random_uuid(),
                now(),
                now(),
                e.id,
                e.establishment_id,
                '{EXECUTION_LIFECYCLE_EVENT_MARKED_DONE}',
                NULL,
                e.marked_done_at,
                jsonb_build_object(
                    'to_status', '{EXECUTION_STATUS_PENDING_VALIDATION}',
                    'end_at', {end_at_exec}
                )
            FROM {tables.executions} e
            WHERE e.status = '{EXECUTION_STATUS_PENDING_VALIDATION}'
              AND e.marked_done_at IS NOT NULL
              AND NOT EXISTS (
                SELECT 1
                FROM {tables.execution_events} existing
                WHERE existing.action_plan_execution_id = e.id
                  AND existing.event_type = '{EXECUTION_LIFECYCLE_EVENT_MARKED_DONE}'
                  AND existing.occurred_at = e.marked_done_at
              )
            """,
            [],
        ),
        (
            f"""
            INSERT INTO {tables.execution_events} (
                id, created_at, updated_at, action_plan_execution_id,
                establishment_id, event_type, actor_membership_id,
                occurred_at, metadata_safe
            )
            SELECT
                gen_random_uuid(),
                now(),
                now(),
                e.id,
                e.establishment_id,
                '{EXECUTION_LIFECYCLE_EVENT_MARKED_DONE}',
                NULL,
                e.marked_done_at,
                jsonb_build_object(
                    'to_status', CASE
                        WHEN e.validated_at IS NOT NULL
                            THEN '{EXECUTION_STATUS_PENDING_VALIDATION}'
                        ELSE '{EXECUTION_STATUS_DONE}'
                    END,
                    'end_at', {end_at_exec}
                )
            FROM {tables.executions} e
            WHERE e.status = '{EXECUTION_STATUS_DONE}'
              AND e.marked_done_at IS NOT NULL
              AND NOT EXISTS (
                SELECT 1
                FROM {tables.execution_events} existing
                WHERE existing.action_plan_execution_id = e.id
                  AND existing.event_type = '{EXECUTION_LIFECYCLE_EVENT_MARKED_DONE}'
                  AND existing.occurred_at = e.marked_done_at
              )
            """,
            [],
        ),
        (
            f"""
            INSERT INTO {tables.execution_events} (
                id, created_at, updated_at, action_plan_execution_id,
                establishment_id, event_type, actor_membership_id,
                occurred_at, metadata_safe
            )
            SELECT
                gen_random_uuid(),
                now(),
                now(),
                e.id,
                e.establishment_id,
                '{EXECUTION_LIFECYCLE_EVENT_VALIDATED}',
                NULL,
                e.validated_at,
                jsonb_build_object(
                    'to_status', '{EXECUTION_STATUS_DONE}',
                    'end_at', {end_at_exec}
                )
            FROM {tables.executions} e
            WHERE e.status = '{EXECUTION_STATUS_DONE}'
              AND e.marked_done_at IS NOT NULL
              AND e.validated_at IS NOT NULL
              AND NOT EXISTS (
                SELECT 1
                FROM {tables.execution_events} existing
                WHERE existing.action_plan_execution_id = e.id
                  AND existing.event_type = '{EXECUTION_LIFECYCLE_EVENT_VALIDATED}'
                  AND existing.occurred_at = e.validated_at
              )
            """,
            [],
        ),
        (
            f"""
            INSERT INTO {tables.execution_events} (
                id, created_at, updated_at, action_plan_execution_id,
                establishment_id, event_type, actor_membership_id,
                occurred_at, metadata_safe
            )
            SELECT
                gen_random_uuid(),
                now(),
                now(),
                e.id,
                e.establishment_id,
                '{EXECUTION_LIFECYCLE_EVENT_CANCELED}',
                NULL,
                e.canceled_at,
                jsonb_build_object(
                    'to_status', '{EXECUTION_STATUS_CANCELED}',
                    'end_at', {end_at_exec}
                )
            FROM {tables.executions} e
            WHERE e.status = '{EXECUTION_STATUS_CANCELED}'
              AND e.canceled_at IS NOT NULL
              AND NOT EXISTS (
                SELECT 1
                FROM {tables.execution_events} existing
                WHERE existing.action_plan_execution_id = e.id
                  AND existing.event_type = '{EXECUTION_LIFECYCLE_EVENT_CANCELED}'
                  AND existing.occurred_at = e.canceled_at
              )
            """,
            [],
        ),
    ]
