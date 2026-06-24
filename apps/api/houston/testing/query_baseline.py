from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from django.db import connection
from django.test.utils import CaptureQueriesContext

# Fixture-scale query-count ceilings for Phase L hot endpoints.
# Measured 2026-06-11 (PostgreSQL test DB, pytest). See:
# docs/audit/db_scalability_phase_l_2026-06-11.md

# GET .../signals/feed/?view_mode=general — owner, 2 feed-visible signals
# Phase L: 11 queries; Phase E: 8 (prefetch-aware serializer + has_more without count)
SIGNAL_FEED_MAX_QUERIES_TWO_ITEMS = 8
# Observed delta when increasing feed items from 1 to 3 (flat after Phase E prefetch fix)
SIGNAL_FEED_MAX_QUERY_DELTA_ONE_TO_THREE_ITEMS = 0

# GET .../execution-feed/?view_mode=general — owner, empty feed
# Phase L: 9 queries; Phase G: 8 (has_more without dual count())
EXECUTION_FEED_EMPTY_MAX_QUERIES = 8
# GET .../execution-feed/?view_mode=personal — staff, 1 visible checklist execution
# Phase L: 13 queries; Phase G: 11 (has_more without dual count() + scoped materialization)
EXECUTION_FEED_ONE_CHECKLIST_MAX_QUERIES = 11
# GET .../execution-feed/?view_mode=general — owner, 3 active actions (post ACT-01 prefetch fix)
EXECUTION_FEED_THREE_ACTIONS_MAX_QUERIES = 9

# GET .../chat/conversations/ — 3 DMs with one message each
# Phase L: 12 queries; Phase S1: 10 (batched latest messages + single participant pass)
CHAT_CONVERSATIONS_LIST_MAX_QUERIES_THREE_ITEMS = 10
# Observed delta when increasing conversations from 1 to 3 (flat after Phase S1 batching)
CHAT_CONVERSATIONS_MAX_QUERY_DELTA_ONE_TO_THREE = 0

# GET .../conversations/{id}/messages/ — default page, 1 stored message
CHAT_MESSAGES_LIST_MAX_QUERIES = 10

# build_pipeline_input — one observation, one BU/AS, no active signals
OBSERVATION_PIPELINE_INPUT_BUILD_MAX_QUERIES = 8


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
