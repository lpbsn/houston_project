from __future__ import annotations

import pytest

from houston.ai.observation_pipeline_schema import (
    ObservationPipelineOutput,
    PipelineCandidateOutput,
)
from houston.establishments.models import BusinessUnit
from houston.establishments.tests.taxonomy_helpers import (
    create_activity_subject,
    create_business_unit,
    create_membership_with_business_unit_scope,
)
from houston.observations.models import ObservationProcessing
from houston.signals.constants import AI_OBSERVATION_PIPELINE_SCHEMA_VERSION
from houston.signals.models import Signal
from houston.signals.permissions import (
    signal_actionable_by_membership,
    signal_visible_in_membership_scope,
)
from houston.signals.services import apply_pipeline_output
from houston.signals.tests.conftest import (
    GOLDEN_OBSERVATION_TEXT,
    RESTAURANT_MODULE_KEY,
    auth_headers,
    build_api_membership,
    create_minimal_v3_signal,
    create_observation,
    create_restaurant_v3_taxonomy,
    golden_two_candidate_pipeline_output,
    login,
    signal_feed_url,
)

pytestmark = pytest.mark.django_db


def _create_signal(
    membership,
    *,
    title: str = "Test signal",
    affected_business_unit: BusinessUnit | None = None,
    responsible_business_unit: BusinessUnit | None = None,
):
    signal = create_minimal_v3_signal(membership, title=title)
    if affected_business_unit is not None or responsible_business_unit is not None:
        if affected_business_unit is not None:
            signal.affected_business_unit = affected_business_unit
        if responsible_business_unit is not None:
            signal.responsible_business_unit = responsible_business_unit
        signal.save(
            update_fields=[
                "affected_business_unit",
                "responsible_business_unit",
                "updated_at",
            ]
        )
    return signal


def test_general_feed_returns_active_signals(api_client):
    membership = build_api_membership()
    _create_signal(membership)
    token = login(api_client, user=membership.user)

    response = api_client.get(
        signal_feed_url(membership.establishment_id) + "?view_mode=general",
        **auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert "module_key" not in body["items"][0]
    assert "domain_key" not in body["items"][0]
    assert "subject_key" not in body["items"][0]
    assert "raw_text" not in response.content.decode()


def test_personal_feed_empty_without_scope_for_staff(api_client):
    from houston.establishments.models import EstablishmentMembership

    membership = build_api_membership(role=EstablishmentMembership.Role.STAFF)
    _create_signal(membership)
    token = login(api_client, user=membership.user)

    response = api_client.get(
        signal_feed_url(membership.establishment_id) + "?view_mode=personal",
        **auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_scoped_manager_general_feed_includes_out_of_scope_signals(api_client):
    from houston.establishments.models import EstablishmentMembership

    membership = build_api_membership(role=EstablishmentMembership.Role.MANAGER)
    in_scope_bu = create_business_unit(
        establishment=membership.establishment,
        key="bar",
        label="Bar",
    )
    out_of_scope_bu = create_business_unit(
        establishment=membership.establishment,
        key="kitchen",
        label="Kitchen",
    )
    create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=in_scope_bu,
    )
    in_scope_signal = _create_signal(
        membership,
        title="In-scope bar signal",
        affected_business_unit=in_scope_bu,
        responsible_business_unit=in_scope_bu,
    )
    out_of_scope_signal = _create_signal(
        membership,
        title="Out-of-scope kitchen signal",
        affected_business_unit=out_of_scope_bu,
        responsible_business_unit=out_of_scope_bu,
    )
    token = login(api_client, user=membership.user)

    personal_response = api_client.get(
        signal_feed_url(membership.establishment_id) + "?view_mode=personal",
        **auth_headers(token),
    )
    assert personal_response.status_code == 200
    personal_ids = {item["id"] for item in personal_response.json()["items"]}
    assert str(in_scope_signal.id) in personal_ids
    assert str(out_of_scope_signal.id) not in personal_ids

    general_response = api_client.get(
        signal_feed_url(membership.establishment_id) + "?view_mode=general",
        **auth_headers(token),
    )
    assert general_response.status_code == 200
    general_ids = {item["id"] for item in general_response.json()["items"]}
    assert str(in_scope_signal.id) in general_ids
    assert str(out_of_scope_signal.id) in general_ids


def test_personal_feed_matches_scope(api_client):
    from houston.establishments.models import EstablishmentMembership

    membership = build_api_membership(role=EstablishmentMembership.Role.MANAGER)
    business_unit = create_business_unit(
        establishment=membership.establishment,
        key="hotel",
        label="Hotel",
    )
    create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=business_unit,
    )
    _create_signal(
        membership,
        affected_business_unit=business_unit,
        responsible_business_unit=business_unit,
    )
    token = login(api_client, user=membership.user)

    response = api_client.get(
        signal_feed_url(membership.establishment_id) + "?view_mode=personal",
        **auth_headers(token),
    )

    assert response.status_code == 200
    assert len(response.json()["items"]) == 1


def test_staff_maintenance_scope_sees_maintenance_signal_in_personal_feed(api_client):
    from houston.establishments.models import EstablishmentMembership

    membership = build_api_membership(role=EstablishmentMembership.Role.STAFF)
    business_unit = create_business_unit(
        establishment=membership.establishment,
        key="maintenance",
        label="Maintenance",
    )
    create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=business_unit,
    )
    observation = create_observation(membership=membership)

    create_activity_subject(
        establishment=membership.establishment,
        business_unit=business_unit,
        label="Maintenance",
    )
    output = ObservationPipelineOutput(
        schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        candidates=[
            PipelineCandidateOutput(
                title="Clim en panne chambre 104",
                structured_summary="Eau au sol, climatisation en panne.",
                issue_focus="clim chambre 104",
                affected_business_unit_key=business_unit.key,
                responsible_business_unit_key=business_unit.key,
                activity_subject_key="maintenance",
                operational_unit_key=None,
                location_text="chambre 104",
                aggregate_into_signal_id=None,
            )
        ],
    )
    outcome = apply_pipeline_output(observation=observation, output=output).outcome
    assert outcome == ObservationProcessing.Outcome.SIGNALS_CREATED

    token = login(api_client, user=membership.user)
    response = api_client.get(
        signal_feed_url(membership.establishment_id) + "?view_mode=personal",
        **auth_headers(token),
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["title"] == "Clim en panne chambre 104"
    assert "raw_text" not in response.content.decode()


def test_general_feed_shows_active_signal_same_establishment(api_client):
    membership = build_api_membership()
    other_membership = build_api_membership()
    assert other_membership.establishment_id != membership.establishment_id

    visible = _create_signal(membership, title="Visible in general feed")
    _create_signal(other_membership, title="Other establishment signal")
    token = login(api_client, user=membership.user)

    response = api_client.get(
        signal_feed_url(membership.establishment_id) + "?view_mode=general",
        **auth_headers(token),
    )

    assert response.status_code == 200
    item_ids = {item["id"] for item in response.json()["items"]}
    assert str(visible.id) in item_ids
    assert len(item_ids) == 1


def _apply_golden_pipeline(*, membership, taxonomy=None):
    if taxonomy is None:
        taxonomy = create_restaurant_v3_taxonomy(membership.establishment)
    observation = create_observation(membership=membership, text=GOLDEN_OBSERVATION_TEXT)
    apply_pipeline_output(
        observation=observation,
        output=golden_two_candidate_pipeline_output(taxonomy=taxonomy),
    )
    return observation, taxonomy


def test_general_feed_shows_two_golden_signals(api_client):
    membership = build_api_membership()
    _, taxonomy = _apply_golden_pipeline(membership=membership)
    token = login(api_client, user=membership.user)

    response = api_client.get(
        signal_feed_url(membership.establishment_id) + "?view_mode=general",
        **auth_headers(token),
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 2
    activity_subjects = {item["activity_subject_normalized_name"] for item in items}
    assert taxonomy.lighting_subject.normalized_name in activity_subjects
    assert taxonomy.stock_subject.normalized_name in activity_subjects
    assert "raw_text" not in response.content.decode()


def test_personal_feed_staff_salle_maintenance_sees_lighting_only(api_client):
    from houston.establishments.models import EstablishmentMembership

    membership = build_api_membership(role=EstablishmentMembership.Role.STAFF)
    taxonomy = create_restaurant_v3_taxonomy(membership.establishment)
    _apply_golden_pipeline(membership=membership, taxonomy=taxonomy)
    create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=taxonomy.restaurant,
    )
    token = login(api_client, user=membership.user)

    response = api_client.get(
        signal_feed_url(membership.establishment_id) + "?view_mode=personal",
        **auth_headers(token),
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["affected_business_unit_key"] == RESTAURANT_MODULE_KEY


def test_personal_feed_staff_bar_stock_sees_syrup_only(api_client):
    from houston.establishments.models import EstablishmentMembership

    membership = build_api_membership(role=EstablishmentMembership.Role.STAFF)
    taxonomy = create_restaurant_v3_taxonomy(membership.establishment)
    _apply_golden_pipeline(membership=membership, taxonomy=taxonomy)
    create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=taxonomy.bar,
    )
    token = login(api_client, user=membership.user)

    response = api_client.get(
        signal_feed_url(membership.establishment_id) + "?view_mode=personal",
        **auth_headers(token),
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["activity_subject_normalized_name"] == taxonomy.stock_subject.normalized_name


def test_staff_restaurant_scope_sees_but_cannot_act_on_maintenance_responsible_signal():
    from houston.establishments.models import EstablishmentMembership

    membership = build_api_membership(role=EstablishmentMembership.Role.STAFF)
    taxonomy = create_restaurant_v3_taxonomy(membership.establishment)
    _apply_golden_pipeline(membership=membership, taxonomy=taxonomy)
    create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=taxonomy.restaurant,
    )
    lighting_signal = Signal.objects.get(
        establishment=membership.establishment,
        affected_business_unit=taxonomy.restaurant,
        responsible_business_unit=taxonomy.maintenance,
    )

    assert signal_visible_in_membership_scope(membership, lighting_signal) is True
    assert signal_actionable_by_membership(membership, lighting_signal) is False


def test_signal_feed_query_count_baseline_two_items(api_client):
    """Phase E ceiling: 2 signals, general view (was 11 in Phase L)."""
    membership = build_api_membership()
    _create_signal(membership, title="Baseline A")
    _create_signal(membership, title="Baseline B")
    token = login(api_client, user=membership.user)
    url = signal_feed_url(membership.establishment_id) + "?view_mode=general"

    from houston.testing.query_baseline import (
        SIGNAL_FEED_MAX_QUERIES_TWO_ITEMS,
        assert_query_count_at_most,
        capture_queries,
    )

    with capture_queries() as context:
        response = api_client.get(url, **auth_headers(token))

    assert response.status_code == 200
    assert len(response.json()["items"]) == 2
    assert_query_count_at_most(
        context,
        max_queries=SIGNAL_FEED_MAX_QUERIES_TWO_ITEMS,
        label="signal_feed_general_two_items",
    )


def test_signal_feed_query_count_grows_with_item_count(api_client):
    """Phase E: per-item serializer overhead should stay flat with prefetch."""
    from houston.testing.query_baseline import (
        SIGNAL_FEED_MAX_QUERY_DELTA_ONE_TO_THREE_ITEMS,
        capture_queries,
    )

    def query_count_for(item_count: int) -> int:
        membership = build_api_membership()
        for index in range(item_count):
            _create_signal(membership, title=f"Scale {index}")
        token = login(api_client, user=membership.user)
        url = signal_feed_url(membership.establishment_id) + "?view_mode=general"
        with capture_queries() as context:
            response = api_client.get(url, **auth_headers(token))
        assert response.status_code == 200
        assert len(response.json()["items"]) == item_count
        return len(context.captured_queries)

    one_item = query_count_for(1)
    three_items = query_count_for(3)
    assert three_items - one_item <= SIGNAL_FEED_MAX_QUERY_DELTA_ONE_TO_THREE_ITEMS
