from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from django.db import close_old_connections
from django.utils import timezone

from houston.actions.services import create_action
from houston.actions.tests.conftest import build_api_membership_on_establishment
from houston.checklists.constants import EXECUTION_SOURCE_TEMPLATE
from houston.checklists.models import ChecklistExecution, ChecklistTemplate
from houston.comments.services import create_signal_comment
from houston.establishments.models import EstablishmentMembership
from houston.notifications.constants import (
    DEDUPE_WINDOW,
    build_default_dedupe_key,
    build_mention_dedupe_key,
)
from houston.notifications.exceptions import NotificationValidationError
from houston.notifications.models import Notification
from houston.notifications.services import (
    archive_notification,
    create_in_app_notification,
    mark_all_notifications_read,
    mark_notification_read,
)
from houston.testing.auth import build_api_membership
from houston.testing.taxonomy import create_signal_v3_for_membership, hotel_maintenance_setup

pytestmark = pytest.mark.django_db


def _open_action(*, owner, staff, maintenance):
    return create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Do not leak this title",
        instruction="Do not leak this instruction",
        assignee_ids=[staff.id],
        due_at=timezone.now() + timezone.timedelta(days=1),
        responsible_business_unit_id=maintenance.id,
    )


def test_create_notification_for_action_assignee():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    _, maintenance, electricite = hotel_maintenance_setup(owner.establishment)
    action = _open_action(owner=owner, staff=staff, maintenance=maintenance)

    notification = create_in_app_notification(
        establishment_id=owner.establishment_id,
        recipient_membership=staff,
        event_key=Notification.EventKey.ACTION_CREATED,
        subject_type=Notification.SubjectType.ACTION,
        subject_id=action.id,
        priority=Notification.Priority.ACTION_REQUIRED,
        actor_membership=owner,
    )

    assert notification is not None
    assert notification.title == "Nouvelle action"
    assert "Do not leak" not in notification.body
    assert action.title not in notification.body


def test_actor_exclusion_skips_self_notification():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    action = _open_action(owner=owner, staff=owner, maintenance=maintenance)

    notification = create_in_app_notification(
        establishment_id=owner.establishment_id,
        recipient_membership=owner,
        event_key=Notification.EventKey.ACTION_CREATED,
        subject_type=Notification.SubjectType.ACTION,
        subject_id=action.id,
        priority=Notification.Priority.ACTION_REQUIRED,
        actor_membership=owner,
    )

    assert notification is None


def test_actor_from_other_establishment_raises():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    outsider = build_api_membership()
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    action = _open_action(owner=owner, staff=staff, maintenance=maintenance)

    with pytest.raises(NotificationValidationError, match="Invalid actor membership."):
        create_in_app_notification(
            establishment_id=owner.establishment_id,
            recipient_membership=staff,
            event_key=Notification.EventKey.ACTION_CREATED,
            subject_type=Notification.SubjectType.ACTION,
            subject_id=action.id,
            priority=Notification.Priority.ACTION_REQUIRED,
            actor_membership=outsider,
        )


@pytest.mark.django_db(transaction=True)
def test_concurrent_create_same_dedupe_only_one_notification():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    action = _open_action(owner=owner, staff=staff, maintenance=maintenance)
    dedupe_key = build_default_dedupe_key(
        event_key=Notification.EventKey.ACTION_CREATED,
        subject_type=Notification.SubjectType.ACTION,
        subject_id=action.id,
    )

    def create_notification(_: int) -> Notification | None:
        close_old_connections()
        try:
            return create_in_app_notification(
                establishment_id=owner.establishment_id,
                recipient_membership=staff,
                event_key=Notification.EventKey.ACTION_CREATED,
                subject_type=Notification.SubjectType.ACTION,
                subject_id=action.id,
                priority=Notification.Priority.ACTION_REQUIRED,
                actor_membership=owner,
                dedupe_key=dedupe_key,
            )
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(create_notification, range(2)))

    created = [result for result in results if result is not None]
    assert len(created) == 1
    assert results.count(None) == 1
    assert (
        Notification.objects.filter(
            recipient_membership_id=staff.id,
            dedupe_key=dedupe_key,
            created_at__gte=timezone.now() - DEDUPE_WINDOW,
        ).count()
        == 1
    )


def test_default_dedupe_key_prevents_duplicate_within_window():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    action = _open_action(owner=owner, staff=staff, maintenance=maintenance)

    first = create_in_app_notification(
        establishment_id=owner.establishment_id,
        recipient_membership=staff,
        event_key=Notification.EventKey.ACTION_CREATED,
        subject_type=Notification.SubjectType.ACTION,
        subject_id=action.id,
        priority=Notification.Priority.ACTION_REQUIRED,
        actor_membership=owner,
    )
    second = create_in_app_notification(
        establishment_id=owner.establishment_id,
        recipient_membership=staff,
        event_key=Notification.EventKey.ACTION_CREATED,
        subject_type=Notification.SubjectType.ACTION,
        subject_id=action.id,
        priority=Notification.Priority.ACTION_REQUIRED,
        actor_membership=owner,
    )

    assert first is not None
    assert second is None
    assert first.dedupe_key == build_default_dedupe_key(
        event_key=Notification.EventKey.ACTION_CREATED,
        subject_type=Notification.SubjectType.ACTION,
        subject_id=action.id,
    )


def test_explicit_dedupe_key_override_dedupes_independently():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    action = _open_action(owner=owner, staff=staff, maintenance=maintenance)
    override = "custom:dedupe:key"

    first = create_in_app_notification(
        establishment_id=owner.establishment_id,
        recipient_membership=staff,
        event_key=Notification.EventKey.ACTION_CREATED,
        subject_type=Notification.SubjectType.ACTION,
        subject_id=action.id,
        priority=Notification.Priority.ACTION_REQUIRED,
        actor_membership=owner,
        dedupe_key=override,
    )
    second = create_in_app_notification(
        establishment_id=owner.establishment_id,
        recipient_membership=staff,
        event_key=Notification.EventKey.ACTION_CREATED,
        subject_type=Notification.SubjectType.ACTION,
        subject_id=action.id,
        priority=Notification.Priority.ACTION_REQUIRED,
        actor_membership=owner,
        dedupe_key=override,
    )

    assert first is not None
    assert second is None
    assert first.dedupe_key == override


def test_different_explicit_dedupe_keys_create_two_notifications():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    action = _open_action(owner=owner, staff=staff, maintenance=maintenance)
    comment_id_a = uuid.uuid4()
    comment_id_b = uuid.uuid4()

    first = create_in_app_notification(
        establishment_id=owner.establishment_id,
        recipient_membership=staff,
        event_key=Notification.EventKey.COMMENT_MENTION_CREATED,
        subject_type=Notification.SubjectType.ACTION,
        subject_id=action.id,
        priority=Notification.Priority.INFO,
        dedupe_key=build_mention_dedupe_key(
            comment_id=comment_id_a,
            mentioned_membership_id=staff.id,
        ),
        exclude_actor_if_recipient=False,
    )
    second = create_in_app_notification(
        establishment_id=owner.establishment_id,
        recipient_membership=staff,
        event_key=Notification.EventKey.COMMENT_MENTION_CREATED,
        subject_type=Notification.SubjectType.ACTION,
        subject_id=action.id,
        priority=Notification.Priority.INFO,
        dedupe_key=build_mention_dedupe_key(
            comment_id=comment_id_b,
            mentioned_membership_id=staff.id,
        ),
        exclude_actor_if_recipient=False,
    )

    assert first is not None
    assert second is not None


def test_unsupported_subject_type_skips_creation():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)

    notification = create_in_app_notification(
        establishment_id=owner.establishment_id,
        recipient_membership=owner,
        event_key=Notification.EventKey.ACTION_CREATED,
        subject_type="unsupported",
        subject_id=uuid.uuid4(),
        priority=Notification.Priority.INFO,
        exclude_actor_if_recipient=False,
    )

    assert notification is None


def test_checklist_execution_subject_recheck():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    now = timezone.now()
    template = ChecklistTemplate.objects.create(
        establishment=owner.establishment,
        created_by=owner,
        business_unit=maintenance,
        title="Secret checklist title",
        status=ChecklistTemplate.Status.ACTIVE,
    )
    execution = ChecklistExecution.objects.create(
        checklist_template=template,
        establishment=owner.establishment,
        assigned_to=staff,
        assigned_by=owner,
        business_unit=maintenance,
        template_title=template.title,
        status=ChecklistExecution.Status.ASSIGNED,
        execution_source=EXECUTION_SOURCE_TEMPLATE,
        last_activity_at=now,
    )

    notification = create_in_app_notification(
        establishment_id=owner.establishment_id,
        recipient_membership=staff,
        event_key=Notification.EventKey.CHECKLIST_EXECUTION_CREATED,
        subject_type=Notification.SubjectType.CHECKLIST_EXECUTION,
        subject_id=execution.id,
        priority=Notification.Priority.ACTION_REQUIRED,
    )

    assert notification is not None
    assert "Secret checklist title" not in notification.title
    assert "Secret checklist title" not in notification.body


def test_comment_mention_subject_recheck_uses_parent_visibility():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = hotel_maintenance_setup(owner.establishment)
    signal = create_signal_v3_for_membership(
        owner,
        affected_business_unit=hotel,
        responsible_business_unit=maintenance,
        activity_subject=electricite,
    )
    comment = create_signal_comment(
        author_membership=owner,
        signal=signal,
        body="Secret comment body should never appear",
        mentioned_membership_ids=[staff.id],
    )

    notification = create_in_app_notification(
        establishment_id=owner.establishment_id,
        recipient_membership=staff,
        event_key=Notification.EventKey.COMMENT_MENTION_CREATED,
        subject_type=Notification.SubjectType.COMMENT,
        subject_id=comment.id,
        priority=Notification.Priority.INFO,
        actor_membership=owner,
        dedupe_key=build_mention_dedupe_key(
            comment_id=comment.id,
            mentioned_membership_id=staff.id,
        ),
    )

    assert notification is not None
    assert "Secret comment body" not in notification.body


def test_mark_read_and_archive_idempotent():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    from houston.notifications.tests.conftest import create_test_notification

    notification = create_test_notification(recipient=owner)

    read_once = mark_notification_read(membership=owner, notification_id=notification.id)
    read_twice = mark_notification_read(membership=owner, notification_id=notification.id)
    assert read_once is not None
    assert read_twice is not None
    assert read_twice.status == Notification.Status.READ
    assert read_twice.read_at is not None

    archived_once = archive_notification(membership=owner, notification_id=notification.id)
    archived_twice = archive_notification(membership=owner, notification_id=notification.id)
    assert archived_once is not None
    assert archived_twice is not None
    assert archived_twice.status == Notification.Status.ARCHIVED
    assert archived_twice.archived_at is not None


def test_archive_unread_sets_read_at_and_removes_from_unread_count():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    from houston.notifications.selectors import count_unread_notifications
    from houston.notifications.tests.conftest import create_test_notification

    notification = create_test_notification(
        recipient=owner,
        status=Notification.Status.UNREAD,
    )
    assert count_unread_notifications(membership=owner) == 1

    archived = archive_notification(membership=owner, notification_id=notification.id)
    assert archived is not None
    assert archived.read_at is not None
    assert archived.archived_at is not None
    assert count_unread_notifications(membership=owner) == 0


def test_mark_all_read_scoped_to_recipient():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    other = build_api_membership()
    from houston.notifications.tests.conftest import create_test_notification

    create_test_notification(recipient=owner, status=Notification.Status.UNREAD)
    create_test_notification(recipient=owner, status=Notification.Status.UNREAD)
    create_test_notification(recipient=other, status=Notification.Status.UNREAD)

    updated = mark_all_notifications_read(
        membership=owner,
        establishment_id=owner.establishment_id,
    )
    assert updated == 2
    assert Notification.objects.filter(
        recipient_membership=owner,
        status=Notification.Status.UNREAD,
    ).count() == 0
    assert Notification.objects.filter(
        recipient_membership=other,
        status=Notification.Status.UNREAD,
    ).count() == 1
