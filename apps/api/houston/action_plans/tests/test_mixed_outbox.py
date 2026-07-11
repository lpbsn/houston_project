from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from django.db import close_old_connections
from django.utils import timezone

from houston.action_plans.mixed_outbox_tasks import (
    MAX_ATTEMPTS,
    process_action_plan_mixed_outbox_batch,
)
from houston.action_plans.models import (
    ActionPlanMixedOutboxEntry,
    ActionPlanMixedSubmission,
)
from houston.action_plans.tests.helpers import (
    action_plan_mixed_submit_url,
    api_mixed_submit_payload,
)
from houston.notifications.models import Notification
from houston.testing.auth import auth_headers, login

pytestmark = pytest.mark.django_db


def _create_submission_with_outbox(
    *,
    owner_membership,
    staff_membership,
    manager_membership,
    catalog_action_plan,
    business_unit,
    api_client,
):
    token = login(api_client, user=owner_membership.user)
    submission_id = uuid.uuid4()
    payload = api_mixed_submit_payload(
        submission_id=submission_id,
        recurring_membership=staff_membership,
        one_shot_membership=manager_membership,
        business_unit=business_unit,
    )
    response = api_client.post(
        action_plan_mixed_submit_url(owner_membership.establishment_id, catalog_action_plan.id),
        payload,
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 201, response.json()
    submission = ActionPlanMixedSubmission.objects.get(submission_id=submission_id)
    return submission


def test_mixed_submit_creates_unique_outbox_effect_keys(
    api_client,
    owner_membership,
    staff_membership,
    manager_membership,
    catalog_action_plan,
    business_unit,
):
    submission = _create_submission_with_outbox(
        owner_membership=owner_membership,
        staff_membership=staff_membership,
        manager_membership=manager_membership,
        catalog_action_plan=catalog_action_plan,
        business_unit=business_unit,
        api_client=api_client,
    )
    entries = ActionPlanMixedOutboxEntry.objects.filter(mixed_submission=submission)
    assert entries.count() > 0
    assert entries.values_list("effect_key", flat=True).distinct().count() == entries.count()


def test_mixed_replay_does_not_create_new_outbox_entries(
    api_client,
    owner_membership,
    staff_membership,
    manager_membership,
    catalog_action_plan,
    business_unit,
):
    token = login(api_client, user=owner_membership.user)
    submission_id = uuid.uuid4()
    payload = api_mixed_submit_payload(
        submission_id=submission_id,
        recurring_membership=staff_membership,
        one_shot_membership=manager_membership,
        business_unit=business_unit,
    )
    url = action_plan_mixed_submit_url(owner_membership.establishment_id, catalog_action_plan.id)
    assert api_client.post(url, payload, format="json", **auth_headers(token)).status_code == 201
    count_after_first = ActionPlanMixedOutboxEntry.objects.count()
    assert api_client.post(url, payload, format="json", **auth_headers(token)).status_code == 200
    assert ActionPlanMixedOutboxEntry.objects.count() == count_after_first


def test_worker_reclaims_expired_lease(
    api_client,
    owner_membership,
    staff_membership,
    manager_membership,
    catalog_action_plan,
    business_unit,
):
    submission = _create_submission_with_outbox(
        owner_membership=owner_membership,
        staff_membership=staff_membership,
        manager_membership=manager_membership,
        catalog_action_plan=catalog_action_plan,
        business_unit=business_unit,
        api_client=api_client,
    )
    entry = ActionPlanMixedOutboxEntry.objects.filter(mixed_submission=submission).first()
    assert entry is not None
    entry.status = ActionPlanMixedOutboxEntry.Status.PROCESSING
    entry.lease_expires_at = timezone.now() - timedelta(minutes=1)
    entry.attempts = 1
    entry.save(update_fields=["status", "lease_expires_at", "attempts", "updated_at"])

    processed = process_action_plan_mixed_outbox_batch(batch_size=10)
    assert processed >= 1
    entry.refresh_from_db()
    assert entry.status == ActionPlanMixedOutboxEntry.Status.PROCESSED


@pytest.mark.django_db(transaction=True)
def test_concurrent_workers_create_single_notification(
    api_client,
    owner_membership,
    staff_membership,
    manager_membership,
    catalog_action_plan,
    business_unit,
):
    submission = _create_submission_with_outbox(
        owner_membership=owner_membership,
        staff_membership=staff_membership,
        manager_membership=manager_membership,
        catalog_action_plan=catalog_action_plan,
        business_unit=business_unit,
        api_client=api_client,
    )
    notification_entry = (
        ActionPlanMixedOutboxEntry.objects.filter(
            mixed_submission=submission,
            effect_type=ActionPlanMixedOutboxEntry.EffectType.NOTIFICATION,
        )
        .order_by("created_at")
        .first()
    )
    assert notification_entry is not None
    ActionPlanMixedOutboxEntry.objects.filter(mixed_submission=submission).exclude(
        id=notification_entry.id,
    ).update(status=ActionPlanMixedOutboxEntry.Status.PROCESSED, processed_at=timezone.now())
    notification_entry.status = ActionPlanMixedOutboxEntry.Status.PENDING
    notification_entry.attempts = 0
    notification_entry.available_at = timezone.now()
    notification_entry.save(
        update_fields=["status", "attempts", "available_at", "updated_at"],
    )

    def run_worker(_: int) -> None:
        close_old_connections()
        try:
            process_action_plan_mixed_outbox_batch(batch_size=1)
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(run_worker, range(2)))

    idempotency_key = notification_entry.payload["idempotency_key"]
    assert (
        Notification.objects.filter(idempotency_key=idempotency_key).count() == 1
    )
    notification_entry.refresh_from_db()
    assert notification_entry.status == ActionPlanMixedOutboxEntry.Status.PROCESSED


def test_outbox_entry_stops_retrying_after_max_attempts(
    api_client,
    owner_membership,
    staff_membership,
    manager_membership,
    catalog_action_plan,
    business_unit,
):
    submission = _create_submission_with_outbox(
        owner_membership=owner_membership,
        staff_membership=staff_membership,
        manager_membership=manager_membership,
        catalog_action_plan=catalog_action_plan,
        business_unit=business_unit,
        api_client=api_client,
    )
    entry = ActionPlanMixedOutboxEntry.objects.filter(mixed_submission=submission).first()
    assert entry is not None
    entry.effect_type = "unsupported"
    entry.status = ActionPlanMixedOutboxEntry.Status.FAILED
    entry.attempts = MAX_ATTEMPTS
    entry.available_at = timezone.now() - timedelta(minutes=1)
    entry.save(update_fields=["effect_type", "status", "attempts", "available_at", "updated_at"])

    before_attempts = entry.attempts
    process_action_plan_mixed_outbox_batch(batch_size=10)
    entry.refresh_from_db()
    assert entry.attempts == before_attempts
    assert entry.status == ActionPlanMixedOutboxEntry.Status.FAILED
