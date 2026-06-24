from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.db import transaction
from django.test import override_settings
from django.utils import timezone
from houston.establishments.tests.conftest import TEST_PASSWORD
from houston.observations.models import ObservationProcessing
from houston.observations.services import submit_observation
from houston.signals.services import recover_orphaned_observation_processing_batch
from houston.testing.factories import build_membership

pytestmark = pytest.mark.django_db(transaction=True)


def test_submit_enqueues_after_commit():
    membership = build_membership()
    membership.user.set_password(TEST_PASSWORD)
    membership.user.save(update_fields=["password"])
    with patch("houston.signals.tasks.process_observation_task.delay") as delay:
        observation = submit_observation(
            membership=membership,
            text="Valid observation text here.",
            temporary_upload_ids=[],
        )
        delay.assert_called_once_with(str(observation.id))


def test_submit_does_not_enqueue_on_transaction_rollback():
    membership = build_membership()
    membership.user.set_password(TEST_PASSWORD)
    membership.user.save(update_fields=["password"])

    with patch("houston.signals.tasks.process_observation_task.delay") as delay:
        with pytest.raises(RuntimeError, match="force rollback"):
            with transaction.atomic():
                submit_observation(
                    membership=membership,
                    text="Valid observation text here.",
                    temporary_upload_ids=[],
                )
                raise RuntimeError("force rollback")

        delay.assert_not_called()


@override_settings(HOUSTON_OBSERVATION_PROCESSING_STUCK_WARNING_SECONDS=30)
def test_enqueue_failure_leaves_queued_for_recovery():
    membership = build_membership()
    membership.user.set_password(TEST_PASSWORD)
    membership.user.save(update_fields=["password"])

    with patch("houston.signals.tasks.process_observation_task.delay") as delay:
        delay.side_effect = RuntimeError("broker unavailable")
        with pytest.raises(RuntimeError, match="broker unavailable"):
            submit_observation(
                membership=membership,
                text="Valid observation text here.",
                temporary_upload_ids=[],
            )

    observation = membership.submitted_observations.get()
    processing = observation.processing
    processing.refresh_from_db()
    assert processing.status == ObservationProcessing.Status.QUEUED
    processing.queued_at = timezone.now() - timedelta(seconds=90)
    processing.save(update_fields=["queued_at", "updated_at"])

    with patch("houston.signals.tasks.process_observation_task.delay") as recovery_delay:
        enqueued = recover_orphaned_observation_processing_batch()
        assert enqueued == 1
        recovery_delay.assert_called_once_with(str(observation.id))
