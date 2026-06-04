from __future__ import annotations

ACTION_TITLE_MAX_LENGTH = 200
ACTION_INSTRUCTION_MAX_LENGTH = 2000

ACTIVE_ACTION_STATUSES = frozenset(
    {
        "open",
        "in_progress",
        "pending_validation",
        "reopened",
    }
)

TERMINAL_ACTION_STATUSES = frozenset({"done", "canceled"})

EXECUTION_FEED_STATUSES = frozenset(
    {
        "open",
        "in_progress",
        "pending_validation",
        "reopened",
    }
)
