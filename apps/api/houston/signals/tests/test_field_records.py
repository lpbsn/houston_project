from datetime import time, timedelta
from uuid import uuid4

import pytest
from django.utils import timezone

from houston.action_plans.dependencies import set_dependency
from houston.action_plans.exceptions import ActionPlanValidationError
from houston.action_plans.services import (
    mark_execution_task_done,
    sync_signal_after_execution_change,
)
from houston.analytics.selectors import AnalyticsReadScope
from houston.brain.record_context import record_context, record_prefetches
from houston.signals.exceptions import (
    SignalPermissionError,
    SignalStateError,
    SignalValidationError,
)
from houston.signals.models import Signal, SignalExecutionLink, SignalSourceObservation
from houston.signals.record_intake import create_intake, finish_intake
from houston.signals.record_selectors import (
    calendar_dates,
    day_records,
    get_record,
    record_queryset,
)
from houston.signals.record_services import add_record_work, create_record, update_record
from houston.testing.auth import (
    assign_business_unit_scope,
    auth_headers,
    build_api_membership,
    build_api_membership_on_establishment,
    login,
)
from houston.testing.pipeline import create_observation
from houston.testing.taxonomy import create_minimal_v3_signal

pytestmark = pytest.mark.django_db


@pytest.fixture
def context():
    owner = build_api_membership(role="owner")
    signal = create_minimal_v3_signal(owner)
    staff = build_api_membership_on_establishment(owner, role="staff")
    assign_business_unit_scope(staff, signal.responsible_business_unit)
    return owner, staff, signal


def change(actor, signal, **data):
    signal.refresh_from_db()
    return update_record(
        actor=actor, record_id=signal.id, expected_updated_at=signal.updated_at, **data
    )


def work(owner, signal, tasks=None):
    signal.refresh_from_db()
    add_record_work(
        actor=owner,
        record_id=signal.id,
        expected_updated_at=signal.updated_at,
        title="Réorganiser le service",
        tasks=tasks or [],
        assignee_id=owner.id,
        quick=True,
    )
    return SignalExecutionLink.objects.get(signal=signal).execution


def test_owner_and_deadline_do_not_require_tasks(context):
    owner, staff, signal = context
    signal = change(
        owner, signal, owner_membership_id=staff.id, due_on=timezone.localdate() + timedelta(days=5)
    )
    assert signal.owner_membership_id == staff.id
    assert signal.work_links.count() == 0
    assert day_records(staff, record_queryset(staff)).filter(pk=signal.pk).exists()


def test_staff_can_progress_but_not_close_or_reassign(context):
    owner, staff, signal = context
    change(owner, signal, owner_membership_id=staff.id)
    signal = change(staff, signal, stage="doing", blocked_reason="Attente d’une livraison")
    assert signal.status == "in_progress"
    with pytest.raises(SignalPermissionError):
        change(staff, signal, stage="closed", closure_reason="resolved")
    with pytest.raises(SignalPermissionError):
        change(staff, signal, owner_membership_id=owner.id)


def test_foreign_or_inactive_member_cannot_own_record(context):
    owner, staff, signal = context
    other = build_api_membership(role="owner")
    with pytest.raises(SignalValidationError):
        change(owner, signal, owner_membership_id=other.id)
    staff.status = "invited"
    staff.save(update_fields=["status"])
    with pytest.raises(SignalValidationError):
        change(owner, signal, owner_membership_id=staff.id)
    assert get_record(other, signal.id) is None


def test_stale_edit_cannot_overwrite_a_new_decision(context):
    owner, _, signal = context
    old = signal.updated_at
    change(owner, signal, blocked_reason="Stock absent")
    with pytest.raises(SignalStateError):
        update_record(actor=owner, record_id=signal.id, expected_updated_at=old, blocked_reason="")
    signal.refresh_from_db()
    assert signal.blocked_reason == "Stock absent"


def test_information_can_close_without_execution_and_reopen_without_losing_evidence(context):
    owner, _, signal = context
    observation = create_observation(membership=owner)
    SignalSourceObservation.objects.create(
        signal=signal, observation=observation, link_type="created_from"
    )
    signal = change(owner, signal, stage="closed", closure_reason="acknowledged")
    assert signal.status == "canceled"
    signal = change(owner, signal, stage="doing")
    assert signal.canceled_at is None
    assert signal.source_observation_links.count() == 1
    assert list(
        signal.record_events.order_by("created_at", "id").values_list("kind", flat=True)
    ) == ["closed", "reopened"]


def test_open_work_prevents_false_resolution(context):
    owner, _, signal = context
    work(owner, signal)
    with pytest.raises(SignalStateError):
        change(owner, signal, stage="closed", closure_reason="resolved")


def test_closed_record_refuses_new_work_link(context):
    from houston.signals.record_services import link_execution

    owner, _, signal = context
    execution = work(owner, signal)
    other = create_record(
        actor=owner,
        title="Information prise en compte",
        business_unit_id=signal.responsible_business_unit_id,
    )
    other = change(owner, other, stage="closed", closure_reason="acknowledged")
    with pytest.raises(SignalStateError):
        link_execution(
            actor=owner,
            record_id=other.id,
            execution_id=execution.id,
            expected_updated_at=other.updated_at,
        )
    assert not other.work_links.exists()


def test_project_owner_loses_access_after_pole_scope_is_revoked(context):
    owner, staff, signal = context
    record = create_record(
        actor=owner,
        title="Projet réservé au pôle",
        business_unit_id=signal.responsible_business_unit_id,
        owner_membership_id=staff.id,
    )
    assert get_record(staff, record.id) is not None
    staff.scope_links.all().delete()
    staff.refresh_from_db()
    assert get_record(staff, record.id) is None


def test_finished_work_requests_verification_instead_of_resolving(context):
    owner, _, signal = context
    execution = work(owner, signal)
    execution.status = "done"
    execution.save(update_fields=["status"])
    sync_signal_after_execution_change(
        signal=signal, actor_membership=owner, triggering_execution=execution
    )
    signal.refresh_from_db()
    assert signal.status == "in_progress"
    assert signal.review_requested_at is not None
    assert signal.resolved_at is None
    assert signal.record_events.filter(kind="review_requested").count() == 1
    sync_signal_after_execution_change(signal=signal, actor_membership=owner)
    assert signal.record_events.filter(kind="review_requested").count() == 1


def test_one_shared_execution_blocks_all_its_records(context):
    owner, _, signal = context
    execution = work(owner, signal)
    other = create_record(
        actor=owner, title="Accueil", business_unit_id=signal.responsible_business_unit_id
    )
    SignalExecutionLink.objects.create(signal=other, execution=execution, added_by=owner)
    with pytest.raises(SignalStateError):
        change(owner, other, stage="closed", closure_reason="resolved")
    assert SignalExecutionLink.objects.filter(execution=execution).count() == 2


def test_calendar_uses_creation_deadline_and_actual_closure(context):
    owner, _, signal = context
    today = timezone.localdate()
    Signal.objects.filter(pk=signal.pk).update(created_at=timezone.now() - timedelta(days=10))
    signal = change(owner, signal, due_on=today - timedelta(days=2))
    dates = calendar_dates(signal, today=today)
    assert dates["start"] == today - timedelta(days=10)
    assert dates["end"] == today and dates["overdue"]
    signal = change(owner, signal, stage="closed", closure_reason="resolved")
    assert calendar_dates(signal)["end"] == today
    assert calendar_dates(signal)["due"] == today - timedelta(days=2)


def test_undated_records_never_enter_calendar(context):
    assert calendar_dates(context[2]) is None


def test_taskless_project_has_no_synthetic_observation(context):
    owner, _, source = context
    record = create_record(
        actor=owner,
        title="Préparer la rentrée",
        business_unit_id=source.responsible_business_unit_id,
    )
    assert get_record(owner, record.id)
    assert record.record_kind == "project"
    assert record.owner_membership_id == owner.id
    assert not record.source_observation_links.exists()
    from django.db.models import Q

    scope = AnalyticsReadScope(
        Q(establishment_id=owner.establishment_id), Q(establishment_id=owner.establishment_id)
    )
    assert not scope.readable_signals_queryset().filter(pk=record.id).exists()


def test_intake_is_stable_idempotent_and_never_exposes_raw_title(context):
    owner, _, _ = context
    observation = create_observation(membership=owner, text="Donnée privée précise à conserver")
    record = create_intake(observation)
    assert create_intake(observation).pk == record.pk
    assert observation.raw_text not in record.title
    finish_intake(observation)
    record.refresh_from_db()
    assert record.title == "Observation à prendre en compte"
    assert record.source_observation_links.count() == 1


def test_dependency_prevents_early_completion_and_cycles(context):
    owner, _, signal = context
    execution = work(owner, signal, ["Vérifier la cause", "Corriger"])
    first, second = list(execution.task_executions.order_by("position"))
    set_dependency(
        actor=owner, execution_id=execution.id, task_id=second.id, depends_on_id=first.id
    )
    with pytest.raises(ActionPlanValidationError):
        set_dependency(
            actor=owner, execution_id=execution.id, task_id=first.id, depends_on_id=second.id
        )
    with pytest.raises(ActionPlanValidationError):
        mark_execution_task_done(task_execution=second, actor=owner)
    mark_execution_task_done(task_execution=first, actor=owner)
    mark_execution_task_done(task_execution=second, actor=owner)
    second.refresh_from_db()
    assert second.status == "done"


def test_brain_snapshot_preserves_decisions_and_is_not_changed_by_later_updates(context):
    owner, _, signal = context
    change(owner, signal, blocked_reason="Vérification du stock")
    frozen_record = (
        Signal.objects.select_related("owner_membership__user")
        .prefetch_related(*record_prefetches(timezone.now()))
        .get(pk=signal.id)
    )
    frozen = record_context(frozen_record)
    change(owner, signal, blocked_reason="")
    assert frozen["blocked_reason"] == "Vérification du stock"
    assert frozen["coverage"]["events_complete"] is True


def test_record_api_enforces_site_and_expected_version(api_client, context):
    owner, _, signal = context
    token = login(api_client, user=owner.user)
    url = f"/api/v1/establishments/{owner.establishment_id}/records/{signal.id}/"
    response = api_client.get(url, **auth_headers(token))
    assert response.status_code == 200, response.content
    assert response.json()["stage"] == "todo"
    response = api_client.patch(url, {"stage": "doing"}, format="json", **auth_headers(token))
    assert response.status_code == 400
    assert (
        api_client.get(url.replace(str(signal.id), str(uuid4())), **auth_headers(token)).status_code
        == 404
    )


def test_pending_task_reorder_preserves_prerequisite_and_original_timestamp(context):
    from houston.action_plans.execution_update import update_action_plan_execution

    owner, _, signal = context
    execution = work(owner, signal, ["Diagnostiquer", "Corriger"])
    first, second = list(execution.task_executions.order_by("position"))
    original = first.created_at
    set_dependency(
        actor=owner, execution_id=execution.id, task_id=second.id, depends_on_id=first.id
    )
    execution.refresh_from_db()
    update_action_plan_execution(
        execution_id=execution.id,
        actor=owner,
        expected_updated_at=execution.updated_at,
        pending_tasks=[
            {
                "id": task.id,
                "task": task.task,
                "position": i,
                "business_unit_id": signal.responsible_business_unit_id,
                "assigned_membership_id": owner.id,
            }
            for i, task in enumerate([second, first], start=1)
        ],
    )
    first.refresh_from_db()
    second.refresh_from_db()
    assert first.created_at == original
    assert second.depends_on_id == first.id
    assert second.position == 1


def test_director_history_contains_prior_lifecycle_and_human_decisions(context):
    from houston.signals.lifecycle_events import record_signal_lifecycle_event
    from houston.signals.record_sections import history_page

    owner, _, signal = context
    record_signal_lifecycle_event(
        signal=signal,
        event_type="signal.created",
        occurred_at=signal.created_at,
        actor_membership=owner,
    )
    change(owner, signal, stage="closed", closure_reason="acknowledged")
    rows = history_page(signal, 0)["items"]
    assert {row["title"] for row in rows} == {"Observation reçue", "Fiche close"}
    assert any("Information prise en compte" in row["text"] for row in rows)


def test_repeated_notification_delivery_does_not_duplicate(context):
    from houston.notifications.models import Notification
    from houston.signals.record_notifications import deliver_record_event

    owner, staff, signal = context
    change(owner, signal, owner_membership_id=staff.id)
    event = signal.record_events.get(kind="assigned")
    deliver_record_event(event.id)
    deliver_record_event(event.id)
    assert (
        Notification.objects.filter(
            subject_id=signal.id, recipient_membership=staff, event_key="signal.record.updated"
        ).count()
        == 1
    )


def test_reminders_use_local_day_and_do_not_repeat(context):
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from houston.notifications.models import Notification
    from houston.signals.record_notifications import deliver_record_reminders

    owner, staff, signal = context
    tomorrow = timezone.now().astimezone(ZoneInfo(owner.establishment.timezone)).date() + timedelta(
        days=1
    )
    change(owner, signal, owner_membership_id=staff.id, due_on=tomorrow)
    before = datetime.combine(
        tomorrow - timedelta(days=1), time(8), tzinfo=ZoneInfo(owner.establishment.timezone)
    )
    deliver_record_reminders(now=before)
    assert not Notification.objects.filter(event_key="signal.record.due").exists()
    deliver_record_reminders(now=before + timedelta(hours=1))
    deliver_record_reminders(now=before + timedelta(hours=3))
    assert (
        Notification.objects.filter(
            subject_id=signal.id, recipient_membership=staff, event_key="signal.record.due"
        ).count()
        == 1
    )


def test_dependency_protects_predecessor_but_allows_whole_group_cleanup(context):
    from django.db.models.deletion import RestrictedError

    owner, _, signal = context
    execution = work(owner, signal, ["Diagnostiquer", "Corriger"])
    first, second = list(execution.task_executions.order_by("position"))
    set_dependency(
        actor=owner, execution_id=execution.id, task_id=second.id, depends_on_id=first.id
    )
    with pytest.raises(RestrictedError):
        first.delete()
    execution.task_executions.all().delete()
    assert not execution.task_executions.exists()


def test_merged_history_protects_survivor_but_allows_joint_cleanup(context):
    from django.db.models.deletion import RestrictedError

    owner, _, target = context
    source = create_record(
        actor=owner, title="Ancien épisode", business_unit_id=target.responsible_business_unit_id
    )
    source.merged_into = target
    source.save(update_fields=["merged_into"])
    with pytest.raises(RestrictedError):
        target.delete()
    ids = [source.id, target.id]
    Signal.objects.filter(id__in=ids).delete()
    assert not Signal.objects.filter(id__in=ids).exists()
