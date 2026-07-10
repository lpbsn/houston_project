from __future__ import annotations

from houston.notifications.models import Notification

PUSH_V1_EVENT_KEYS: frozenset[str] = frozenset(
    {
        Notification.EventKey.ACTION_PLAN_EXECUTION_CREATED,
        Notification.EventKey.ACTION_PLAN_EXECUTION_PENDING_VALIDATION,
        Notification.EventKey.ACTION_PLAN_EXECUTION_CANCELED,
        Notification.EventKey.ACTION_PLAN_EXECUTION_REOPENED,
        Notification.EventKey.COMMENT_MENTION_CREATED,
        Notification.EventKey.COMMENT_SIGNAL_CREATED,
        Notification.EventKey.COMMENT_ACTION_PLAN_EXECUTION_CREATED,
        Notification.EventKey.COMMENT_REPLY_CREATED,
        Notification.EventKey.SIGNAL_CREATED,
        Notification.EventKey.SIGNAL_URGENCY_CHANGED,
        Notification.EventKey.SIGNAL_PINNED,
        Notification.EventKey.SIGNAL_RESOLVED,
        Notification.EventKey.SIGNAL_CANCELED,
        Notification.EventKey.CHAT_MESSAGE_RECEIVED,
    }
)
