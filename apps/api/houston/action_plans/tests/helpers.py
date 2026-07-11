from __future__ import annotations

import uuid
from datetime import time

from django.utils import timezone

from houston.action_plans.constants import CATALOG_STATUS_ACTIVE
from houston.action_plans.models import ActionPlan, ActionPlanTask
from houston.signals.models import Signal
from houston.testing.taxonomy import create_minimal_v3_signal


def action_plans_url(establishment_id, query: str = "") -> str:
    base = f"/api/v1/establishments/{establishment_id}/action-plans/"
    return base + query


def action_plan_url(establishment_id, action_plan_id, suffix: str = "") -> str:
    base = f"/api/v1/establishments/{establishment_id}/action-plans/{action_plan_id}/"
    return base + suffix.lstrip("/")


def action_plan_execution_url(establishment_id, execution_id, suffix: str = "") -> str:
    base = f"/api/v1/establishments/{establishment_id}/action-plan-executions/{execution_id}/"
    return base + suffix.lstrip("/")


def action_plan_execution_feed_url(establishment_id, query: str = "") -> str:
    base = f"/api/v1/establishments/{establishment_id}/action-plan-execution-feed/"
    return base + query


def action_plan_task_url(establishment_id, task_execution_id, suffix: str = "") -> str:
    base = (
        f"/api/v1/establishments/{establishment_id}/action-plan-execution-tasks/"
        f"{task_execution_id}/"
    )
    return base + suffix.lstrip("/")


def action_plan_schedule_url(establishment_id, action_plan_id) -> str:
    return f"/api/v1/establishments/{establishment_id}/action-plans/{action_plan_id}/schedule/"


def action_plan_mixed_submit_url(establishment_id, action_plan_id) -> str:
    return (
        f"/api/v1/establishments/{establishment_id}/action-plans/{action_plan_id}/mixed-submit/"
    )


def action_plan_schedule_detail_url(establishment_id, schedule_id, suffix: str = "") -> str:
    base = f"/api/v1/establishments/{establishment_id}/action-plan-schedules/{schedule_id}/"
    return base + suffix.lstrip("/")


def action_plan_schedule_deactivate_url(establishment_id, schedule_id) -> str:
    return action_plan_schedule_detail_url(establishment_id, schedule_id, "deactivate/")


_RECURRENCE_DAY_NAMES = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)

# Sync-on-create uses visible_only=True; today's occurrence must pass
# visible_from = occurrence_start - 1h <= now.
_VISIBLE_TEST_START_AT = time(0, 30)
_VISIBLE_TEST_END_AT = time(1, 30)


def recurrence_days_for_visible_today(*, base: list[str] | None = None) -> list[str]:
    """Ensure today's weekday is in recurrence so sync-on-create has an occurrence."""
    days = list(base or ["monday", "wednesday", "friday"])
    today = _RECURRENCE_DAY_NAMES[timezone.now().weekday()]
    if today not in days:
        days.append(today)
    return days


def visible_schedule_window(*, period_days: int = 14) -> dict:
    """Schedule window where today's occurrence is visible at any time-of-day."""
    today = timezone.now().date()
    return {
        "start_date": today,
        "end_date": today + timezone.timedelta(days=period_days),
        "start_at": _VISIBLE_TEST_START_AT,
        "end_at": _VISIBLE_TEST_END_AT,
    }


def schedule_window_from_datetime(
    dt,
    *,
    duration_hours: int = 1,
    period_days: int = 14,
) -> dict:
    end_dt = dt + timezone.timedelta(hours=duration_hours)
    start_at = dt.time().replace(microsecond=0)
    end_at = end_dt.time().replace(microsecond=0)
    if end_at <= start_at:
        start_at = time(9, 0)
        end_at = time(10, 0)
    return {
        "start_date": dt.date(),
        "end_date": dt.date() + timezone.timedelta(days=period_days),
        "start_at": start_at,
        "end_at": end_at,
    }


def build_schedule_assignee_payload(*, membership, business_unit) -> dict:
    return {
        "membership_id": membership.id,
        "business_unit_id": business_unit.id,
    }


def api_schedule_assignee_payload(*, membership, business_unit) -> dict:
    payload = build_schedule_assignee_payload(
        membership=membership,
        business_unit=business_unit,
    )
    return {
        "membership_id": str(payload["membership_id"]),
        "business_unit_id": str(payload["business_unit_id"]),
    }


def api_recurring_schedule_payload(
    *,
    staff_membership,
    business_unit,
    recurrence_days=None,
    **overrides,
) -> dict:
    window = visible_schedule_window(period_days=14)
    if recurrence_days is None:
        recurrence_days = recurrence_days_for_visible_today()
    payload = {
        "start_date": window["start_date"].isoformat(),
        "end_date": window["end_date"].isoformat(),
        "start_at": window["start_at"].isoformat(),
        "end_at": window["end_at"].isoformat(),
        "recurrence_days": recurrence_days,
        "assignees": [
            api_schedule_assignee_payload(
                membership=staff_membership,
                business_unit=business_unit,
            )
        ],
    }
    payload.update(overrides)
    return payload


def build_assignee_payload(*, membership, business_unit) -> dict:
    return {
        "membership_id": membership.id,
        "business_unit_id": business_unit.id,
    }


def build_task_payload(
    *,
    task: str,
    business_unit,
    position: int = 1,
    description: str = "",
    deadline_at=None,
    assigned_membership=None,
) -> dict:
    payload = {
        "task": task,
        "business_unit_id": business_unit.id,
        "position": position,
        "description": description,
        "deadline_at": deadline_at,
    }
    if assigned_membership is not None:
        payload["assigned_membership_id"] = assigned_membership.id
    return payload


def api_task_payload(
    *,
    task: str,
    business_unit,
    position: int = 1,
    description: str = "",
    deadline_at=None,
    assigned_membership=None,
) -> dict:
    payload = build_task_payload(
        task=task,
        business_unit=business_unit,
        position=position,
        description=description,
        deadline_at=deadline_at,
        assigned_membership=assigned_membership,
    )
    payload["business_unit_id"] = str(payload["business_unit_id"])
    if payload.get("assigned_membership_id") is not None:
        payload["assigned_membership_id"] = str(payload["assigned_membership_id"])
    if payload.get("deadline_at") is not None:
        payload["deadline_at"] = payload["deadline_at"].isoformat().replace("+00:00", "Z")
    return payload


def api_mixed_submit_payload(
    *,
    submission_id: uuid.UUID | None = None,
    recurring_membership,
    one_shot_membership,
    business_unit,
    recurrence_days=None,
) -> dict:
    window = visible_schedule_window(period_days=14)
    if recurrence_days is None:
        recurrence_days = recurrence_days_for_visible_today()
    start_at = timezone.now() + timezone.timedelta(days=1)
    end_at = start_at + timezone.timedelta(hours=2)
    return {
        "submission_id": str(submission_id or uuid.uuid4()),
        "schedule_body": {
            "start_date": window["start_date"].isoformat(),
            "end_date": window["end_date"].isoformat(),
            "start_at": window["start_at"].isoformat(),
            "end_at": window["end_at"].isoformat(),
            "recurrence_days": recurrence_days,
            "use_shared_chronology": False,
            "assignees": [
                api_schedule_assignee_payload(
                    membership=recurring_membership,
                    business_unit=business_unit,
                )
            ],
        },
        "use_body": {
            "use_shared_chronology": False,
            "assignees": [
                {
                    **api_assignee_payload(
                        membership=one_shot_membership,
                        business_unit=business_unit,
                    ),
                    "start_at": start_at.isoformat().replace("+00:00", "Z"),
                    "end_at": end_at.isoformat().replace("+00:00", "Z"),
                }
            ],
        },
    }


def api_assignee_payload(*, membership, business_unit) -> dict:
    payload = build_assignee_payload(membership=membership, business_unit=business_unit)
    return {
        "membership_id": str(payload["membership_id"]),
        "business_unit_id": str(payload["business_unit_id"]),
    }


def create_catalog_action_plan(*, owner_membership, business_unit) -> ActionPlan:
    plan = ActionPlan.objects.create(
        establishment=owner_membership.establishment,
        created_by=owner_membership,
        pilot_business_unit=business_unit,
        title="Catalog plan",
        description="Reusable plan",
        is_reusable=True,
        catalog_status=CATALOG_STATUS_ACTIVE,
    )
    ActionPlanTask.objects.create(
        action_plan=plan,
        business_unit=business_unit,
        task="Check inventory",
        position=1,
    )
    return plan


def create_open_signal(*, owner_membership, title: str = "Leaky pipe") -> Signal:
    return create_minimal_v3_signal(
        owner_membership,
        title=title,
        status=Signal.Status.OPEN,
    )
