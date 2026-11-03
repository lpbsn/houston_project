"""Personal day, one card per execution.

The classification is one SQL pass over the member's active work. My Day does
not materialize schedules or promote executions: those stay on the beat and on
the execution feed.
"""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone as dt_timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from django.db import connection
from django.utils import timezone

from houston.action_plans.constants import (
    EXECUTION_STATUS_IN_PROGRESS,
    EXECUTION_STATUS_PENDING_VALIDATION,
    EXECUTION_STATUS_SCHEDULED,
    TASK_STATUS_PENDING,
)
from houston.action_plans.models import (
    ActionPlanAssignee,
    ActionPlanExecution,
    ActionPlanExecutionTask,
    ActionPlanExecutionTeam,
)
from houston.establishments.models import BusinessUnit, EstablishmentMembership

MY_DAY_SECTION_ACTION = "action"
MY_DAY_SECTION_FOLLOW = "follow"
MY_DAY_SECTION_UPCOMING = "upcoming"
MY_DAY_SECTIONS = (
    MY_DAY_SECTION_ACTION,
    MY_DAY_SECTION_FOLLOW,
    MY_DAY_SECTION_UPCOMING,
)

MY_DAY_KIND_VALIDATE = "validate"
MY_DAY_KIND_AWAITING_VALIDATION = "awaiting_validation"
MY_DAY_KIND_SCHEDULED = "scheduled"
MY_DAY_KIND_REALIZE = "realize"
MY_DAY_KIND_TASKS = "tasks"
MY_DAY_KIND_FOLLOW = "follow"
MY_DAY_KIND_FINALIZE = "finalize"
MY_DAY_KIND_RELAY = "relay"
MY_DAY_TASK_KINDS = frozenset({MY_DAY_KIND_TASKS, MY_DAY_KIND_SCHEDULED})

MY_DAY_INITIAL_PAGE_SIZE = 5
MY_DAY_CONTINUATION_PAGE_SIZE = 10
MY_DAY_CURSOR_MAX_AGE = timedelta(minutes=15)
_CURSOR_VERSION = "v1"
_SORT_SENTINEL = datetime(9999, 12, 31, tzinfo=dt_timezone.utc)

class MyDayCursorError(Exception):
    pass


@dataclass(frozen=True)
class MyDayCursor:
    section: str
    sort_rank: int
    sort_at: datetime
    execution_id: UUID
    as_of: datetime
    auth_hash: str


@dataclass(frozen=True)
class MyDayTaskRow:
    id: UUID
    title: str
    due_at: datetime | None
    late: bool
    shared: bool
    pole: str | None


@dataclass(frozen=True)
class MyDayCard:
    execution_id: UUID
    title: str
    pilot_pole: str
    section: str
    kind: str
    start_at: datetime | None
    plan_end_at: datetime | None
    plan_all_day: bool
    late: bool
    own_tasks_done: bool
    tasks: list[MyDayTaskRow]
    sort_rank: int
    sort_at: datetime


@dataclass(frozen=True)
class MyDaySectionPage:
    count: int | None
    next_cursor: str | None
    items: list[MyDayCard]


@dataclass(frozen=True)
class MyDayRead:
    as_of: datetime
    sections: dict[str, MyDaySectionPage] | None
    section: str | None
    items: list[MyDayCard] | None
    next_cursor: str | None


def my_day_auth_context_hash(*, membership, scope_ids) -> str:
    raw = json.dumps(
        {
            "establishment_id": str(membership.establishment_id),
            "membership_id": str(membership.id),
            "role": membership.role,
            "scope_business_unit_ids": sorted(str(scope_id) for scope_id in scope_ids),
            "status": membership.status,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def encode_my_day_cursor(
    *,
    section: str,
    sort_rank: int,
    sort_at: datetime,
    execution_id: UUID,
    as_of: datetime,
    auth_hash: str,
) -> str:
    payload = {
        "as_of": as_of.isoformat(),
        "auth": auth_hash,
        "id": str(execution_id),
        "section": section,
        "sort_at": sort_at.isoformat(),
        "sort_rank": sort_rank,
        "v": _CURSOR_VERSION,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return base64.urlsafe_b64encode(raw.encode()).decode("ascii").rstrip("=")


def parse_my_day_cursor(raw: str, *, now: datetime, auth_hash: str) -> MyDayCursor:
    if not raw or not isinstance(raw, str):
        raise MyDayCursorError
    padding = "=" * (-len(raw) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(f"{raw}{padding}").decode())
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise MyDayCursorError from exc
    if not isinstance(payload, dict) or payload.get("v") != _CURSOR_VERSION:
        raise MyDayCursorError
    try:
        section = payload["section"]
        if section not in MY_DAY_SECTIONS:
            raise MyDayCursorError
        sort_rank = int(payload["sort_rank"])
        sort_at = datetime.fromisoformat(payload["sort_at"])
        execution_id = UUID(payload["id"])
        as_of = datetime.fromisoformat(payload["as_of"])
        cursor_auth = payload["auth"]
    except (KeyError, TypeError, ValueError) as exc:
        raise MyDayCursorError from exc
    if sort_at.tzinfo is None or as_of.tzinfo is None:
        raise MyDayCursorError
    if cursor_auth != auth_hash:
        raise MyDayCursorError
    if as_of > now + timedelta(minutes=1) or now - as_of > MY_DAY_CURSOR_MAX_AGE:
        raise MyDayCursorError
    return MyDayCursor(
        section=section,
        sort_rank=sort_rank,
        sort_at=sort_at,
        execution_id=execution_id,
        as_of=as_of,
        auth_hash=cursor_auth,
    )


def read_my_day(
    *,
    membership,
    scope_ids,
    auth_hash: str,
    now: datetime | None = None,
    cursor: MyDayCursor | None = None,
) -> MyDayRead:
    """Classify the member's active work and hydrate one page.

    One statement classifies. A second statement loads tasks only when the
    page contains a card that shows them.
    """
    as_of = cursor.as_of if cursor is not None else (now or timezone.now())
    zone = ZoneInfo(membership.establishment.timezone)
    local_day = as_of.astimezone(zone).date()
    tomorrow = datetime.combine(local_day + timedelta(days=1), time.min, tzinfo=zone)
    is_manager = membership.role == EstablishmentMembership.Role.MANAGER
    page_size = MY_DAY_CONTINUATION_PAGE_SIZE if cursor is not None else MY_DAY_INITIAL_PAGE_SIZE

    sql, params = _page_sql(continuation=cursor is not None)
    query_params = {
        **_base_params(
            membership_id=membership.id,
            establishment_id=membership.establishment_id,
            as_of=as_of,
            tomorrow=tomorrow,
            is_manager=is_manager,
            scope_ids=scope_ids,
        ),
        "limit": page_size + 1,
    }
    if cursor is not None:
        query_params.update(
            section=cursor.section,
            cursor_rank=cursor.sort_rank,
            cursor_sort_at=cursor.sort_at,
            cursor_id=cursor.execution_id,
        )

    rows = _fetch_dicts(sql, query_params | params)
    served, has_more = _trim_page(rows, page_size=page_size, continuation=cursor is not None)
    cards = [_card_from_row(row, tasks=[]) for row in served]
    if any(card.kind in MY_DAY_TASK_KINDS for card in cards):
        tasks_by_execution = _load_tasks(
            execution_ids=[card.execution_id for card in cards if card.kind in MY_DAY_TASK_KINDS],
            membership_id=membership.id,
            as_of=as_of,
            tomorrow=tomorrow,
            is_manager=is_manager,
            scope_ids=scope_ids,
        )
        cards = [
            MyDayCard(
                execution_id=card.execution_id,
                title=card.title,
                pilot_pole=card.pilot_pole,
                section=card.section,
                kind=card.kind,
                start_at=card.start_at,
                plan_end_at=card.plan_end_at,
                plan_all_day=card.plan_all_day,
                late=card.late,
                own_tasks_done=card.own_tasks_done,
                tasks=tasks_by_execution.get(card.execution_id, []),
                sort_rank=card.sort_rank,
                sort_at=card.sort_at,
            )
            for card in cards
        ]

    if cursor is not None:
        return MyDayRead(
            as_of=as_of,
            sections=None,
            section=cursor.section,
            items=cards,
            next_cursor=_next_cursor(cards, has_more=has_more, as_of=as_of, auth_hash=auth_hash),
        )

    sections: dict[str, MyDaySectionPage] = {}
    grouped: dict[str, list[MyDayCard]] = {section: [] for section in MY_DAY_SECTIONS}
    counts = {section: 0 for section in MY_DAY_SECTIONS}
    more = {section: False for section in MY_DAY_SECTIONS}
    for row, card in zip(served, cards, strict=True):
        grouped[card.section].append(card)
        counts[card.section] = int(row["section_count"])
        if int(row["rn"]) > page_size:
            more[card.section] = True
    # Rows with rn = page_size + 1 were trimmed from `served`. Recover the
    # overflow flag from the untrimmed page instead.
    for row in rows:
        section = row["section"]
        counts[section] = int(row["section_count"])
        if int(row["rn"]) > page_size:
            more[section] = True
    for section in MY_DAY_SECTIONS:
        items = grouped[section]
        sections[section] = MyDaySectionPage(
            count=counts[section],
            next_cursor=_next_cursor(
                items,
                has_more=more[section],
                as_of=as_of,
                auth_hash=auth_hash,
            ),
            items=items,
        )
    return MyDayRead(as_of=as_of, sections=sections, section=None, items=None, next_cursor=None)


def my_day_classification_sql(*, membership, scope_ids, as_of: datetime) -> tuple[str, dict]:
    """The classified pass, for EXPLAIN. Same statement the page reads."""
    zone = ZoneInfo(membership.establishment.timezone)
    local_day = as_of.astimezone(zone).date()
    tomorrow = datetime.combine(local_day + timedelta(days=1), time.min, tzinfo=zone)
    sql, extra = _page_sql(continuation=False)
    params = {
        **_base_params(
            membership_id=membership.id,
            establishment_id=membership.establishment_id,
            as_of=as_of,
            tomorrow=tomorrow,
            is_manager=membership.role == EstablishmentMembership.Role.MANAGER,
            scope_ids=scope_ids,
        ),
        "limit": MY_DAY_INITIAL_PAGE_SIZE + 1,
        **extra,
    }
    return sql, params


def _next_cursor(cards: list[MyDayCard], *, has_more: bool, as_of: datetime, auth_hash: str) -> str | None:
    if not has_more or not cards:
        return None
    last = cards[-1]
    return encode_my_day_cursor(
        section=last.section,
        sort_rank=last.sort_rank,
        sort_at=last.sort_at,
        execution_id=last.execution_id,
        as_of=as_of,
        auth_hash=auth_hash,
    )


def _trim_page(rows: list[dict], *, page_size: int, continuation: bool) -> tuple[list[dict], bool]:
    if continuation:
        return rows[:page_size], len(rows) > page_size
    served = [row for row in rows if int(row["rn"]) <= page_size]
    return served, any(int(row["rn"]) > page_size for row in rows)


def _card_from_row(row: dict, *, tasks: list[MyDayTaskRow]) -> MyDayCard:
    return MyDayCard(
        execution_id=row["id"],
        title=row["title"],
        pilot_pole=row["pilot_pole"],
        section=row["section"],
        kind=row["kind"],
        start_at=row["start_at"],
        plan_end_at=row["plan_end_at"],
        plan_all_day=bool(row["plan_all_day"]),
        late=bool(row["late"]),
        own_tasks_done=bool(row["own_tasks_done"]),
        tasks=tasks,
        sort_rank=int(row["sort_rank"]),
        sort_at=row["sort_at"],
    )


def _load_tasks(
    *,
    execution_ids: list[UUID],
    membership_id,
    as_of: datetime,
    tomorrow: datetime,
    is_manager: bool,
    scope_ids,
) -> dict[UUID, list[MyDayTaskRow]]:
    if not execution_ids:
        return {}
    execution = ActionPlanExecution._meta.db_table
    task = ActionPlanExecutionTask._meta.db_table
    team = ActionPlanExecutionTeam._meta.db_table
    assignee = ActionPlanAssignee._meta.db_table
    business_unit = BusinessUnit._meta.db_table
    sql = f"""
    WITH params AS (
      SELECT
        %(membership_id)s::uuid AS membership_id,
        %(as_of)s::timestamptz AS as_of,
        %(tomorrow)s::timestamptz AS tomorrow,
        %(is_manager)s::boolean AS is_manager
    ),
    scope AS (
      SELECT unnest(%(scope_ids)s::uuid[]) AS business_unit_id
    ),
    visible_assignment AS (
      SELECT a.action_plan_execution_id AS execution_id
      FROM (
        SELECT a.action_plan_execution_id
        FROM {assignee} a
        CROSS JOIN params p
        WHERE a.membership_id = p.membership_id
          AND a.visible_from IS NULL
        UNION ALL
        SELECT a.action_plan_execution_id
        FROM {assignee} a
        CROSS JOIN params p
        WHERE a.membership_id = p.membership_id
          AND a.visible_from <= p.as_of
      ) a
    )
    SELECT
      task.id,
      task.action_plan_execution_id AS execution_id,
      task.task AS title,
      task.deadline_at AS due_at,
      (task.deadline_at IS NOT NULL AND task.deadline_at < p.as_of) AS late,
      (task.assigned_membership_id IS NULL) AS shared,
      CASE
        WHEN team.business_unit_id <> e.pilot_business_unit_id THEN bu.specific_name
        ELSE NULL
      END AS pole
    FROM {task} task
    JOIN {execution} e ON e.id = task.action_plan_execution_id
    JOIN {team} team ON team.id = task.execution_team_id
    JOIN {business_unit} bu ON bu.id = team.business_unit_id
    LEFT JOIN visible_assignment va ON va.execution_id = e.id
    CROSS JOIN params p
    WHERE task.action_plan_execution_id = ANY(%(execution_ids)s::uuid[])
      AND task.status = %(pending)s
      AND ({_relevant_sql()})
    ORDER BY
      task.action_plan_execution_id,
      CASE
        WHEN task.deadline_at IS NOT NULL AND task.deadline_at < p.as_of THEN 0
        WHEN task.deadline_at IS NOT NULL AND task.deadline_at < p.tomorrow THEN 1
        WHEN task.deadline_at IS NULL THEN 2
        ELSE 3
      END,
      task.deadline_at ASC NULLS LAST,
      task.id
    """
    rows = _fetch_dicts(
        sql,
        {
            "membership_id": membership_id,
            "as_of": as_of,
            "tomorrow": tomorrow,
            "is_manager": is_manager,
            "scope_ids": _uuid_array(scope_ids),
            "execution_ids": _uuid_array(execution_ids),
            "pending": TASK_STATUS_PENDING,
        },
    )
    grouped: dict[UUID, list[MyDayTaskRow]] = {}
    for row in rows:
        grouped.setdefault(row["execution_id"], []).append(
            MyDayTaskRow(
                id=row["id"],
                title=row["title"],
                due_at=row["due_at"],
                late=bool(row["late"]),
                shared=bool(row["shared"]),
                pole=row["pole"],
            )
        )
    return grouped


def _relevant_sql() -> str:
    return """
    (
      task.id IS NOT NULL
      AND task.assigned_membership_id = p.membership_id
      AND va.execution_id IS NOT NULL
    )
    OR (
      task.id IS NOT NULL
      AND task.assigned_membership_id IS NULL
      AND team.business_unit_id IN (SELECT business_unit_id FROM scope)
      AND (
        team.business_unit_id <> e.pilot_business_unit_id
        OR va.execution_id IS NOT NULL
        OR (
          p.is_manager
          AND e.pilot_business_unit_id IN (SELECT business_unit_id FROM scope)
          AND team.business_unit_id = e.pilot_business_unit_id
        )
      )
    )
    """


def _page_sql(*, continuation: bool) -> tuple[str, dict]:
    execution = ActionPlanExecution._meta.db_table
    task = ActionPlanExecutionTask._meta.db_table
    team = ActionPlanExecutionTeam._meta.db_table
    assignee = ActionPlanAssignee._meta.db_table
    business_unit = BusinessUnit._meta.db_table
    membership = EstablishmentMembership._meta.db_table
    active = (
        EXECUTION_STATUS_SCHEDULED,
        EXECUTION_STATUS_IN_PROGRESS,
        EXECUTION_STATUS_PENDING_VALIDATION,
    )
    status_arms = "\n      UNION ALL\n".join(
        f"""
      SELECT
        e.id, e.title, e.status, e.start_at, e.end_at, e.all_day,
        e.last_activity_at, e.pilot_business_unit_id
      FROM {execution} e
      CROSS JOIN params p
      WHERE e.establishment_id = p.establishment_id
        AND e.status = '{status}'
        AND {visible}
        """
        for status in active
        for visible in ("e.visible_from IS NULL", "e.visible_from <= p.as_of")
    )
    cte = f"""
    WITH params AS (
      SELECT
        %(membership_id)s::uuid AS membership_id,
        %(establishment_id)s::uuid AS establishment_id,
        %(as_of)s::timestamptz AS as_of,
        %(tomorrow)s::timestamptz AS tomorrow,
        %(is_manager)s::boolean AS is_manager,
        %(sort_sentinel)s::timestamptz AS sort_sentinel
    ),
    scope AS (
      SELECT unnest(%(scope_ids)s::uuid[]) AS business_unit_id
    ),
    visible_assignment AS (
      SELECT
        a.action_plan_execution_id AS execution_id,
        bool_or(team.is_pilot) AS is_pilot
      FROM (
        SELECT a.action_plan_execution_id, a.execution_team_id
        FROM {assignee} a
        CROSS JOIN params p
        WHERE a.membership_id = p.membership_id
          AND a.visible_from IS NULL
        UNION ALL
        SELECT a.action_plan_execution_id, a.execution_team_id
        FROM {assignee} a
        CROSS JOIN params p
        WHERE a.membership_id = p.membership_id
          AND a.visible_from <= p.as_of
      ) a
      JOIN {team} team ON team.id = a.execution_team_id
      GROUP BY a.action_plan_execution_id
    ),
    active_exec AS (
      {status_arms}
    ),
    candidates AS (
      SELECT e.id
      FROM active_exec e
      JOIN visible_assignment va ON va.execution_id = e.id
      UNION
      SELECT DISTINCT e.id
      FROM active_exec e
      JOIN {task} task ON task.action_plan_execution_id = e.id
      JOIN {team} team ON team.id = task.execution_team_id
      CROSS JOIN params p
      LEFT JOIN visible_assignment va ON va.execution_id = e.id
      WHERE task.status = %(pending)s
        AND task.assigned_membership_id IS NULL
        AND team.business_unit_id IN (SELECT business_unit_id FROM scope)
        AND (
          team.business_unit_id <> e.pilot_business_unit_id
          OR va.execution_id IS NOT NULL
          OR (
            p.is_manager
            AND e.pilot_business_unit_id IN (SELECT business_unit_id FROM scope)
            AND team.business_unit_id = e.pilot_business_unit_id
          )
        )
      UNION
      SELECT e.id
      FROM active_exec e
      CROSS JOIN params p
      WHERE p.is_manager
        AND e.status = '{EXECUTION_STATUS_PENDING_VALIDATION}'
        AND e.pilot_business_unit_id IN (SELECT business_unit_id FROM scope)
      UNION
      SELECT e.id
      FROM active_exec e
      CROSS JOIN params p
      WHERE p.is_manager
        AND e.status = '{EXECUTION_STATUS_IN_PROGRESS}'
        AND e.pilot_business_unit_id IN (SELECT business_unit_id FROM scope)
        AND EXISTS (
          SELECT 1 FROM {task} task WHERE task.action_plan_execution_id = e.id
        )
        AND NOT EXISTS (
          SELECT 1 FROM {task} task
          WHERE task.action_plan_execution_id = e.id
            AND task.status = %(pending)s
        )
        AND NOT EXISTS (
          SELECT 1
          FROM {assignee} a
          JOIN {team} team ON team.id = a.execution_team_id AND team.is_pilot
          JOIN {membership} m ON m.id = a.membership_id AND m.status = '{EstablishmentMembership.Status.ACTIVE}'
          WHERE a.action_plan_execution_id = e.id
        )
    ),
    task_facts AS (
      SELECT
        e.id AS execution_id,
        task.id AS task_id,
        task.status AS task_status,
        task.deadline_at,
        task.assigned_membership_id,
        ({_relevant_sql()}) AS relevant
      FROM candidates c
      JOIN active_exec e ON e.id = c.id
      LEFT JOIN {task} task ON task.action_plan_execution_id = e.id
      LEFT JOIN {team} team ON team.id = task.execution_team_id
      LEFT JOIN visible_assignment va ON va.execution_id = e.id
      CROSS JOIN params p
    ),
    agg AS (
      SELECT
        execution_id,
        count(task_id) AS plan_task_count,
        count(task_id) FILTER (WHERE task_status = %(pending)s) AS plan_pending,
        count(task_id) FILTER (WHERE relevant AND task_status = %(pending)s) AS relevant_pending,
        count(task_id) FILTER (
          WHERE relevant AND task_status = %(pending)s
            AND deadline_at IS NOT NULL AND deadline_at < (SELECT as_of FROM params)
        ) AS late_count,
        count(task_id) FILTER (
          WHERE relevant AND task_status = %(pending)s
            AND deadline_at IS NOT NULL
            AND deadline_at >= (SELECT as_of FROM params)
            AND deadline_at < (SELECT tomorrow FROM params)
        ) AS today_count,
        count(task_id) FILTER (
          WHERE relevant AND task_status = %(pending)s AND deadline_at IS NULL
        ) AS undated_count,
        count(task_id) FILTER (
          WHERE relevant AND task_status = %(pending)s
            AND deadline_at >= (SELECT tomorrow FROM params)
        ) AS future_count,
        COALESCE(bool_or(
          assigned_membership_id = (SELECT membership_id FROM params)
          AND task_status IS NOT NULL
          AND task_status <> %(pending)s
        ), FALSE) AS own_tasks_done,
        min(deadline_at) FILTER (
          WHERE relevant AND task_status = %(pending)s
            AND deadline_at IS NOT NULL AND deadline_at < (SELECT as_of FROM params)
        ) AS min_late,
        min(deadline_at) FILTER (
          WHERE relevant AND task_status = %(pending)s
            AND deadline_at >= (SELECT as_of FROM params)
            AND deadline_at < (SELECT tomorrow FROM params)
        ) AS min_today,
        min(deadline_at) FILTER (
          WHERE relevant AND task_status = %(pending)s
            AND deadline_at >= (SELECT tomorrow FROM params)
        ) AS min_future
      FROM task_facts
      GROUP BY execution_id
    ),
    active_pilot AS (
      SELECT DISTINCT a.action_plan_execution_id AS execution_id
      FROM {assignee} a
      JOIN {team} team ON team.id = a.execution_team_id AND team.is_pilot
      JOIN {membership} m ON m.id = a.membership_id AND m.status = '{EstablishmentMembership.Status.ACTIVE}'
      WHERE a.action_plan_execution_id IN (SELECT id FROM candidates)
    ),
    facts AS (
      SELECT
        e.id,
        e.title,
        e.status,
        e.start_at,
        e.end_at AS plan_end_at,
        e.all_day AS plan_all_day,
        e.last_activity_at,
        bu.specific_name AS pilot_pole,
        COALESCE(agg.plan_task_count, 0) AS plan_task_count,
        COALESCE(agg.plan_pending, 0) AS plan_pending,
        COALESCE(agg.relevant_pending, 0) AS relevant_pending,
        COALESCE(agg.late_count, 0) AS late_count,
        COALESCE(agg.today_count, 0) AS today_count,
        COALESCE(agg.undated_count, 0) AS undated_count,
        COALESCE(agg.future_count, 0) AS future_count,
        COALESCE(agg.own_tasks_done, FALSE) AS own_tasks_done,
        agg.min_late,
        agg.min_today,
        agg.min_future,
        (va.execution_id IS NOT NULL) AS is_visible_assignee,
        COALESCE(va.is_pilot, FALSE) AS is_pilot_assignee,
        (pilot.execution_id IS NOT NULL) AS has_active_pilot_assignee,
        (
          p.is_manager
          AND e.pilot_business_unit_id IN (SELECT business_unit_id FROM scope)
        ) AS is_pilot_manager,
        p.sort_sentinel
      FROM candidates c
      JOIN active_exec e ON e.id = c.id
      JOIN {business_unit} bu ON bu.id = e.pilot_business_unit_id
      LEFT JOIN agg ON agg.execution_id = e.id
      LEFT JOIN visible_assignment va ON va.execution_id = e.id
      LEFT JOIN active_pilot pilot ON pilot.execution_id = e.id
      CROSS JOIN params p
    ),
    labeled AS (
      SELECT
        facts.*,
        CASE
          WHEN status = '{EXECUTION_STATUS_PENDING_VALIDATION}' AND is_pilot_manager THEN '{MY_DAY_SECTION_ACTION}'
          WHEN status = '{EXECUTION_STATUS_PENDING_VALIDATION}' AND is_visible_assignee THEN '{MY_DAY_SECTION_FOLLOW}'
          WHEN status = '{EXECUTION_STATUS_PENDING_VALIDATION}' THEN NULL
          WHEN status = '{EXECUTION_STATUS_SCHEDULED}'
            AND (is_visible_assignee OR relevant_pending > 0) THEN '{MY_DAY_SECTION_UPCOMING}'
          WHEN status = '{EXECUTION_STATUS_SCHEDULED}' THEN NULL
          WHEN status = '{EXECUTION_STATUS_IN_PROGRESS}'
            AND plan_task_count = 0 AND is_visible_assignee THEN '{MY_DAY_SECTION_ACTION}'
          WHEN status = '{EXECUTION_STATUS_IN_PROGRESS}'
            AND relevant_pending > 0
            AND (late_count > 0 OR today_count > 0 OR undated_count > 0) THEN '{MY_DAY_SECTION_ACTION}'
          WHEN status = '{EXECUTION_STATUS_IN_PROGRESS}'
            AND relevant_pending > 0 THEN '{MY_DAY_SECTION_UPCOMING}'
          WHEN status = '{EXECUTION_STATUS_IN_PROGRESS}'
            AND relevant_pending = 0 AND plan_pending > 0 AND is_visible_assignee THEN '{MY_DAY_SECTION_FOLLOW}'
          WHEN status = '{EXECUTION_STATUS_IN_PROGRESS}'
            AND plan_task_count > 0 AND plan_pending = 0
            AND is_visible_assignee AND is_pilot_assignee THEN '{MY_DAY_SECTION_ACTION}'
          WHEN status = '{EXECUTION_STATUS_IN_PROGRESS}'
            AND plan_task_count > 0 AND plan_pending = 0
            AND is_visible_assignee THEN '{MY_DAY_SECTION_FOLLOW}'
          WHEN status = '{EXECUTION_STATUS_IN_PROGRESS}'
            AND plan_task_count > 0 AND plan_pending = 0
            AND is_pilot_manager AND NOT has_active_pilot_assignee THEN '{MY_DAY_SECTION_ACTION}'
          ELSE NULL
        END AS section,
        CASE
          WHEN status = '{EXECUTION_STATUS_PENDING_VALIDATION}' AND is_pilot_manager THEN '{MY_DAY_KIND_VALIDATE}'
          WHEN status = '{EXECUTION_STATUS_PENDING_VALIDATION}' AND is_visible_assignee THEN '{MY_DAY_KIND_AWAITING_VALIDATION}'
          WHEN status = '{EXECUTION_STATUS_SCHEDULED}'
            AND (is_visible_assignee OR relevant_pending > 0) THEN '{MY_DAY_KIND_SCHEDULED}'
          WHEN status = '{EXECUTION_STATUS_IN_PROGRESS}'
            AND plan_task_count = 0 AND is_visible_assignee THEN '{MY_DAY_KIND_REALIZE}'
          WHEN status = '{EXECUTION_STATUS_IN_PROGRESS}' AND relevant_pending > 0 THEN '{MY_DAY_KIND_TASKS}'
          WHEN status = '{EXECUTION_STATUS_IN_PROGRESS}'
            AND relevant_pending = 0 AND plan_pending > 0 AND is_visible_assignee THEN '{MY_DAY_KIND_FOLLOW}'
          WHEN status = '{EXECUTION_STATUS_IN_PROGRESS}'
            AND plan_task_count > 0 AND plan_pending = 0
            AND is_visible_assignee AND is_pilot_assignee THEN '{MY_DAY_KIND_FINALIZE}'
          WHEN status = '{EXECUTION_STATUS_IN_PROGRESS}'
            AND plan_task_count > 0 AND plan_pending = 0
            AND is_visible_assignee THEN '{MY_DAY_KIND_FOLLOW}'
          WHEN status = '{EXECUTION_STATUS_IN_PROGRESS}'
            AND plan_task_count > 0 AND plan_pending = 0
            AND is_pilot_manager AND NOT has_active_pilot_assignee THEN '{MY_DAY_KIND_RELAY}'
          ELSE NULL
        END AS kind
      FROM facts
    ),
    classified AS (
      SELECT
        id,
        title,
        pilot_pole,
        section,
        kind,
        start_at,
        plan_end_at,
        plan_all_day,
        (section = '{MY_DAY_SECTION_ACTION}' AND kind = '{MY_DAY_KIND_TASKS}' AND late_count > 0) AS late,
        own_tasks_done,
        CASE
          WHEN section = '{MY_DAY_SECTION_ACTION}' AND kind = '{MY_DAY_KIND_TASKS}' AND late_count > 0 THEN 0
          WHEN section = '{MY_DAY_SECTION_ACTION}' AND kind = '{MY_DAY_KIND_TASKS}' AND today_count > 0 AND late_count = 0 THEN 1
          WHEN section = '{MY_DAY_SECTION_ACTION}' THEN 2
          ELSE 0
        END AS sort_rank,
        COALESCE(
          CASE
            WHEN section = '{MY_DAY_SECTION_ACTION}' AND kind = '{MY_DAY_KIND_TASKS}' AND late_count > 0 THEN min_late
            WHEN section = '{MY_DAY_SECTION_ACTION}' AND kind = '{MY_DAY_KIND_TASKS}' AND today_count > 0 AND late_count = 0 THEN min_today
            WHEN section = '{MY_DAY_SECTION_ACTION}' THEN last_activity_at
            WHEN section = '{MY_DAY_SECTION_UPCOMING}' AND kind = '{MY_DAY_KIND_SCHEDULED}' THEN COALESCE(start_at, sort_sentinel)
            WHEN section = '{MY_DAY_SECTION_UPCOMING}' THEN min_future
            ELSE last_activity_at
          END,
          last_activity_at
        ) AS sort_at,
        CASE
          WHEN section = '{MY_DAY_SECTION_FOLLOW}' THEN TRUE
          WHEN section = '{MY_DAY_SECTION_ACTION}'
            AND NOT (kind = '{MY_DAY_KIND_TASKS}' AND (late_count > 0 OR (today_count > 0 AND late_count = 0))) THEN TRUE
          ELSE FALSE
        END AS sort_desc
      FROM labeled
      WHERE section IS NOT NULL
    )
    """
    if continuation:
        sql = cte + """
        SELECT *
        FROM classified
        WHERE section = %(section)s
          AND (
            sort_rank > %(cursor_rank)s
            OR (
              sort_rank = %(cursor_rank)s
              AND (
                (NOT sort_desc AND sort_at > %(cursor_sort_at)s)
                OR (sort_desc AND sort_at < %(cursor_sort_at)s)
                OR (sort_at = %(cursor_sort_at)s AND id > %(cursor_id)s)
              )
            )
          )
        ORDER BY
          sort_rank,
          CASE WHEN NOT sort_desc THEN sort_at END ASC,
          CASE WHEN sort_desc THEN sort_at END DESC,
          id ASC
        LIMIT %(limit)s
        """
    else:
        sql = cte + """
        SELECT *
        FROM (
          SELECT
            classified.*,
            count(*) OVER (PARTITION BY section) AS section_count,
            row_number() OVER (
              PARTITION BY section
              ORDER BY
                sort_rank,
                CASE WHEN NOT sort_desc THEN sort_at END ASC,
                CASE WHEN sort_desc THEN sort_at END DESC,
                id ASC
            ) AS rn
          FROM classified
        ) numbered
        WHERE rn <= %(limit)s
        ORDER BY section, rn
        """
    return sql, {"pending": TASK_STATUS_PENDING}


def _base_params(*, membership_id, establishment_id, as_of, tomorrow, is_manager, scope_ids) -> dict:
    return {
        "membership_id": membership_id,
        "establishment_id": establishment_id,
        "as_of": as_of,
        "tomorrow": tomorrow,
        "is_manager": is_manager,
        "sort_sentinel": _SORT_SENTINEL,
        "scope_ids": _uuid_array(scope_ids),
    }


def _uuid_array(values) -> str:
    if not values:
        return "{}"
    return "{" + ",".join(str(value) for value in values) + "}"


def _fetch_dicts(sql: str, params: dict) -> list[dict]:
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]
