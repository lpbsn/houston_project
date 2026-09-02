from __future__ import annotations

import logging
import uuid

from django.conf import settings
from django.db import transaction
from django.template.loader import render_to_string

from houston.establishments.models import ContentReport
from houston.establishments.resend_client import send_invitation_email_via_resend

logger = logging.getLogger(__name__)


def schedule_content_report_operator_email(*, report_id: uuid.UUID) -> None:
    transaction.on_commit(
        lambda: _enqueue_content_report_email(report_id=str(report_id)),
    )


def _enqueue_content_report_email(*, report_id: str) -> None:
    from houston.establishments.tasks import send_content_report_operator_email_task

    send_content_report_operator_email_task.delay(report_id)


def send_content_report_operator_email(*, report_id: str) -> None:
    operator_email = getattr(settings, "HOUSTON_OPERATOR_EMAIL", "") or ""
    if not settings.RESEND_API_KEY or not operator_email:
        logger.info(
            "content_report_operator_email_skipped",
            extra={"event": "content_report_operator_email_skipped", "report_id": report_id},
        )
        return

    report = ContentReport.objects.filter(id=report_id).first()
    if report is None:
        return

    context = {
        "report_id": str(report.id),
        "establishment_id": str(report.establishment_id),
        "reporter_membership_id": str(report.reporter_membership_id),
        "target_membership_id": (
            str(report.target_membership_id) if report.target_membership_id else ""
        ),
        "content_kind": report.content_kind,
        "content_id": str(report.content_id) if report.content_id else "",
        "status": report.status,
    }
    subject = f"Spore — signalement {report.id}"
    html_body = render_to_string("establishments/email/content_report.html", context)
    text_body = render_to_string("establishments/email/content_report.txt", context)
    send_invitation_email_via_resend(
        to_email=operator_email,
        from_email=settings.HOUSTON_INVITATION_EMAIL_FROM,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        idempotency_key=f"content-report/{report.id}",
    )
