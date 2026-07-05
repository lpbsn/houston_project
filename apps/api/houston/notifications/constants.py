from __future__ import annotations

import uuid
from datetime import timedelta

NOTIFICATION_TITLE_MAX_LENGTH = 120
NOTIFICATION_BODY_MAX_LENGTH = 280
DEDUPE_KEY_MAX_LENGTH = 255

DEDUPE_WINDOW = timedelta(minutes=5)

MENTION_DEDUPE_KEY_TEMPLATE = "comment.mention.created:{comment_id}:{mentioned_membership_id}"

LOT1_EVENT_KEYS: frozenset[str] = frozenset(
    {
        "action_plan.execution.created",
        "action_plan.execution.pending_validation",
        "action_plan.execution.canceled",
        "action_plan.execution.reopened",
        "comment.mention.created",
        "signal.created",
        "signal.urgency_changed",
        "signal.pinned",
        "signal.resolved",
        "signal.canceled",
    }
)

# Generic copy only — never inject subject title, comment body, or observation text.
NOTIFICATION_COPY: dict[str, tuple[str, str]] = {
    "action_plan.execution.created": (
        "Nouveau plan d'action",
        "Une exécution de plan d'action vous a été assignée.",
    ),
    "action_plan.execution.pending_validation": (
        "Plan d'action à valider",
        "Une exécution de plan d'action attend votre validation.",
    ),
    "action_plan.execution.canceled": (
        "Plan d'action annulé",
        "Une exécution de plan d'action a été annulée.",
    ),
    "action_plan.execution.reopened": (
        "Plan d'action rouvert",
        "Une exécution de plan d'action a été rouverte.",
    ),
    "comment.mention.created": (
        "Mention",
        "Vous avez été mentionné dans un commentaire.",
    ),
    "signal.created": (
        "Nouveau signal",
        "Un signal a été créé sur votre pôle.",
    ),
    "signal.urgency_changed": (
        "Signal urgent",
        "Un signal est passé en urgence élevée.",
    ),
    "signal.pinned": (
        "Signal épinglé",
        "Un signal a été épinglé.",
    ),
    "signal.resolved": (
        "Signal résolu",
        "Un signal a été résolu.",
    ),
    "signal.canceled": (
        "Signal annulé",
        "Un signal a été annulé.",
    ),
}

DEFAULT_ACTOR_DISPLAY_NAME = "Quelqu'un"

INVALID_STATUS_FILTER_ERROR_DETAIL = "Filtre de statut invalide."
INVALID_PAGE_SIZE_ERROR_DETAIL = "page_size must be between 1 and 50."
INVALID_CURSOR_ERROR_DETAIL = "Invalid cursor."
NOTIFICATION_NOT_FOUND_ERROR_DETAIL = "Not found."


def build_default_dedupe_key(
    *,
    event_key: str,
    subject_type: str,
    subject_id: uuid.UUID,
) -> str:
    return f"{event_key}:{subject_type}:{subject_id}"


def build_mention_dedupe_key(
    *,
    comment_id: uuid.UUID,
    mentioned_membership_id: uuid.UUID,
) -> str:
    return MENTION_DEDUPE_KEY_TEMPLATE.format(
        comment_id=comment_id,
        mentioned_membership_id=mentioned_membership_id,
    )


def render_notification_copy(
    event_key: str,
    *,
    actor_display_name: str | None = None,
) -> tuple[str, str]:
    title_template, body_template = NOTIFICATION_COPY[event_key]
    if "{actor_display_name}" in body_template:
        display_name = actor_display_name or DEFAULT_ACTOR_DISPLAY_NAME
        body = body_template.format(actor_display_name=display_name)
    else:
        body = body_template
    return title_template, body
