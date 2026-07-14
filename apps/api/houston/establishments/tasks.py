from __future__ import annotations

import logging

from celery import shared_task

from houston.establishments.invitation_email import send_establishment_invitation_email
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
def send_establishment_invitation_email_task(
    self,
    invitation_id: str,
    raw_token: str,
) -> None:
    try:
        send_establishment_invitation_email(
            invitation_id=invitation_id,
            raw_token=raw_token,
        )
    except InvitationEmailTemporaryError as exc:
        logger.warning(
            "invitation_email_task_retrying",
            extra={
                "event": "invitation_email_task_retrying",
                "invitation_id": invitation_id,
                "exception_class": type(exc).__name__,
                "retry_count": self.request.retries,
            },
        )
        raise self.retry() from None
    except InvitationEmailPermanentError as exc:
        logger.error(
            "invitation_email_task_failed_permanent",
            extra={
                "event": "invitation_email_task_failed_permanent",
                "invitation_id": invitation_id,
                "exception_class": type(exc).__name__,
                "retry_count": self.request.retries,
            },
            exc_info=False,
        )
        return

    logger.info(
        "invitation_email_task_completed",
        extra={
            "event": "invitation_email_task_completed",
            "invitation_id": invitation_id,
        },
    )
