"""Stable entry point before AI classification. Never expose raw text as a public title."""

from zoneinfo import ZoneInfo

from django.db import transaction

from houston.signals.models import Signal, SignalAlias, SignalSourceObservation


def create_intake(observation):
    record, created = Signal.objects.get_or_create(
        intake_observation=observation,
        defaults={
            "establishment_id": observation.establishment_id,
            "record_kind": Signal.RecordKind.INTAKE,
            "routing_status": Signal.RoutingStatus.UNASSIGNED,
            "title": "Observation en préparation",
            "structured_summary": "",
            "last_activity_at": observation.submitted_at,
        },
    )
    if created:
        SignalSourceObservation.objects.create(
            signal=record,
            observation=observation,
            link_type="created_from",
        )
    return record


def adopt_intake(observation, values):
    record = (
        Signal.objects.select_for_update()
        .filter(
            intake_observation=observation,
            record_kind=Signal.RecordKind.INTAKE,
        )
        .first()
    )
    if record is None:
        return Signal.objects.create(**values)
    for field, value in values.items():
        if field in {"status", "last_activity_at"}:
            continue
        if field in {"title", "structured_summary"} and record.content_edited_by_user:
            continue
        setattr(record, field, value)
    record.record_kind = Signal.RecordKind.OBSERVATION
    record.save()
    return record


@transaction.atomic
def finish_intake(observation):
    record = (
        Signal.objects.select_for_update()
        .filter(
            intake_observation=observation,
            record_kind=Signal.RecordKind.INTAKE,
        )
        .first()
    )
    if record is None:
        return
    targets = (
        Signal.objects.filter(
            establishment_id=observation.establishment_id,
            source_observation_links__observation=observation,
            record_kind=Signal.RecordKind.OBSERVATION,
        )
        .distinct()
        .order_by("created_at", "id")
    )
    target = targets.first()
    # Only an untouched placeholder may disappear automatically. Human decisions win.
    untouched = (
        not record.content_edited_by_user
        and record.owner_membership_id is None
        and record.due_on is None
        and record.status == "open"
        and not record.record_events.exists()
        and not record.comments.exists()
    )
    if target and untouched:
        SignalAlias.objects.create(
            former_signal_id=record.id, target=target, original_created_at=record.created_at
        )
        record.delete()
    elif target is None:
        # An informational observation is still actionable even if AI finds no candidate.
        record.title = "Observation à prendre en compte"
        record.save(update_fields=["title", "updated_at"])


def attach_execution(execution):
    """No synthetic observation is created for a project or a recurring execution."""
    from houston.signals.models import SignalExecutionLink

    if execution.source_signal_id:
        record_id = execution.source_signal_id
    else:
        record = Signal.objects.create(
            establishment_id=execution.establishment_id,
            record_kind=Signal.RecordKind.PROJECT,
            title=execution.title,
            structured_summary=execution.description,
            routing_status=Signal.RoutingStatus.UNASSIGNED,
            responsible_business_unit_id=execution.pilot_business_unit_id,
            affected_business_unit_id=execution.pilot_business_unit_id,
            status="in_progress",
            owner_membership_id=execution.chronology_owner_membership_id or execution.created_by_id,
            due_on=execution.end_at.astimezone(ZoneInfo(execution.establishment.timezone)).date()
            if execution.end_at
            else None,
            last_activity_at=execution.last_activity_at,
        )
        record_id = record.id
    SignalExecutionLink.objects.get_or_create(
        signal_id=record_id,
        execution=execution,
        defaults={"added_by": execution.created_by},
    )
