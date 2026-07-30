from __future__ import annotations

from datetime import time as dt_time
from unittest.mock import patch

import pytest
from django.utils import timezone

from houston.action_plans.constants import (
    EXECUTION_LIFECYCLE_EVENT_MARKED_DONE,
    EXECUTION_STATUS_DONE,
    EXECUTION_STATUS_IN_PROGRESS,
)
from houston.action_plans.models import (
    ActionPlan,
    ActionPlanAssignee,
    ActionPlanExecution,
    ActionPlanExecutionLifecycleEvent,
    ActionPlanExecutionTask,
    ActionPlanExecutionTeam,
    ActionPlanSchedule,
)
from houston.action_plans.services import mark_action_plan_execution_done
from houston.comments.models import Comment, CommentMention
from houston.establishments.models import EstablishmentMembership
from houston.gamification.constants import (
    DELTA_RECURRING_EXECUTION_DONE,
    REASON_RECURRING_EXECUTION_DONE,
    SOURCE_TYPE_ACTION_PLAN_EXECUTION,
)
from houston.gamification.exceptions import GamificationValidationError
from houston.gamification.models import PointTransaction
from houston.gamification.services import award_recurring_execution_done_points
from houston.testing.factories import create_establishment, create_membership
from houston.testing.taxonomy import create_business_unit

pytestmark = pytest.mark.django_db


def _setup():
    establishment = create_establishment(name="GAM-05 Hotel", timezone="UTC")
    business_unit = create_business_unit(establishment=establishment, key="restaurant")
    owner = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    participant = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    return establishment, business_unit, owner, participant


def _create_plan_and_schedule(
    *,
    creator,
    business_unit,
    requires_validation=False,
):
    today = timezone.now().date()
    plan = ActionPlan.objects.create(
        establishment=creator.establishment,
        created_by=creator,
        pilot_business_unit=business_unit,
        title="Recurring plan",
        description="Recurring plan",
        requires_validation=requires_validation,
    )
    schedule = ActionPlanSchedule.objects.create(
        action_plan=plan,
        establishment=creator.establishment,
        created_by=creator,
        use_shared_chronology=True,
        start_date=today,
        end_date=today + timezone.timedelta(days=7),
        start_at=dt_time(8, 0),
        end_at=dt_time(9, 0),
        recurrence_days=["monday", "tuesday", "wednesday", "thursday", "friday"],
        status=ActionPlanSchedule.Status.ACTIVE,
    )
    return plan, schedule


def _create_execution(
    *,
    creator,
    business_unit,
    plan=None,
    schedule=None,
    requires_validation=False,
    occurrence_date=None,
    direct_assignee=None,
    task_assignee=None,
):
    now = timezone.now()
    if plan is None:
        plan = ActionPlan.objects.create(
            establishment=creator.establishment,
            created_by=creator,
            pilot_business_unit=business_unit,
            title="One-shot plan",
            description="One-shot plan",
            requires_validation=requires_validation,
        )
    execution = ActionPlanExecution.objects.create(
        action_plan=plan,
        action_plan_schedule=schedule,
        establishment=creator.establishment,
        created_by=creator,
        title=plan.title,
        description=plan.description,
        pilot_business_unit=business_unit,
        requires_validation=requires_validation,
        use_shared_chronology=True,
        status=EXECUTION_STATUS_IN_PROGRESS,
        occurrence_date=occurrence_date or now.date(),
        start_at=now - timezone.timedelta(minutes=15),
        end_at=now + timezone.timedelta(minutes=45),
        last_activity_at=now,
    )
    team = ActionPlanExecutionTeam.objects.create(
        action_plan_execution=execution,
        business_unit=business_unit,
        is_pilot=True,
    )
    if direct_assignee is not None:
        ActionPlanAssignee.objects.create(
            action_plan_execution=execution,
            execution_team=team,
            membership=direct_assignee,
        )
    if task_assignee is not None:
        ActionPlanExecutionTask.objects.create(
            action_plan_execution=execution,
            execution_team=team,
            task="Do it",
            position=1,
            assigned_membership=task_assignee,
        )
    return execution


def _create_execution_comment_mention(*, execution, author, mentioned):
    comment = Comment.objects.create(
        establishment=execution.establishment,
        action_plan_execution=execution,
        author_membership=author,
        body="Mention",
    )
    CommentMention.objects.create(
        comment=comment,
        mentioned_membership=mentioned,
    )
    return comment


def _marked_done_event(execution):
    return ActionPlanExecutionLifecycleEvent.objects.get(
        action_plan_execution=execution,
        event_type=EXECUTION_LIFECYCLE_EVENT_MARKED_DONE,
    )


def _gam05_txs(*, membership=None, execution=None):
    qs = PointTransaction.objects.filter(
        reason_code=REASON_RECURRING_EXECUTION_DONE,
        source_type=SOURCE_TYPE_ACTION_PLAN_EXECUTION,
    )
    if membership is not None:
        qs = qs.filter(membership=membership)
    if execution is not None:
        qs = qs.filter(source_id=str(execution.id))
    return list(qs.order_by("created_at", "id"))


def test_recurring_without_validation_direct_assignee_awards():
    _establishment, business_unit, owner, participant = _setup()
    plan, schedule = _create_plan_and_schedule(
        creator=owner,
        business_unit=business_unit,
    )
    execution = _create_execution(
        creator=owner,
        business_unit=business_unit,
        plan=plan,
        schedule=schedule,
        direct_assignee=participant,
    )

    mark_action_plan_execution_done(
        execution_id=execution.id,
        actor_membership=owner,
    )

    event = _marked_done_event(execution)
    txs = _gam05_txs(membership=participant, execution=execution)
    assert len(txs) == 1
    assert txs[0].delta == DELTA_RECURRING_EXECUTION_DONE
    assert txs[0].source_event_id == str(event.id)
    assert txs[0].occurred_at == event.occurred_at


def test_direct_task_and_mention_dedupe_to_one_award():
    _establishment, business_unit, owner, participant = _setup()
    plan, schedule = _create_plan_and_schedule(
        creator=owner,
        business_unit=business_unit,
    )
    execution = _create_execution(
        creator=owner,
        business_unit=business_unit,
        plan=plan,
        schedule=schedule,
        direct_assignee=participant,
        task_assignee=participant,
    )
    _create_execution_comment_mention(
        execution=execution,
        author=owner,
        mentioned=participant,
    )

    mark_action_plan_execution_done(
        execution_id=execution.id,
        actor_membership=owner,
    )

    txs = _gam05_txs(membership=participant, execution=execution)
    assert len(txs) == 1
    assert txs[0].delta == DELTA_RECURRING_EXECUTION_DONE


def test_mention_created_after_marked_done_occurred_at_is_excluded():
    _establishment, business_unit, owner, participant = _setup()
    plan, schedule = _create_plan_and_schedule(
        creator=owner,
        business_unit=business_unit,
    )
    execution = _create_execution(
        creator=owner,
        business_unit=business_unit,
        plan=plan,
        schedule=schedule,
    )
    mark_action_plan_execution_done(
        execution_id=execution.id,
        actor_membership=owner,
    )
    event = _marked_done_event(execution)
    comment = _create_execution_comment_mention(
        execution=execution,
        author=owner,
        mentioned=participant,
    )
    Comment.objects.filter(pk=comment.pk).update(
        created_at=event.occurred_at + timezone.timedelta(seconds=1),
    )

    execution.refresh_from_db()
    award_recurring_execution_done_points(execution=execution)

    assert _gam05_txs(membership=participant, execution=execution) == []


def test_two_occurrences_of_same_schedule_award_separately():
    _establishment, business_unit, owner, participant = _setup()
    plan, schedule = _create_plan_and_schedule(
        creator=owner,
        business_unit=business_unit,
    )
    first = _create_execution(
        creator=owner,
        business_unit=business_unit,
        plan=plan,
        schedule=schedule,
        occurrence_date=schedule.start_date,
        direct_assignee=participant,
    )
    second = _create_execution(
        creator=owner,
        business_unit=business_unit,
        plan=plan,
        schedule=schedule,
        occurrence_date=schedule.start_date + timezone.timedelta(days=1),
        direct_assignee=participant,
    )

    mark_action_plan_execution_done(execution_id=first.id, actor_membership=owner)
    mark_action_plan_execution_done(execution_id=second.id, actor_membership=owner)

    txs = _gam05_txs(membership=participant)
    assert len(txs) == 2
    assert {tx.source_id for tx in txs} == {str(first.id), str(second.id)}


def test_action_plan_creator_only_participant_awards_zero():
    _establishment, business_unit, owner, _participant = _setup()
    plan, schedule = _create_plan_and_schedule(
        creator=owner,
        business_unit=business_unit,
    )
    execution = _create_execution(
        creator=owner,
        business_unit=business_unit,
        plan=plan,
        schedule=schedule,
        direct_assignee=owner,
    )

    mark_action_plan_execution_done(
        execution_id=execution.id,
        actor_membership=owner,
    )

    assert _gam05_txs(execution=execution) == []


def test_execution_creator_actor_can_receive_when_not_action_plan_creator():
    _establishment, business_unit, alice, _participant = _setup()
    bob = create_membership(
        establishment=alice.establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    plan, schedule = _create_plan_and_schedule(
        creator=alice,
        business_unit=business_unit,
    )
    execution = _create_execution(
        creator=bob,
        business_unit=business_unit,
        plan=plan,
        schedule=schedule,
        direct_assignee=bob,
    )

    mark_action_plan_execution_done(
        execution_id=execution.id,
        actor_membership=bob,
    )

    assert _gam05_txs(membership=alice, execution=execution) == []
    txs = _gam05_txs(membership=bob, execution=execution)
    assert len(txs) == 1
    assert txs[0].delta == DELTA_RECURRING_EXECUTION_DONE


def test_recurring_with_validation_awards_zero():
    _establishment, business_unit, owner, participant = _setup()
    plan, schedule = _create_plan_and_schedule(
        creator=owner,
        business_unit=business_unit,
        requires_validation=True,
    )
    execution = _create_execution(
        creator=owner,
        business_unit=business_unit,
        plan=plan,
        schedule=schedule,
        requires_validation=True,
        direct_assignee=participant,
    )

    marked = mark_action_plan_execution_done(
        execution_id=execution.id,
        actor_membership=owner,
    )

    assert marked.status == ActionPlanExecution.Status.PENDING_VALIDATION
    assert _gam05_txs(execution=execution) == []


def test_non_recurring_without_validation_awards_zero():
    _establishment, business_unit, owner, participant = _setup()
    execution = _create_execution(
        creator=owner,
        business_unit=business_unit,
        direct_assignee=participant,
    )

    mark_action_plan_execution_done(
        execution_id=execution.id,
        actor_membership=owner,
    )

    assert _gam05_txs(execution=execution) == []


def test_deactivated_participant_awards_zero():
    _establishment, business_unit, owner, participant = _setup()
    participant.status = EstablishmentMembership.Status.DEACTIVATED
    participant.save(update_fields=["status", "updated_at"])
    plan, schedule = _create_plan_and_schedule(
        creator=owner,
        business_unit=business_unit,
    )
    execution = _create_execution(
        creator=owner,
        business_unit=business_unit,
        plan=plan,
        schedule=schedule,
        direct_assignee=participant,
    )

    mark_action_plan_execution_done(
        execution_id=execution.id,
        actor_membership=owner,
    )

    assert _gam05_txs(membership=participant, execution=execution) == []


def test_double_helper_call_is_idempotent():
    _establishment, business_unit, owner, participant = _setup()
    plan, schedule = _create_plan_and_schedule(
        creator=owner,
        business_unit=business_unit,
    )
    execution = _create_execution(
        creator=owner,
        business_unit=business_unit,
        plan=plan,
        schedule=schedule,
        direct_assignee=participant,
    )
    mark_action_plan_execution_done(
        execution_id=execution.id,
        actor_membership=owner,
    )
    execution.refresh_from_db()

    award_recurring_execution_done_points(execution=execution)

    txs = _gam05_txs(membership=participant, execution=execution)
    assert len(txs) == 1
    event = _marked_done_event(execution)
    assert txs[0].source_event_id == str(event.id)
    assert txs[0].occurred_at == event.occurred_at


def test_missing_canonical_lifecycle_raises_for_eligible_done_execution():
    _establishment, business_unit, owner, participant = _setup()
    plan, schedule = _create_plan_and_schedule(
        creator=owner,
        business_unit=business_unit,
    )
    execution = _create_execution(
        creator=owner,
        business_unit=business_unit,
        plan=plan,
        schedule=schedule,
        direct_assignee=participant,
    )
    ActionPlanExecution.objects.filter(pk=execution.pk).update(status=EXECUTION_STATUS_DONE)
    execution.refresh_from_db()

    with pytest.raises(GamificationValidationError) as exc_info:
        award_recurring_execution_done_points(execution=execution)

    assert exc_info.value.code == "gamification_recurring_execution_done_lifecycle_missing"
    assert _gam05_txs(execution=execution) == []


def test_award_failure_rolls_back_mark_done_and_lifecycle():
    _establishment, business_unit, owner, participant = _setup()
    plan, schedule = _create_plan_and_schedule(
        creator=owner,
        business_unit=business_unit,
    )
    execution = _create_execution(
        creator=owner,
        business_unit=business_unit,
        plan=plan,
        schedule=schedule,
        direct_assignee=participant,
    )

    with patch(
        "houston.gamification.services.award_points",
        side_effect=RuntimeError("award failed"),
    ), pytest.raises(RuntimeError, match="award failed"):
        mark_action_plan_execution_done(
            execution_id=execution.id,
            actor_membership=owner,
        )

    execution.refresh_from_db()
    assert execution.status == EXECUTION_STATUS_IN_PROGRESS
    assert execution.marked_done_at is None
    assert execution.marked_done_by_membership_id is None
    assert not ActionPlanExecutionLifecycleEvent.objects.filter(
        action_plan_execution=execution,
        event_type=EXECUTION_LIFECYCLE_EVENT_MARKED_DONE,
    ).exists()
    assert _gam05_txs(execution=execution) == []
