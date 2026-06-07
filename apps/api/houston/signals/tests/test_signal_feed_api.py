from __future__ import annotations

import pytest
from django.utils import timezone

from houston.ai.observation_pipeline_schema import (
    ObservationPipelineOutput,
    PipelineCandidateOutput,
)
from houston.establishments.models import BusinessUnit
from houston.establishments.taxonomy_backfill import backfill_business_units_from_legacy_taxonomy
from houston.establishments.tests.taxonomy_helpers import (
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
    RESTAURANT_BAR_STOCK_SUBJECT_KEY,
    RESTAURANT_SALLE_MAINTENANCE_SUBJECT_KEY,
    auth_headers,
    build_api_membership,
    classify_golden_restaurant_signals,
    create_observation,
    create_restaurant_business_units,
    create_restaurant_lighting_bar_stock_taxonomy,
    create_taxonomy,
    golden_two_candidate_pipeline_output,
    login,
    signal_feed_url,
)

pytestmark = pytest.mark.django_db


def _create_signal(
    membership,
    *,
    title: str = "Test signal",
    taxonomy: tuple | None = None,
    affected_business_unit: BusinessUnit | None = None,
    responsible_business_unit: BusinessUnit | None = None,
):
    if taxonomy is None:
        taxonomy = create_taxonomy(membership.establishment)
    module, domain, subject = taxonomy
    now = timezone.now()
    return Signal.objects.create(
        establishment=membership.establishment,
        operational_module=module,
        operational_domain=domain,
        operational_subject=subject,
        affected_business_unit=affected_business_unit,
        responsible_business_unit=responsible_business_unit,
        title=title,
        structured_summary="Structured summary safe.",
        last_activity_at=now,
    )


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


def test_personal_feed_matches_scope(api_client):
    from houston.establishments.models import EstablishmentMembership

    membership = build_api_membership(role=EstablishmentMembership.Role.MANAGER)
    taxonomy = create_taxonomy(membership.establishment)
    business_unit = create_business_unit(
        establishment=membership.establishment,
        key=taxonomy[0].key,
        label=taxonomy[0].label,
    )
    create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=business_unit,
    )
    _create_signal(
        membership,
        taxonomy=taxonomy,
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
    taxonomy = create_taxonomy(membership.establishment)
    module, domain, subject = taxonomy
    business_unit = create_business_unit(
        establishment=membership.establishment,
        key=module.key,
        label=module.label,
    )
    create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=business_unit,
    )
    observation = create_observation(membership=membership)

    output = ObservationPipelineOutput(
        schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        candidates=[
            PipelineCandidateOutput(
                title="Clim en panne chambre 104",
                structured_summary="Eau au sol, climatisation en panne.",
                operational_module_key=module.key,
                operational_domain_key=domain.key,
                operational_subject_key=subject.key,
                operational_unit_key=None,
                aggregate_into_signal_id=None,
            )
        ],
    )
    outcome = apply_pipeline_output(observation=observation, output=output)
    assert outcome == ObservationProcessing.Outcome.SIGNALS_CREATED
    backfill_business_units_from_legacy_taxonomy(establishment_id=membership.establishment_id)
    created_signal = Signal.objects.get(
        establishment=membership.establishment,
        title="Clim en panne chambre 104",
    )
    created_signal.affected_business_unit = business_unit
    created_signal.responsible_business_unit = business_unit
    created_signal.save(
        update_fields=["affected_business_unit", "responsible_business_unit", "updated_at"]
    )

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
        taxonomy = create_restaurant_lighting_bar_stock_taxonomy(membership.establishment)
    business_units = create_restaurant_business_units(membership.establishment)
    observation = create_observation(membership=membership, text=GOLDEN_OBSERVATION_TEXT)
    apply_pipeline_output(
        observation=observation,
        output=golden_two_candidate_pipeline_output(taxonomy=taxonomy),
    )
    classify_golden_restaurant_signals(
        establishment=membership.establishment,
        business_units=business_units,
    )
    return observation, taxonomy, business_units


def test_general_feed_shows_two_golden_signals(api_client):
    membership = build_api_membership()
    _apply_golden_pipeline(membership=membership)
    token = login(api_client, user=membership.user)

    response = api_client.get(
        signal_feed_url(membership.establishment_id) + "?view_mode=general",
        **auth_headers(token),
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 2
    subject_keys = {item["subject_key"] for item in items}
    assert RESTAURANT_SALLE_MAINTENANCE_SUBJECT_KEY in subject_keys
    assert RESTAURANT_BAR_STOCK_SUBJECT_KEY in subject_keys
    assert "raw_text" not in response.content.decode()


def test_personal_feed_staff_salle_maintenance_sees_lighting_only(api_client):
    from houston.establishments.models import EstablishmentMembership

    membership = build_api_membership(role=EstablishmentMembership.Role.STAFF)
    taxonomy = create_restaurant_lighting_bar_stock_taxonomy(membership.establishment)
    _, _, business_units = _apply_golden_pipeline(membership=membership, taxonomy=taxonomy)
    create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=business_units.restaurant,
    )
    token = login(api_client, user=membership.user)

    response = api_client.get(
        signal_feed_url(membership.establishment_id) + "?view_mode=personal",
        **auth_headers(token),
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["subject_key"] == RESTAURANT_SALLE_MAINTENANCE_SUBJECT_KEY


def test_personal_feed_staff_bar_stock_sees_syrup_only(api_client):
    from houston.establishments.models import EstablishmentMembership

    membership = build_api_membership(role=EstablishmentMembership.Role.STAFF)
    taxonomy = create_restaurant_lighting_bar_stock_taxonomy(membership.establishment)
    _, _, business_units = _apply_golden_pipeline(membership=membership, taxonomy=taxonomy)
    create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=business_units.bar,
    )
    token = login(api_client, user=membership.user)

    response = api_client.get(
        signal_feed_url(membership.establishment_id) + "?view_mode=personal",
        **auth_headers(token),
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["subject_key"] == RESTAURANT_BAR_STOCK_SUBJECT_KEY


def test_staff_restaurant_scope_sees_but_cannot_act_on_maintenance_responsible_signal():
    from houston.establishments.models import EstablishmentMembership

    membership = build_api_membership(role=EstablishmentMembership.Role.STAFF)
    taxonomy = create_restaurant_lighting_bar_stock_taxonomy(membership.establishment)
    _, _, business_units = _apply_golden_pipeline(membership=membership, taxonomy=taxonomy)
    create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=business_units.restaurant,
    )
    lighting_signal = Signal.objects.get(
        establishment=membership.establishment,
        operational_subject__key=RESTAURANT_SALLE_MAINTENANCE_SUBJECT_KEY,
    )

    assert signal_visible_in_membership_scope(membership, lighting_signal) is True
    assert signal_actionable_by_membership(membership, lighting_signal) is False
