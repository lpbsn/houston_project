from __future__ import annotations

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
    base = (
        f"/api/v1/establishments/{establishment_id}/action-plan-executions/{execution_id}/"
    )
    return base + suffix.lstrip("/")


def action_plan_task_url(establishment_id, task_execution_id, suffix: str = "") -> str:
    base = (
        f"/api/v1/establishments/{establishment_id}/action-plan-execution-tasks/"
        f"{task_execution_id}/"
    )
    return base + suffix.lstrip("/")


def action_plan_schedule_url(establishment_id, action_plan_id) -> str:
    return (
        f"/api/v1/establishments/{establishment_id}/action-plans/{action_plan_id}/schedule/"
    )


def action_plan_schedule_detail_url(establishment_id, schedule_id, suffix: str = "") -> str:
    base = f"/api/v1/establishments/{establishment_id}/action-plan-schedules/{schedule_id}/"
    return base + suffix.lstrip("/")


def action_plan_schedule_deactivate_url(establishment_id, schedule_id) -> str:
    return action_plan_schedule_detail_url(establishment_id, schedule_id, "deactivate/")


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
    now = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
    window = schedule_window_from_datetime(now, duration_hours=1, period_days=14)
    if recurrence_days is None:
        recurrence_days = ["monday", "wednesday", "friday"]
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


def build_task_payload(*, task: str, business_unit, position: int = 1) -> dict:
    return {
        "task": task,
        "business_unit_id": business_unit.id,
        "position": position,
    }


def api_task_payload(*, task: str, business_unit, position: int = 1) -> dict:
    payload = build_task_payload(task=task, business_unit=business_unit, position=position)
    payload["business_unit_id"] = str(payload["business_unit_id"])
    return payload


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
