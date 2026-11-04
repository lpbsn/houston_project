from houston.signals.exceptions import SignalStateError
from houston.signals.models import SignalAlias, SignalExecutionLink, SignalParticipant


def prepare_record_merge(source, target):
    if any(
        (
            source.is_project,
            target.is_project,
            source.parent_project_id,
            target.parent_project_id,
            source.planning_predecessor_id,
            target.planning_predecessor_id,
            source.planning_successors.exists(),
            target.planning_successors.exists(),
            source.planned_start_on,
            target.planned_start_on,
            source.is_milestone,
            target.is_milestone,
        )
    ):
        raise SignalStateError(
            "Ces fiches portent une organisation de projet ou une planification. "
            "Conservez leurs liens et traitez le rapprochement explicitement."
        )
    # A routing operation must never silently choose between two human decisions.
    fields = ("owner_membership_id", "due_on", "blocked_reason", "waiting_for_membership_id")
    for field in fields:
        left, right = getattr(source, field), getattr(target, field)
        if left and right and left != right:
            raise SignalStateError(
                "Les fiches ont des responsables, dates ou blocages différents. "
                "Harmonisez-les avant le rapprochement."
            )
        if left and not right:
            setattr(target, field, left)
    target.save(update_fields=[*fields, "updated_at"])
    SignalAlias.objects.update_or_create(
        former_signal_id=source.id,
        defaults={
            "target": target,
            "original_created_at": source.created_at,
        },
    )
    SignalAlias.objects.filter(target=source).update(target=target)
    for link in source.work_links.select_related("execution").iterator(chunk_size=100):
        SignalExecutionLink.objects.get_or_create(
            signal=target, execution=link.execution, defaults={"added_by": link.added_by}
        )
    for participant in source.participants.iterator(chunk_size=100):
        SignalParticipant.objects.get_or_create(
            signal=target,
            membership_id=participant.membership_id,
            defaults={"notifications_enabled": participant.notifications_enabled},
        )
    from houston.brain.models import BrainObjectiveRecord

    for link in source.objective_links.iterator(chunk_size=100):
        BrainObjectiveRecord.objects.get_or_create(signal=target, objective_id=link.objective_id)
