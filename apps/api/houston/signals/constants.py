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

# System transition eligibility (service terminal transition + AP sync reopen/auto-resolve).
# interesting excluded.
CANCEL_RESOLVE_SIGNAL_STATUSES = frozenset({"open", "in_progress"})

# Manual cancel / resolve API + permission_hints only (EVO-SIG-03).
# in_progress must be resolved via action plans, not manual commands.
MANUAL_CANCEL_RESOLVE_SIGNAL_STATUSES = frozenset({"open"})

SIGNAL_IN_PROGRESS_MANUAL_RESOLVE_DETAIL = (
    "Signal in progress must be resolved through its action plans."
)
SIGNAL_IN_PROGRESS_MANUAL_CANCEL_DETAIL = (
    "Signal in progress cannot be canceled manually; cancel via its action plans."
)

# Default Signal Feed visibility (excludes archived).
FEED_SIGNAL_STATUSES = frozenset(
    {"open", "in_progress", "interesting", "resolved", "canceled"}
)

SIGNAL_RESOLUTION_REQUEST_COMMENT_MAX_LENGTH = 2000

SIGNAL_RESOLUTION_NO_MANAGER_REVIEWER_DETAIL = (
    "Aucun manager actif ne couvre le pôle responsable de cette observation."
)
SIGNAL_RESOLUTION_NO_DIRECTOR_REVIEWER_DETAIL = (
    "Aucun director actif n'est disponible pour valider cette demande."
)
SIGNAL_RESOLUTION_PENDING_EXISTS_DETAIL = (
    "Une demande de résolution est déjà en attente pour cette observation."
)
SIGNAL_RESOLUTION_BLOCKING_EXECUTION_DETAIL = (
    "Une exécution liée bloque la demande de résolution."
)
SIGNAL_RESOLUTION_NOT_OPEN_DETAIL = (
    "Seules les observations ouvertes peuvent faire l'objet d'une demande de résolution."
)
SIGNAL_RESOLUTION_NO_RESPONSIBLE_POLE_DETAIL = (
    "L'observation doit avoir un pôle responsable pour demander la résolution."
)
SIGNAL_RESOLUTION_REQUESTER_ENGAGED_DETAIL = (
    "Vous avez une demande de résolution en attente ; annulez-la avant de résoudre "
    "directement, ou attendez la décision du reviewer."
)
SIGNAL_RESOLUTION_NOT_PENDING_DETAIL = "Cette demande de résolution n'est plus en attente."
SIGNAL_RESOLUTION_REVIEWER_INELIGIBLE_DETAIL = (
    "Vous n'êtes plus éligible pour traiter cette demande de résolution."
)
