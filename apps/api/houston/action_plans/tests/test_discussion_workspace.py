import pytest
from django.utils import timezone

from houston.action_plans.exceptions import ActionPlanPermissionError
from houston.action_plans.tests.helpers import build_assignee_payload, create_execution
from houston.chat.workspace_selectors import communication_search, plan_discussions
from houston.comments.discussion_services import (
    task_from_comment,
    update_comment_tool,
    update_discussion_preference,
)
from houston.comments.exceptions import CommentNotFoundError
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
    with pytest.raises(CommentNotFoundError):
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


def test_latest_plan_comment_lookup_uses_execution_index(owner_membership, discussion):
    from django.db import connection

    from houston.chat.workspace_selectors import PLAN_COMMENT_LATEST_INDEX
    from houston.comments.models import Comment

    plan, _comment = discussion
    lookup = Comment.objects.filter(
        establishment_id=owner_membership.establishment_id,
        action_plan_execution_id=plan.id,
    ).order_by("-created_at", "-id")[:1]
    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL enable_seqscan = off")
        plan_text = lookup.explain()
    assert PLAN_COMMENT_LATEST_INDEX in plan_text


def test_plan_discussion_query_count_stays_flat(api_client, owner_membership, business_unit):
    from houston.action_plans.tests.helpers import build_assignee_payload, create_execution
    from houston.comments.services import create_action_plan_execution_comment
    from houston.testing.auth import auth_headers, login
    from houston.testing.query_baseline import (
        CHAT_WORKSPACE_MAX_QUERY_DELTA_ONE_TO_THREE,
        CHAT_WORKSPACE_PLANS_MAX_QUERIES,
        capture_queries,
    )

    def add_plan(title: str) -> None:
        plan = create_execution(
            owner_membership,
            business_unit=business_unit,
            title=title,
            assignees=[
                build_assignee_payload(membership=owner_membership, business_unit=business_unit)
            ],
        )
        create_action_plan_execution_comment(
            author_membership=owner_membership,
            execution=plan,
            body=f"Discussion {title}",
        )

    def measure() -> tuple[int, int]:
        token = login(api_client, user=owner_membership.user)
        url = (
            f"/api/v1/establishments/{owner_membership.establishment_id}/chat/workspace/?tab=plans"
        )
        with capture_queries() as captured:
            response = api_client.get(url, **auth_headers(token))
        assert response.status_code == 200
        return len(captured.captured_queries), len(response.json()["items"])

    add_plan("Un")
    one_queries, one_items = measure()
    add_plan("Deux")
    add_plan("Trois")
    three_queries, three_items = measure()
    assert one_items == 1
    assert three_items == 3
    assert three_queries - one_queries <= CHAT_WORKSPACE_MAX_QUERY_DELTA_ONE_TO_THREE
    assert three_queries <= CHAT_WORKSPACE_PLANS_MAX_QUERIES


def test_french_comment_search_uses_gin_index(owner_membership, discussion):
    from django.contrib.postgres.search import SearchQuery, SearchVector
    from django.db import connection

    from houston.chat.workspace_selectors import communication_search
    from houston.comments.models import Comment
    from houston.testing.query_baseline import capture_queries

    _plan, _comment = discussion
    queryset = Comment.objects.annotate(search=SearchVector("body", config="french")).filter(
        search=SearchQuery("affiches", config="french", search_type="plain")
    )
    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL enable_seqscan = off")
        cursor.execute("SET LOCAL enable_indexscan = off")
        cursor.execute("SET LOCAL enable_indexonlyscan = off")
        plan_text = queryset.explain()
    assert "comment_search_idx" in plan_text
    with capture_queries() as captured:
        communication_search(membership=owner_membership, query="affiches")
    sql = " ".join(query["sql"] for query in captured.captured_queries)
    assert "to_tsvector" in sql
    assert "french" in sql


def test_merged_cursor_interleaves_chat_and_plan_comments_without_gaps(
    owner_membership, staff_membership, discussion, monkeypatch
):
    import uuid
    from datetime import timedelta

    from django.utils import timezone

    from houston.chat import workspace_selectors
    from houston.chat.api.views import parse_message_cursor
    from houston.chat.models import ChatMessage
    from houston.chat.services import create_or_get_dm_conversation
    from houston.chat.workspace_selectors import communication_search
    from houston.comments.models import Comment

    plan, comment = discussion
    conversation, _created = create_or_get_dm_conversation(
        actor_membership=owner_membership,
        target_membership_id=staff_membership.id,
    )
    monkeypatch.setattr(workspace_selectors, "PAGE_SIZE", 2)
    base = timezone.now()
    expected = []
    comment.created_at = base
    comment.save(update_fields=["created_at"])
    expected.append(comment.id)
    for index in range(1, 4):
        if index % 2 == 0:
            row = Comment.objects.create(
                establishment=plan.establishment,
                action_plan_execution=plan,
                author_membership=owner_membership,
                body=f"Affiches {index}",
            )
        else:
            row = ChatMessage.objects.create(
                conversation=conversation,
                author_membership=owner_membership,
                body=f"Affiches {index}",
                client_message_id=uuid.uuid4(),
            )
        row.created_at = base - timedelta(minutes=index)
        row.save(update_fields=["created_at"])
        expected.append(row.id)

    seen = []
    cursor = None
    for _page_index in range(6):
        page = communication_search(
            membership=owner_membership,
            query="affiches",
            cursor=parse_message_cursor(cursor) if cursor else None,
        )
        seen.extend(item["id"] for item in page["items"])
        cursor = page["cursor"]
        if cursor is None:
            break
    assert seen == expected
    assert cursor is None


def test_inactive_member_cannot_search_discussions(owner_membership, discussion):
    owner_membership.status = "deactivated"
    assert communication_search(membership=owner_membership)["items"] == []
    assert plan_discussions(membership=owner_membership)["items"] == []
