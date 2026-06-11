from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from django.db import connection
from django.test.utils import CaptureQueriesContext

# Fixture-scale query-count ceilings for Phase L hot endpoints.
# Measured 2026-06-11 (PostgreSQL test DB, pytest). See:
# docs/audit/db_scalability_phase_l_2026-06-11.md

# GET .../signals/feed/?view_mode=general — owner, 2 feed-visible signals
SIGNAL_FEED_MAX_QUERIES_TWO_ITEMS = 11
# Observed delta when increasing feed items from 1 to 3 (serializer partial N+1)
SIGNAL_FEED_MAX_QUERY_DELTA_ONE_TO_THREE_ITEMS = 2

# GET .../execution-feed/?view_mode=general — owner, empty feed
EXECUTION_FEED_EMPTY_MAX_QUERIES = 9
# GET .../execution-feed/?view_mode=personal — staff, 1 visible checklist execution
EXECUTION_FEED_ONE_CHECKLIST_MAX_QUERIES = 13

# GET .../chat/conversations/ — 3 DMs with one message each
CHAT_CONVERSATIONS_LIST_MAX_QUERIES_THREE_ITEMS = 12
# Observed delta when increasing conversations from 1 to 3 (latest-message N+1)
CHAT_CONVERSATIONS_MAX_QUERY_DELTA_ONE_TO_THREE = 2

# GET .../conversations/{id}/messages/ — default page, 1 stored message
CHAT_MESSAGES_LIST_MAX_QUERIES = 10


@contextmanager
def capture_queries() -> Iterator[CaptureQueriesContext]:
    with CaptureQueriesContext(connection) as context:
        yield context


def assert_query_count_at_most(
    context: CaptureQueriesContext,
    *,
    max_queries: int,
    label: str,
) -> int:
    count = len(context.captured_queries)
    assert count <= max_queries, (
        f"{label}: expected at most {max_queries} queries, got {count}"
    )
    return count
