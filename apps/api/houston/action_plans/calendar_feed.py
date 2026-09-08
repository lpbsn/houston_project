from __future__ import annotations

from datetime import date, datetime, time, timedelta

from django.utils import timezone

from houston.action_plans.constants import CALENDAR_MAX_WINDOW_DAYS, ExecutionFeedViewMode
from houston.action_plans.exceptions import ActionPlanValidationError
from houston.action_plans.lifecycle_promotion import ensure_execution_lifecycle_for_read
from houston.action_plans.materialization import (
    materialize_visible_schedule_occurrences_in_window,
)
from houston.action_plans.selectors import (
    action_plan_execution_calendar_items_queryset,
    action_plan_execution_calendar_unplanned_queryset,
    action_plan_execution_overdue,
    annotate_action_plan_execution_feed_pins,
)
from houston.establishments.membership_scope import membership_scope_prefetch
from houston.establishments.models import EstablishmentMembership
from houston.establishments.role_constants import ADMIN_ROLES
from houston.establishments.timezone_utils import (
    establishment_local_date,
    establishment_timezone,
)


class ActionPlanExecutionCalendarWindowError(ActionPlanValidationError):
    pass


def _membership_for_calendar(
    membership: EstablishmentMembership,
) -> EstablishmentMembership:
    if membership.role in ADMIN_ROLES:
        return membership
    return (
        EstablishmentMembership.objects.filter(pk=membership.pk)
        .select_related("establishment")
        .prefetch_related(membership_scope_prefetch())
        .get()
    )


def parse_calendar_window_dates(
    *,
    from_raw: str | None,
    to_raw: str | None,
) -> tuple[date, date]:
    if not from_raw or not to_raw:
        raise ActionPlanExecutionCalendarWindowError("from and to are required.")
    try:
        from_date = date.fromisoformat(from_raw)
        to_date = date.fromisoformat(to_raw)
    except ValueError as exc:
        raise ActionPlanExecutionCalendarWindowError(
            "from and to must be ISO dates (YYYY-MM-DD)."
        ) from exc
    if from_date > to_date:
        raise ActionPlanExecutionCalendarWindowError("from must be on or before to.")
    if (to_date - from_date).days > CALENDAR_MAX_WINDOW_DAYS:
        raise ActionPlanExecutionCalendarWindowError(
            f"Calendar window cannot exceed {CALENDAR_MAX_WINDOW_DAYS} days."
        )
    return from_date, to_date


def build_action_plan_execution_calendar(
    *,
    membership: EstablishmentMembership,
    view_mode: ExecutionFeedViewMode,
    from_date: date,
    to_date: date,
) -> dict:
    membership = _membership_for_calendar(membership)
    establishment = membership.establishment
    tz = establishment_timezone(establishment)
    local_today = establishment_local_date(establishment=establishment)
    window_start = datetime.combine(from_date, time.min, tzinfo=tz)
    window_end = datetime.combine(to_date + timedelta(days=1), time.min, tzinfo=tz) - timedelta(
        microseconds=1
    )

    if to_date >= local_today:
        materialize_visible_schedule_occurrences_in_window(
            membership=membership,
            view_mode=view_mode,
            from_date=from_date,
            until_date=to_date,
        )
    ensure_execution_lifecycle_for_read(establishment_id=membership.establishment_id)

    items_qs = annotate_action_plan_execution_feed_pins(
        action_plan_execution_calendar_items_queryset(
            membership=membership,
            view_mode=view_mode,
            window_start=window_start,
            window_end=window_end,
        ),
        membership=membership,
    )
    unplanned_qs = annotate_action_plan_execution_feed_pins(
        action_plan_execution_calendar_unplanned_queryset(
            membership=membership,
            view_mode=view_mode,
        ),
        membership=membership,
    )
    as_of = timezone.now()
    items = list(items_qs)
    unplanned = list(unplanned_qs)
    return {
        "timezone": str(tz),
        "items": items,
        "unplanned": unplanned,
        "as_of": as_of,
    }
