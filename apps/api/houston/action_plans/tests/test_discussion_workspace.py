import pytest
from django.utils import timezone

from houston.action_plans.exceptions import ActionPlanPermissionError
from houston.action_plans.tests.helpers import build_assignee_payload, create_execution
from houston.chat.exceptions import ChatNotFoundError
from houston.chat.workspace_selectors import communication_search, plan_discussions
from houston.comments.discussion_services import (
    task_from_comment,
    update_comment_tool,
    update_discussion_preference,
)
from houston.comments.models import Comment, PlanDiscussionPreference
from houston.comments.services import create_action_plan_execution_comment
from houston.notifications.discussion_preferences import comment_notification_allowed

pytestmark = pytest.mark.django_db


@pytest.fixture
def discussion(owner_membership, staff_membership, business_unit):
    plan = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Préparer les affiches",
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
    )
    comment = create_action_plan_execution_comment(
        author_membership=staff_membership,
        execution=plan,
        body="Commander les affiches de livraison.",
    )
    return plan, comment


def test_plan_inbox_reuses_discussion_and_marks_only_loaded_messages(owner_membership, discussion):
    plan, comment = discussion
    assert plan_discussions(membership=owner_membership)["items"][0]["unread"]
    update_discussion_preference(
        membership=owner_membership,
        execution_id=plan.id,
        seen=True,
        seen_through=comment.created_at,
    )
    assert not plan_discussions(membership=owner_membership)["items"][0]["unread"]
    newer = Comment.objects.create(
        establishment=plan.establishment,
        action_plan_execution=plan,
        author_membership=comment.author_membership,
        body="Une nouvelle livraison",
    )
    update_discussion_preference(
        membership=owner_membership,
        execution_id=plan.id,
        seen=True,
        seen_through=comment.created_at,
    )
    assert plan_discussions(membership=owner_membership)["items"][0]["id"] == newer.id
    assert plan_discussions(membership=owner_membership)["items"][0]["unread"]


def test_task_creation_preserves_existing_work_and_is_idempotent(
    owner_membership, staff_membership, discussion
):
    plan, comment = discussion
    original = set(plan.task_executions.values_list("id", flat=True))
    task_id = task_from_comment(
        membership=owner_membership,
        comment_id=comment.id,
        title="Commander les affiches",
        assigned_membership_id=staff_membership.id,
        deadline_at=None,
    )
    assert (
        task_from_comment(
            membership=owner_membership,
            comment_id=comment.id,
            title="Commander les affiches",
            assigned_membership_id=staff_membership.id,
            deadline_at=None,
        )
        == task_id
    )
    assert plan.task_executions.count() == len(original) + 1
    assert original.issubset(set(plan.task_executions.values_list("id", flat=True)))
    assert plan.task_executions.get(id=task_id).assigned_membership_id == staff_membership.id
    comment.refresh_from_db()
    assert comment.created_task_id == task_id


def test_staff_cannot_bypass_execution_edit_permissions(staff_membership, discussion):
    _, comment = discussion
    with pytest.raises(ActionPlanPermissionError):
        task_from_comment(
            membership=staff_membership,
            comment_id=comment.id,
            title="Nouvelle tâche",
            assigned_membership_id=staff_membership.id,
            deadline_at=None,
        )
    comment.refresh_from_db()
    assert comment.created_task_id is None


def test_out_of_scope_member_cannot_read_search_or_pin(out_of_scope_staff, discussion):
    _, comment = discussion
    assert communication_search(membership=out_of_scope_staff, query="affiches")["items"] == []
    with pytest.raises(ChatNotFoundError):
        update_comment_tool(
            membership=out_of_scope_staff, comment_id=comment.id, operation="pin", active=True
        )


def test_decision_pin_and_unresolved_filter(owner_membership, discussion):
    plan, comment = discussion
    update_comment_tool(
        membership=owner_membership, comment_id=comment.id, operation="pin", active=True
    )
    comment.refresh_from_db()
    assert comment.pinned_at is not None
    assert len(plan_discussions(membership=owner_membership, unresolved=True)["items"]) == 1
    comment.resolved_at = timezone.now()
    comment.save(update_fields=["resolved_at"])
    assert plan_discussions(membership=owner_membership, unresolved=True)["items"] == []


def test_plan_silent_mode_preserves_business_actions_notifications(owner_membership, discussion):
    plan, comment = discussion
    update_discussion_preference(membership=owner_membership, execution_id=plan.id, mode="silent")
    assert not comment_notification_allowed(
        comment_id=comment.id, membership_id=owner_membership.id
    )
    assert (
        PlanDiscussionPreference.objects.get(
            execution=plan, membership=owner_membership
        ).notification_mode
        == "silent"
    )


def test_inactive_member_cannot_search_discussions(owner_membership, discussion):
    owner_membership.status = "deactivated"
    assert communication_search(membership=owner_membership)["items"] == []
    assert plan_discussions(membership=owner_membership)["items"] == []
