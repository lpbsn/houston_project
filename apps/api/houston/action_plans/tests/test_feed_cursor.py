from __future__ import annotations

import pytest
from django.utils import timezone

from houston.action_plans.feed_cursor import (
    DEADLINE_BUCKET_OVERDUE,
    ActionPlanExecutionFeedCursorError,
    _after_cursor_filter,
    action_plan_execution_feed_auth_context_hash,
    action_plan_execution_feed_order_by,
    encode_action_plan_execution_feed_cursor,
    parse_action_plan_execution_feed_cursor,
    validate_action_plan_execution_feed_cursor_context,
)
from houston.action_plans.selectors import annotate_action_plan_execution_feed_sort_keys
from houston.action_plans.tests.helpers import create_execution

pytestmark = pytest.mark.django_db


def _auth_hash(
    membership,
    *,
    view_mode="general",
    category="all",
    scope="establishment",
):
    return action_plan_execution_feed_auth_context_hash(
        memberships=[membership],
        view_mode=view_mode,
        category=category,
        scope=scope,
    )


def test_cursor_round_trips_v1_context(owner_membership, business_unit):
    now = timezone.now()
    execution = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Cursor encoded",
        end_at=now - timezone.timedelta(hours=2),
    )
    auth_hash = _auth_hash(owner_membership)

    cursor = encode_action_plan_execution_feed_cursor(
        execution,
        as_of=now,
        view_mode="general",
        category="all",
        auth_context_hash=auth_hash,
    )
    parsed = parse_action_plan_execution_feed_cursor(cursor)

    assert parsed is not None
    assert parsed.view_mode == "general"
    assert parsed.category == "all"
    assert parsed.auth_context_hash == auth_hash
    assert parsed.deadline_bucket == DEADLINE_BUCKET_OVERDUE


def test_cursor_context_mismatch_rejects_category_change(owner_membership, business_unit):
    now = timezone.now()
    execution = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Cursor context",
    )
    cursor = parse_action_plan_execution_feed_cursor(
        encode_action_plan_execution_feed_cursor(
            execution,
            as_of=now,
            view_mode="general",
            category="all",
            auth_context_hash=_auth_hash(owner_membership),
        ),
    )
    assert cursor is not None

    with pytest.raises(ActionPlanExecutionFeedCursorError) as exc_info:
        validate_action_plan_execution_feed_cursor_context(
            cursor,
            view_mode="general",
            category="in_progress",
            auth_context_hash=_auth_hash(owner_membership, category="in_progress"),
        )

    assert exc_info.value.code == "cursor_context_mismatch"


def test_cursor_context_distinguishes_establishment_and_cross(owner_membership):
    establishment_hash = _auth_hash(owner_membership, scope="establishment")
    cross_hash = _auth_hash(owner_membership, scope="cross")

    assert establishment_hash != cross_hash


def test_cursor_auth_context_changes_with_membership_role(owner_membership):
    before = _auth_hash(owner_membership)
    owner_membership.role = owner_membership.Role.DIRECTOR
    owner_membership.save(update_fields=["role", "updated_at"])

    assert _auth_hash(owner_membership) != before


def test_after_cursor_filter_continues_operational_list_order(
    owner_membership,
    business_unit,
):
    now = timezone.now()
    first = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Earlier deadline",
        end_at=now + timezone.timedelta(hours=1),
    )
    second = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Later deadline",
        end_at=now + timezone.timedelta(hours=2),
    )

    from houston.action_plans.selectors import action_plan_execution_feed_queryset

    queryset = action_plan_execution_feed_queryset(
        membership=owner_membership,
        view_mode="general",
    )
    annotated = annotate_action_plan_execution_feed_sort_keys(
        queryset,
        membership=owner_membership,
        as_of=now,
    )
    cursor = parse_action_plan_execution_feed_cursor(
        encode_action_plan_execution_feed_cursor(
            first,
            as_of=now,
            view_mode="general",
            category="all",
            auth_context_hash=_auth_hash(owner_membership),
        ),
    )
    assert cursor is not None

    following_ids = list(
        annotated.filter(_after_cursor_filter(cursor))
        .order_by(*action_plan_execution_feed_order_by())
        .values_list("id", flat=True),
    )

    assert following_ids == [second.id]


def test_pending_validation_ties_use_id_ascending_before_deadline_or_activity(
    owner_membership,
    business_unit,
):
    now = timezone.now()
    first_created = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Pending A",
        status="pending_validation",
        requires_validation=True,
    )
    second_created = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Pending B",
        status="pending_validation",
        requires_validation=True,
    )
    lower_id, higher_id = sorted([first_created, second_created], key=lambda item: item.id)
    lower_id.marked_done_at = now
    lower_id.end_at = now + timezone.timedelta(days=5)
    lower_id.last_activity_at = now - timezone.timedelta(days=2)
    lower_id.save(update_fields=["marked_done_at", "end_at", "last_activity_at", "updated_at"])
    higher_id.marked_done_at = now
    higher_id.end_at = now - timezone.timedelta(days=1)
    higher_id.last_activity_at = now
    higher_id.save(update_fields=["marked_done_at", "end_at", "last_activity_at", "updated_at"])

    from houston.action_plans.selectors import action_plan_execution_feed_queryset

    queryset = annotate_action_plan_execution_feed_sort_keys(
        action_plan_execution_feed_queryset(
            membership=owner_membership,
            view_mode="general",
        ),
        membership=owner_membership,
        as_of=now,
    )
    ordered_ids = list(
        queryset.order_by(*action_plan_execution_feed_order_by()).values_list("id", flat=True),
    )
    assert ordered_ids == [lower_id.id, higher_id.id]

    cursor = parse_action_plan_execution_feed_cursor(
        encode_action_plan_execution_feed_cursor(
            lower_id,
            as_of=now,
            view_mode="general",
            category="all",
            auth_context_hash=_auth_hash(owner_membership),
        ),
    )
    assert cursor is not None
    following_ids = list(
        queryset.filter(_after_cursor_filter(cursor))
        .order_by(*action_plan_execution_feed_order_by())
        .values_list("id", flat=True),
    )
    assert following_ids == [higher_id.id]
