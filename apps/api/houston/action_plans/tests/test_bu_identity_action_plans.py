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
from houston.establishments.models import BusinessUnit, CatalogBusinessUnit
from houston.establishments.public_serialization import (
    serialize_business_unit_public,
    serialize_business_unit_ref,
)
from houston.establishments.selectors import (
    get_establishment_business_unit_tree,
    serialize_business_unit_tree_item,
)
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
    assert payload["affected_business_unit_key"] == business_unit.normalized_specific_name
    assert (
        payload["responsible_business_unit_key"]
        == maintenance_business_unit.normalized_specific_name
    )
    assert payload["affected_business_unit_label"] == business_unit.specific_name
    assert (
        payload["responsible_business_unit_label"]
        == maintenance_business_unit.specific_name
    )


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
    assert food_court.normalized_specific_name == "food_court"
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
    from houston.establishments.business_unit_identity import (
        normalize_generic_activity_subject_name,
    )
    from houston.establishments.models import ActivitySubject, CatalogActivitySubject

    catalog_subject = CatalogActivitySubject.objects.create(
        catalog_business_unit=maintenance_business_unit.catalog_business_unit,
        key="maintenance__eclairage",
        label="Éclairage catalogue",
        description="Desc catalogue",
        active=True,
    )
    subject = ActivitySubject.objects.create(
        establishment=owner_membership.establishment,
        business_unit=maintenance_business_unit,
        catalog_activity_subject=catalog_subject,
        normalized_name=normalize_generic_activity_subject_name(catalog_subject.label),
        routing_key=catalog_subject.key,
        label="",
        description="",
        source=ActivitySubject.Source.CATALOG_SUGGESTION,
        active=True,
    )

    payload = _serialize_activity_subject(subject)
    assert payload is not None
    assert payload["is_generic"] is True
    assert payload["label"] == "Éclairage catalogue"
    assert payload["catalog_key"] == "maintenance__eclairage"
    assert "routing_key" not in payload


def test_signal_summary_activity_subject_label_matches_lot5_nested_ref(
    owner_membership,
    business_unit,
    maintenance_business_unit,
):
    from houston.establishments.business_unit_identity import (
        normalize_generic_activity_subject_name,
    )
    from houston.establishments.models import ActivitySubject, CatalogActivitySubject

    catalog_subject = CatalogActivitySubject.objects.create(
        catalog_business_unit=maintenance_business_unit.catalog_business_unit,
        key="maintenance__label_drift",
        label="Label catalogue",
        description="",
        active=True,
    )
    subject = ActivitySubject.objects.create(
        establishment=owner_membership.establishment,
        business_unit=maintenance_business_unit,
        catalog_activity_subject=catalog_subject,
        normalized_name=normalize_generic_activity_subject_name(catalog_subject.label),
        routing_key=catalog_subject.key,
        label="",
        description="",
        source=ActivitySubject.Source.CATALOG_SUGGESTION,
        active=True,
    )

    signal = create_v3_signal(
        owner_membership.establishment,
        affected_business_unit=business_unit,
        responsible_business_unit=maintenance_business_unit,
        activity_subject=subject,
        title="Label drift signal",
    )
    _plan, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=maintenance_business_unit.id,
        title="Label drift plan",
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
            "source_signal__activity_subject__catalog_activity_subject",
            "created_by__user",
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
    assert payload["activity_subject"]["label"] == "Label catalogue"
    assert payload["signal_summary"]["activity_subject_label"] == "Label catalogue"
    assert subject.label == ""


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


def test_serialize_raises_on_incomplete_business_unit_identity(business_unit):
    from houston.establishments.public_serialization import (
        IncompleteBusinessUnitIdentityError,
    )

    incomplete = BusinessUnit(
        id=business_unit.id,
        establishment_id=business_unit.establishment_id,
        specific_name="",
        normalized_specific_name="",
        routing_key="",
        instance_description="",
        active=True,
    )
    with pytest.raises(IncompleteBusinessUnitIdentityError):
        serialize_business_unit_public(business_unit=incomplete)
    with pytest.raises(IncompleteBusinessUnitIdentityError):
        serialize_business_unit_ref(business_unit=incomplete)
    with pytest.raises(IncompleteBusinessUnitIdentityError):
        serialize_business_unit_tree_item(business_unit=incomplete)


def test_runtime_tree_serializes_complete_identity_only(
    owner_membership,
    business_unit,
):
    tree = get_establishment_business_unit_tree(
        establishment_id=owner_membership.establishment_id,
        active_only=True,
    )
    assert tree is not None
    tree_ids = {item["id"] for item in tree["business_units"]}
    assert business_unit.id in tree_ids
    item = next(unit for unit in tree["business_units"] if unit["id"] == business_unit.id)
    assert item["specific_name"] == business_unit.specific_name
    assert "routing_key" not in item
    assert "generic" in item
    assert "activity_subjects" in item


def test_business_unit_tree_query_count_flat_across_business_units():
    from houston.testing.factories import create_establishment
    from houston.testing.query_baseline import capture_queries

    one_bu_establishment = create_establishment(name="Tree One BU")
    single_unit = create_business_unit(
        establishment=one_bu_establishment,
        key="hotel",
        label="Hotel",
    )
    create_activity_subject(
        establishment=one_bu_establishment,
        business_unit=single_unit,
        label="Maintenance",
    )

    three_bu_establishment = create_establishment(name="Tree Three BU")
    for key, label in (("hotel", "Hotel"), ("bar", "Bar"), ("kitchen", "Kitchen")):
        unit = create_business_unit(
            establishment=three_bu_establishment,
            key=key,
            label=label,
        )
        create_activity_subject(
            establishment=three_bu_establishment,
            business_unit=unit,
            label=f"{label} subject",
        )

    with capture_queries() as one_bu_context:
        one_tree = get_establishment_business_unit_tree(
            establishment_id=one_bu_establishment.id,
            active_only=True,
        )
    with capture_queries() as three_bu_context:
        three_tree = get_establishment_business_unit_tree(
            establishment_id=three_bu_establishment.id,
            active_only=True,
        )

    assert one_tree is not None
    assert three_tree is not None
    assert len(one_tree["business_units"]) == 1
    assert len(three_tree["business_units"]) == 3
    for unit in three_tree["business_units"]:
        _assert_lot5_business_unit_shape(
            {
                "id": unit["id"],
                "specific_name": unit["specific_name"],
                "instance_description": unit["instance_description"],
                "active": unit["active"],
                "generic": unit["generic"],
            }
        )
        assert "routing_key" not in unit
    assert len(one_bu_context.captured_queries) == len(three_bu_context.captured_queries)
