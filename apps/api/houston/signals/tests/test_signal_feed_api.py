from __future__ import annotations

import pytest
from django.utils import timezone

from houston.ai.observation_pipeline_schema import (
    ObservationPipelineOutput,
    PipelineCandidateOutput,
)
from houston.establishments.models import MembershipScope
from houston.observations.models import ObservationProcessing
from houston.signals.constants import AI_OBSERVATION_PIPELINE_SCHEMA_VERSION
from houston.signals.models import Signal
from houston.signals.services import apply_pipeline_output
from houston.signals.tests.conftest import (
    GOLDEN_OBSERVATION_TEXT,
    RESTAURANT_BAR_STOCK_SUBJECT_KEY,
    RESTAURANT_SALLE_MAINTENANCE_SUBJECT_KEY,
    auth_headers,
    build_api_membership,
    create_observation,
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
    MembershipScope.objects.create(membership=membership, operational_domain=taxonomy[1])
    _create_signal(membership, taxonomy=taxonomy)
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
    MembershipScope.objects.create(membership=membership, operational_subject=subject)
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
    observation = create_observation(membership=membership, text=GOLDEN_OBSERVATION_TEXT)
    apply_pipeline_output(
        observation=observation,
        output=golden_two_candidate_pipeline_output(taxonomy=taxonomy),
    )
    return observation, taxonomy


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
    MembershipScope.objects.create(
        membership=membership,
        operational_subject=taxonomy.salle_maintenance_subject,
    )
    _apply_golden_pipeline(membership=membership, taxonomy=taxonomy)
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
    MembershipScope.objects.create(
        membership=membership,
        operational_subject=taxonomy.bar_stock_subject,
    )
    _apply_golden_pipeline(membership=membership, taxonomy=taxonomy)
    token = login(api_client, user=membership.user)

    response = api_client.get(
        signal_feed_url(membership.establishment_id) + "?view_mode=personal",
        **auth_headers(token),
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["subject_key"] == RESTAURANT_BAR_STOCK_SUBJECT_KEY
