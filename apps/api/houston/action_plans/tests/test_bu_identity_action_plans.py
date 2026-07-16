"""Action Plan × BusinessUnit Lot 5 identity alignment (P0/P1)."""

from __future__ import annotations

import pytest

from houston.action_plans.api.serializers import (
    _serialize_activity_subject,
    _serialize_business_unit,
    serialize_execution_detail,
)
from houston.action_plans.exceptions import ActionPlanValidationError
from houston.action_plans.services import create_action_plan_with_execution
from houston.action_plans.tests.helpers import (
    action_plan_url,
    build_assignee_payload,
    build_task_payload,
)
from houston.establishments.models import CatalogBusinessUnit
from houston.establishments.public_serialization import serialize_business_unit_ref
from houston.testing.auth import auth_headers, login
from houston.testing.taxonomy import (
    create_activity_subject,
    create_business_unit,
    create_v3_signal,
)

pytestmark = pytest.mark.django_db


def _assert_lot5_business_unit_shape(payload: dict) -> None:
    assert set(payload.keys()) == {
        "id",
        "specific_name",
        "instance_description",
        "active",
        "generic",
    }
    assert "routing_key" not in payload
    assert "key" not in payload
    assert "label" not in payload
    assert set(payload["generic"].keys()) == {
        "key",
        "label",
        "description",
        "unit_type",
    }


def test_signal_detail_exposes_responsible_affected_activity_subject_ids(
    api_client,
    owner_membership,
    business_unit,
    maintenance_business_unit,
):
    subject = create_activity_subject(
        establishment=owner_membership.establishment,
        business_unit=maintenance_business_unit,
        label="Électricité",
    )
    signal = create_v3_signal(
        owner_membership.establishment,
        affected_business_unit=business_unit,
        responsible_business_unit=maintenance_business_unit,
        activity_subject=subject,
        title="Taxonomy ids signal",
    )
    token = login(api_client, user=owner_membership.user)
    response = api_client.get(
        f"/api/v1/establishments/{owner_membership.establishment_id}/signals/{signal.id}/",
        **auth_headers(token),
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["affected_business_unit_id"] == str(business_unit.id)
    assert payload["responsible_business_unit_id"] == str(maintenance_business_unit.id)
    assert payload["activity_subject_id"] == str(subject.id)
    assert payload["affected_business_unit_key"] == business_unit.key
    assert payload["responsible_business_unit_key"] == maintenance_business_unit.key
    assert payload["affected_business_unit_label"] == business_unit.label
    assert payload["responsible_business_unit_label"] == maintenance_business_unit.label


def test_linked_create_pilot_matches_responsible_uuid_not_catalog_key(
    owner_membership,
):
    catalog, _ = CatalogBusinessUnit.objects.get_or_create(
        key="restaurant",
        defaults={
            "label": "Restaurant",
            "description": "",
            "unit_type": CatalogBusinessUnit.DefaultUnitType.DEDICATED,
            "active": True,
            "sort_order": 0,
        },
    )
    food_court = create_business_unit(
        establishment=owner_membership.establishment,
        key="food_court",
        label="Food Court",
    )
    food_court.catalog_business_unit = catalog
    food_court.save(update_fields=["catalog_business_unit", "updated_at"])
    subject = create_activity_subject(
        establishment=owner_membership.establishment,
        business_unit=food_court,
        label="Stock",
    )
    signal = create_v3_signal(
        owner_membership.establishment,
        affected_business_unit=food_court,
        responsible_business_unit=food_court,
        activity_subject=subject,
        title="Food Court signal",
    )

    plan, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=signal.responsible_business_unit_id,
        title="Food Court plan",
        source_signal_id=signal.id,
        tasks=[build_task_payload(task="Check stock", business_unit=food_court)],
        assignees=[
            build_assignee_payload(
                membership=owner_membership,
                business_unit=food_court,
            )
        ],
    )

    assert plan.pilot_business_unit_id == food_court.id
    assert execution.pilot_business_unit_id == food_court.id
    assert food_court.key == "food_court"
    assert food_court.catalog_business_unit.key == "restaurant"


def test_linked_create_distinguishes_sibling_instances_same_catalog(
    owner_membership,
):
    food_court = create_business_unit(
        establishment=owner_membership.establishment,
        key="food_court",
        label="Food Court",
    )
    rooftop = create_business_unit(
        establishment=owner_membership.establishment,
        key="rooftop",
        label="Rooftop",
    )
    catalog = food_court.catalog_business_unit
    rooftop.catalog_business_unit = catalog
    rooftop.save(update_fields=["catalog_business_unit", "updated_at"])

    subject = create_activity_subject(
        establishment=owner_membership.establishment,
        business_unit=rooftop,
        label="Service",
    )
    signal = create_v3_signal(
        owner_membership.establishment,
        affected_business_unit=food_court,
        responsible_business_unit=rooftop,
        activity_subject=subject,
        title="Rooftop responsible",
    )

    plan, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=rooftop.id,
        title="Rooftop plan",
        source_signal_id=signal.id,
        tasks=[build_task_payload(task="Close terrace", business_unit=rooftop)],
        assignees=[
            build_assignee_payload(membership=owner_membership, business_unit=rooftop)
        ],
    )

    assert plan.pilot_business_unit_id == rooftop.id
    assert execution.pilot_business_unit_id == rooftop.id
    assert plan.pilot_business_unit_id != food_court.id


def test_linked_create_copies_signal_taxonomy_onto_action_plan_and_initial_execution(
    owner_membership,
    business_unit,
    maintenance_business_unit,
):
    subject = create_activity_subject(
        establishment=owner_membership.establishment,
        business_unit=maintenance_business_unit,
        label="Électricité",
    )
    signal = create_v3_signal(
        owner_membership.establishment,
        affected_business_unit=business_unit,
        responsible_business_unit=maintenance_business_unit,
        activity_subject=subject,
        title="Copy taxonomy",
    )

    plan, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=maintenance_business_unit.id,
        title="Linked taxonomy plan",
        source_signal_id=signal.id,
        tasks=[
            build_task_payload(task="Fix light", business_unit=maintenance_business_unit)
        ],
        assignees=[
            build_assignee_payload(
                membership=owner_membership,
                business_unit=maintenance_business_unit,
            )
        ],
    )

    assert plan.affected_business_unit_id == signal.affected_business_unit_id
    assert plan.responsible_business_unit_id == signal.responsible_business_unit_id
    assert plan.activity_subject_id == signal.activity_subject_id
    assert execution.affected_business_unit_id == signal.affected_business_unit_id
    assert execution.responsible_business_unit_id == signal.responsible_business_unit_id
    assert execution.activity_subject_id == signal.activity_subject_id


def test_action_plan_business_unit_serializer_uses_specific_name_and_generic(
    business_unit,
):
    payload = _serialize_business_unit(business_unit)
    assert payload is not None
    _assert_lot5_business_unit_shape(payload)
    assert payload["specific_name"] == business_unit.specific_name
    assert payload["generic"]["key"] == business_unit.catalog_business_unit.key
    assert payload["generic"]["label"] == business_unit.catalog_business_unit.label
    assert serialize_business_unit_ref(business_unit=business_unit) == payload


def test_generic_activity_subject_label_resolved_on_execution(
    owner_membership,
    maintenance_business_unit,
):
    from houston.establishments.models import CatalogActivitySubject

    catalog_subject = CatalogActivitySubject.objects.create(
        catalog_business_unit=maintenance_business_unit.catalog_business_unit,
        key="maintenance__eclairage",
        label="Éclairage catalogue",
        description="Desc catalogue",
        active=True,
    )
    subject = create_activity_subject(
        establishment=owner_membership.establishment,
        business_unit=maintenance_business_unit,
        label="Local override ignored for generic path",
    )
    subject.catalog_activity_subject = catalog_subject
    subject.label = catalog_subject.label
    subject.source = subject.Source.CATALOG_SUGGESTION
    subject.save()

    payload = _serialize_activity_subject(subject)
    assert payload is not None
    assert payload["is_generic"] is True
    assert payload["label"] == "Éclairage catalogue"
    assert payload["catalog_key"] == "maintenance__eclairage"
    assert "routing_key" not in payload


def test_create_rejects_inactive_business_unit_selection(
    owner_membership,
    business_unit,
):
    business_unit.active = False
    business_unit.save(update_fields=["active", "updated_at"])

    with pytest.raises(ActionPlanValidationError, match="Invalid business unit"):
        create_action_plan_with_execution(
            establishment_id=owner_membership.establishment_id,
            created_by=owner_membership,
            pilot_business_unit_id=business_unit.id,
            title="Inactive pilot",
            tasks=[build_task_payload(task="Task", business_unit=business_unit)],
            assignees=[
                build_assignee_payload(
                    membership=owner_membership,
                    business_unit=business_unit,
                )
            ],
        )


def test_action_plan_detail_readable_when_pilot_business_unit_inactive(
    api_client,
    owner_membership,
    business_unit,
    catalog_action_plan,
):
    business_unit.active = False
    business_unit.save(update_fields=["active", "updated_at"])

    token = login(api_client, user=owner_membership.user)
    response = api_client.get(
        action_plan_url(owner_membership.establishment_id, catalog_action_plan.id),
        **auth_headers(token),
    )
    assert response.status_code == 200
    pilot = response.json()["pilot_business_unit"]
    _assert_lot5_business_unit_shape(pilot)
    assert pilot["active"] is False
    assert pilot["specific_name"] == business_unit.specific_name
    assert pilot["generic"]["label"] == business_unit.catalog_business_unit.label


def test_execution_detail_serializes_lot5_business_units(
    owner_membership,
    business_unit,
    maintenance_business_unit,
    signal,
):
    plan, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=signal.responsible_business_unit_id,
        title="Lot5 execution",
        source_signal_id=signal.id,
        tasks=[
            build_task_payload(task="Inspect", business_unit=maintenance_business_unit)
        ],
        assignees=[
            build_assignee_payload(
                membership=owner_membership,
                business_unit=maintenance_business_unit,
            )
        ],
    )
    execution = (
        type(execution)
        .objects.select_related(
            "pilot_business_unit__catalog_business_unit",
            "affected_business_unit__catalog_business_unit",
            "responsible_business_unit__catalog_business_unit",
            "activity_subject__catalog_activity_subject",
            "created_by__user",
            "source_signal",
        )
        .prefetch_related(
            "assignees__membership__user",
            "assignees__execution_team__business_unit__catalog_business_unit",
            "task_executions__execution_team__business_unit__catalog_business_unit",
            "execution_teams__business_unit__catalog_business_unit",
        )
        .get(id=execution.id)
    )
    payload = serialize_execution_detail(execution, membership=owner_membership)
    _assert_lot5_business_unit_shape(payload["pilot_business_unit"])
    assert payload["affected_business_unit"] is not None
    _assert_lot5_business_unit_shape(payload["affected_business_unit"])
    assert payload["responsible_business_unit"] is not None
    _assert_lot5_business_unit_shape(payload["responsible_business_unit"])
    assert payload["signal_summary"]["responsible_business_unit_id"] == (
        signal.responsible_business_unit_id
    )
    assert plan.id is not None
