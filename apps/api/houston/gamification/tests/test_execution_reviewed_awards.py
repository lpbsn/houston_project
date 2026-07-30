from __future__ import annotations

from datetime import time as dt_time
from unittest.mock import patch

import pytest
from django.utils import timezone

from houston.action_plans.constants import (
    EXECUTION_LIFECYCLE_EVENT_VALIDATED,
    EXECUTION_STATUS_DONE,
    EXECUTION_STATUS_IN_PROGRESS,
    EXECUTION_STATUS_PENDING_VALIDATION,
)
from houston.action_plans.models import (
    ActionPlan,
    ActionPlanAssignee,
    ActionPlanExecution,
    ActionPlanExecutionLifecycleEvent,
    ActionPlanExecutionReview,
    ActionPlanExecutionTask,
    ActionPlanExecutionTeam,
    ActionPlanSchedule,
)
from houston.action_plans.services import (
    mark_action_plan_execution_done,
    validate_action_plan_execution,
)
from houston.comments.models import Comment, CommentMention
from houston.establishments.models import EstablishmentMembership
from houston.gamification.constants import (
    REASON_EXECUTION_REVIEWED,
    REASON_RECURRING_EXECUTION_DONE,
    SOURCE_TYPE_ACTION_PLAN_EXECUTION,
)
from houston.gamification.exceptions import GamificationValidationError
from houston.gamification.models import PointTransaction
from houston.gamification.services import (
    award_action_plan_execution_reviewed_points,
    open_season,
)
from houston.testing.factories import create_establishment, create_membership
from houston.testing.taxonomy import create_business_unit

pytestmark = pytest.mark.django_db


def _setup():
    establishment = create_establishment(name="GAM-06 Hotel", timezone="UTC")
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
    requires_validation=True,
):
    today = timezone.now().date()
    plan = ActionPlan.objects.create(
        establishment=creator.establishment,
        created_by=creator,
        pilot_business_unit=business_unit,
        title="Recurring reviewed plan",
        description="Recurring reviewed plan",
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
    requires_validation=True,
    occurrence_date=None,
    direct_assignee=None,
    task_assignee=None,
    status=EXECUTION_STATUS_IN_PROGRESS,
):
    now = timezone.now()
    if plan is None:
        plan = ActionPlan.objects.create(
            establishment=creator.establishment,
            created_by=creator,
            pilot_business_unit=business_unit,
            title="Reviewed plan",
            description="Reviewed plan",
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
        status=status,
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


def _review(execution):
    return ActionPlanExecutionReview.objects.get(
        action_plan_execution=execution,
        is_active=True,
    )


def _gam06_txs(*, membership=None, execution=None):
    qs = PointTransaction.objects.filter(
        reason_code=REASON_EXECUTION_REVIEWED,
        source_type=SOURCE_TYPE_ACTION_PLAN_EXECUTION,
    )
    if membership is not None:
        qs = qs.filter(membership=membership)
    if execution is not None:
        qs = qs.filter(source_id=str(execution.id))
    return list(qs.order_by("created_at", "id"))


def _gam05_txs(*, execution=None):
    qs = PointTransaction.objects.filter(
        reason_code=REASON_RECURRING_EXECUTION_DONE,
        source_type=SOURCE_TYPE_ACTION_PLAN_EXECUTION,
    )
    if execution is not None:
        qs = qs.filter(source_id=str(execution.id))
    return list(qs.order_by("created_at", "id"))


def _mark_and_validate(*, execution, reviewer, stars):
    pending = mark_action_plan_execution_done(
        execution_id=execution.id,
        actor_membership=reviewer,
    )
    return validate_action_plan_execution(
        execution_id=pending.id,
        actor_membership=reviewer,
        stars=stars,
    )


def test_direct_assignee_awards_review_stars():
    _establishment, business_unit, owner, participant = _setup()
    execution = _create_execution(
        creator=owner,
        business_unit=business_unit,
        direct_assignee=participant,
    )

    validated = _mark_and_validate(execution=execution, reviewer=owner, stars=5)

    review = _review(validated)
    txs = _gam06_txs(membership=participant, execution=execution)
    assert len(txs) == 1
    assert txs[0].delta == 5
    assert txs[0].source_event_id == str(review.id)
    assert txs[0].occurred_at == review.reviewed_at


def test_direct_task_and_mention_dedupe_to_one_award():
    _establishment, business_unit, owner, participant = _setup()
    execution = _create_execution(
        creator=owner,
        business_unit=business_unit,
        direct_assignee=participant,
        task_assignee=participant,
    )
    _create_execution_comment_mention(
        execution=execution,
        author=owner,
        mentioned=participant,
    )

    _mark_and_validate(execution=execution, reviewer=owner, stars=3)

    txs = _gam06_txs(membership=participant, execution=execution)
    assert len(txs) == 1
    assert txs[0].delta == 3


def test_action_plan_creator_is_excluded_even_when_assigned():
    _establishment, business_unit, creator, _participant = _setup()
    reviewer = create_membership(
        establishment=creator.establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    execution = _create_execution(
        creator=creator,
        business_unit=business_unit,
        direct_assignee=creator,
    )

    _mark_and_validate(execution=execution, reviewer=reviewer, stars=5)

    assert _gam06_txs(membership=creator, execution=execution) == []


def test_reviewer_is_excluded_even_when_mentioned():
    _establishment, business_unit, owner, _participant = _setup()
    reviewer = create_membership(
        establishment=owner.establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    execution = _create_execution(
        creator=owner,
        business_unit=business_unit,
    )
    _create_execution_comment_mention(
        execution=execution,
        author=owner,
        mentioned=reviewer,
    )

    _mark_and_validate(execution=execution, reviewer=reviewer, stars=5)

    assert _gam06_txs(membership=reviewer, execution=execution) == []


def test_execution_creator_can_receive_when_not_action_plan_creator_or_reviewer():
    _establishment, business_unit, plan_creator, _participant = _setup()
    execution_creator = create_membership(
        establishment=plan_creator.establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    reviewer = create_membership(
        establishment=plan_creator.establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    plan = ActionPlan.objects.create(
        establishment=plan_creator.establishment,
        created_by=plan_creator,
        pilot_business_unit=business_unit,
        title="Catalog-origin reviewed plan",
        description="Catalog-origin reviewed plan",
        requires_validation=True,
    )
    execution = _create_execution(
        creator=execution_creator,
        business_unit=business_unit,
        plan=plan,
        direct_assignee=execution_creator,
    )

    _mark_and_validate(execution=execution, reviewer=reviewer, stars=4)

    txs = _gam06_txs(membership=execution_creator, execution=execution)
    assert len(txs) == 1
    assert txs[0].delta == 4


def test_zero_star_review_creates_no_points():
    _establishment, business_unit, owner, participant = _setup()
    execution = _create_execution(
        creator=owner,
        business_unit=business_unit,
        direct_assignee=participant,
    )

    validated = _mark_and_validate(execution=execution, reviewer=owner, stars=0)

    validated.refresh_from_db()
    assert validated.status == EXECUTION_STATUS_DONE
    assert _review(validated).stars == 0
    assert _gam06_txs(execution=execution) == []


def test_mention_created_after_review_is_excluded_on_replay():
    _establishment, business_unit, owner, participant = _setup()
    execution = _create_execution(
        creator=owner,
        business_unit=business_unit,
    )
    validated = _mark_and_validate(execution=execution, reviewer=owner, stars=5)
    review = _review(validated)
    comment = _create_execution_comment_mention(
        execution=execution,
        author=owner,
        mentioned=participant,
    )
    Comment.objects.filter(pk=comment.pk).update(
        created_at=review.reviewed_at + timezone.timedelta(seconds=1),
    )

    validated.refresh_from_db()
    award_action_plan_execution_reviewed_points(execution=validated)

    assert _gam06_txs(membership=participant, execution=execution) == []


def test_recurring_with_validation_awards_gam06_not_gam05():
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

    _mark_and_validate(execution=execution, reviewer=owner, stars=2)

    gam06 = _gam06_txs(membership=participant, execution=execution)
    assert len(gam06) == 1
    assert gam06[0].delta == 2
    assert _gam05_txs(execution=execution) == []


def test_double_helper_call_is_idempotent():
    _establishment, business_unit, owner, participant = _setup()
    execution = _create_execution(
        creator=owner,
        business_unit=business_unit,
        direct_assignee=participant,
    )
    validated = _mark_and_validate(execution=execution, reviewer=owner, stars=3)
    review = _review(validated)

    award_action_plan_execution_reviewed_points(execution=validated)

    txs = _gam06_txs(membership=participant, execution=execution)
    assert len(txs) == 1
    assert txs[0].delta == 3
    assert txs[0].source_event_id == str(review.id)
    assert txs[0].occurred_at == review.reviewed_at


@pytest.mark.django_db(transaction=True)
def test_concurrent_helper_calls_converge_to_one_transaction():
    from concurrent.futures import ThreadPoolExecutor

    from django.db import close_old_connections, connection

    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL-only concurrency test")

    _establishment, business_unit, owner, participant = _setup()
    open_season(owner.establishment, month_start_local=timezone.now().date().replace(day=1))
    execution = _create_execution(
        creator=owner,
        business_unit=business_unit,
        direct_assignee=participant,
        status=EXECUTION_STATUS_DONE,
    )
    now = timezone.now()
    execution.validated_at = now
    execution.validated_by_membership = owner
    execution.save(update_fields=["validated_at", "validated_by_membership", "updated_at"])
    ActionPlanExecutionReview.objects.create(
        action_plan_execution=execution,
        reviewer_membership=owner,
        stars=5,
        reviewed_at=now,
    )

    def run_award():
        close_old_connections()
        try:
            award_action_plan_execution_reviewed_points(execution=execution)
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run_award), pool.submit(run_award)]
        for future in futures:
            future.result(timeout=15)

    txs = _gam06_txs(membership=participant, execution=execution)
    assert len(txs) == 1
    assert txs[0].delta == 5


def test_validated_execution_without_review_raises_integrity_error():
    _establishment, business_unit, owner, participant = _setup()
    execution = _create_execution(
        creator=owner,
        business_unit=business_unit,
        direct_assignee=participant,
        status=EXECUTION_STATUS_DONE,
    )

    with pytest.raises(GamificationValidationError) as exc_info:
        award_action_plan_execution_reviewed_points(execution=execution)

    assert exc_info.value.code == "gamification_execution_review_missing"
    assert _gam06_txs(execution=execution) == []


def test_award_failure_rolls_back_validate_and_partial_points():
    _establishment, business_unit, owner, first_participant = _setup()
    second_participant = create_membership(
        establishment=owner.establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    execution = _create_execution(
        creator=owner,
        business_unit=business_unit,
        direct_assignee=first_participant,
        task_assignee=second_participant,
    )
    pending = mark_action_plan_execution_done(
        execution_id=execution.id,
        actor_membership=owner,
    )

    from houston.gamification import services as gamification_services

    real_award_points = gamification_services.award_points
    calls = {"count": 0}

    def fail_on_second_award(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 2:
            raise RuntimeError("award failed")
        return real_award_points(*args, **kwargs)

    with patch(
        "houston.gamification.services.award_points",
        side_effect=fail_on_second_award,
    ), pytest.raises(RuntimeError, match="award failed"):
        validate_action_plan_execution(
            execution_id=pending.id,
            actor_membership=owner,
            stars=5,
        )

    pending.refresh_from_db()
    assert pending.status == EXECUTION_STATUS_PENDING_VALIDATION
    assert pending.validated_at is None
    assert pending.validated_by_membership_id is None
    assert not ActionPlanExecutionReview.objects.filter(
        action_plan_execution=pending,
    ).exists()
    assert not ActionPlanExecutionLifecycleEvent.objects.filter(
        action_plan_execution=pending,
        event_type=EXECUTION_LIFECYCLE_EVENT_VALIDATED,
    ).exists()
    assert _gam06_txs(execution=pending) == []
    assert calls["count"] == 2
