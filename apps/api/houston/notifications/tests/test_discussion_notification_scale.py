"""Discussion preferences are read once per delivery, not once per recipient.

Silent blocks the discussion, including mentions. Task assignment and deadline
notifications stay on the execution update path and are not filtered.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from django.utils import timezone

from houston.action_plans.execution_update import update_action_plan_execution
from houston.action_plans.tests.helpers import build_assignee_payload, create_execution
from houston.chat.models import ChatMessage, ChatMessageMention, ChatParticipant
from houston.chat.services import (
    create_group_conversation,
    create_message,
    create_or_get_dm_conversation,
)
from houston.comments.discussion_services import task_from_comment, update_discussion_preference
from houston.comments.models import PlanDiscussionPreference
from houston.comments.services import create_action_plan_execution_comment
from houston.establishments.models import EstablishmentMembership
from houston.notifications.models import Notification
from houston.notifications.scheduling import (
    _deliver_chat_message_notifications,
    _deliver_comment_notifications,
    _load_chat_message,
)
from houston.testing.auth import build_api_membership_on_establishment
from houston.testing.query_baseline import capture_queries

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


def _enable_chat(membership: EstablishmentMembership) -> None:
    establishment = membership.establishment
    if establishment.chat_enabled:
        return
    establishment.chat_enabled = True
    establishment.save(update_fields=["chat_enabled", "updated_at"])


def _preference_statements(captured) -> list[str]:
    """Batched preference reads only.

    Visibility checks inside notification creation may still touch mentions once
    per recipient. Those are not the discussion-mode lookup.
    """
    matched = []
    for query in captured.captured_queries:
        sql = query["sql"].lower()
        if "plandiscussionpreference" in sql or "notification_mode" in sql:
            matched.append(query["sql"])
            continue
        batched_mention = " in (" in sql and (
            "commentmention" in sql or "chatmessagemention" in sql
        )
        if batched_mention:
            matched.append(query["sql"])
    return matched


def test_chat_preference_queries_stay_constant_as_recipients_grow(owner_membership):
    _enable_chat(owner_membership)
    peers = [build_api_membership_on_establishment(owner_membership) for _index in range(4)]
    conversation = create_group_conversation(
        actor_membership=owner_membership,
        title="Équipe terrain",
        membership_ids=[peer.id for peer in peers],
    )
    ChatParticipant.objects.filter(conversation=conversation, membership__in=peers).update(
        notification_mode="mentions"
    )
    message = ChatMessage.objects.create(
        conversation=conversation,
        author_membership=owner_membership,
        body="Bonjour l'équipe",
        client_message_id=uuid.uuid4(),
    )
    ChatMessageMention.objects.create(message=message, membership=peers[0], start=0, end=1)
    loaded = _load_chat_message(message_id=message.id)

    def deliver(recipients: list[EstablishmentMembership]) -> list[str]:
        # Replace the resolver result by calling the same delivery filter through
        # the production function's recipient set: deactivate everyone else.
        active_ids = {owner_membership.id, *(recipient.id for recipient in recipients)}
        EstablishmentMembership.objects.filter(
            establishment=owner_membership.establishment
        ).exclude(id__in=active_ids).update(status=EstablishmentMembership.Status.DEACTIVATED)
        with capture_queries() as captured:
            _deliver_chat_message_notifications(message=loaded, actor_membership=owner_membership)
        EstablishmentMembership.objects.filter(id__in=[peer.id for peer in peers]).update(
            status=EstablishmentMembership.Status.ACTIVE
        )
        Notification.objects.filter(subject_id=conversation.id).delete()
        return _preference_statements(captured)

    one = deliver([peers[0]])
    many = deliver(peers)
    assert len(one) == len(many)
    assert len(many) <= 4


def test_plan_preference_queries_stay_constant_as_recipients_grow(
    owner_membership, staff_membership, discussion
):
    _plan, comment = discussion
    extras = [build_api_membership_on_establishment(owner_membership) for _index in range(3)]
    PlanDiscussionPreference.objects.create(
        execution=_plan,
        membership=staff_membership,
        notification_mode="mentions",
    )
    for extra in extras:
        PlanDiscussionPreference.objects.create(
            execution=_plan,
            membership=extra,
            notification_mode="all",
        )

    def deliver(recipients):
        with capture_queries() as captured:
            _deliver_comment_notifications(
                comment=comment,
                event_key=Notification.EventKey.COMMENT_REPLY_CREATED,
                recipients=recipients,
                actor_membership=owner_membership,
            )
        Notification.objects.filter(subject_id=comment.id).delete()
        return _preference_statements(captured)

    one = deliver([staff_membership])
    many = deliver([staff_membership, *extras])
    assert len(one) == len(many)
    assert len(many) <= 4


def test_silent_blocks_mentions_but_not_task_assignment_or_deadlines(
    owner_membership,
    staff_membership,
    discussion,
    django_capture_on_commit_callbacks,
):
    plan, comment = discussion
    _enable_chat(owner_membership)
    conversation, _created = create_or_get_dm_conversation(
        actor_membership=owner_membership,
        target_membership_id=staff_membership.id,
    )
    ChatParticipant.objects.filter(conversation=conversation, membership=staff_membership).update(
        notification_mode="silent"
    )
    update_discussion_preference(
        membership=staff_membership,
        execution_id=plan.id,
        mode="silent",
    )
    body = f"@{staff_membership.user.username} merci"
    with django_capture_on_commit_callbacks(execute=True):
        create_message(
            author_membership=owner_membership,
            establishment_id=owner_membership.establishment_id,
            conversation_id=conversation.id,
            client_message_id=uuid.uuid4(),
            body=body,
            mentions=[
                {
                    "membership_id": staff_membership.id,
                    "start": 0,
                    "end": len(staff_membership.user.username) + 1,
                }
            ],
        )
        create_action_plan_execution_comment(
            author_membership=owner_membership,
            execution=plan,
            body="Merci pour les affiches",
            mentioned_membership_ids=[staff_membership.id],
        )
    assert not Notification.objects.filter(
        recipient_membership=staff_membership,
        event_key=Notification.EventKey.CHAT_MESSAGE_RECEIVED,
    ).exists()
    assert not Notification.objects.filter(
        recipient_membership=staff_membership,
        subject_type=Notification.SubjectType.COMMENT,
    ).exists()

    deadline = timezone.now() + timedelta(days=2)
    with django_capture_on_commit_callbacks(execute=True):
        task_id = task_from_comment(
            membership=owner_membership,
            comment_id=comment.id,
            title="Poser les affiches",
            assigned_membership_id=staff_membership.id,
            deadline_at=deadline,
        )
    assignment = Notification.objects.filter(
        recipient_membership=staff_membership,
        event_key=Notification.EventKey.ACTION_PLAN_EXECUTION_UPDATED,
        subject_id=plan.id,
    )
    assert assignment.exists()

    plan.refresh_from_db()
    pending = []
    later = deadline + timedelta(days=1)
    for task in plan.task_executions.filter(status="pending").order_by("position"):
        pending.append(
            {
                "id": task.id,
                "task": task.task,
                "description": task.description,
                "business_unit_id": task.execution_team.business_unit_id,
                "position": task.position,
                "assigned_membership_id": task.assigned_membership_id,
                "deadline_at": later if task.id == task_id else task.deadline_at,
            }
        )
    with django_capture_on_commit_callbacks(execute=True):
        update_action_plan_execution(
            execution_id=plan.id,
            actor=owner_membership,
            expected_updated_at=plan.updated_at,
            pending_tasks=pending,
        )
    assert (
        Notification.objects.filter(
            recipient_membership=staff_membership,
            event_key=Notification.EventKey.ACTION_PLAN_EXECUTION_UPDATED,
            subject_id=plan.id,
        ).count()
        >= 2
    )
