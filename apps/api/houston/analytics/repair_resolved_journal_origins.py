"""Bounded repair of allowlisted resolution_origin on existing resolved journal events."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from django.db import connection as default_connection
from django.db import transaction

from houston.signals.constants import (
    SIGNAL_LIFECYCLE_EVENT_RESOLVED,
    SIGNAL_RESOLUTION_ORIGIN_VALUES,
)
from houston.signals.models import Signal, SignalLifecycleEvent

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RepairResolvedJournalOriginsResult:
    dry_run: bool
    patched: int
    would_patch: int
    unrecoverable: int
    already_ok: int
    event_ids: tuple[UUID, ...]
    signal_ids: tuple[UUID, ...]


def repair_resolved_journal_origins(*, dry_run: bool = True) -> RepairResolvedJournalOriginsResult:
    """Copy the current allowlisted signal origin onto matching resolved journal rows.

    Dry-run by default. Writes only when ``dry_run`` is false. Idempotent: a second
    apply patches zero rows.
    """
    connection = default_connection
    if connection.vendor != "postgresql":
        raise RuntimeError("Resolved journal origin repair requires PostgreSQL.")
    events_table = connection.ops.quote_name(SignalLifecycleEvent._meta.db_table)
    signals_table = connection.ops.quote_name(Signal._meta.db_table)
    origin_in = ", ".join(f"'{value}'" for value in sorted(SIGNAL_RESOLUTION_ORIGIN_VALUES))
    patchable_where = f"""
        e.event_type = '{SIGNAL_LIFECYCLE_EVENT_RESOLVED}'
        AND s.id = e.signal_id
        AND s.resolved_at IS NOT NULL
        AND e.occurred_at = s.resolved_at
        AND s.resolution_origin IN ({origin_in})
        AND (
            e.metadata_safe->>'resolution_origin' IS NULL
            OR e.metadata_safe->>'resolution_origin' NOT IN ({origin_in})
        )
        AND NOT EXISTS (
            SELECT 1
            FROM {events_table} later
            WHERE later.signal_id = e.signal_id
              AND later.event_type = '{SIGNAL_LIFECYCLE_EVENT_RESOLVED}'
              AND later.occurred_at > e.occurred_at
        )
    """
    select_sql = f"""
        SELECT e.id, e.signal_id
        FROM {events_table} e
        INNER JOIN {signals_table} s ON s.id = e.signal_id
        WHERE {patchable_where}
        ORDER BY e.id
    """
    already_ok_sql = f"""
        SELECT COUNT(*)
        FROM {events_table} e
        WHERE e.event_type = '{SIGNAL_LIFECYCLE_EVENT_RESOLVED}'
          AND e.metadata_safe->>'resolution_origin' IN ({origin_in})
    """
    missing_origin_sql = f"""
        SELECT COUNT(*)
        FROM {events_table} e
        WHERE e.event_type = '{SIGNAL_LIFECYCLE_EVENT_RESOLVED}'
          AND (
            e.metadata_safe->>'resolution_origin' IS NULL
            OR e.metadata_safe->>'resolution_origin' NOT IN ({origin_in})
          )
    """
    update_sql = f"""
        UPDATE {events_table} e
        SET metadata_safe = e.metadata_safe
            || jsonb_build_object('resolution_origin', s.resolution_origin),
            updated_at = now()
        FROM {signals_table} s
        WHERE {patchable_where}
        RETURNING e.id, e.signal_id
    """

    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(select_sql)
            patchable_rows = cursor.fetchall()
            cursor.execute(already_ok_sql)
            already_ok = int(cursor.fetchone()[0])
            cursor.execute(missing_origin_sql)
            missing_origin = int(cursor.fetchone()[0])
            patched_rows = patchable_rows
            if not dry_run and patchable_rows:
                cursor.execute(update_sql)
                patched_rows = cursor.fetchall()
            elif not dry_run:
                patched_rows = []

    event_ids = tuple(row[0] for row in patchable_rows)
    signal_ids = tuple(row[1] for row in patchable_rows)
    patch_count = len(patchable_rows)
    unrecoverable = missing_origin - patch_count
    action = "would_patch" if dry_run else "patched"
    for event_id, signal_id in zip(event_ids, signal_ids, strict=True):
        logger.info(
            "repair_resolved_journal_origins %s event_id=%s signal_id=%s",
            action,
            event_id,
            signal_id,
        )
    if not dry_run and len(patched_rows) != patch_count:
        raise RuntimeError("Resolved journal origin repair updated an unexpected row set.")
    return RepairResolvedJournalOriginsResult(
        dry_run=dry_run,
        patched=0 if dry_run else patch_count,
        would_patch=patch_count if dry_run else 0,
        unrecoverable=unrecoverable,
        already_ok=already_ok,
        event_ids=event_ids,
        signal_ids=signal_ids,
    )
