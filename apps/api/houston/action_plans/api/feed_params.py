from __future__ import annotations

from rest_framework import status
from rest_framework.response import Response

from houston.action_plans.constants import EXECUTION_FEED_CATEGORIES

DEFAULT_FEED_PAGE_SIZE = 25
MAX_FEED_PAGE_SIZE = 50


def parse_feed_page_size(raw: str | None) -> int:
    if raw is None or raw == "":
        return DEFAULT_FEED_PAGE_SIZE
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_FEED_PAGE_SIZE
    return min(max(value, 1), MAX_FEED_PAGE_SIZE)


def parse_execution_feed_category(raw: str | None):
    if raw is None or raw.strip() == "":
        return "all", None
    category = raw.strip().lower()
    if category not in EXECUTION_FEED_CATEGORIES:
        return None, Response(
            {
                "code": "validation_error",
                "detail": (
                    "category must be all, pending_validation, overdue, "
                    "in_progress, done or canceled."
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    return category, None
