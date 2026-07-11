from __future__ import annotations

import pytest
from django.utils import timezone

from houston.action_plans.constants import (
    EXECUTION_STATUS_CANCELED,
    EXECUTION_STATUS_DONE,
)
from houston.action_plans.feed_cursor import (
    DEADLINE_BUCKET_OVERDUE,
    DEADLINE_BUCKET_TERMINAL,
    _after_cursor_filter,
    deadline_bucket_for_execution,
    encode_action_plan_execution_feed_cursor,
    parse_action_plan_execution_feed_cursor,
    sort_end_at_for_execution,
)
from houston.action_plans.selectors import annotate_action_plan_execution_feed_sort_keys
from houston.action_plans.tests.test_execution_feed_api import _create_execution

pytestmark = pytest.mark.django_db


def test_deadline_bucket_for_terminal_done_and_canceled(owner_membership, business_unit):
    now = timezone.now()
    done = _create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Done terminal",
        status=EXECUTION_STATUS_DONE,
        end_at=now - timezone.timedelta(days=1),
    )
    canceled = _create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Canceled terminal",
        status=EXECUTION_STATUS_CANCELED,
        end_at=now - timezone.timedelta(days=1),
    )

    assert deadline_bucket_for_execution(done, now) == DEADLINE_BUCKET_TERMINAL
    assert deadline_bucket_for_execution(canceled, now) == DEADLINE_BUCKET_TERMINAL
    assert deadline_bucket_for_execution(done, now) != DEADLINE_BUCKET_OVERDUE


def test_sort_end_at_for_terminal_is_none_even_with_db_end_at(owner_membership, business_unit):
    now = timezone.now()
    done = _create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Done with end_at",
        status=EXECUTION_STATUS_DONE,
        end_at=now + timezone.timedelta(days=1),
    )

    assert done.end_at is not None
    assert sort_end_at_for_execution(done) is None


def test_encode_terminal_cursor_uses_bucket_three_and_empty_end_at(
    owner_membership,
    business_unit,
):
    now = timezone.now()
    done = _create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Done encoded",
        status=EXECUTION_STATUS_DONE,
        end_at=now - timezone.timedelta(hours=2),
    )

    cursor = encode_action_plan_execution_feed_cursor(done, as_of=now)
    parsed = parse_action_plan_execution_feed_cursor(cursor)

    assert parsed is not None
    assert parsed.deadline_bucket == DEADLINE_BUCKET_TERMINAL
    assert parsed.end_at is None


def test_after_cursor_filter_selects_terminal_by_last_activity_not_end_at(
    owner_membership,
    business_unit,
):
    now = timezone.now()
    newer_done = _create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Newer done",
        status=EXECUTION_STATUS_DONE,
        last_activity_at=now - timezone.timedelta(hours=1),
        end_at=now + timezone.timedelta(days=2),
    )
    older_done = _create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Older done",
        status=EXECUTION_STATUS_DONE,
        last_activity_at=now - timezone.timedelta(days=2),
        end_at=now - timezone.timedelta(days=1),
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
        encode_action_plan_execution_feed_cursor(newer_done, as_of=now),
    )
    assert cursor is not None

    following_ids = list(
        annotated.filter(_after_cursor_filter(cursor))
        .order_by("status_rank", "-last_activity_at")
        .values_list("id", flat=True),
    )

    assert following_ids == [older_done.id]
