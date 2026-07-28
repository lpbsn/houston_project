from __future__ import annotations

MAX_CANDIDATES_PER_OBSERVATION = 5
SIGNAL_TITLE_MAX_LENGTH = 200
SIGNAL_STRUCTURED_SUMMARY_MAX_LENGTH = 2000
SIGNAL_LOCATION_TEXT_MAX_LENGTH = 255
AI_LOCATION_TEXT_MAX_LENGTH = 120
AI_ISSUE_FOCUS_MAX_LENGTH = 80
AI_CANONICAL_OBJECT_MAX_LENGTH = 255
AI_INFORMATION_TYPE_MAX_LENGTH = 64
STRUCTURED_SUMMARY_SHORT_MAX_LENGTH = 280

AI_OBSERVATION_PIPELINE_SCHEMA_VERSION = "ai_observation_pipeline_v6"
AI_OBSERVATION_PIPELINE_PROMPT_VERSION = "ai_observation_pipeline_v6_2"

AI_SIGNAL_KIND_VALUES = ("actionable", "informational")
AI_EXPECTED_ACTION_VALUES = (
    "clean_secure",
    "repair",
    "replenish",
    "inspect",
    "coordinate",
    "assist",
    "inform",
    "monitor",
    "safety_response",
)

# Must stay aligned with Signal.Status.OPEN, IN_PROGRESS, and INTERESTING.
# Aggregation targets, uniqueness constraint, linked action-plan creation.
ACTIVE_SIGNAL_STATUSES = frozenset({"open", "in_progress", "interesting"})

# Cancel / resolve commands only (interesting excluded).
CANCEL_RESOLVE_SIGNAL_STATUSES = frozenset({"open", "in_progress"})

# Default Signal Feed visibility (excludes archived).
FEED_SIGNAL_STATUSES = frozenset(
    {"open", "in_progress", "interesting", "resolved", "canceled"}
)
