from __future__ import annotations

import base64
import uuid
from datetime import datetime

from django.db.models import Q, QuerySet
from django.utils.dateparse import parse_datetime

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 50


class PlatformCursorError(Exception):
    def __init__(self, detail: str = "Invalid cursor.") -> None:
        self.detail = detail
        super().__init__(detail)


def encode_created_at_cursor(*, created_at: datetime, object_id: uuid.UUID) -> str:
    raw = f"{created_at.isoformat()}|{object_id}"
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")


def decode_created_at_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
        created_at_raw, object_id_raw = raw.split("|", 1)
        created_at = parse_datetime(created_at_raw)
        object_id = uuid.UUID(object_id_raw)
    except (ValueError, TypeError, UnicodeDecodeError) as exc:
        raise PlatformCursorError from exc
    if created_at is None:
        raise PlatformCursorError
    return created_at, object_id


def apply_created_at_desc_cursor(queryset: QuerySet, *, cursor: str | None) -> QuerySet:
    if not cursor:
        return queryset
    created_at, object_id = decode_created_at_cursor(cursor)
    return queryset.filter(
        Q(created_at__lt=created_at) | Q(created_at=created_at, id__lt=object_id)
    )


def parse_page_size(raw) -> int:
    try:
        size = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_PAGE_SIZE
    return max(1, min(size, MAX_PAGE_SIZE))
