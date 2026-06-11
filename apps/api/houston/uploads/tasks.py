from __future__ import annotations

from celery import shared_task

from houston.uploads.services import cleanup_expired_uploads


@shared_task
def cleanup_expired_uploads_task() -> int:
    return cleanup_expired_uploads()
