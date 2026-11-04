"""Small project hierarchy; membership never grants access to its children."""

from django.db import transaction

from houston.establishments.models import Establishment
from houston.signals.exceptions import SignalStateError, SignalValidationError
from houston.signals.models import Signal
from houston.signals.record_selectors import get_record, record_stage

MAX_DEPTH = 3
MAX_PROJECT_RECORDS = 200


def lock_workspace(actor):
    # Serializes graph edits before acquiring record locks (same order in all commands).
    Establishment.objects.select_for_update().get(pk=actor.establishment_id)


def validate_hierarchy(actor, record, parent_id, *, is_project, is_milestone):
    from houston.signals.record_services import _require_manager

    if is_project and (is_milestone or record.record_kind != "project"):
        raise SignalValidationError(
            "Un projet est une fiche créée sans observation, distincte d’un jalon."
        )
    if not is_project and record.pk and record.project_records.exists():
        raise SignalValidationError("Détachez les fiches avant de retirer le format projet.")
    if not parent_id:
        return
    parent = get_record(actor, parent_id)
    if not parent or not parent.is_project or record_stage(parent) == "closed":
        raise SignalValidationError("Choisissez un projet ouvert de votre périmètre.")
    _require_manager(actor, parent)
    if (
        Signal.objects.filter(parent_project_id=parent.id).exclude(pk=record.pk).count()
        >= MAX_PROJECT_RECORDS
    ):
        raise SignalValidationError(
            "Ce projet contient déjà 200 fiches. Utilisez des sous-projets."
        )
    seen = {record.pk}
    depth = 1
    node = parent
    while node:
        if node.pk in seen:
            raise SignalValidationError("Un projet ne peut pas se contenir lui-même.")
        seen.add(node.pk)
        depth += 1
        if depth > MAX_DEPTH:
            raise SignalValidationError("Limitez l’organisation à trois niveaux.")
        node = (
            Signal.objects.filter(
                pk=node.parent_project_id, establishment=actor.establishment
            ).first()
            if node.parent_project_id
            else None
        )
    # Moving a populated project also accounts for its entire subtree.
    frontier = [record.pk]
    while frontier:
        children = list(
            Signal.objects.filter(
                parent_project_id__in=frontier, establishment=actor.establishment
            ).values_list("id", flat=True)[: MAX_PROJECT_RECORDS + 1]
        )
        if not children:
            break
        depth += 1
        if depth > MAX_DEPTH or len(children) > MAX_PROJECT_RECORDS:
            raise SignalValidationError("Ce déplacement dépasse les trois niveaux autorisés.")
        frontier = children


@transaction.atomic
def organize_record(
    *,
    actor,
    record_id,
    expected_updated_at,
    parent_project_id=None,
    is_project=False,
    is_milestone=False,
):
    from houston.signals.record_services import _event, _lock, _require_manager

    lock_workspace(actor)
    record = _lock(actor, record_id, expected_updated_at)
    _require_manager(actor, record)
    validate_hierarchy(
        actor, record, parent_project_id, is_project=is_project, is_milestone=is_milestone
    )
    if is_milestone and not record.due_on:
        raise SignalValidationError("Un jalon doit avoir une échéance.")
    if is_milestone and record.planned_start_on and record.planned_start_on != record.due_on:
        raise SignalValidationError("Le début planifié d’un jalon doit être sa date d’échéance.")
    before = str(record.parent_project_id) if record.parent_project_id else None
    record.parent_project_id = parent_project_id
    record.is_project = is_project
    record.is_milestone = is_milestone
    record.save(update_fields=["parent_project", "is_project", "is_milestone", "updated_at"])
    _event(
        record,
        actor,
        "project_changed",
        {
            "parent_project": {
                "before": before,
                "after": str(parent_project_id) if parent_project_id else None,
            },
            "is_project": is_project,
            "is_milestone": is_milestone,
        },
    )
    return record


def require_project_closeable(record):
    if (
        record.is_project
        and record.project_records.exclude(status__in=["resolved", "canceled"]).exists()
    ):
        raise SignalStateError(
            "Des fiches ou sous-projets restent ouverts. Vérifiez-les avant de clore le projet."
        )
