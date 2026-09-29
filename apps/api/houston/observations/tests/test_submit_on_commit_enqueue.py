from __future__ import annotations

import time
import uuid
from unittest.mock import patch

import pytest
from django.db import transaction
from django.test import override_settings
from houston.establishments.models import EstablishmentMembership
from houston.establishments.tests.conftest import TEST_PASSWORD
from houston.observations.exceptions import ObservationSubmissionConflictError
from houston.observations.models import Observation, ObservationProcessing
from houston.observations.services import submit_observation
from houston.realtime.groups import establishment_group_name, membership_group_name
from houston.signals.services import recover_orphaned_observation_processing_batch
from houston.testing.auth import login
from houston.testing.factories import (
    build_membership,
    create_establishment,
    create_membership,
    create_user,
)
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db(transaction=True)


def _submit(membership, *, text="Valid observation text here.", client_submission_id=None):
    return submit_observation(
        membership=membership,
        text=text,
        temporary_upload_ids=[],
        client_submission_id=client_submission_id or uuid.uuid4(),
    )


def test_submit_enqueues_after_commit():
    membership = build_membership()
    membership.user.set_password(TEST_PASSWORD)
    membership.user.save(update_fields=["password"])
    with patch(
        "houston.core.celery_publish.publish_celery_task",
        return_value=True,
    ) as publish:
        observation = _submit(membership)
        publish.assert_called_once()
        assert publish.call_args.kwargs["args"] == (str(observation.id),)
    observation.processing.refresh_from_db()
    assert observation.processing.published_at is not None


def test_submit_does_not_enqueue_on_transaction_rollback():
    membership = build_membership()
    membership.user.set_password(TEST_PASSWORD)
    membership.user.save(update_fields=["password"])

    with patch(
        "houston.core.celery_publish.publish_celery_task",
        return_value=True,
    ) as publish:
        with pytest.raises(RuntimeError, match="force rollback"):
            with transaction.atomic():
                _submit(membership)
                raise RuntimeError("force rollback")

        publish.assert_not_called()


@override_settings(HOUSTON_OBSERVATION_PROCESSING_STUCK_WARNING_SECONDS=30)
def test_enqueue_failure_leaves_queued_for_recovery():
    membership = build_membership()
    membership.user.set_password(TEST_PASSWORD)
    membership.user.save(update_fields=["password"])

    with patch(
        "houston.core.celery_publish.publish_celery_task",
        return_value=False,
    ):
        observation = _submit(membership)

    processing = observation.processing
    processing.refresh_from_db()
    assert processing.status == ObservationProcessing.Status.QUEUED
    assert processing.published_at is None

    with patch(
        "houston.core.celery_publish.publish_celery_task",
        return_value=True,
    ) as recovery_publish:
        enqueued = recover_orphaned_observation_processing_batch()
        assert enqueued == 1
        recovery_publish.assert_called_once()
        assert recovery_publish.call_args.kwargs["args"] == (str(observation.id),)


def test_same_submission_key_returns_existing_observation():
    membership = build_membership()
    client_submission_id = uuid.uuid4()
    with patch("houston.core.celery_publish.publish_celery_task", return_value=True) as publish:
        first = _submit(membership, client_submission_id=client_submission_id)
        second = _submit(membership, client_submission_id=client_submission_id)
    assert first.id == second.id
    assert Observation.objects.filter(submitted_by_membership=membership).count() == 1
    publish.assert_called_once()


def test_reused_submission_key_with_different_text_conflicts():
    membership = build_membership()
    client_submission_id = uuid.uuid4()
    with patch("houston.core.celery_publish.publish_celery_task", return_value=True):
        _submit(membership, client_submission_id=client_submission_id)
        with pytest.raises(ObservationSubmissionConflictError) as caught:
            _submit(
                membership,
                text="A different observation command.",
                client_submission_id=client_submission_id,
            )
    assert caught.value.error_code == "conflict_error"


@pytest.mark.django_db(transaction=True)
@override_settings(HOUSTON_CELERY_PUBLISH_TIMEOUT_SECONDS=1)
def test_api_submit_returns_201_when_publish_hangs():
    establishment = create_establishment(name="Observation Hotel")
    staff = create_user(username="obs_publish_hang")
    create_membership(
        establishment=establishment,
        user=staff,
        role=EstablishmentMembership.Role.STAFF,
    )
    api_client = APIClient(enforce_csrf_checks=True)
    token = login(api_client, user=staff)

    def _hang(*_args, **_kwargs):
        time.sleep(30)

    started = time.monotonic()
    with patch(
        "houston.signals.tasks.process_observation_task.apply_async",
        side_effect=_hang,
    ):
        response = api_client.post(
            f"/api/v1/establishments/{establishment.id}/observations/",
            {
                "text": "Observation persistée malgré un publish qui ne confirme pas.",
                "temporary_upload_ids": [],
                "client_submission_id": str(uuid.uuid4()),
            },
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
    elapsed = time.monotonic() - started

    assert response.status_code == 201
    assert elapsed < 3
    assert Observation.objects.filter(establishment=establishment).count() == 1
    observation = Observation.objects.get(id=response.json()["id"])
    assert observation.processing.published_at is None
    assert observation.processing.status == ObservationProcessing.Status.QUEUED


def test_submit_invalidates_submitter_membership_only():
    membership = build_membership()
    peer = create_membership(
        establishment=membership.establishment,
        user=create_user(username=f"peer_{uuid.uuid4().hex[:8]}"),
        role=EstablishmentMembership.Role.STAFF,
    )
    with (
        patch("houston.core.celery_publish.publish_celery_task", return_value=True),
        patch("houston.realtime.broadcast._send_to_group") as mock_send,
    ):
        observation = _submit(membership)

    assert mock_send.call_count == 1
    call = mock_send.call_args.kwargs
    assert call["group_name"] == membership_group_name(
        establishment_id=membership.establishment_id,
        membership_id=membership.id,
    )
    assert call["group_name"] != establishment_group_name(
        establishment_id=membership.establishment_id,
    )
    assert call["group_name"] != membership_group_name(
        establishment_id=membership.establishment_id,
        membership_id=peer.id,
    )
    assert call["payload"]["subject_type"] == "observation_processing"
    assert call["payload"]["reason"] == "observation_processing.updated"
    assert call["payload"]["entity_id"] == str(observation.id)
    assert "raw_text" not in call["payload"]


def test_replayed_submit_does_not_invalidate_again():
    membership = build_membership()
    client_submission_id = uuid.uuid4()
    with (
        patch("houston.core.celery_publish.publish_celery_task", return_value=True),
        patch("houston.realtime.broadcast.notify_membership_invalidation") as mock_notify,
    ):
        _submit(membership, client_submission_id=client_submission_id)
        _submit(membership, client_submission_id=client_submission_id)

    mock_notify.assert_called_once()


def test_submit_rollback_does_not_invalidate():
    membership = build_membership()
    with (
        patch("houston.core.celery_publish.publish_celery_task", return_value=True),
        patch("houston.realtime.broadcast.notify_membership_invalidation") as mock_notify,
    ):
        with pytest.raises(RuntimeError, match="force rollback"):
            with transaction.atomic():
                _submit(membership)
                raise RuntimeError("force rollback")

    mock_notify.assert_not_called()


def test_api_submit_returns_201_when_channels_send_fails():
    establishment = create_establishment(name="Observation Hotel")
    staff = create_user(username="obs_channels_down")
    create_membership(
        establishment=establishment,
        user=staff,
        role=EstablishmentMembership.Role.STAFF,
    )
    api_client = APIClient(enforce_csrf_checks=True)
    token = login(api_client, user=staff)

    with (
        patch("houston.core.celery_publish.publish_celery_task", return_value=True),
        patch(
            "houston.realtime.broadcast.async_to_sync",
            side_effect=RuntimeError("channels down"),
        ),
    ):
        response = api_client.post(
            f"/api/v1/establishments/{establishment.id}/observations/",
            {
                "text": "Observation persistée malgré un échec Channels.",
                "temporary_upload_ids": [],
                "client_submission_id": str(uuid.uuid4()),
            },
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

    assert response.status_code == 201
    observation = Observation.objects.get(id=response.json()["id"])
    assert observation.processing.status == ObservationProcessing.Status.QUEUED
    assert observation.processing.published_at is not None
