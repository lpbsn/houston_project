from __future__ import annotations

MAX_CANDIDATES_PER_OBSERVATION = 5
MAX_ACTIVE_SIGNALS_CONTEXT = 20
SIGNAL_TITLE_MAX_LENGTH = 200
SIGNAL_STRUCTURED_SUMMARY_MAX_LENGTH = 2000
SIGNAL_LOCATION_TEXT_MAX_LENGTH = 255
AI_LOCATION_TEXT_MAX_LENGTH = 120
STRUCTURED_SUMMARY_SHORT_MAX_LENGTH = 280

AI_OBSERVATION_PIPELINE_SCHEMA_VERSION = "ai_observation_pipeline_v1"
AI_OBSERVATION_PIPELINE_SCHEMA_VERSION_V3 = "ai_observation_pipeline_v3"
AI_OBSERVATION_PIPELINE_PROMPT_VERSION = "ai_observation_pipeline_v2"
AI_OBSERVATION_PIPELINE_PROMPT_VERSION_V3 = "ai_observation_pipeline_v3"

# Must stay aligned with Signal.Status.OPEN and Signal.Status.IN_PROGRESS.
ACTIVE_SIGNAL_STATUSES = frozenset({"open", "in_progress"})

# Default Signal Feed visibility (excludes canceled and archived).
FEED_SIGNAL_STATUSES = frozenset({"open", "in_progress", "resolved"})
