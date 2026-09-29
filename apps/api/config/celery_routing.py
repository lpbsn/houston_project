from __future__ import annotations

from kombu import Exchange, Queue

QUEUE_AI_INTERACTIVE = "ai_interactive"
QUEUE_OPERATIONAL = "operational"
QUEUE_AI_BACKGROUND = "ai_background"
QUEUE_MAINTENANCE = "maintenance"

WORKER_QUEUES = {
    "ai_interactive": (QUEUE_AI_INTERACTIVE,),
    "operational": (QUEUE_OPERATIONAL,),
    "background": (QUEUE_AI_BACKGROUND, QUEUE_MAINTENANCE),
}


def _durable_queue(name: str) -> Queue:
    exchange = Exchange(name, type="direct", durable=True)
    return Queue(name, exchange=exchange, routing_key=name, durable=True)


CELERY_TASK_QUEUES = (
    _durable_queue(QUEUE_AI_INTERACTIVE),
    _durable_queue(QUEUE_OPERATIONAL),
    _durable_queue(QUEUE_AI_BACKGROUND),
    _durable_queue(QUEUE_MAINTENANCE),
)

CELERY_TASK_ROUTES = {
    "houston.signals.tasks.process_observation_task": {"queue": QUEUE_AI_INTERACTIVE},
    "houston.signals.tasks.recover_stuck_observation_processing_task": {
        "queue": QUEUE_OPERATIONAL
    },
    "houston.analytics.tasks.classify_signal_pattern_task": {"queue": QUEUE_AI_BACKGROUND},
    "houston.analytics.tasks.recover_due_signal_pattern_classifications_task": {
        "queue": QUEUE_OPERATIONAL
    },
    "houston.action_plans.tasks.materialize_action_plan_schedules_horizon_task": {
        "queue": QUEUE_OPERATIONAL
    },
    "houston.action_plans.tasks.promote_scheduled_action_plan_executions_task": {
        "queue": QUEUE_OPERATIONAL
    },
    "houston.action_plans.planning_outbox_tasks.process_action_plan_planning_outbox_batch_task": {
        "queue": QUEUE_OPERATIONAL
    },
    "houston.notifications.push.tasks.send_push_for_notification_task": {
        "queue": QUEUE_OPERATIONAL
    },
    "houston.accounts.tasks.send_email_change_email_task": {"queue": QUEUE_OPERATIONAL},
    "houston.accounts.tasks.send_password_reset_email_task": {"queue": QUEUE_OPERATIONAL},
    "houston.establishments.tasks.send_establishment_invitation_email_task": {
        "queue": QUEUE_OPERATIONAL
    },
    "houston.establishments.tasks.send_content_report_operator_email_task": {
        "queue": QUEUE_MAINTENANCE
    },
    "houston.chat.tasks.purge_chat_messages_task": {"queue": QUEUE_MAINTENANCE},
    "houston.chat.tasks.cleanup_chat_upload_orphans_task": {"queue": QUEUE_MAINTENANCE},
    "houston.chat.tasks.generate_chat_upload_thumbnail_task": {"queue": QUEUE_MAINTENANCE},
    "houston.comments.tasks.cleanup_action_plan_comment_media_task": {
        "queue": QUEUE_MAINTENANCE
    },
    "houston.comments.tasks.generate_action_plan_comment_upload_thumbnail_task": {
        "queue": QUEUE_MAINTENANCE
    },
    "houston.uploads.tasks.cleanup_expired_uploads_task": {"queue": QUEUE_MAINTENANCE},
    "houston.gamification.tasks.rollover_gamification_seasons_task": {
        "queue": QUEUE_MAINTENANCE
    },
}
