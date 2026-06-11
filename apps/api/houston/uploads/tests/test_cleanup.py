from __future__ import annotations

import logging
import uuid
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from houston.accounts.models import User
from houston.establishments.models import Establishment
from houston.organizations.models import Organization
from houston.uploads.models import TemporaryUpload
from houston.uploads.services import cleanup_expired_uploads
from houston.uploads.tasks import cleanup_expired_uploads_task

pytestmark = pytest.mark.django_db


def _create_expired_upload():
    organization = Organization.objects.create(
        name=f"Org {uuid.uuid4().hex[:6]}",
        status=Organization.Status.ACTIVE,
    )
    establishment = Establishment.objects.create(
        name="Cleanup Hotel",
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )
    user = User.objects.create_user(
        username=f"cleanup_{uuid.uuid4().hex[:8]}",
        email=f"{uuid.uuid4().hex[:8]}@example.com",
        password="secret-password-12",
        status=User.Status.ACTIVE,
    )
    upload = TemporaryUpload(
        establishment=establishment,
        uploaded_by=user,
        content_type="image/png",
        stored_extension="png",
        size_bytes=4,
        expires_at=timezone.now() - timedelta(hours=1),
    )
    upload.file.save(
        "photo.png",
        SimpleUploadedFile("photo.png", b"\x89PNG\r\n\x1a\n", content_type="image/png"),
        save=False,
    )
    upload.save()
    return upload


def test_cleanup_expired_uploads_deletes_validated_orphans():
    upload = _create_expired_upload()

    deleted_count = cleanup_expired_uploads()
    assert deleted_count == 1
    upload.refresh_from_db()
    assert upload.status == TemporaryUpload.Status.DELETED


def test_cleanup_expired_uploads_task_delegates_to_service():
    upload = _create_expired_upload()

    deleted_count = cleanup_expired_uploads_task.run()
    assert deleted_count == 1
    upload.refresh_from_db()
    assert upload.status == TemporaryUpload.Status.DELETED


def test_cleanup_expired_uploads_is_idempotent_on_second_run():
    upload = _create_expired_upload()

    assert cleanup_expired_uploads() == 1
    assert cleanup_expired_uploads() == 0
    upload.refresh_from_db()
    assert upload.status == TemporaryUpload.Status.DELETED


def test_cleanup_expired_uploads_task_double_run_is_safe():
    upload = _create_expired_upload()

    assert cleanup_expired_uploads_task.run() == 1
    assert cleanup_expired_uploads_task.run() == 0
    upload.refresh_from_db()
    assert upload.status == TemporaryUpload.Status.DELETED


def test_cleanup_expired_uploads_task_failure_logs_safe_context(caplog):
    with patch(
        "houston.uploads.tasks.cleanup_expired_uploads",
        side_effect=RuntimeError("storage unavailable"),
    ):
        with caplog.at_level(logging.ERROR, logger="houston.uploads.tasks"):
            with pytest.raises(RuntimeError, match="storage unavailable"):
                cleanup_expired_uploads_task.run()

    failure_records = [
        record
        for record in caplog.records
        if record.getMessage() == "upload_cleanup_task_failed"
    ]
    assert len(failure_records) == 1
    record = failure_records[0]
    assert record.task_name == "cleanup_expired_uploads_task"
    assert record.exception_class == "RuntimeError"
    assert "private_media" not in caplog.text
