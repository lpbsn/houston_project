"""Documents are a permission-filtered index of existing plan attachments, never copies."""

from datetime import timedelta

from django.db.models import F, Q
from django.utils import timezone

from houston.action_plans.models import ActionPlanExecution
from houston.action_plans.selectors import action_plan_execution_feed_queryset
from houston.comments.api.serializers import serialize_action_plan_comment_attachment
from houston.comments.models import ActionPlanCommentAttachment
from houston.comments.upload_services import _retention_days
from houston.signals.record_selectors import linked_executions, record_queryset


def record_documents(*, actor, record, offset=0, query=""):
    allowed = action_plan_execution_feed_queryset(membership=actor, view_mode="general")
    if record.is_project:
        visible_children = (
            record_queryset(actor)
            .filter(
                Q(pk=record.id)
                | Q(parent_project_id=record.id)
                | Q(parent_project__parent_project_id=record.id)
            )
            .values("id")
        )
        executions = (
            ActionPlanExecution.objects.filter(establishment_id=actor.establishment_id)
            .filter(
                Q(source_signal_id__in=visible_children)
                | Q(record_links__signal_id__in=visible_children)
            )
            .distinct()
        )
    else:
        executions = linked_executions(record)
    executions = executions.filter(pk__in=allowed.values("pk"))
    now = timezone.now()
    # Match the owning attachment preview/purge policy, including closed plans.
    executions = executions.exclude(status="canceled").filter(
        ~Q(status="done")
        | Q(validated_at__gt=now - timedelta(days=_retention_days()))
        | Q(validated_at__isnull=True, marked_done_at__gt=now - timedelta(days=_retention_days()))
    )
    rows = ActionPlanCommentAttachment.objects.filter(
        action_plan_execution_id__in=executions.values("id"),
        comment__establishment_id=actor.establishment_id,
        upload__establishment_id=actor.establishment_id,
        upload__status="linked",
        comment__action_plan_execution_id=F("action_plan_execution_id"),
        upload__action_plan_execution_id=F("action_plan_execution_id"),
    ).select_related("upload", "comment__author_membership__user", "action_plan_execution")
    if query:
        rows = rows.filter(original_filename__icontains=query[:100])
    page = list(rows.order_by("-created_at", "-id")[offset : offset + 31])
    return {
        "items": [
            {
                **serialize_action_plan_comment_attachment(row, viewer_membership_id=actor.id),
                "execution_id": row.action_plan_execution_id,
                "execution_title": row.action_plan_execution.title,
            }
            for row in page[:30]
        ],
        "next_offset": offset + 30 if len(page) > 30 else None,
    }
