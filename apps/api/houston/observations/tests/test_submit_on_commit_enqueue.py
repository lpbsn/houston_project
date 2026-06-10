from __future__ import annotations

from unittest.mock import patch

import pytest
from houston.establishments.tests.conftest import TEST_PASSWORD
from houston.observations.services import submit_observation
from houston.testing.factories import build_membership

pytestmark = pytest.mark.django_db(transaction=True)


def test_submit_enqueues_after_commit():
    membership = build_membership()
    membership.user.set_password(TEST_PASSWORD)
    membership.user.save(update_fields=["password"])
    with patch("houston.observations.services._enqueue_observation_processing") as enqueue:
        submit_observation(
            membership=membership,
            text="Valid observation text here.",
            temporary_upload_ids=[],
        )
        enqueue.assert_called_once()
