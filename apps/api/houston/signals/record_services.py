"""Field record commands. Deterministic writes own state; AI can only enrich evidence."""

from datetime import datetime, time
from zoneinfo import ZoneInfo

from django.db import IntegrityError, transaction
from django.utils import timezone

from houston.accounts.legal_services import require_current_terms
from houston.establishments.models import BusinessUnit, EstablishmentMembership
from houston.signals.constants import ACTIVE_SIGNAL_STATUSES
from houston.signals.exceptions import (
    SignalPermissionError,
    SignalStateError,
    SignalValidationError,
)
from houston.signals.models import (
    Signal,
    SignalExecutionLink,
    SignalParticipant,
    SignalRecordEvent,
)
from houston.signals.record_permissions import can_manage_record, can_progress_record
from houston.signals.record_selectors import get_record, linked_executions, record_stage


def _lock(actor, record_id, expected_updated_at=None):
    visible = get_record(actor, record_id)
    if visible is None:
        raise SignalPermissionError("Cette fiche n’est pas accessible.")
    signal = Signal.objects.select_for_update().get(pk=visible.id)
    if expected_updated_at is not None and signal.updated_at != expected_updated_at:
        raise SignalStateError(
            "La fiche a changé. Actualisez avant de recommencer.", code="stale_record"
        )
    require_current_terms(user=actor.user)
    return signal


def _require_manager(actor, signal):
    if not can_manage_record(actor, signal):
        raise SignalPermissionError("Vous ne pouvez pas modifier cette fiche.")


def _member(signal, membership_id):
    if membership_id is None:
        return None
    member = (
        EstablishmentMembership.objects.select_related("user")
        .filter(
            pk=membership_id,
            establishment_id=signal.establishment_id,
            status="active",
        )
        .first()
    )
    if member is None:
        raise SignalValidationError("Ce membre n’est pas actif dans cet établissement.")
    # Participants and ownership do not widen access to a pole, plan or private thread.
    from houston.signals.permissions import signal_pole_visible_to_membership

    if signal.record_kind == "project" and member.role == "manager":
        from houston.establishments.membership_scope import membership_scope_covers_business_unit

        if not signal.responsible_business_unit or not membership_scope_covers_business_unit(
            member, signal.responsible_business_unit
        ):
            raise SignalValidationError("Ce membre ne couvre pas le pôle de la fiche.")
    if not signal_pole_visible_to_membership(member, signal):
        raise SignalValidationError("Ce membre ne couvre pas le pôle de la fiche.")
    return member


def _event(signal, actor, kind, changes):
    event = SignalRecordEvent.objects.create(signal=signal, actor=actor, kind=kind, changes=changes)
    from houston.signals.services import _schedule_signal_invalidation

    _schedule_signal_invalidation(signal=signal, reason="signal.updated")
    if kind in {
        "assigned",
        "closed",
        "reopened",
        "review_requested",
        "linked",
        "taken_in_charge",
        "work_added",
    }:
        from houston.signals.record_notifications import schedule_record_event

        schedule_record_event(event.id)
    return event


@transaction.atomic
def create_record(*, actor, title, business_unit_id, owner_membership_id=None, due_on=None):
    require_current_terms(user=actor.user)
    unit = BusinessUnit.objects.filter(
        pk=business_unit_id,
        establishment_id=actor.establishment_id,
        active=True,
    ).first()
    if not unit:
        raise SignalValidationError("Choisissez un pôle actif.")
    signal = Signal(
        establishment=actor.establishment,
        responsible_business_unit=unit,
        affected_business_unit=unit,
        routing_status="unassigned",
        title=title.strip(),
        structured_summary="",
        record_kind=Signal.RecordKind.PROJECT,
        last_activity_at=timezone.now(),
        due_on=due_on,
    )
    _require_manager(actor, signal)
    if not signal.title or len(signal.title) > 200:
        raise SignalValidationError("Le titre doit contenir entre 1 et 200 caractères.")
    if due_on and due_on < timezone.now().astimezone(ZoneInfo(actor.establishment.timezone)).date():
        raise SignalValidationError("L’échéance ne peut pas précéder la création.")
    signal.owner_membership = _member(signal, owner_membership_id) if owner_membership_id else actor
    signal.save()
    _event(signal, actor, "created", {"record_kind": "project"})
    return signal


@transaction.atomic
def update_record(*, actor, record_id, expected_updated_at, **data):
    signal = _lock(actor, record_id, expected_updated_at)
    if not can_progress_record(actor, signal):
        raise SignalPermissionError("Vous ne pouvez pas modifier cette fiche.")
    if not can_manage_record(actor, signal) and set(data) - {"stage", "blocked_reason"}:
        raise SignalPermissionError("Seul le manager peut modifier ces éléments.")
    before = record_stage(signal)
    changes = {}
    kind = "updated"
    for field in ("title", "structured_summary", "due_on", "blocked_reason"):
        if field in data and data[field] != getattr(signal, field):
            old, new = getattr(signal, field), data[field]
            if (
                field == "due_on"
                and new
                and new
                < signal.created_at.astimezone(ZoneInfo(signal.establishment.timezone)).date()
            ):
                raise SignalValidationError("L’échéance ne peut pas précéder la création.")
            changes[field] = {
                "before": str(old) if old is not None else None,
                "after": str(new) if new is not None else None,
            }
            setattr(signal, field, new)
            if field == "due_on":
                signal.due_revision += 1
            if field in ("title", "structured_summary"):
                signal.content_edited_by_user = True
    for field in ("owner_membership_id", "waiting_for_membership_id"):
        if field in data and data[field] != getattr(signal, field):
            member = _member(signal, data[field])
            changes[field] = {
                "before": str(getattr(signal, field) or ""),
                "after": str(member.id) if member else None,
            }
            setattr(signal, field.removesuffix("_id"), member)
            if field == "owner_membership_id":
                kind = "assigned"
    stage = data.get("stage")
    if stage is not None and stage != before:
        if stage not in {"todo", "doing", "review", "closed"}:
            raise SignalValidationError("Étape inconnue.")
        if stage in {"todo", "closed"} or before == "closed":
            _require_manager(actor, signal)
        if stage == "closed":
            from houston.signals.permissions import get_pending_resolution_request_for_signal

            if get_pending_resolution_request_for_signal(signal):
                raise SignalStateError("Traitez d’abord la demande de résolution en attente.")
            reason = data.get("closure_reason")
            if reason not in Signal.ClosureReason.values:
                raise SignalValidationError("Indiquez pourquoi cette fiche est close.")
            if (
                linked_executions(signal)
                .filter(status__in=["in_progress", "scheduled", "pending_validation"])
                .exists()
            ):
                raise SignalStateError(
                    "Des actions restent ouvertes. Terminez-les ou annulez-les explicitement."
                )
            signal.closure_reason = reason
            signal.status = "resolved" if reason == "resolved" else "canceled"
            if reason == "resolved":
                signal.resolved_at, signal.resolved_by_membership = timezone.now(), actor
                signal.resolution_origin = "manual"
            else:
                signal.canceled_at, signal.canceled_by_membership = timezone.now(), actor
            signal.review_requested_at = None
            kind = "closed"
        else:
            if before == "closed":
                collision = (
                    Signal.objects.filter(
                        establishment_id=signal.establishment_id,
                        status__in=ACTIVE_SIGNAL_STATUSES,
                        routing_status="resolved",
                        affected_business_unit_id=signal.affected_business_unit_id,
                        responsible_business_unit_id=signal.responsible_business_unit_id,
                        activity_subject_id=signal.activity_subject_id,
                        operational_unit_id=signal.operational_unit_id,
                        issue_focus=signal.issue_focus,
                    )
                    .exclude(pk=signal.id)
                    .exists()
                )
                if signal.routing_status == "resolved" and collision:
                    raise SignalStateError(
                        "Un sujet équivalent est déjà actif. Poursuivez dans sa fiche "
                        "pour conserver les deux épisodes."
                    )
                signal.resolved_at = signal.canceled_at = None
                signal.resolved_by_membership = signal.canceled_by_membership = None
                signal.resolution_origin = None
                signal.closure_reason = ""
                kind = "reopened"
            elif stage == "review":
                kind = "review_requested"
            elif stage == "doing":
                kind = "taken_in_charge"
            signal.status = "open" if stage == "todo" else "in_progress"
            signal.review_requested_at = timezone.now() if stage == "review" else None
        changes["stage"] = {"before": before, "after": stage}
        changes["closure_reason"] = signal.closure_reason
        signal.is_pinned = False
        signal.pinned_at = signal.pinned_by_membership = None
        from houston.signals.lifecycle_events import record_signal_lifecycle_event

        event_name = {
            "todo": "signal.moved_open",
            "doing": "signal.moved_in_progress",
            "review": "signal.moved_in_progress",
            "closed": f"signal.{signal.status}",
        }[stage]
        if signal.record_kind == Signal.RecordKind.OBSERVATION:
            lifecycle_event = record_signal_lifecycle_event(
                signal=signal,
                event_type=event_name,
                actor_membership=actor,
                occurred_at=timezone.now(),
                metadata_safe={"to_status": signal.status, "origin": "record"},
            )
            from houston.gamification.services import award_signal_progress_points

            award_signal_progress_points(signal=signal, lifecycle_event=lifecycle_event)
    if changes:
        signal.last_activity_at = timezone.now()
        try:
            with transaction.atomic():
                signal.save()
        except IntegrityError as exc:
            from houston.signals.services import _is_active_aggregation_unique_violation

            if _is_active_aggregation_unique_violation(exc):
                raise SignalStateError(
                    "Un sujet équivalent est déjà actif. Actualisez et poursuivez dans cette fiche."
                ) from exc
            raise
        _event(signal, actor, kind, changes)
    return signal


@transaction.atomic
def set_participants(*, actor, record_id, expected_updated_at, membership_ids):
    signal = _lock(actor, record_id, expected_updated_at)
    _require_manager(actor, signal)
    if len(set(membership_ids)) > 50:
        raise SignalValidationError("Maximum 50 participants par fiche.")
    members = [_member(signal, pk) for pk in set(membership_ids)]
    SignalParticipant.objects.filter(signal=signal).exclude(
        membership_id__in=membership_ids
    ).delete()
    for member in members:
        SignalParticipant.objects.get_or_create(signal=signal, membership=member)
    signal.save(update_fields=["updated_at"])
    _event(signal, actor, "participants_changed", {"membership_ids": [str(m.id) for m in members]})
    return signal


@transaction.atomic
def link_execution(*, actor, record_id, execution_id, expected_updated_at):
    from houston.action_plans.models import ActionPlanExecution
    from houston.action_plans.permissions import can_update_action_plan_execution_content

    signal = _lock(actor, record_id, expected_updated_at)
    _require_manager(actor, signal)
    if record_stage(signal) == "closed":
        raise SignalStateError("Rouvrez la fiche avant d’y rattacher du travail.")
    execution = (
        ActionPlanExecution.objects.select_for_update()
        .filter(
            pk=execution_id,
            establishment_id=actor.establishment_id,
        )
        .first()
    )
    if execution is None or not can_update_action_plan_execution_content(actor, execution):
        raise SignalPermissionError("Ce plan n’est pas modifiable dans votre périmètre.")
    link, created = SignalExecutionLink.objects.get_or_create(
        signal=signal,
        execution=execution,
        defaults={"added_by": actor},
    )
    if created:
        signal.save(update_fields=["updated_at"])
        _event(signal, actor, "linked", {"execution_id": str(execution.id)})
    return signal


@transaction.atomic
def add_record_work(
    *, actor, record_id, expected_updated_at, title, tasks, assignee_id, due_on=None, quick=False
):
    from houston.action_plans.services import create_action_plan_with_execution

    signal = _lock(actor, record_id, expected_updated_at)
    _require_manager(actor, signal)
    if record_stage(signal) == "closed":
        raise SignalStateError("Rouvrez la fiche avant d’y ajouter du travail.")
    member = _member(signal, assignee_id or signal.owner_membership_id)
    if member is None:
        raise SignalValidationError("Choisissez la personne qui réalisera ce travail.")
    unit_id = signal.responsible_business_unit_id or signal.affected_business_unit_id
    if unit_id is None:
        raise SignalValidationError("Attribuez d’abord un pôle à la fiche.")
    zone = ZoneInfo(signal.establishment.timezone)
    deadline = datetime.combine(due_on, time.max, tzinfo=zone) if due_on else None
    quick_link = (
        SignalExecutionLink.objects.select_related("execution")
        .filter(
            signal=signal,
            is_quick_tasks=True,
        )
        .first()
        if quick
        else None
    )
    if quick_link and quick_link.execution.status == "in_progress":
        from houston.action_plans.execution_update import update_action_plan_execution

        execution = quick_link.execution
        current_tasks = list(execution.task_executions.select_related("execution_team").all())
        pending = [
            {
                "id": t.id,
                "task": t.task,
                "description": t.description,
                "business_unit_id": t.execution_team.business_unit_id,
                "assigned_membership_id": t.assigned_membership_id,
                "deadline_at": t.deadline_at,
                "position": t.position,
            }
            for t in current_tasks
            if t.status == "pending"
        ]
        position = max((t.position for t in current_tasks), default=0)
        pending.extend(
            {
                "task": task,
                "position": position + i + 1,
                "business_unit_id": unit_id,
                "assigned_membership_id": member.id,
                "deadline_at": deadline,
            }
            for i, task in enumerate(tasks)
        )
        assignees = [
            {
                "membership_id": a.membership_id,
                "business_unit_id": a.execution_team.business_unit_id,
            }
            for a in execution.assignees.select_related("execution_team")
        ]
        if member.id not in {a["membership_id"] for a in assignees}:
            assignees.append({"membership_id": member.id, "business_unit_id": unit_id})
        update_action_plan_execution(
            execution_id=execution.id,
            actor=actor,
            expected_updated_at=execution.updated_at,
            pending_tasks=pending,
            assignees=assignees,
        )
    else:
        if quick_link:
            quick_link.is_quick_tasks = False
            quick_link.save(update_fields=["is_quick_tasks", "updated_at"])
        _, execution = create_action_plan_with_execution(
            establishment_id=signal.establishment_id,
            created_by=actor,
            pilot_business_unit_id=unit_id,
            title=title or signal.title,
            tasks=[
                {
                    "task": task,
                    "position": i + 1,
                    "business_unit_id": unit_id,
                    "assigned_membership_id": member.id,
                    "deadline_at": deadline,
                }
                for i, task in enumerate(tasks)
            ],
            assignees=[{"membership_id": member.id, "business_unit_id": unit_id}],
            source_signal_id=signal.id,
            use_shared_chronology=True,
            requires_validation=True,
            end_at=deadline,
        )
        SignalExecutionLink.objects.update_or_create(
            signal=signal,
            execution=execution,
            defaults={"added_by": actor, "is_quick_tasks": quick},
        )
    signal.refresh_from_db()
    signal.review_requested_at = None
    fields = ["review_requested_at", "updated_at"]
    if signal.due_on is None and due_on is not None:
        signal.due_on = due_on
        signal.due_revision += 1
        fields.extend(["due_on", "due_revision"])
    signal.save(update_fields=fields)
    _event(signal, actor, "work_added", {"execution_id": str(execution.id)})
    return signal


@transaction.atomic
def run_record_command(*, actor, record_id, expected_updated_at, command, **data):
    signal = _lock(actor, record_id, expected_updated_at)
    common = {"actor": actor, "record_id": signal.id, "expected_updated_at": expected_updated_at}
    required = {
        "participants": ["membership_ids"],
        "link_work": ["execution_id"],
        "dependency": ["execution_id", "task_id", "depends_on_id"],
        "follow": ["enabled"],
        "link_objective": ["objective_id"],
        "work": [],
    }
    if command not in required or any(key not in data for key in required[command]):
        raise SignalValidationError("La demande est incomplète.")
    if command == "participants":
        return set_participants(**common, membership_ids=data["membership_ids"])
    if command == "link_work":
        return link_execution(**common, execution_id=data["execution_id"])
    if command == "work":
        return add_record_work(
            **common,
            title=data.get("title", ""),
            tasks=data.get("tasks", []),
            assignee_id=data.get("assignee_id"),
            due_on=data.get("due_on"),
            quick=data.get("quick", False),
        )
    if command == "dependency":
        _require_manager(actor, signal)
        if not linked_executions(signal).filter(pk=data["execution_id"]).exists():
            raise SignalPermissionError("Ce travail n’appartient pas à cette fiche.")
        from houston.action_plans.dependencies import set_dependency

        set_dependency(
            actor=actor,
            execution_id=data["execution_id"],
            task_id=data["task_id"],
            depends_on_id=data["depends_on_id"],
        )
        signal.save(update_fields=["updated_at"])
        _event(
            signal,
            actor,
            "dependency_changed",
            {"task_id": str(data["task_id"]), "depends_on_id": str(data["depends_on_id"] or "")},
        )
    elif command == "follow":
        SignalParticipant.objects.update_or_create(
            signal=signal, membership=actor, defaults={"notifications_enabled": data["enabled"]}
        )
    elif command == "link_objective":
        _require_manager(actor, signal)
        if actor.role not in ("owner", "director"):
            raise SignalPermissionError("Le suivi KPI est réservé à la direction.")
        from houston.brain.models import BrainObjective, BrainObjectiveRecord

        objective = BrainObjective.objects.filter(
            pk=data["objective_id"], establishment=actor.establishment
        ).first()
        if objective is None:
            raise SignalValidationError("Objectif introuvable dans cet établissement.")
        BrainObjectiveRecord.objects.get_or_create(objective=objective, signal=signal)
        signal.save(update_fields=["updated_at"])
        _event(signal, actor, "objective_linked", {"objective_id": str(objective.id)})
    return signal
