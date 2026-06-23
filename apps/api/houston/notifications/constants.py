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
        "action.created",
        "action.reassigned",
        "action.pending_validation",
        "action.reopened",
        "action.canceled",
        "checklist.execution.created",
        "checklist.execution.canceled",
        "comment.mention.created",
    }
)

# Generic copy only — never inject subject title, comment body, or observation text.
NOTIFICATION_COPY: dict[str, tuple[str, str]] = {
    "action.created": (
        "Nouvelle action",
        "Une action vous a été assignée.",
    ),
    "action.reassigned": (
        "Action réassignée",
        "Une action a été réassignée.",
    ),
    "action.pending_validation": (
        "Action à valider",
        "Une action attend votre validation.",
    ),
    "action.reopened": (
        "Action rouverte",
        "Une action a été rouverte.",
    ),
    "action.canceled": (
        "Action annulée",
        "Une action a été annulée.",
    ),
    "checklist.execution.created": (
        "Checklist assignée",
        "Une exécution de checklist vous a été assignée.",
    ),
    "checklist.execution.canceled": (
        "Checklist annulée",
        "Une exécution de checklist a été annulée.",
    ),
    "comment.mention.created": (
        "Mention",
        "Vous avez été mentionné dans un commentaire.",
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


def build_action_reassigned_dedupe_key(
    *,
    action_id: uuid.UUID,
    reassignment_id: uuid.UUID,
) -> str:
    return f"action.reassigned:action:{action_id}:{reassignment_id}"


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
