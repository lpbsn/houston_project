from __future__ import annotations

from unittest.mock import patch

import pytest
from django.db import transaction
from houston.establishments.tests.conftest import TEST_PASSWORD
from houston.observations.services import submit_observation
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
