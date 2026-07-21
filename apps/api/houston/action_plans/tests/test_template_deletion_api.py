from __future__ import annotations

import pytest
from django.utils import timezone

from houston.action_plans.constants import (
    CANCEL_ORIGIN_MANUAL,
    CATALOG_STATUS_ACTIVE,
    EXECUTION_STATUS_CANCELED,
    EXECUTION_STATUS_DONE,
    EXECUTION_STATUS_IN_PROGRESS,
    EXECUTION_STATUS_PENDING_VALIDATION,
    EXECUTION_STATUS_SCHEDULED,
)
from houston.action_plans.models import (
    ActionPlan,
    ActionPlanExecution,
    ActionPlanSchedule,
    ActionPlanTask,
)
from houston.action_plans.services import create_execution_from_action_plan
from houston.action_plans.tests.helpers import (
    action_plan_url,
    build_assignee_payload,
    create_catalog_action_plan,
)
from houston.establishments.models import EstablishmentMembership
from houston.observations.models import Observation
from houston.testing.auth import auth_headers, login
from houston.testing.factories import create_establishment, create_membership
from houston.testing.taxonomy import create_business_unit

pytestmark = pytest.mark.django_db


def _make_scheduled_execution(
    *,
    catalog_action_plan,
    owner_membership,
    staff_membership,
    business_unit,
):
    start_at = timezone.now() + timezone.timedelta(days=2)
    return create_execution_from_action_plan(
        action_plan_id=catalog_action_plan.id,
        actor=owner_membership,
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
        start_at=start_at,
        end_at=start_at + timezone.timedelta(hours=1),
        visible_from=start_at - timezone.timedelta(hours=1),
        emit_side_effects=False,
    )


def _make_started_execution(
    *,
    catalog_action_plan,
    owner_membership,
    staff_membership,
    business_unit,
):
    return create_execution_from_action_plan(
        action_plan_id=catalog_action_plan.id,
        actor=owner_membership,
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
        emit_side_effects=False,
    )


def test_owner_can_delete_active_template(api_client, owner_membership, catalog_action_plan):
    token = login(api_client, user=owner_membership.user)
    response = api_client.delete(
        action_plan_url(owner_membership.establishment_id, catalog_action_plan.id),
        **auth_headers(token),
    )
    assert response.status_code == 204
    assert response.content == b""
    assert not ActionPlan.objects.filter(id=catalog_action_plan.id).exists()


def test_director_can_delete_template(
    api_client,
    establishment,
    business_unit,
    owner_membership,
):
    director = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    plan = create_catalog_action_plan(
        owner_membership=owner_membership,
        business_unit=business_unit,
    )
    token = login(api_client, user=director.user)
    response = api_client.delete(
        action_plan_url(establishment.id, plan.id),
        **auth_headers(token),
    )
    assert response.status_code == 204
    assert not ActionPlan.objects.filter(id=plan.id).exists()


@pytest.mark.parametrize(
    "membership_fixture",
    ["manager_membership", "staff_membership"],
)
def test_manager_and_staff_cannot_delete_template(
    request,
    api_client,
    catalog_action_plan,
    membership_fixture,
):
    membership = request.getfixturevalue(membership_fixture)
    token = login(api_client, user=membership.user)
    response = api_client.delete(
        action_plan_url(membership.establishment_id, catalog_action_plan.id),
        **auth_headers(token),
    )
    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert ActionPlan.objects.filter(id=catalog_action_plan.id).exists()


def test_owner_can_delete_inactive_template(
    api_client,
    owner_membership,
    business_unit,
    inactive_catalog_action_plan,
):
    ActionPlanTask.objects.create(
        action_plan=inactive_catalog_action_plan,
        business_unit=business_unit,
        task="Task",
        position=1,
    )
    token = login(api_client, user=owner_membership.user)
    response = api_client.delete(
        action_plan_url(owner_membership.establishment_id, inactive_catalog_action_plan.id),
        **auth_headers(token),
    )
    assert response.status_code == 204
    assert not ActionPlan.objects.filter(id=inactive_catalog_action_plan.id).exists()


def test_delete_mixed_execution_statuses(
    api_client,
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    scheduled = _make_scheduled_execution(
        catalog_action_plan=catalog_action_plan,
        owner_membership=owner_membership,
        staff_membership=staff_membership,
        business_unit=business_unit,
    )
    in_progress = _make_started_execution(
        catalog_action_plan=catalog_action_plan,
        owner_membership=owner_membership,
        staff_membership=staff_membership,
        business_unit=business_unit,
    )
    assert in_progress.status == EXECUTION_STATUS_IN_PROGRESS

    pending = _make_started_execution(
        catalog_action_plan=catalog_action_plan,
        owner_membership=owner_membership,
        staff_membership=staff_membership,
        business_unit=business_unit,
    )
    pending.status = EXECUTION_STATUS_PENDING_VALIDATION
    pending.save(update_fields=["status", "updated_at"])

    done = _make_started_execution(
        catalog_action_plan=catalog_action_plan,
        owner_membership=owner_membership,
        staff_membership=staff_membership,
        business_unit=business_unit,
    )
    done.status = EXECUTION_STATUS_DONE
    done.marked_done_at = timezone.now()
    done.save(update_fields=["status", "marked_done_at", "updated_at"])

    canceled = _make_started_execution(
        catalog_action_plan=catalog_action_plan,
        owner_membership=owner_membership,
        staff_membership=staff_membership,
        business_unit=business_unit,
    )
    canceled.status = EXECUTION_STATUS_CANCELED
    canceled.canceled_at = timezone.now()
    canceled.cancel_origin = CANCEL_ORIGIN_MANUAL
    canceled.save(update_fields=["status", "canceled_at", "cancel_origin", "updated_at"])

    schedule = ActionPlanSchedule.objects.create(
        action_plan=catalog_action_plan,
        establishment=catalog_action_plan.establishment,
        created_by=owner_membership,
        start_date=timezone.now().date(),
        end_date=timezone.now().date(),
        start_at=timezone.now().time().replace(microsecond=0),
        end_at=(timezone.now() + timezone.timedelta(hours=1)).time().replace(microsecond=0),
        use_shared_chronology=True,
    )
    keep_ids = [in_progress.id, pending.id, done.id, canceled.id]

    token = login(api_client, user=owner_membership.user)
    response = api_client.delete(
        action_plan_url(owner_membership.establishment_id, catalog_action_plan.id),
        **auth_headers(token),
    )
    assert response.status_code == 204

    assert not ActionPlan.objects.filter(id=catalog_action_plan.id).exists()
    assert not ActionPlanSchedule.objects.filter(id=schedule.id).exists()
    assert not ActionPlanExecution.objects.filter(id=scheduled.id).exists()

    for execution_id in keep_ids:
        execution = ActionPlanExecution.objects.get(id=execution_id)
        assert execution.action_plan_id is None
        assert execution.action_plan_schedule_id is None


def test_delete_blocked_by_observation_rolls_back(
    api_client,
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    scheduled = _make_scheduled_execution(
        catalog_action_plan=catalog_action_plan,
        owner_membership=owner_membership,
        staff_membership=staff_membership,
        business_unit=business_unit,
    )
    Observation.objects.create(
        establishment_id=scheduled.establishment_id,
        submitted_by_membership=owner_membership,
        raw_text="Blocks delete",
        origin=Observation.Origin.DIRECT_REPORT,
        action_plan_execution=scheduled,
        submitted_at=timezone.now(),
    )

    token = login(api_client, user=owner_membership.user)
    response = api_client.delete(
        action_plan_url(owner_membership.establishment_id, catalog_action_plan.id),
        **auth_headers(token),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "execution_observation_integrity"
    assert ActionPlan.objects.filter(id=catalog_action_plan.id).exists()
    assert ActionPlanExecution.objects.filter(id=scheduled.id).exists()
    catalog_action_plan.refresh_from_db()
    assert catalog_action_plan.catalog_status == CATALOG_STATUS_ACTIVE
    scheduled.refresh_from_db()
    assert scheduled.action_plan_id == catalog_action_plan.id
    assert scheduled.status == EXECUTION_STATUS_SCHEDULED


def test_delete_other_establishment_returns_404(
    api_client,
    owner_membership,
    catalog_action_plan,
):
    other = create_establishment(name="Other hotel")
    other_owner = create_membership(
        establishment=other,
        role=EstablishmentMembership.Role.OWNER,
    )
    create_business_unit(establishment=other, key="restaurant")
    token = login(api_client, user=other_owner.user)
    response = api_client.delete(
        action_plan_url(other.id, catalog_action_plan.id),
        **auth_headers(token),
    )
    assert response.status_code == 404
    assert ActionPlan.objects.filter(id=catalog_action_plan.id).exists()


def test_double_delete_returns_404(api_client, owner_membership, catalog_action_plan):
    token = login(api_client, user=owner_membership.user)
    url = action_plan_url(owner_membership.establishment_id, catalog_action_plan.id)
    first = api_client.delete(url, **auth_headers(token))
    assert first.status_code == 204
    second = api_client.delete(url, **auth_headers(token))
    assert second.status_code == 404


def test_detail_exposes_can_delete_hint_for_owner(
    api_client,
    owner_membership,
    catalog_action_plan,
):
    token = login(api_client, user=owner_membership.user)
    response = api_client.get(
        action_plan_url(owner_membership.establishment_id, catalog_action_plan.id),
        **auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["permission_hints"]["can_delete"] is True


def test_detail_can_delete_false_for_manager(
    api_client,
    manager_membership,
    catalog_action_plan,
):
    token = login(api_client, user=manager_membership.user)
    response = api_client.get(
        action_plan_url(manager_membership.establishment_id, catalog_action_plan.id),
        **auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["permission_hints"]["can_delete"] is False
