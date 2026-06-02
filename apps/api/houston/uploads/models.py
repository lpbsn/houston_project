from __future__ import annotations

from django.db import models

from houston.core.models import BaseModel
from houston.uploads.private_storage import get_private_media_storage


def temporary_upload_path(instance: TemporaryUpload, filename: str) -> str:
    extension = instance.stored_extension or "bin"
    return (
        f"establishments/{instance.establishment_id}/temporary/"
        f"{instance.id}.{extension}"
    )


class TemporaryUpload(BaseModel):
    class Status(models.TextChoices):
        VALIDATED = "validated", "Validated"
        LINKED = "linked", "Linked"
        DELETED = "deleted", "Deleted"

    establishment = models.ForeignKey(
        "establishments.Establishment",
        on_delete=models.CASCADE,
        related_name="temporary_uploads",
    )
    uploaded_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="temporary_uploads",
    )
    file = models.FileField(
        upload_to=temporary_upload_path,
        storage=get_private_media_storage,
        max_length=512,
    )
    content_type = models.CharField(max_length=120)
    stored_extension = models.CharField(max_length=16)
    size_bytes = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.VALIDATED,
    )
    expires_at = models.DateTimeField()
    linked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["establishment", "status", "expires_at"],
                name="tmp_upload_est_status_exp_idx",
            ),
            models.Index(fields=["uploaded_by"], name="tmp_upload_user_idx"),
        ]

    def __str__(self) -> str:
        return f"TemporaryUpload {self.id} [{self.status}]"
