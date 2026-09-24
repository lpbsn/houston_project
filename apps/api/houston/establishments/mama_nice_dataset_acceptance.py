from __future__ import annotations

from collections import Counter
from datetime import date, timedelta

from houston.action_plans.constants import CATALOG_STATUS_ACTIVE, CATALOG_STATUS_INACTIVE
from houston.action_plans.models import ActionPlan, ActionPlanExecution, ActionPlanSchedule
from houston.action_plans.selectors import (
    action_plan_execution_calendar_items_queryset,
    action_plan_execution_overdue,
)
from houston.analytics.models import OperationalPattern
from houston.chat.models import ChatConversation, ChatMessage
from houston.comments.models import Comment
from houston.establishments.mama_nice_dataset_clock import (
    freeze_django_now,
    load_persisted_reference_at,
    non_terminal_runtime_errors,
)
from houston.establishments.mama_nice_dataset_compiler import (
    CompiledOccurrence,
    CompiledOneshot,
    compile_mama_nice_dataset,
)
from houston.establishments.mama_nice_dataset_constants import (
    ACTIVE_PLAN_COUNT,
    ACTIVE_SIGNAL_MAX_AGE_DAYS,
    FUTURE_BY_MONTH,
    FUTURE_EXECUTION_COUNT,
    FUTURE_WINDOW_END,
    FUTURE_WINDOW_START,
    HISTORICAL_EXECUTION_COUNT,
    INACTIVE_PLAN_COUNT,
    OBJECT_TYPE_EXECUTION,
    OBJECT_TYPE_SCHEDULE,
    OVERDUE_EXECUTION_COUNT,
    OVERDUE_MAX_DAYS,
    OVERDUE_MIN_DAYS,
    PARIS_TZ,
    REUSABLE_PLAN_COUNT,
    SNAPSHOT,
    TOTAL_OBSERVATIONS,
    TOTAL_SIGNALS,
)
from houston.establishments.mama_nice_dataset_exceptions import MamaNiceDatasetError
from houston.establishments.models import Establishment, EstablishmentMembership, MamaNiceSeedRecord
from houston.gamification.models import BadgeAward, GamificationSeason
from houston.observations.models import Observation
from houston.signals.models import Signal

TOTAL_EXECUTION_COUNT = HISTORICAL_EXECUTION_COUNT + FUTURE_EXECUTION_COUNT


def authored_calendar_specs():
    return list(compile_mama_nice_dataset().future_executions)


def authored_calendar_identity(item: CompiledOneshot | CompiledOccurrence) -> str:
    if isinstance(item, CompiledOneshot):
        return item.seed_key
    return f"{item.schedule_seed_key}:{item.occurrence_date.isoformat()}"


def runtime_calendar_remaining_specs(*, reference_at):
    return [item for item in authored_calendar_specs() if item.start_at > reference_at]


def runtime_calendar_elapsed_specs(*, reference_at):
    return [item for item in authored_calendar_specs() if item.start_at <= reference_at]


def _resolve_authored_calendar_execution(*, establishment: Establishment, spec):
    if isinstance(spec, CompiledOneshot):
        record = MamaNiceSeedRecord.objects.filter(
            establishment=establishment,
            object_type=OBJECT_TYPE_EXECUTION,
            seed_key=spec.seed_key,
        ).first()
        if record is None:
            return None
        return ActionPlanExecution.objects.filter(id=record.object_id).first()
    record = MamaNiceSeedRecord.objects.filter(
        establishment=establishment,
        object_type=OBJECT_TYPE_SCHEDULE,
        seed_key=spec.schedule_seed_key,
    ).first()
    if record is None:
        return None
    return ActionPlanExecution.objects.filter(
        establishment=establishment,
        action_plan_schedule_id=record.object_id,
        occurrence_date=spec.occurrence_date,
        start_at=spec.start_at,
    ).first()


def _seeded_chat_row_errors(establishment: Establishment) -> list[str]:
    conversation_count = ChatConversation.objects.filter(establishment=establishment).count()
    message_count = ChatMessage.objects.filter(
        conversation__establishment=establishment
    ).count()
    if not conversation_count and not message_count:
        return []
    return [
        "chat rows were seeded: "
        f"{conversation_count} conversations, {message_count} messages"
    ]


def validate_mama_nice_dataset(*, establishment: Establishment) -> list[str]:
    errors: list[str] = []
    errors.extend(_seeded_chat_row_errors(establishment))
    if Observation.objects.filter(establishment=establishment).count() != TOTAL_OBSERVATIONS:
        errors.append("observation count diverges")
    if Signal.objects.filter(establishment=establishment).count() != TOTAL_SIGNALS:
        errors.append("signal count diverges")
    if Observation.objects.filter(establishment=establishment, media_items__isnull=False).exists():
        errors.append("observation media were generated")
    reference_at = load_persisted_reference_at(establishment) or SNAPSHOT
    compiled = compile_mama_nice_dataset()
    calendar_specs = list(compiled.future_executions)
    if len(calendar_specs) != FUTURE_EXECUTION_COUNT:
        errors.append(
            f"authored calendar specs {len(calendar_specs)} != {FUTURE_EXECUTION_COUNT}"
        )
    authored_month_counts = Counter(
        (item.start_at.astimezone(PARIS_TZ).year, item.start_at.astimezone(PARIS_TZ).month)
        for item in calendar_specs
    )
    if dict(authored_month_counts) != FUTURE_BY_MONTH:
        errors.append(
            f"authored calendar month split {dict(sorted(authored_month_counts.items()))}"
        )
    resolved_calendar: list[ActionPlanExecution] = []
    for spec in calendar_specs:
        execution = _resolve_authored_calendar_execution(establishment=establishment, spec=spec)
        if execution is None:
            errors.append(
                f"{authored_calendar_identity(spec)}: authored calendar execution missing"
            )
            continue
        resolved_calendar.append(execution)
    authored_calendar_ids = {item.id for item in resolved_calendar}
    if len(authored_calendar_ids) != len(resolved_calendar):
        errors.append("authored calendar executions are duplicated")
    if (
        len(resolved_calendar) == FUTURE_EXECUTION_COUNT
        and len(authored_calendar_ids) != FUTURE_EXECUTION_COUNT
    ):
        errors.append("authored calendar executions are duplicated")
    all_executions = ActionPlanExecution.objects.filter(establishment=establishment)
    if all_executions.count() != TOTAL_EXECUTION_COUNT:
        errors.append(f"execution total {all_executions.count()} != {TOTAL_EXECUTION_COUNT}")
    authored_historical = all_executions.exclude(id__in=authored_calendar_ids)
    if authored_historical.count() != HISTORICAL_EXECUTION_COUNT:
        errors.append(
            "authored historical executions "
            f"{authored_historical.count()} != {HISTORICAL_EXECUTION_COUNT}"
        )
    elapsed = all_executions.filter(start_at__lte=reference_at)
    remaining = all_executions.filter(start_at__gt=reference_at)
    if elapsed.count() + remaining.count() != TOTAL_EXECUTION_COUNT:
        errors.append(
            "runtime execution partition "
            f"{elapsed.count()}+{remaining.count()} != {TOTAL_EXECUTION_COUNT}"
        )
    if elapsed.filter(id__in=remaining.values("id")).exists():
        errors.append("runtime elapsed and remaining execution sets overlap")
    expected_elapsed = HISTORICAL_EXECUTION_COUNT + len(
        [item for item in calendar_specs if item.start_at <= reference_at]
    )
    expected_remaining = len([item for item in calendar_specs if item.start_at > reference_at])
    if elapsed.count() != expected_elapsed:
        errors.append(
            f"runtime elapsed executions {elapsed.count()} != {expected_elapsed} at reference_at"
        )
    if remaining.count() != expected_remaining:
        errors.append(
            "runtime remaining executions "
            f"{remaining.count()} != {expected_remaining} at reference_at"
        )
    historical = elapsed
    director = EstablishmentMembership.objects.filter(
        establishment=establishment,
        user__email="director.demo.mama.nice@example.com",
        status=EstablishmentMembership.Status.ACTIVE,
    ).first()
    if director is None:
        errors.append("fictive director is missing")
        return errors
    with freeze_django_now(reference_at):
        rows = list(
            action_plan_execution_calendar_items_queryset(
                membership=director,
                view_mode="general",
                window_start=FUTURE_WINDOW_START,
                window_end=FUTURE_WINDOW_END,
            )
        )
    remaining_rows = [item for item in rows if item.start_at > reference_at]
    if len(remaining_rows) != expected_remaining:
        errors.append(
            "director calendar remaining rows "
            f"{len(remaining_rows)} != {expected_remaining} authored remaining"
        )
    allowed_started = {
        "in_progress",
        "pending_validation",
        "done",
        "canceled",
    }
    if any(
        item.start_at <= reference_at and item.status not in allowed_started for item in rows
    ):
        errors.append("calendar contains historical start_at")
    if ActionPlanSchedule.objects.filter(establishment=establishment).count() != 28:
        errors.append("schedule count diverges")
    reusable_plans = ActionPlan.objects.filter(establishment=establishment, is_reusable=True)
    if reusable_plans.count() != REUSABLE_PLAN_COUNT:
        errors.append("reusable plan count diverges")
    if reusable_plans.filter(catalog_status=CATALOG_STATUS_ACTIVE).count() != ACTIVE_PLAN_COUNT:
        errors.append("active reusable plan count diverges")
    if reusable_plans.filter(catalog_status=CATALOG_STATUS_INACTIVE).count() != INACTIVE_PLAN_COUNT:
        errors.append("inactive reusable plan count diverges")
    if OperationalPattern.objects.filter(organization=establishment.organization).count() < 24:
        errors.append("pattern count is below 24")
    closed = GamificationSeason.objects.filter(
        establishment=establishment,
        status=GamificationSeason.Status.CLOSED,
    ).count()
    active = GamificationSeason.objects.filter(
        establishment=establishment,
        status=GamificationSeason.Status.ACTIVE,
    ).count()
    if closed != 6 or active != 1:
        errors.append(f"seasons closed/active {closed}/{active} != 6/1")
    badge_members = (
        BadgeAward.objects.filter(establishment=establishment)
        .exclude(
            membership__user__email__in={
                "leonard.p.boisson@gmail.com",
                "director.mama.nice@example.com",
            }
        )
        .values("membership_id")
        .distinct()
        .count()
    )
    if badge_members != 21:
        errors.append(f"badge members {badge_members} != 21")
    seed_chat = MamaNiceSeedRecord.objects.filter(
        establishment=establishment,
        object_type__startswith="chat",
    ).count()
    if seed_chat:
        errors.append("seed records contain Chat object types")
    if MamaNiceSeedRecord.objects.filter(
        establishment=establishment,
        object_type__in=["chat", "chat_conversation", "chat_message"],
    ).exists():
        errors.append("Chat objects were seeded")
    if Comment.objects.filter(establishment=establishment, signal__isnull=False).count() < 19:
        errors.append("signal comments are missing")
    governance_emails = {"leonard.p.boisson@gmail.com", "director.mama.nice@example.com"}
    if Observation.objects.filter(
        establishment=establishment,
        submitted_by_membership__user__email__in=governance_emails,
    ).exists():
        errors.append("governance accounts authored observations")
    executions = list(ActionPlanExecution.objects.filter(establishment=establishment))
    errors.extend(non_terminal_runtime_errors(executions=executions, reference_at=reference_at))
    overdue = [
        execution
        for execution in historical
        if action_plan_execution_overdue(execution=execution, now=reference_at)
    ]
    if len(overdue) != OVERDUE_EXECUTION_COUNT:
        errors.append(f"overdue executions {len(overdue)} != {OVERDUE_EXECUTION_COUNT}")
    if any(item.status != "pending_validation" for item in overdue):
        errors.append("overdue executions must be pending validation")
    for item in overdue:
        late = reference_at - item.end_at
        if late < timedelta(days=OVERDUE_MIN_DAYS) or late > timedelta(
            days=OVERDUE_MAX_DAYS, hours=1
        ):
            errors.append(f"{item.title}: overdue {late} is outside 2-7 days")
    open_late = historical.filter(
        status__in={"scheduled", "in_progress", "pending_validation"},
        end_at__lt=reference_at - timedelta(days=OVERDUE_MAX_DAYS, hours=1),
    )
    if open_late.exists():
        errors.append("an open execution is more than 7 days late")
    scheduled_or_progress_overdue = [
        item for item in overdue if item.status in {"scheduled", "in_progress"}
    ]
    if scheduled_or_progress_overdue:
        errors.append("scheduled or in-progress executions must not be overdue")
    on_time_active = authored_historical.filter(
        status__in={"in_progress", "pending_validation"}
    ).exclude(id__in=[item.id for item in overdue])
    if on_time_active.filter(status="in_progress").count() != 10:
        errors.append("in-progress on-time historical count diverges")
    if on_time_active.filter(status="pending_validation").count() != 10:
        errors.append("pending-validation on-time historical count diverges")
    if historical.filter(end_at__isnull=True).exists():
        errors.append("historical executions must have end_at")
    terminal = historical.exclude(status__in={"in_progress", "pending_validation", "scheduled"})
    if terminal.filter(end_at__gt=reference_at).exists():
        errors.append("terminal historical executions must have end_at <= reference_at")
    cutoff = reference_at - timedelta(days=ACTIVE_SIGNAL_MAX_AGE_DAYS)
    active_signals = Signal.objects.filter(
        establishment=establishment,
        status__in={"open", "in_progress", "interesting"},
    )
    if active_signals.filter(created_at__lt=cutoff).exists():
        errors.append("an active Signal is older than 30 days at snapshot")
    from houston.establishments.mama_nice_dataset_scenarios import (
        ROOFTOP_CLOSURE_IDENTITY,
        ROOFTOP_OPENING_TOKENS,
        proactive_project_specs,
    )

    spec = next(
        item for item in proactive_project_specs() if item.seed_key == ROOFTOP_CLOSURE_IDENTITY
    )
    closure = ActionPlanExecution.objects.filter(
        establishment=establishment,
        start_at=spec.start_at,
        action_plan_schedule__isnull=False,
    ).first()
    if closure is None:
        errors.append("rooftop closure occurrence is missing")
    else:
        visible = [closure.title, *(task.task for task in closure.task_executions.all())]
        if any(
            any(token in text.casefold() for token in ROOFTOP_OPENING_TOKENS) for text in visible
        ):
            errors.append("rooftop closure execution still uses opening copy")
    for seed_key, start_day, end_day in (
        ("oneshot:public:tim-lienderss", date(2026, 9, 24), date(2026, 9, 26)),
        ("oneshot:private:horizon-azur-2026-11-12", date(2026, 11, 10), date(2026, 11, 13)),
        ("oneshot:public:club-sonore-2026-10-22", date(2026, 10, 22), date(2026, 10, 22)),
    ):
        record = MamaNiceSeedRecord.objects.filter(
            establishment=establishment,
            seed_key=seed_key,
            object_type="execution",
        ).first()
        if record is None:
            errors.append(f"{seed_key}: seed record missing")
            continue
        execution = ActionPlanExecution.objects.filter(id=record.object_id).first()
        if execution is None:
            errors.append(f"{seed_key}: execution missing")
            continue
        if execution.start_at.astimezone(PARIS_TZ).date() != start_day:
            errors.append(f"{seed_key}: start date diverged")
        if execution.end_at.astimezone(PARIS_TZ).date() != end_day:
            errors.append(f"{seed_key}: end date diverged")
        if not execution.assignees.exists():
            errors.append(f"{seed_key}: assignees missing")
        if not execution.task_executions.exists():
            errors.append(f"{seed_key}: tasks missing")
    compiled_tim = next(
        item for item in compiled.oneshots if item.seed_key == "oneshot:public:tim-lienderss"
    )
    if compiled_tim.start_at.date() != date(2026, 9, 24) or compiled_tim.end_at.date() != date(
        2026, 9, 26
    ):
        errors.append("compiled TIM LIENDERSS window diverged")
    sunday = next(
        item
        for item in compiled.future_executions
        if getattr(item, "schedule_seed_key", None) == "schedule:super-sunday"
        and item.occurrence_date == date(2026, 9, 27)
    )
    if (sunday.end_at - sunday.start_at) > timedelta(hours=4):
        errors.append("Super Sunday must stay an hourly occurrence")
    return errors


def assert_mama_nice_dataset(*, establishment: Establishment) -> None:
    errors = validate_mama_nice_dataset(establishment=establishment)
    if errors:
        raise MamaNiceDatasetError(errors)
