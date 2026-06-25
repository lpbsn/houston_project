from __future__ import annotations

import logging
import uuid

import pytest
from django.db import transaction

from houston.notifications.scheduling import _run_notification_after_commit

pytestmark = pytest.mark.django_db(transaction=True)

LOGGER_NAME = "houston.notifications.scheduling"


def test_notification_deliver_failure_logs_on_commit(caplog: pytest.LogCaptureFixture) -> None:
    subject_id = uuid.uuid4()

    def deliver() -> None:
        raise RuntimeError("simulated notification deliver failure")

    with caplog.at_level(logging.ERROR, logger=LOGGER_NAME):
        with transaction.atomic():
            _run_notification_after_commit(
                deliver=deliver,
                event_key="action.created",
                subject_type="action",
                subject_id=subject_id,
            )

    assert any(
        "Failed to create in-app notification after business commit" in record.getMessage()
        for record in caplog.records
    )
    failure_record = next(
        record
        for record in caplog.records
        if "Failed to create in-app notification after business commit" in record.getMessage()
    )
    assert failure_record.event_key == "action.created"
    assert failure_record.subject_type == "action"
    assert failure_record.subject_id == str(subject_id)
    assert failure_record.exc_info is not None
