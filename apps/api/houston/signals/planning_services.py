"""Date-only planning. Preview then atomic confirmation; no implicit task/status edits."""

from datetime import timedelta
from zoneinfo import ZoneInfo

from django.db import transaction
from django.utils import timezone

from houston.signals.exceptions import (
    SignalPermissionError,
    SignalStateError,
    SignalValidationError,
)
from houston.signals.models import Signal
from houston.signals.project_services import lock_workspace
from houston.signals.record_selectors import get_record, record_queryset, record_stage

MAX_CHAIN = 200


def planned_start(record):
    return record.planned_start_on or (
        record.due_on
        if record.is_milestone
        else record.created_at.astimezone(ZoneInfo(record.establishment.timezone)).date()
    )


def validate_dates(record, start, due):
    created = record.created_at.astimezone(ZoneInfo(record.establishment.timezone)).date()
    if start is None or due is None or not created <= start <= due:
        raise SignalValidationError(
            "Le début planifié doit suivre la création et précéder l’échéance."
        )
    if record.is_milestone and start != due:
        raise SignalValidationError("Un jalon se déroule sur une seule date.")
    if record.planning_predecessor_id:
        previous = Signal.objects.filter(
            pk=record.planning_predecessor_id, establishment=record.establishment
        ).first()
        if previous is None or previous.due_on is None or start <= previous.due_on:
            raise SignalValidationError("Le début doit suivre l’échéance de la fiche préalable.")


def require_date_edit(record, data):
    """Ordinary edits cannot bypass the planning preview or dependency invariant."""
    date_changed = any(
        k in data and data[k] != getattr(record, k) for k in ("due_on", "planned_start_on")
    )
    if not date_changed:
        return
    if record_stage(record) == "closed":
        raise SignalValidationError("Rouvrez la fiche avant de modifier sa planification.")
    due = data.get("due_on", record.due_on)
    start = data.get("planned_start_on", record.planned_start_on)
    if record.planning_successors.exists():
        raise SignalValidationError(
            "Utilisez Planifier pour vérifier l’impact sur les fiches suivantes."
        )
    if record.is_milestone and not due:
        raise SignalValidationError("Un jalon conserve une échéance.")
    if start or record.planning_predecessor_id:
        effective_start = start or (
            due
            if record.is_milestone
            else record.created_at.astimezone(ZoneInfo(record.establishment.timezone)).date()
        )
        validate_dates(record, effective_start, due)


@transaction.atomic
def set_record_predecessor(*, actor, record_id, expected_updated_at, predecessor_id):
    from houston.signals.record_services import _event, _lock, _require_manager

    lock_workspace(actor)
    record = _lock(actor, record_id, expected_updated_at)
    _require_manager(actor, record)
    if record_stage(record) == "closed":
        raise SignalStateError("Rouvrez la fiche avant de modifier ses dépendances.")
    if predecessor_id:
        predecessor = get_record(actor, predecessor_id)
        if not predecessor:
            raise SignalPermissionError("La fiche préalable n’est pas accessible.")
        _require_manager(actor, predecessor)
        if not record.due_on or not predecessor.due_on:
            raise SignalValidationError("Les deux fiches doivent avoir une échéance.")
        seen = {record.id}
        node = predecessor
        for _ in range(MAX_CHAIN):
            if node.id in seen:
                raise SignalValidationError("Cette dépendance créerait une boucle.")
            seen.add(node.id)
            if not node.planning_predecessor_id:
                break
            node = Signal.objects.get(
                pk=node.planning_predecessor_id, establishment=actor.establishment
            )
        else:
            raise SignalValidationError("La chaîne dépasse 200 fiches. Divisez la planification.")
        if planned_start(record) <= predecessor.due_on:
            raise SignalValidationError(
                "Planifiez d’abord cette fiche après l’échéance du préalable."
            )
    before = record.planning_predecessor_id
    record.planning_predecessor_id = predecessor_id
    record.save(update_fields=["planning_predecessor", "updated_at"])
    _event(
        record,
        actor,
        "planning_dependency_changed",
        {
            "before": str(before) if before else None,
            "after": str(predecessor_id) if predecessor_id else None,
        },
    )
    return record


def _descendants(root):
    """Bounded breadth-first graph, including unchanged descendants in the version guard."""
    records = {root.id: root}
    frontier = [root.id]
    while frontier:
        children = list(
            Signal.objects.filter(
                establishment_id=root.establishment_id, planning_predecessor_id__in=frontier
            )
            .select_related("establishment")
            .order_by("id")[: MAX_CHAIN + 1]
        )
        frontier = []
        for row in children:
            if row.id in records:
                raise SignalStateError(
                    "La planification contient une boucle. Corrigez les dépendances."
                )
            records[row.id] = row
            frontier.append(row.id)
        if len(records) > MAX_CHAIN:
            raise SignalValidationError(
                "Cette opération dépasse 200 fiches. Divisez la planification."
            )
    return records


@transaction.atomic
def schedule_record(
    *, actor, record_id, expected_updated_at, start_on, due_on, apply=False, expected_versions=None
):
    from houston.signals.record_services import _event, _lock, _require_manager

    lock_workspace(actor)
    root = _lock(actor, record_id, expected_updated_at)
    _require_manager(actor, root)
    if record_stage(root) == "closed":
        raise SignalStateError("Rouvrez la fiche avant de modifier sa planification.")
    validate_dates(root, start_on, due_on)
    records = _descendants(root)
    # Lock the snapshot before computing or persisting; external lifecycle edits also conflict.
    locked = {
        r.id: r
        for r in Signal.objects.select_for_update()
        .filter(pk__in=records)
        .select_related("establishment")
        .order_by("id")
    }
    records = {pk: locked[pk] for pk in records}
    if records[root.id].updated_at != expected_updated_at:
        raise SignalStateError("La fiche a changé. Actualisez la proposition.", code="stale_record")
    visible = set(record_queryset(actor).filter(pk__in=records).values_list("id", flat=True))
    if len(visible) != len(records):
        raise SignalPermissionError(
            "Cette planification concerne des fiches hors de votre périmètre. "
            "Demandez à la direction de la modifier."
        )
    versions = [{"id": r.id, "updated_at": r.updated_at} for r in records.values()]
    if apply:
        expected = {v["id"]: v["updated_at"] for v in (expected_versions or [])}
        if expected != {r.id: r.updated_at for r in records.values()}:
            raise SignalStateError(
                "La planification a changé. Relisez l’impact avant de confirmer.",
                code="stale_record",
            )
    proposed = {root.id: (start_on, due_on)}
    changes = []
    for row in records.values():
        _require_manager(actor, row)
        before_start = planned_start(row)
        if row.id != root.id:
            previous_end = proposed[row.planning_predecessor_id][1]
            if not row.due_on:
                raise SignalStateError(
                    "Une fiche liée n’a plus d’échéance. Corrigez sa planification."
                )
            delta = max(0, (previous_end + timedelta(days=1) - before_start).days)
            proposed[row.id] = (
                before_start + timedelta(days=delta),
                row.due_on + timedelta(days=delta),
            )
        new_start, new_due = proposed[row.id]
        changed = (
            new_start != before_start
            or new_due != row.due_on
            or (row.id == root.id and row.planned_start_on is None)
        )
        if not changed:
            continue
        if record_stage(row) == "closed":
            raise SignalStateError(
                "Le décalage toucherait une fiche close. "
                "Détachez ou revoyez cette dépendance avant de continuer."
            )
        changes.append(
            {
                "id": row.id,
                "title": row.title,
                "before_start": before_start,
                "before_due": row.due_on,
                "start_on": new_start,
                "due_on": new_due,
            }
        )
        if apply:
            old_due = row.due_on
            row.planned_start_on, row.due_on = new_start, new_due
            if old_due != new_due:
                row.due_revision += 1
            row.last_activity_at = timezone.now()
            row.save(
                update_fields=[
                    "planned_start_on",
                    "due_on",
                    "due_revision",
                    "last_activity_at",
                    "updated_at",
                ]
            )
            _event(
                row,
                actor,
                "planning_changed",
                {
                    "planned_start_on": {"before": str(before_start), "after": str(new_start)},
                    "due_on": {"before": str(old_due) if old_due else None, "after": str(new_due)},
                },
            )
    return {"changes": changes, "versions": versions, "applied": apply}
