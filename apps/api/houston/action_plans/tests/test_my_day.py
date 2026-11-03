from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from houston.action_plans.day_selectors import (
    MY_DAY_CONTINUATION_PAGE_SIZE,
    MY_DAY_INITIAL_PAGE_SIZE,
    MyDayCursorError,
    encode_my_day_cursor,
    my_day_auth_context_hash,
    my_day_classification_sql,
    parse_my_day_cursor,
    read_my_day,
)
from houston.action_plans.models import (
    ActionPlanAssignee,
    ActionPlanExecution,
    ActionPlanExecutionTask,
    ActionPlanExecutionTeam,
)
from houston.action_plans.tests.helpers import (
    build_assignee_payload,
    build_schedule_assignee_payload,
    build_task_payload,
    create_execution,
    schedule_window_from_datetime,
)
from houston.establishments.models import EstablishmentMembership, MembershipScope
from houston.testing.factories import create_establishment, create_membership
from houston.testing.taxonomy import (
    create_business_unit,
    create_membership_with_business_unit_scope,
)

pytestmark = pytest.mark.django_db


def _scope_ids(membership):
    return list(membership.scope_links.values_list("business_unit_id", flat=True))


def _read(membership, **kwargs):
    _ = membership.establishment.timezone
    scope_ids = _scope_ids(membership)
    return read_my_day(
        membership=membership,
        scope_ids=scope_ids,
        auth_hash=my_day_auth_context_hash(membership=membership, scope_ids=scope_ids),
        **kwargs,
    )


def _cards(reading, section):
    return reading.sections[section].items


def _by_title(reading, title):
    for section in reading.sections.values():
        for card in section.items:
            if card.title == title:
                return card
    return None


def _queries(membership, **kwargs):
    _ = membership.establishment.timezone
    scope_ids = _scope_ids(membership)
    auth_hash = my_day_auth_context_hash(membership=membership, scope_ids=scope_ids)
    with CaptureQueriesContext(connection) as captured:
        reading = read_my_day(
            membership=membership,
            scope_ids=scope_ids,
            auth_hash=auth_hash,
            **kwargs,
        )
    return reading, captured.captured_queries


def _selector_sql(queries):
    return [query["sql"] for query in queries if "WITH params AS" in query["sql"] or "unnest" in query["sql"]]


def assigned_execution(owner, business_unit, member, title="Préparer le service", **kwargs):
    return create_execution(
        owner,
        business_unit=business_unit,
        title=title,
        assignees=[build_assignee_payload(membership=member, business_unit=business_unit)],
        **kwargs,
    )


def _drop_tasks(execution):
    execution.task_executions.all().delete()


def test_named_work_is_only_for_the_visible_assignee(
    owner_membership, staff_membership, business_unit
):
    execution = assigned_execution(owner_membership, business_unit, staff_membership)
    task = execution.task_executions.get()
    task.assigned_membership = staff_membership
    task.save(update_fields=["assigned_membership"])
    assert _by_title(_read(owner_membership), execution.title) is None
    card = _by_title(_read(staff_membership), execution.title)
    assert card is not None
    assert [item.id for item in card.tasks] == [task.id]

    assignee = execution.assignees.get()
    assignee.visible_from = timezone.now() + timedelta(days=1)
    assignee.save(update_fields=["visible_from"])
    execution.visible_from = timezone.now() - timedelta(hours=1)
    execution.created_by = staff_membership
    execution.save(update_fields=["visible_from", "created_by", "updated_at"])
    assert _by_title(_read(staff_membership), execution.title) is None


def test_contributor_collective_ignores_a_future_personal_assignment(
    owner_membership,
    staff_membership,
    business_unit,
    maintenance_business_unit,
):
    create_membership_with_business_unit_scope(
        membership=staff_membership,
        business_unit=maintenance_business_unit,
    )
    execution = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Contrôle partagé",
        assignees=[build_assignee_payload(membership=owner_membership, business_unit=business_unit)],
        tasks=[
            build_task_payload(
                task="Tâche cuisine",
                business_unit=business_unit,
                position=1,
                assigned_membership=owner_membership,
            ),
            build_task_payload(
                task="Tâche maintenance",
                business_unit=maintenance_business_unit,
                position=2,
            ),
        ],
    )
    team = execution.execution_teams.get(business_unit=maintenance_business_unit)
    ActionPlanAssignee.objects.create(
        action_plan_execution=execution,
        execution_team=team,
        membership=staff_membership,
        visible_from=timezone.now() + timedelta(days=2),
    )
    card = _by_title(_read(staff_membership), execution.title)
    assert card is not None
    assert [item.title for item in card.tasks] == ["Tâche maintenance"]


def test_pilot_collective_stays_with_assignees_and_the_pilot_manager(
    owner_membership,
    staff_membership,
    manager_membership,
    business_unit,
):
    colleague = create_membership(
        establishment=staff_membership.establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    create_membership_with_business_unit_scope(membership=colleague, business_unit=business_unit)
    execution = assigned_execution(
        owner_membership,
        business_unit,
        staff_membership,
        title="Collectif pilote",
    )
    task = execution.task_executions.get()
    assert task.assigned_membership_id is None
    assert _by_title(_read(staff_membership), execution.title) is not None
    assert _by_title(_read(manager_membership), execution.title) is not None
    assert _by_title(_read(colleague), execution.title) is None

    task.assigned_membership = staff_membership
    task.save(update_fields=["assigned_membership"])
    staff_card = _by_title(_read(staff_membership), execution.title)
    assert [item.id for item in staff_card.tasks] == [task.id]
    assert _by_title(_read(manager_membership), execution.title) is None
    assert _by_title(_read(colleague), execution.title) is None


def test_owner_and_director_do_not_inherit_other_peoples_day(
    owner_membership, staff_membership, manager_membership, business_unit
):
    execution = assigned_execution(owner_membership, business_unit, staff_membership)
    execution.status = ActionPlanExecution.Status.PENDING_VALIDATION
    execution.save(update_fields=["status", "updated_at"])
    director = create_membership(
        establishment=owner_membership.establishment,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    assert _cards(_read(owner_membership), "action") == []
    assert _cards(_read(director), "action") == []
    assert _by_title(_read(manager_membership), execution.title).kind == "validate"


def test_undated_task_stays_actionable_when_the_plan_ends_later(
    owner_membership, staff_membership, business_unit
):
    execution = assigned_execution(owner_membership, business_unit, staff_membership, title="Sans échéance")
    execution.end_at = timezone.now() + timedelta(days=10)
    execution.save(update_fields=["end_at", "updated_at"])
    card = _by_title(_read(staff_membership), execution.title)
    assert card.section == "action"
    assert card.kind == "tasks"
    assert card.tasks[0].due_at is None
    assert card.plan_end_at == execution.end_at
    assert card.late is False


def test_one_card_keeps_late_and_future_tasks_together(
    owner_membership, staff_membership, business_unit
):
    staff_membership.establishment.timezone = "Europe/Paris"
    staff_membership.establishment.save(update_fields=["timezone"])
    as_of = datetime(2026, 10, 30, 22, 30, tzinfo=dt_timezone.utc)
    execution = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Retard et vendredi",
        assignees=[build_assignee_payload(membership=staff_membership, business_unit=business_unit)],
        tasks=[
            build_task_payload(
                task="Déjà due",
                business_unit=business_unit,
                position=1,
                deadline_at=datetime(2026, 10, 30, 21, 0, tzinfo=dt_timezone.utc),
                assigned_membership=staff_membership,
            ),
            build_task_payload(
                task="Vendredi",
                business_unit=business_unit,
                position=2,
                deadline_at=datetime(2026, 11, 6, 8, 0, tzinfo=dt_timezone.utc),
                assigned_membership=staff_membership,
            ),
        ],
    )
    reading = _read(staff_membership, now=as_of)
    matches = [card for card in _cards(reading, "action") if card.execution_id == execution.id]
    assert len(matches) == 1
    assert _by_title(reading, execution.title) is matches[0]
    assert [item.title for item in matches[0].tasks] == ["Déjà due", "Vendredi"]
    assert matches[0].late is True
    assert _cards(reading, "upcoming") == []


def test_future_tasks_only_make_one_upcoming_card(
    owner_membership, staff_membership, business_unit
):
    execution = assigned_execution(owner_membership, business_unit, staff_membership, title="Plus tard")
    task = execution.task_executions.get()
    task.deadline_at = timezone.now() + timedelta(days=4)
    task.assigned_membership = staff_membership
    task.save(update_fields=["deadline_at", "assigned_membership"])
    reading = _read(staff_membership)
    assert _by_title(reading, execution.title).section == "upcoming"
    assert len(_cards(reading, "upcoming")) == 1
    assert _cards(reading, "action") == []


def test_plan_without_tasks_is_work_for_its_assignee_only(
    owner_membership, staff_membership, manager_membership, business_unit, maintenance_business_unit
):
    create_membership_with_business_unit_scope(
        membership=staff_membership,
        business_unit=maintenance_business_unit,
    )
    execution = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Brief sans tâche",
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=maintenance_business_unit)
        ],
    )
    _drop_tasks(execution)
    card = _by_title(_read(staff_membership), execution.title)
    assert card.section == "action"
    assert card.kind == "realize"
    assert card.tasks == []
    assert _by_title(_read(manager_membership), execution.title) is None


def test_follow_copy_depends_on_tasks_the_member_actually_treated(
    owner_membership, staff_membership, business_unit
):
    colleague = create_membership(
        establishment=staff_membership.establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    create_membership_with_business_unit_scope(membership=colleague, business_unit=business_unit)
    untouched = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Rien à moi",
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit),
            build_assignee_payload(membership=colleague, business_unit=business_unit),
        ],
        tasks=[
            build_task_payload(
                task="Chez l'autre",
                business_unit=business_unit,
                assigned_membership=colleague,
            )
        ],
    )
    untouched_card = _by_title(_read(staff_membership), untouched.title)
    assert untouched_card.section == "follow"
    assert untouched_card.kind == "follow"
    assert untouched_card.own_tasks_done is False
    assert untouched_card.tasks == []

    treated = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Les miennes sont faites",
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit),
            build_assignee_payload(membership=colleague, business_unit=business_unit),
        ],
        tasks=[
            build_task_payload(
                task="La mienne",
                business_unit=business_unit,
                position=1,
                assigned_membership=staff_membership,
            ),
            build_task_payload(
                task="La sienne",
                business_unit=business_unit,
                position=2,
                assigned_membership=colleague,
            ),
        ],
    )
    mine = treated.task_executions.get(task="La mienne")
    mine.status = ActionPlanExecutionTask.Status.DONE
    mine.save(update_fields=["status"])
    treated_card = _by_title(_read(staff_membership), treated.title)
    assert treated_card.section == "follow"
    assert treated_card.own_tasks_done is True
    assert treated_card.tasks == []


def test_finalizing_and_relay_follow_who_can_close(
    owner_membership, staff_membership, manager_membership, business_unit, maintenance_business_unit
):
    contributor = create_membership(
        establishment=staff_membership.establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    create_membership_with_business_unit_scope(
        membership=contributor,
        business_unit=maintenance_business_unit,
    )
    pilot_plan = assigned_execution(
        owner_membership, business_unit, staff_membership, title="À clôturer"
    )
    task = pilot_plan.task_executions.get()
    task.status = ActionPlanExecutionTask.Status.DONE
    task.save(update_fields=["status"])
    assert _by_title(_read(staff_membership), pilot_plan.title).kind == "finalize"

    watched = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Suivi contributeur",
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit),
            build_assignee_payload(membership=contributor, business_unit=maintenance_business_unit),
        ],
        tasks=[
            build_task_payload(task="Faite", business_unit=business_unit, position=1),
            build_task_payload(
                task="Faite aussi",
                business_unit=maintenance_business_unit,
                position=2,
            ),
        ],
    )
    watched.task_executions.update(status=ActionPlanExecutionTask.Status.DONE)
    assert _by_title(_read(contributor), watched.title).section == "follow"
    assert _by_title(_read(staff_membership), watched.title).kind == "finalize"
    assert _by_title(_read(manager_membership), watched.title) is None

    relay = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Relais",
        assignees=[
            build_assignee_payload(membership=contributor, business_unit=maintenance_business_unit)
        ],
        tasks=[build_task_payload(task="Faite", business_unit=maintenance_business_unit)],
    )
    relay.task_executions.update(status=ActionPlanExecutionTask.Status.DONE)
    assert _by_title(_read(manager_membership), relay.title).kind == "relay"
    assert _by_title(_read(contributor), relay.title).section == "follow"
    assert _by_title(_read(staff_membership), relay.title) is None


def test_task_pole_is_shown_only_when_it_differs_from_the_pilot(
    owner_membership, staff_membership, business_unit, maintenance_business_unit
):
    create_membership_with_business_unit_scope(
        membership=staff_membership,
        business_unit=maintenance_business_unit,
    )
    execution = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Deux pôles",
        assignees=[build_assignee_payload(membership=staff_membership, business_unit=business_unit)],
        tasks=[
            build_task_payload(task="Pilote", business_unit=business_unit, position=1),
            build_task_payload(
                task="Ailleurs",
                business_unit=maintenance_business_unit,
                position=2,
            ),
        ],
    )
    card = _by_title(_read(staff_membership), execution.title)
    poles = {item.title: item.pole for item in card.tasks}
    assert poles["Pilote"] is None
    assert poles["Ailleurs"] == maintenance_business_unit.specific_name
    assert card.pilot_pole == business_unit.specific_name


def test_validation_is_shared_by_pilot_managers_and_hides_pending_tasks(
    owner_membership, staff_membership, manager_membership, business_unit
):
    other_manager = create_membership(
        establishment=manager_membership.establishment,
        role=EstablishmentMembership.Role.MANAGER,
    )
    create_membership_with_business_unit_scope(
        membership=other_manager,
        business_unit=business_unit,
    )
    execution = assigned_execution(
        owner_membership, business_unit, staff_membership, title="À valider"
    )
    task = execution.task_executions.get()
    task.assigned_membership = staff_membership
    task.save(update_fields=["assigned_membership"])
    execution.status = ActionPlanExecution.Status.PENDING_VALIDATION
    execution.save(update_fields=["status", "updated_at"])
    for manager in (manager_membership, other_manager):
        card = _by_title(_read(manager), execution.title)
        assert card.section == "action"
        assert card.kind == "validate"
        assert card.tasks == []
        assert card.late is False
    waiting = _by_title(_read(staff_membership), execution.title)
    assert waiting.section == "follow"
    assert waiting.kind == "awaiting_validation"
    assert waiting.tasks == []

    execution.status = ActionPlanExecution.Status.DONE
    execution.save(update_fields=["status", "updated_at"])
    assert _by_title(_read(manager_membership), execution.title) is None
    assert _by_title(_read(staff_membership), execution.title) is None

    execution.status = ActionPlanExecution.Status.IN_PROGRESS
    execution.save(update_fields=["status", "updated_at"])
    assert _by_title(_read(staff_membership), execution.title).kind == "tasks"
    assert _by_title(_read(manager_membership), execution.title) is None


def test_scheduled_visibility_and_terminal_statuses(
    owner_membership, staff_membership, business_unit
):
    far = assigned_execution(owner_membership, business_unit, staff_membership, title="Dans quarante jours")
    far.status = ActionPlanExecution.Status.SCHEDULED
    far.start_at = timezone.now() + timedelta(days=40)
    far.visible_from = timezone.now() - timedelta(hours=1)
    far.save(update_fields=["status", "start_at", "visible_from", "updated_at"])
    card = _by_title(_read(staff_membership), far.title)
    assert card.section == "upcoming"
    assert card.kind == "scheduled"
    assert card.late is False

    hidden = assigned_execution(owner_membership, business_unit, staff_membership, title="Pas encore visible")
    hidden.visible_from = timezone.now() + timedelta(days=2)
    hidden.save(update_fields=["visible_from", "updated_at"])
    done = assigned_execution(owner_membership, business_unit, staff_membership, title="Terminé")
    done.status = ActionPlanExecution.Status.DONE
    done.save(update_fields=["status", "updated_at"])
    canceled = assigned_execution(owner_membership, business_unit, staff_membership, title="Annulé")
    canceled.status = ActionPlanExecution.Status.CANCELED
    canceled.save(update_fields=["status", "updated_at"])
    reading = _read(staff_membership)
    assert _by_title(reading, hidden.title) is None
    assert _by_title(reading, done.title) is None
    assert _by_title(reading, canceled.title) is None


def test_my_day_does_not_promote_a_due_scheduled_execution(
    owner_membership, staff_membership, business_unit
):
    execution = assigned_execution(owner_membership, business_unit, staff_membership, title="Dû mais programmé")
    execution.status = ActionPlanExecution.Status.SCHEDULED
    execution.start_at = timezone.now() - timedelta(minutes=5)
    execution.visible_from = timezone.now() - timedelta(hours=1)
    execution.save(update_fields=["status", "start_at", "visible_from", "updated_at"])
    card = _by_title(_read(staff_membership), execution.title)
    assert card.kind == "scheduled"
    assert card.section == "upcoming"
    execution.refresh_from_db()
    assert execution.status == ActionPlanExecution.Status.SCHEDULED


def test_other_establishment_sees_nothing(owner_membership, staff_membership, business_unit):
    assigned_execution(owner_membership, business_unit, staff_membership)
    other = create_membership(establishment=create_establishment(), role="staff")
    assert _cards(_read(other), "action") == []


def test_cursor_rejects_garbage_age_and_auth_changes(
    api_client, owner_membership, staff_membership, business_unit
):
    from houston.testing.auth import auth_headers, login

    for index in range(MY_DAY_INITIAL_PAGE_SIZE + 1):
        assigned_execution(
            owner_membership,
            business_unit,
            staff_membership,
            title=f"Page {index}",
        )
    token = login(api_client, user=staff_membership.user)
    url = f"/api/v1/establishments/{staff_membership.establishment_id}/my-day/"
    first = api_client.get(url, **auth_headers(token))
    assert first.status_code == 200
    body = first.json()
    assert len(body["sections"]["action"]["items"]) == MY_DAY_INITIAL_PAGE_SIZE
    cursor = body["sections"]["action"]["next_cursor"]
    assert cursor
    assert api_client.get(url + "?cursor=%%%", **auth_headers(token)).status_code == 400
    assert api_client.get(url + "?section=action", **auth_headers(token)).status_code == 400
    stale = encode_my_day_cursor(
        section="action",
        sort_rank=2,
        sort_at=timezone.now(),
        execution_id=uuid4(),
        as_of=timezone.now() - timedelta(minutes=16),
        auth_hash="unused",
    )
    assert api_client.get(url + f"?section=action&cursor={stale}", **auth_headers(token)).status_code == 400

    scope_ids = _scope_ids(staff_membership)
    auth_hash = my_day_auth_context_hash(membership=staff_membership, scope_ids=scope_ids)
    parsed = parse_my_day_cursor(cursor, now=timezone.now(), auth_hash=auth_hash)
    staff_membership.role = EstablishmentMembership.Role.MANAGER
    staff_membership.save(update_fields=["role"])
    changed = my_day_auth_context_hash(membership=staff_membership, scope_ids=scope_ids)
    with pytest.raises(MyDayCursorError):
        parse_my_day_cursor(cursor, now=timezone.now(), auth_hash=changed)
    assert (
        api_client.get(url + f"?section=action&cursor={cursor}", **auth_headers(token)).status_code
        == 400
    )
    assert parsed.section == "action"


def test_continuation_keeps_the_first_pages_day_across_midnight(
    owner_membership, staff_membership, business_unit
):
    staff_membership.establishment.timezone = "Pacific/Honolulu"
    staff_membership.establishment.save(update_fields=["timezone"])
    as_of = datetime(2026, 11, 1, 9, 55, tzinfo=dt_timezone.utc)
    later = as_of + timedelta(minutes=10)
    execution = assigned_execution(owner_membership, business_unit, staff_membership, title="Autour de minuit")
    task = execution.task_executions.get()
    task.deadline_at = datetime(2026, 11, 1, 10, 30, tzinfo=dt_timezone.utc)
    task.assigned_membership = staff_membership
    task.save(update_fields=["deadline_at", "assigned_membership"])
    emerging = assigned_execution(owner_membership, business_unit, staff_membership, title="Devient visible")
    emerging.visible_from = as_of + timedelta(minutes=4)
    emerging.save(update_fields=["visible_from", "updated_at"])

    first = _read(staff_membership, now=as_of)
    card = _by_title(first, execution.title)
    assert card.section == "upcoming"
    assert _by_title(first, emerging.title) is None
    scope_ids = _scope_ids(staff_membership)
    auth_hash = my_day_auth_context_hash(membership=staff_membership, scope_ids=scope_ids)
    cursor = parse_my_day_cursor(
        encode_my_day_cursor(
            section=card.section,
            sort_rank=card.sort_rank,
            sort_at=card.sort_at,
            execution_id=card.execution_id,
            as_of=as_of,
            auth_hash=auth_hash,
        ),
        now=later,
        auth_hash=auth_hash,
    )
    continued = _read(staff_membership, cursor=cursor)
    assert continued.as_of == as_of
    fresh = _read(staff_membership, now=later)
    assert _by_title(fresh, execution.title).section == "action"
    assert _by_title(fresh, emerging.title) is not None
    assert continued.as_of < fresh.as_of


def test_api_contract_and_tenant_boundary(
    api_client, owner_membership, staff_membership, business_unit
):
    from houston.testing.auth import auth_headers, login

    execution = assigned_execution(owner_membership, business_unit, staff_membership)
    token = login(api_client, user=staff_membership.user)
    url = f"/api/v1/establishments/{staff_membership.establishment_id}/my-day/"
    response = api_client.get(url, **auth_headers(token))
    assert response.status_code == 200
    body = response.json()
    assert body["sections"]["action"]["count"] == 1
    item = body["sections"]["action"]["items"][0]
    assert item["execution_id"] == str(execution.id)
    assert item["tasks"][0]["shared"] is True
    assert item["tasks"][0]["pole"] is None
    assert item["pilot_pole"] == business_unit.specific_name
    other_site = create_establishment()
    assert (
        api_client.get(
            f"/api/v1/establishments/{other_site.id}/my-day/",
            **auth_headers(token),
        ).status_code
        == 404
    )


def test_pages_partition_a_section_without_offset(owner_membership, staff_membership, business_unit):
    base = timezone.now()
    for index in range(45):
        execution = assigned_execution(
            owner_membership,
            business_unit,
            staff_membership,
            title=f"Carte {index:02d}",
        )
        execution.last_activity_at = base - timedelta(seconds=index)
        execution.save(update_fields=["last_activity_at", "updated_at"])
    reading = _read(staff_membership)
    action = reading.sections["action"]
    assert action.count == 45
    assert len(action.items) == MY_DAY_INITIAL_PAGE_SIZE
    assert action.items[0].title == "Carte 00"
    seen = [card.execution_id for card in action.items]
    cursor_raw = action.next_cursor
    scope_ids = _scope_ids(staff_membership)
    auth_hash = my_day_auth_context_hash(membership=staff_membership, scope_ids=scope_ids)
    pages = 0
    while cursor_raw:
        pages += 1
        cursor = parse_my_day_cursor(cursor_raw, now=reading.as_of, auth_hash=auth_hash)
        page = _read(staff_membership, cursor=cursor)
        assert page.sections is None
        assert len(page.items) <= MY_DAY_CONTINUATION_PAGE_SIZE
        seen.extend(card.execution_id for card in page.items)
        cursor_raw = page.next_cursor
        _, queries = _queries(staff_membership, cursor=cursor)
        sql = " ".join(query["sql"] for query in queries)
        assert "OFFSET" not in sql.upper()
    remaining = 45 - MY_DAY_INITIAL_PAGE_SIZE
    assert pages == -(-remaining // MY_DAY_CONTINUATION_PAGE_SIZE)
    assert len(seen) == 45
    assert len(set(seen)) == 45


def test_selector_query_ceiling_does_not_follow_history(
    owner_membership, staff_membership, manager_membership, business_unit
):
    validation = assigned_execution(
        owner_membership, business_unit, staff_membership, title="Validation seule"
    )
    validation.status = ActionPlanExecution.Status.PENDING_VALIDATION
    validation.save(update_fields=["status", "updated_at"])
    _, quiet = _queries(manager_membership)
    assert len(_selector_sql(quiet)) == 1

    assigned_execution(owner_membership, business_unit, staff_membership, title="Avec tâche")
    _, busy = _queries(staff_membership)
    assert len(_selector_sql(busy)) == 2
    for query in busy:
        assert "OFFSET" not in query["sql"].upper()


def _walk_plan(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk_plan(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_plan(item)


def _explain(membership, *, seqscan_off: bool) -> list[dict]:
    _ = membership.establishment.timezone
    scope_ids = _scope_ids(membership)
    sql, params = my_day_classification_sql(
        membership=membership,
        scope_ids=scope_ids,
        as_of=timezone.now(),
    )
    with connection.cursor() as cursor:
        if seqscan_off:
            cursor.execute("SET LOCAL enable_seqscan = off")
        cursor.execute("EXPLAIN (FORMAT JSON) " + sql, params)
        return cursor.fetchone()[0]


def test_explain_can_use_the_assignee_and_execution_indexes(
    owner_membership, staff_membership, business_unit
):
    assigned_execution(owner_membership, business_unit, staff_membership)
    with connection.cursor() as cursor:
        cursor.execute("ANALYZE action_plans_actionplanassignee")
        cursor.execute("ANALYZE action_plans_actionplanexecution")
    plan = _explain(staff_membership, seqscan_off=True)
    index_names = {
        node.get("Index Name")
        for node in _walk_plan(plan)
        if node.get("Index Name")
    }
    assert "ap_assignee_member_visible_idx" in index_names
    assert "Seq Scan" not in _execution_scan_types(plan)
    task_scans = [
        node.get("Node Type")
        for node in _walk_plan(plan)
        if node.get("Relation Name") == ActionPlanExecutionTask._meta.db_table
        and node.get("Node Type") == "Seq Scan"
    ]
    assert task_scans == []


def _insert_executions(
    *,
    establishment,
    actor,
    poles,
    people,
    count,
    status,
    tasks_each,
    start_at=None,
    visible_from=None,
):
    now = timezone.now()
    executions = [
        ActionPlanExecution(
            establishment=establishment,
            created_by=actor,
            title=f"{status}-{index}-{uuid4().hex[:8]}",
            pilot_business_unit=poles[index % len(poles)],
            status=status,
            use_shared_chronology=True,
            last_activity_at=now - timedelta(seconds=index),
            start_at=start_at,
            visible_from=visible_from,
            requires_validation=False,
        )
        for index in range(count)
    ]
    ActionPlanExecution.objects.bulk_create(executions, batch_size=500)
    teams = [
        ActionPlanExecutionTeam(
            action_plan_execution=execution,
            business_unit=execution.pilot_business_unit,
            is_pilot=True,
        )
        for execution in executions
    ]
    ActionPlanExecutionTeam.objects.bulk_create(teams, batch_size=500)
    team_by_execution = {team.action_plan_execution_id: team for team in teams}
    assignees = []
    tasks = []
    for index, execution in enumerate(executions):
        team = team_by_execution[execution.id]
        assignees.append(
            ActionPlanAssignee(
                action_plan_execution=execution,
                execution_team=team,
                membership=people[index % len(people)],
            )
        )
        for position in range(1, tasks_each + 1):
            assigned = None
            if position % 3 != 0:
                assigned = people[(index + position) % len(people)]
            deadline = None
            if position == 2:
                deadline = now - timedelta(hours=2)
            elif position == 3:
                deadline = now + timedelta(days=5)
            tasks.append(
                ActionPlanExecutionTask(
                    action_plan_execution=execution,
                    execution_team=team,
                    task=f"Tâche {position}",
                    position=position,
                    status=ActionPlanExecutionTask.Status.PENDING,
                    deadline_at=deadline,
                    assigned_membership=assigned,
                )
            )
    ActionPlanAssignee.objects.bulk_create(assignees, batch_size=500)
    if tasks:
        ActionPlanExecutionTask.objects.bulk_create(tasks, batch_size=1000)
    return executions


def _analyze_my_day_tables():
    with connection.cursor() as cursor:
        for table in (
            ActionPlanExecution._meta.db_table,
            ActionPlanAssignee._meta.db_table,
            ActionPlanExecutionTask._meta.db_table,
            ActionPlanExecutionTeam._meta.db_table,
        ):
            cursor.execute(f"ANALYZE {table}")


def _execution_scan_types(plan) -> list[str]:
    return [
        node.get("Node Type")
        for node in _walk_plan(plan)
        if node.get("Relation Name") == ActionPlanExecution._meta.db_table
    ]


def test_volume_keeps_one_classification_and_the_feed_index(
    owner_membership,
    staff_membership,
    manager_membership,
    business_unit,
    maintenance_business_unit,
    catalog_action_plan,
):
    from houston.action_plans.schedule_services import create_action_plan_schedule

    establishment = owner_membership.establishment
    third = create_business_unit(establishment=establishment, key="housekeeping", label="Housekeeping")
    other_staff = create_membership(establishment=establishment, role=EstablishmentMembership.Role.STAFF)
    create_membership_with_business_unit_scope(membership=other_staff, business_unit=business_unit)
    for pole in (business_unit, maintenance_business_unit, third):
        MembershipScope.objects.get_or_create(
            membership=manager_membership,
            business_unit=pole,
            defaults={"establishment": establishment},
        )
    poles = [business_unit, maintenance_business_unit, third]
    people = [staff_membership, other_staff]
    _insert_executions(
        establishment=establishment,
        actor=owner_membership,
        poles=poles,
        people=people,
        count=30,
        status=ActionPlanExecution.Status.IN_PROGRESS,
        tasks_each=5,
    )
    _, at_thirty = _queries(staff_membership)
    assert len(_selector_sql(at_thirty)) == 2

    _insert_executions(
        establishment=establishment,
        actor=owner_membership,
        poles=poles,
        people=people,
        count=170,
        status=ActionPlanExecution.Status.IN_PROGRESS,
        tasks_each=5,
    )
    _insert_executions(
        establishment=establishment,
        actor=owner_membership,
        poles=poles,
        people=[manager_membership],
        count=20,
        status=ActionPlanExecution.Status.PENDING_VALIDATION,
        tasks_each=1,
    )
    _insert_executions(
        establishment=establishment,
        actor=owner_membership,
        poles=poles,
        people=people,
        count=20,
        status=ActionPlanExecution.Status.SCHEDULED,
        tasks_each=1,
        start_at=timezone.now() + timedelta(days=40),
        visible_from=timezone.now() - timedelta(hours=1),
    )
    _insert_executions(
        establishment=establishment,
        actor=owner_membership,
        poles=poles,
        people=people,
        count=300,
        status=ActionPlanExecution.Status.DONE,
        tasks_each=1,
    )
    later = timezone.now() + timedelta(days=3)
    create_action_plan_schedule(
        action_plan=catalog_action_plan,
        actor=owner_membership,
        recurrence_days=["monday", "wednesday", "friday"],
        assignees=[
            build_schedule_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
        use_shared_chronology=True,
        **schedule_window_from_datetime(later),
    )
    assert not ActionPlanExecution.objects.filter(
        establishment=establishment,
        status=ActionPlanExecution.Status.SCHEDULED,
        start_at__lte=timezone.now(),
    ).exists()

    named = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Tâche nominative de l'autre",
        assignees=[build_assignee_payload(membership=other_staff, business_unit=business_unit)],
        tasks=[
            build_task_payload(
                task="Privée",
                business_unit=business_unit,
                assigned_membership=other_staff,
            )
        ],
    )
    shared = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Collectif du pôle",
        assignees=[build_assignee_payload(membership=other_staff, business_unit=business_unit)],
        tasks=[build_task_payload(task="Pour le pôle", business_unit=business_unit)],
    )
    staff_reading = _read(staff_membership)
    manager_reading = _read(manager_membership)
    assert _by_title(staff_reading, named.title) is None
    assert _by_title(manager_reading, named.title) is None
    shared_card = _by_title(manager_reading, shared.title)
    assert shared_card is not None
    assert shared_card.tasks[0].shared is True
    for section in staff_reading.sections.values():
        assert len(section.items) <= MY_DAY_INITIAL_PAGE_SIZE
        assert section.count >= len(section.items)
    _, at_two_hundred = _queries(staff_membership)
    assert len(_selector_sql(at_two_hundred)) == len(_selector_sql(at_thirty))
    cursor = staff_reading.sections["action"].next_cursor
    if cursor is not None:
        scope_ids = _scope_ids(staff_membership)
        parsed = parse_my_day_cursor(
            cursor,
            now=staff_reading.as_of,
            auth_hash=my_day_auth_context_hash(membership=staff_membership, scope_ids=scope_ids),
        )
        page, page_queries = _queries(staff_membership, cursor=parsed)
        assert len(page.items) <= MY_DAY_CONTINUATION_PAGE_SIZE
        assert page.as_of == staff_reading.as_of
        assert all("OFFSET" not in query["sql"].upper() for query in page_queries)
        assert len(_selector_sql(page_queries)) <= 2

    _analyze_my_day_tables()
    forced = _explain(staff_membership, seqscan_off=True)
    forced_indexes = {
        node.get("Index Name") for node in _walk_plan(forced) if node.get("Index Name")
    }
    assert "ap_assignee_member_visible_idx" in forced_indexes
    assert "ap_exec_feed_idx" in forced_indexes

    _insert_executions(
        establishment=establishment,
        actor=owner_membership,
        poles=poles,
        people=people,
        count=800,
        status=ActionPlanExecution.Status.IN_PROGRESS,
        tasks_each=5,
    )
    _analyze_my_day_tables()
    _, at_thousand = _queries(staff_membership)
    assert len(_selector_sql(at_thousand)) == 2
    started = timezone.now()
    _read(staff_membership)
    assert (timezone.now() - started).total_seconds() < 2
    free = _explain(staff_membership, seqscan_off=False)
    assert "Seq Scan" not in _execution_scan_types(free), _execution_scan_types(free)
    free_indexes = {node.get("Index Name") for node in _walk_plan(free) if node.get("Index Name")}
    assert "ap_exec_feed_idx" in free_indexes


def test_get_does_not_materialize_or_promote_and_stays_flat(
    api_client, owner_membership, staff_membership, business_unit
):
    from houston.testing.auth import auth_headers, login

    _insert_executions(
        establishment=owner_membership.establishment,
        actor=owner_membership,
        poles=[business_unit],
        people=[staff_membership],
        count=20,
        status=ActionPlanExecution.Status.IN_PROGRESS,
        tasks_each=2,
    )
    director = create_membership(
        establishment=owner_membership.establishment,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    url = f"/api/v1/establishments/{owner_membership.establishment_id}/my-day/"

    def get_count(membership):
        token = login(api_client, user=membership.user)
        with (
            patch(
                "houston.action_plans.materialization.ensure_visible_action_plan_executions_materialized"
            ) as materialized,
            patch(
                "houston.action_plans.lifecycle_promotion.ensure_execution_lifecycle_for_read"
            ) as promoted,
            CaptureQueriesContext(connection) as captured,
        ):
            response = api_client.get(url, **auth_headers(token))
        assert response.status_code == 200
        assert materialized.call_count == 0
        assert promoted.call_count == 0
        return len(captured.captured_queries)

    before = get_count(staff_membership)
    director_before = get_count(director)
    _insert_executions(
        establishment=owner_membership.establishment,
        actor=owner_membership,
        poles=[business_unit],
        people=[staff_membership],
        count=80,
        status=ActionPlanExecution.Status.IN_PROGRESS,
        tasks_each=2,
    )
    assert get_count(staff_membership) == before
    assert get_count(director) == director_before


def test_horizon_task_creates_the_row_my_day_does_not_invent(
    owner_membership, staff_membership, business_unit, catalog_action_plan
):
    from houston.action_plans.schedule_services import create_action_plan_schedule
    from houston.action_plans.tasks import materialize_action_plan_schedules_horizon_task

    later = timezone.now() + timedelta(days=2)
    schedule = create_action_plan_schedule(
        action_plan=catalog_action_plan,
        actor=owner_membership,
        recurrence_days=["monday", "tuesday", "wednesday", "thursday", "friday"],
        assignees=[
            build_schedule_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
        use_shared_chronology=True,
        **schedule_window_from_datetime(later),
    )
    ActionPlanExecution.objects.filter(action_plan_schedule=schedule).delete()
    _read(staff_membership)
    assert not ActionPlanExecution.objects.filter(action_plan_schedule=schedule).exists()
    created = materialize_action_plan_schedules_horizon_task(
        establishment_id=str(owner_membership.establishment_id),
    )
    assert created > 0
    execution = ActionPlanExecution.objects.filter(action_plan_schedule=schedule).first()
    assert execution is not None
    execution.visible_from = timezone.now() - timedelta(minutes=1)
    execution.save(update_fields=["visible_from", "updated_at"])
    execution.assignees.update(visible_from=execution.visible_from)
    assert _by_title(_read(staff_membership), execution.title) is not None


def test_promotion_tick_is_batched_and_my_day_waits_for_it(
    owner_membership, staff_membership, business_unit
):
    from houston.action_plans.tasks import promote_scheduled_action_plan_executions_task

    past = timezone.now() - timedelta(minutes=10)
    _insert_executions(
        establishment=owner_membership.establishment,
        actor=owner_membership,
        poles=[business_unit],
        people=[staff_membership],
        count=201,
        status=ActionPlanExecution.Status.SCHEDULED,
        tasks_each=0,
        start_at=past,
        visible_from=past,
    )
    first = promote_scheduled_action_plan_executions_task()
    assert first == {"promoted": 200, "availability_emitted": 200}
    remaining = ActionPlanExecution.objects.get(
        establishment=owner_membership.establishment,
        status=ActionPlanExecution.Status.SCHEDULED,
        start_at__lte=timezone.now(),
    )
    card = _by_title(_read(staff_membership), remaining.title)
    assert card.kind == "scheduled"
    assert card.section == "upcoming"
    second = promote_scheduled_action_plan_executions_task()
    assert second["promoted"] == 1
    remaining.refresh_from_db()
    assert remaining.status == ActionPlanExecution.Status.IN_PROGRESS
    assert _by_title(_read(staff_membership), remaining.title).kind == "realize"

