from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from django.db import close_old_connections
from django.test import TransactionTestCase

from houston.action_plans.constants import CATALOG_STATUS_INACTIVE
from houston.action_plans.models import (
    ActionPlanExecution,
    ActionPlanMixedOutboxEntry,
    ActionPlanMixedSubmission,
    ActionPlanSchedule,
)
from houston.action_plans.tests.helpers import (
    action_plan_mixed_submit_url,
    api_mixed_submit_payload,
)
from houston.establishments.models import EstablishmentMembership
from houston.testing.auth import auth_headers, login

pytestmark = pytest.mark.django_db


def _submit_mixed(
    api_client,
    *,
    token,
    establishment_id,
    action_plan_id,
    payload,
):
    return api_client.post(
        action_plan_mixed_submit_url(establishment_id, action_plan_id),
        payload,
        format="json",
        **auth_headers(token),
    )


def test_mixed_submit_creates_schedule_and_one_shot_execution(
    api_client,
    owner_membership,
    staff_membership,
    manager_membership,
    catalog_action_plan,
    business_unit,
):
    token = login(api_client, user=owner_membership.user)
    submission_id = uuid.uuid4()
    payload = api_mixed_submit_payload(
        submission_id=submission_id,
        recurring_membership=staff_membership,
        one_shot_membership=manager_membership,
        business_unit=business_unit,
    )

    response = _submit_mixed(
        api_client,
        token=token,
        establishment_id=owner_membership.establishment_id,
        action_plan_id=catalog_action_plan.id,
        payload=payload,
    )

    assert response.status_code == 201, response.json()
    body = response.json()
    assert body["replayed"] is False
    assert body["schedule_id"]
    assert body["execution"]["id"]

    submission = ActionPlanMixedSubmission.objects.get(submission_id=submission_id)
    assert submission.schedule_id is not None
    assert submission.execution_id is not None
    assert ActionPlanSchedule.objects.filter(id=submission.schedule_id).count() == 1
    assert ActionPlanExecution.objects.filter(id=submission.execution_id).count() == 1
    assert ActionPlanMixedOutboxEntry.objects.filter(mixed_submission=submission).exists()


def test_mixed_submit_replay_returns_200_without_duplicates(
    api_client,
    owner_membership,
    staff_membership,
    manager_membership,
    catalog_action_plan,
    business_unit,
):
    token = login(api_client, user=owner_membership.user)
    submission_id = uuid.uuid4()
    payload = api_mixed_submit_payload(
        submission_id=submission_id,
        recurring_membership=staff_membership,
        one_shot_membership=manager_membership,
        business_unit=business_unit,
    )

    first = _submit_mixed(
        api_client,
        token=token,
        establishment_id=owner_membership.establishment_id,
        action_plan_id=catalog_action_plan.id,
        payload=payload,
    )
    assert first.status_code == 201

    second = _submit_mixed(
        api_client,
        token=token,
        establishment_id=owner_membership.establishment_id,
        action_plan_id=catalog_action_plan.id,
        payload=payload,
    )
    assert second.status_code == 200, second.json()
    assert second.json()["replayed"] is True
    assert ActionPlanMixedSubmission.objects.count() == 1
    assert ActionPlanSchedule.objects.count() == 1
    assert (
        ActionPlanExecution.objects.filter(action_plan_schedule_id=second.json()["schedule_id"])
        .count()
        == ActionPlanExecution.objects.filter(
            action_plan_schedule_id=first.json()["schedule_id"]
        ).count()
    )


def test_mixed_submit_conflict_on_payload_mismatch(
    api_client,
    owner_membership,
    staff_membership,
    manager_membership,
    catalog_action_plan,
    business_unit,
):
    token = login(api_client, user=owner_membership.user)
    submission_id = uuid.uuid4()
    first_payload = api_mixed_submit_payload(
        submission_id=submission_id,
        recurring_membership=staff_membership,
        one_shot_membership=manager_membership,
        business_unit=business_unit,
    )
    assert _submit_mixed(
        api_client,
        token=token,
        establishment_id=owner_membership.establishment_id,
        action_plan_id=catalog_action_plan.id,
        payload=first_payload,
    ).status_code == 201

    second_payload = api_mixed_submit_payload(
        submission_id=submission_id,
        recurring_membership=manager_membership,
        one_shot_membership=staff_membership,
        business_unit=business_unit,
    )
    response = _submit_mixed(
        api_client,
        token=token,
        establishment_id=owner_membership.establishment_id,
        action_plan_id=catalog_action_plan.id,
        payload=second_payload,
    )
    assert response.status_code == 409
    assert response.json()["code"] == "mixed_submission_conflict"


def test_mixed_submit_actor_conflict(
    api_client,
    owner_membership,
    manager_membership,
    staff_membership,
    catalog_action_plan,
    business_unit,
):
    owner_token = login(api_client, user=owner_membership.user)
    manager_token = login(api_client, user=manager_membership.user)
    submission_id = uuid.uuid4()
    payload = api_mixed_submit_payload(
        submission_id=submission_id,
        recurring_membership=staff_membership,
        one_shot_membership=manager_membership,
        business_unit=business_unit,
    )
    assert _submit_mixed(
        api_client,
        token=owner_token,
        establishment_id=owner_membership.establishment_id,
        action_plan_id=catalog_action_plan.id,
        payload=payload,
    ).status_code == 201

    response = _submit_mixed(
        api_client,
        token=manager_token,
        establishment_id=manager_membership.establishment_id,
        action_plan_id=catalog_action_plan.id,
        payload=payload,
    )
    assert response.status_code == 403
    assert response.json()["code"] == "mixed_submission_actor_conflict"


def test_mixed_submit_replay_forbidden_when_permissions_revoked(
    api_client,
    owner_membership,
    staff_membership,
    manager_membership,
    catalog_action_plan,
    business_unit,
):
    token = login(api_client, user=owner_membership.user)
    submission_id = uuid.uuid4()
    payload = api_mixed_submit_payload(
        submission_id=submission_id,
        recurring_membership=staff_membership,
        one_shot_membership=manager_membership,
        business_unit=business_unit,
    )
    assert _submit_mixed(
        api_client,
        token=token,
        establishment_id=owner_membership.establishment_id,
        action_plan_id=catalog_action_plan.id,
        payload=payload,
    ).status_code == 201

    catalog_action_plan.catalog_status = CATALOG_STATUS_INACTIVE
    catalog_action_plan.save(update_fields=["catalog_status", "updated_at"])

    response = _submit_mixed(
        api_client,
        token=token,
        establishment_id=owner_membership.establishment_id,
        action_plan_id=catalog_action_plan.id,
        payload=payload,
    )
    assert response.status_code == 403


def test_mixed_submit_failed_use_rolls_back_submission(
    api_client,
    owner_membership,
    staff_membership,
    catalog_action_plan,
    business_unit,
):
    token = login(api_client, user=owner_membership.user)
    submission_id = uuid.uuid4()
    payload = api_mixed_submit_payload(
        submission_id=submission_id,
        recurring_membership=staff_membership,
        one_shot_membership=staff_membership,
        business_unit=business_unit,
    )
    payload["use_body"]["assignees"] = [
        {
            "membership_id": str(uuid.uuid4()),
            "business_unit_id": str(business_unit.id),
        }
    ]

    response = _submit_mixed(
        api_client,
        token=token,
        establishment_id=owner_membership.establishment_id,
        action_plan_id=catalog_action_plan.id,
        payload=payload,
    )
    assert response.status_code == 400
    assert response.json()["failed_step"] == "use"
    assert ActionPlanMixedSubmission.objects.count() == 0
    assert ActionPlanSchedule.objects.count() == 0
    assert ActionPlanMixedOutboxEntry.objects.count() == 0


class MixedSubmissionConcurrencyTests(TransactionTestCase):
    def test_concurrent_mixed_submit_is_idempotent(self):
        from rest_framework.test import APIClient

        from houston.action_plans.tests.helpers import create_catalog_action_plan
        from houston.testing.factories import create_establishment, create_membership
        from houston.testing.taxonomy import (
            create_business_unit,
            create_membership_with_business_unit_scope,
        )

        establishment = create_establishment(name="Mixed Concurrent Hotel", timezone="UTC")
        business_unit = create_business_unit(establishment=establishment, key="bar")
        owner = create_membership(
            establishment=establishment,
            role=EstablishmentMembership.Role.OWNER,
        )
        staff = create_membership(
            establishment=establishment,
            role=EstablishmentMembership.Role.STAFF,
        )
        manager = create_membership(
            establishment=establishment,
            role=EstablishmentMembership.Role.MANAGER,
        )
        create_membership_with_business_unit_scope(membership=staff, business_unit=business_unit)
        create_membership_with_business_unit_scope(membership=manager, business_unit=business_unit)
        plan = create_catalog_action_plan(owner_membership=owner, business_unit=business_unit)
        submission_id = uuid.uuid4()
        payload = api_mixed_submit_payload(
            submission_id=submission_id,
            recurring_membership=staff,
            one_shot_membership=manager,
            business_unit=business_unit,
        )

        def submit(_: int) -> int:
            close_old_connections()
            try:
                client = APIClient(enforce_csrf_checks=True)
                token = login(client, user=owner.user)
                response = client.post(
                    action_plan_mixed_submit_url(establishment.id, plan.id),
                    payload,
                    format="json",
                    **auth_headers(token),
                )
                return response.status_code
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            statuses = list(executor.map(submit, range(2)))

        assert sorted(statuses) == [200, 201]
        assert ActionPlanMixedSubmission.objects.count() == 1
        assert ActionPlanSchedule.objects.count() == 1
