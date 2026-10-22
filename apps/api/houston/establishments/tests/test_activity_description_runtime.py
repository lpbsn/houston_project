from __future__ import annotations

from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from houston.ai.observation_pipeline import build_pipeline_input
from houston.core.exceptions import DomainValidationError
from houston.establishments.business_unit_domain_service import update_business_unit
from houston.establishments.models import (
    ACTIVITY_DESCRIPTION_MAX_LENGTH,
    ACTIVITY_DESCRIPTION_MIN_LENGTH,
    INSTANCE_DESCRIPTION_MAX_LENGTH,
    BusinessUnit,
    EstablishmentActivityDescription,
    EstablishmentMembership,
)
from houston.establishments.taxonomy_snapshot import build_establishment_context
from houston.establishments.tests.test_runtime_config_mutations import (
    auth_headers,
    create_membership_for_user,
    create_user,
    login,
    setup_active_establishment_with_runtime,
)
from houston.observations.models import ObservationProcessing
from houston.signals.constants import AI_OBSERVATION_PIPELINE_PROMPT_VERSION
from houston.testing.pipeline import create_observation

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


def activity_description_url(establishment_id) -> str:
    return f"/api/v1/establishments/{establishment_id}/activity-description/"


def business_unit_detail_url(establishment_id, business_unit_id) -> str:
    return f"/api/v1/establishments/{establishment_id}/business-units/{business_unit_id}/"


def test_missing_activity_description_is_readable_and_created_on_edit(api_client):
    establishment, owner, hotel, _maintenance = setup_active_establishment_with_runtime()
    hotel_name = hotel.specific_name
    subject_labels = list(
        hotel.activity_subjects.order_by("label").values_list("label", flat=True)
    )
    access_token = login(api_client, user=owner)
    headers = auth_headers(access_token)

    read_response = api_client.get(
        activity_description_url(establishment.id),
        **headers,
    )
    assert read_response.status_code == 200
    assert read_response.json() == {"description": ""}
    assert not EstablishmentActivityDescription.objects.filter(
        establishment=establishment
    ).exists()

    created = api_client.patch(
        activity_description_url(establishment.id),
        {"description": "  Hôtel de centre-ville, avec jardin.  "},
        format="json",
        **headers,
    )
    assert created.status_code == 200
    assert created.json() == {"description": "Hôtel de centre-ville, avec jardin."}
    row = EstablishmentActivityDescription.objects.get(establishment=establishment)
    assert row.source == EstablishmentActivityDescription.Source.MANUAL
    assert row.submitted_by_id == owner.id
    assert row.validated_at is not None
    validated_at = row.validated_at
    submitted_by_id = row.submitted_by_id

    reread = api_client.get(activity_description_url(establishment.id), **headers)
    assert reread.status_code == 200
    assert reread.json()["description"] == "Hôtel de centre-ville, avec jardin."

    updated = api_client.patch(
        activity_description_url(establishment.id),
        {"description": "Hôtel de centre-ville, salle et petit-déjeuner."},
        format="json",
        **headers,
    )
    assert updated.status_code == 200
    row.refresh_from_db()
    assert row.description == "Hôtel de centre-ville, salle et petit-déjeuner."
    assert row.source == EstablishmentActivityDescription.Source.MANUAL
    assert row.submitted_by_id == submitted_by_id
    assert row.validated_at == validated_at
    hotel.refresh_from_db()
    assert hotel.specific_name == hotel_name
    assert (
        list(hotel.activity_subjects.order_by("label").values_list("label", flat=True))
        == subject_labels
    )


def test_activity_description_rejects_exact_bounds_without_truncating(api_client):
    establishment, owner, _hotel, _maintenance = setup_active_establishment_with_runtime()
    access_token = login(api_client, user=owner)
    headers = auth_headers(access_token)
    ceiling = "😀" * ACTIVITY_DESCRIPTION_MAX_LENGTH
    over = "é" * (ACTIVITY_DESCRIPTION_MAX_LENGTH + 1)

    accepted = api_client.patch(
        activity_description_url(establishment.id),
        {"description": f"  {ceiling}  "},
        format="json",
        **headers,
    )
    assert accepted.status_code == 200
    assert accepted.json()["description"] == ceiling
    assert len(accepted.json()["description"]) == ACTIVITY_DESCRIPTION_MAX_LENGTH

    rejected = api_client.patch(
        activity_description_url(establishment.id),
        {"description": over},
        format="json",
        **headers,
    )
    assert rejected.status_code == 400
    EstablishmentActivityDescription.objects.get(establishment=establishment).refresh_from_db()
    stored = EstablishmentActivityDescription.objects.get(establishment=establishment)
    assert stored.description == ceiling

    too_short = api_client.patch(
        activity_description_url(establishment.id),
        {"description": "é" * (ACTIVITY_DESCRIPTION_MIN_LENGTH - 1)},
        format="json",
        **headers,
    )
    assert too_short.status_code == 400
    stored.refresh_from_db()
    assert stored.description == ceiling


def test_director_can_edit_activity_description_and_others_cannot(api_client):
    establishment, _owner, _hotel, _maintenance = setup_active_establishment_with_runtime(
        owner_username="activity_desc_owner"
    )
    director = create_user(username="activity_desc_director")
    create_membership_for_user(
        user=director,
        establishment=establishment,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    director_token = login(api_client, user=director)
    response = api_client.patch(
        activity_description_url(establishment.id),
        {"description": "Description rédigée par le directeur."},
        format="json",
        **auth_headers(director_token),
    )
    assert response.status_code == 200
    assert (
        EstablishmentActivityDescription.objects.get(establishment=establishment).description
        == "Description rédigée par le directeur."
    )

    for role in ("manager", "staff"):
        actor = create_user(username=f"activity_desc_{role}")
        create_membership_for_user(user=actor, establishment=establishment, role=role)
        token = login(api_client, user=actor)
        forbidden = api_client.patch(
            activity_description_url(establishment.id),
            {"description": "Texte qui ne doit pas être enregistré."},
            format="json",
            **auth_headers(token),
        )
        assert forbidden.status_code == 403
    stored = EstablishmentActivityDescription.objects.get(establishment=establishment)
    assert stored.description == "Description rédigée par le directeur."


def test_activity_description_is_scoped_to_the_active_establishment(api_client):
    establishment, owner, _hotel, _maintenance = setup_active_establishment_with_runtime(
        owner_username="activity_desc_scope_owner"
    )
    other, _other_owner, _other_hotel, _other_maintenance = (
        setup_active_establishment_with_runtime(owner_username="activity_desc_other_owner")
    )
    access_token = login(api_client, user=owner)
    response = api_client.get(
        activity_description_url(other.id),
        **auth_headers(access_token),
    )
    assert response.status_code == 404
    assert not EstablishmentActivityDescription.objects.filter(
        establishment=establishment
    ).exists()


def test_historical_pole_description_survives_a_rename_and_blocks_an_overlong_write(
    api_client,
):
    establishment, owner, hotel, _maintenance = setup_active_establishment_with_runtime(
        owner_username="activity_desc_pole_owner"
    )
    historical = "H" * (INSTANCE_DESCRIPTION_MAX_LENGTH + 1)
    BusinessUnit.objects.filter(pk=hotel.pk).update(instance_description=historical)
    access_token = login(api_client, user=owner)
    headers = auth_headers(access_token)

    renamed = api_client.patch(
        business_unit_detail_url(establishment.id, hotel.id),
        {"specific_name": "Hôtel historique"},
        format="json",
        **headers,
    )
    assert renamed.status_code == 200
    assert renamed.json()["specific_name"] == "Hôtel historique"
    assert renamed.json()["instance_description"] == historical
    hotel.refresh_from_db()
    assert hotel.instance_description == historical

    rejected = api_client.patch(
        business_unit_detail_url(establishment.id, hotel.id),
        {
            "specific_name": "Nom abandonné",
            "instance_description": "😀" * (INSTANCE_DESCRIPTION_MAX_LENGTH + 1),
        },
        format="json",
        **headers,
    )
    assert rejected.status_code == 400
    hotel.refresh_from_db()
    assert hotel.specific_name == "Hôtel historique"
    assert hotel.instance_description == historical

    accepted = api_client.patch(
        business_unit_detail_url(establishment.id, hotel.id),
        {"instance_description": "😀" * INSTANCE_DESCRIPTION_MAX_LENGTH},
        format="json",
        **headers,
    )
    assert accepted.status_code == 200
    hotel.refresh_from_db()
    assert hotel.specific_name == "Hôtel historique"
    assert hotel.instance_description == "😀" * INSTANCE_DESCRIPTION_MAX_LENGTH
    assert len(hotel.instance_description) == INSTANCE_DESCRIPTION_MAX_LENGTH


def test_domain_rename_does_not_rewrite_an_overlong_pole_description():
    establishment, _owner, hotel, _maintenance = setup_active_establishment_with_runtime(
        owner_username="activity_desc_domain_owner"
    )
    historical = "P" * (INSTANCE_DESCRIPTION_MAX_LENGTH + 1)
    BusinessUnit.objects.filter(pk=hotel.pk).update(instance_description=historical)

    updated = update_business_unit(
        establishment_id=establishment.id,
        business_unit_id=hotel.id,
        specific_name="Pôle renommé",
    )
    assert updated.specific_name == "Pôle renommé"
    assert updated.instance_description == historical

    with pytest.raises(DomainValidationError) as exc_info:
        update_business_unit(
            establishment_id=establishment.id,
            business_unit_id=hotel.id,
            specific_name="Pôle refusé",
            instance_description="x" * (INSTANCE_DESCRIPTION_MAX_LENGTH + 1),
        )
    assert exc_info.value.code == "invalid_instance_description_length"
    hotel.refresh_from_db()
    assert hotel.specific_name == "Pôle renommé"
    assert hotel.instance_description == historical


def test_future_pipeline_input_reads_the_edited_description_without_requeue(api_client):
    establishment, owner, hotel, _maintenance = setup_active_establishment_with_runtime(
        owner_username="activity_desc_pipeline_owner"
    )
    EstablishmentActivityDescription.objects.create(
        establishment=establishment,
        description="Description initiale de l'établissement.",
        source=EstablishmentActivityDescription.Source.MANUAL,
        submitted_by=owner,
    )
    BusinessUnit.objects.filter(pk=hotel.pk).update(
        instance_description="Description initiale du pôle."
    )
    observation = create_observation(
        membership=owner.establishment_memberships.get(),
    )
    processing = observation.processing
    assert processing.status == ObservationProcessing.Status.QUEUED
    published_at = processing.published_at
    access_token = login(api_client, user=owner)

    with patch("houston.signals.services.enqueue_observation_processing") as enqueue:
        response = api_client.patch(
            activity_description_url(establishment.id),
            {"description": "Description actualisée pour la prochaine analyse."},
            format="json",
            **auth_headers(access_token),
        )
        assert response.status_code == 200
        pole = api_client.patch(
            business_unit_detail_url(establishment.id, hotel.id),
            {"instance_description": "Périmètre actualisé du pôle hôtel."},
            format="json",
            **auth_headers(access_token),
        )
        assert pole.status_code == 200
        context = build_establishment_context(establishment_id=establishment.id)
        payload = build_pipeline_input(observation=observation)

    assert enqueue.call_count == 0
    processing.refresh_from_db()
    assert processing.status == ObservationProcessing.Status.QUEUED
    assert processing.published_at == published_at
    assert context["activity_description"] == (
        "Description actualisée pour la prochaine analyse."
    )
    assert payload["prompt_version"] == AI_OBSERVATION_PIPELINE_PROMPT_VERSION
    assert payload["establishment_context"]["activity_description"] == (
        "Description actualisée pour la prochaine analyse."
    )
    active_units = {
        unit["specific_name"]: unit["instance_description"]
        for unit in payload["establishment_context"]["active_business_units"]
    }
    routing_units = {
        unit["specific_name"]: unit["instance_description"]
        for unit in payload["routing_taxonomy"]["business_units"]
    }
    assert active_units[hotel.specific_name] == "Périmètre actualisé du pôle hôtel."
    assert routing_units[hotel.specific_name] == "Périmètre actualisé du pôle hôtel."
