from __future__ import annotations

import logging

from celery import shared_task

from houston.accounts.email_change_email import send_email_change_confirmation_email
from houston.establishments.resend_client import (
    InvitationEmailPermanentError,
    InvitationEmailTemporaryError,
)

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    ignore_result=True,
    max_retries=3,
    default_retry_delay=30,
)
def send_email_change_email_task(self, change_id: str, raw_token: str) -> None:
    try:
        send_email_change_confirmation_email(change_id=change_id, raw_token=raw_token)
    except InvitationEmailTemporaryError as exc:
        logger.warning(
            "email_change_email_task_retrying",
            extra={
                "event": "email_change_email_task_retrying",
                "email_change_id": change_id,
                "exception_class": type(exc).__name__,
                "retry_count": self.request.retries,
            },
        )
        raise self.retry() from None
    except InvitationEmailPermanentError as exc:
        logger.error(
            "email_change_email_task_failed_permanent",
            extra={
                "event": "email_change_email_task_failed_permanent",
                "email_change_id": change_id,
                "exception_class": type(exc).__name__,
                "retry_count": self.request.retries,
            },
            exc_info=False,
        )
        return

    logger.info(
        "email_change_email_task_completed",
        extra={
            "event": "email_change_email_task_completed",
            "email_change_id": change_id,
        },
    )
