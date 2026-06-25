from __future__ import annotations

import io
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import close_old_connections
from django.test import Client, override_settings
from django.urls import reverse
from PIL import Image

from houston.establishments.models import EstablishmentMembership
from houston.observations.media_access import sign_observation_media_preview
from houston.observations.models import Observation, ObservationMedia
from houston.signals.models import Signal, SignalSourceObservation
from houston.signals.services import (
    aggregate_candidate_into_signal,
    apply_pipeline_output,
    resolve_signal,
)
from houston.signals.tests.conftest import (
    auth_headers,
    build_api_membership,
    create_minimal_v3_signal,
    create_restaurant_v3_taxonomy,
    golden_two_candidate_pipeline_output,
    login,
    signal_detail_url,
)
from houston.uploads.models import TemporaryUpload
from houston.uploads.private_storage import get_private_media_storage

pytestmark = pytest.mark.django_db


def _png_upload() -> SimpleUploadedFile:
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), color="red").save(buffer, format="PNG")
    buffer.seek(0)
    return SimpleUploadedFile("photo.png", buffer.read(), content_type="image/png")


def _uploads_url(establishment_id) -> str:
    return f"/api/v1/establishments/{establishment_id}/temporary-uploads/"


def _create_observation_with_photo(*, api_client, membership, text: str = "A" * 20):
    token = login(api_client, user=membership.user)
    upload_response = api_client.post(
        _uploads_url(membership.establishment_id),
        {"file": _png_upload()},
        format="multipart",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert upload_response.status_code == 201
    upload_id = upload_response.json()["id"]

    submit_response = api_client.post(
        f"/api/v1/establishments/{membership.establishment_id}/observations/",
        {"text": text, "temporary_upload_ids": [upload_id]},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert submit_response.status_code == 201
    observation_id = submit_response.json()["id"]
    observation = Observation.objects.get(id=observation_id)
    return observation, token


def _link_created_from(*, signal: Signal, observation: Observation):
    SignalSourceObservation.objects.create(
        signal=signal,
        observation=observation,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
    )


def test_signal_detail_returns_created_from_media_items(api_client):
    membership = build_api_membership()
    observation, token = _create_observation_with_photo(
        api_client=api_client,
        membership=membership,
    )
    signal = create_minimal_v3_signal(membership, title="Photo signal")
    _link_created_from(signal=signal, observation=observation)

    response = api_client.get(
        signal_detail_url(membership.establishment_id, signal.id),
        **auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["media_count"] == 1
    assert body["source_context"]["media_count"] == 1
    assert len(body["media_items"]) == 1
    item = body["media_items"][0]
    assert set(item.keys()) == {
        "id",
        "preview_url",
        "content_type",
        "size_bytes",
        "position",
        "observation_id",
    }
    assert item["observation_id"] == str(observation.id)
    assert item["position"] == 1
    assert "storage_key" not in response.content.decode()

    preview = Client().get(item["preview_url"])
    assert preview.status_code == 200
    assert preview["Content-Type"] == item["content_type"]


def test_aggregated_observation_media_deleted_and_not_in_detail(api_client):
    membership = build_api_membership()
    created_obs, token = _create_observation_with_photo(
        api_client=api_client,
        membership=membership,
    )
    aggregated_obs, _ = _create_observation_with_photo(
        api_client=api_client,
        membership=membership,
        text="B" * 20,
    )
    signal = create_minimal_v3_signal(membership, title="Aggregate target")
    _link_created_from(signal=signal, observation=created_obs)

    aggregate_candidate_into_signal(signal=signal, observation=aggregated_obs)

    assert not ObservationMedia.objects.filter(observation_id=aggregated_obs.id).exists()
    storage = get_private_media_storage()
    for media in ObservationMedia.objects.filter(observation_id=created_obs.id):
        assert storage.exists(media.storage_key)

    response = api_client.get(
        signal_detail_url(membership.establishment_id, signal.id),
        **auth_headers(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["media_count"] == 1
    assert len(body["media_items"]) == 1
    assert body["media_items"][0]["observation_id"] == str(created_obs.id)


@pytest.mark.django_db(transaction=True)
def test_resolve_deletes_created_from_media(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    observation, token = _create_observation_with_photo(
        api_client=api_client,
        membership=membership,
    )
    signal = create_minimal_v3_signal(membership, title="Resolve me")
    _link_created_from(signal=signal, observation=observation)
    media = ObservationMedia.objects.get(observation_id=observation.id)
    upload_id = media.temporary_upload_id
    storage_key = media.storage_key

    response = api_client.post(
        signal_detail_url(membership.establishment_id, signal.id) + "resolve/",
        **auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == Signal.Status.RESOLVED
    assert body["media_count"] == 0
    assert body["media_items"] == []
    assert not ObservationMedia.objects.filter(observation_id=observation.id).exists()
    upload = TemporaryUpload.objects.get(id=upload_id)
    assert upload.status == TemporaryUpload.Status.DELETED
    storage = get_private_media_storage()
    assert not storage.exists(storage_key)


def test_cancel_deletes_created_from_media(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    observation, token = _create_observation_with_photo(
        api_client=api_client,
        membership=membership,
    )
    signal = create_minimal_v3_signal(membership, title="Cancel me")
    _link_created_from(signal=signal, observation=observation)

    response = api_client.post(
        signal_detail_url(membership.establishment_id, signal.id) + "cancel/",
        **auth_headers(token),
    )

    assert response.status_code == 200
    assert not ObservationMedia.objects.filter(observation_id=observation.id).exists()


def test_preview_rejects_invalid_token(api_client):
    membership = build_api_membership()
    observation, token = _create_observation_with_photo(
        api_client=api_client,
        membership=membership,
    )
    signal = create_minimal_v3_signal(membership, title="Preview guard")
    _link_created_from(signal=signal, observation=observation)

    detail = api_client.get(
        signal_detail_url(membership.establishment_id, signal.id),
        **auth_headers(token),
    )
    preview_url = detail.json()["media_items"][0]["preview_url"]
    bad_url = preview_url.replace("token=", "token=invalid")

    assert Client().get(bad_url).status_code == 404


def test_preview_rejects_wrong_establishment(api_client):
    membership = build_api_membership()
    other_membership = build_api_membership()
    observation, token = _create_observation_with_photo(
        api_client=api_client,
        membership=membership,
    )
    signal = create_minimal_v3_signal(membership, title="Establishment scope")
    _link_created_from(signal=signal, observation=observation)

    detail = api_client.get(
        signal_detail_url(membership.establishment_id, signal.id),
        **auth_headers(token),
    )
    preview_url = detail.json()["media_items"][0]["preview_url"]
    parsed = urlparse(preview_url)
    wrong_path = parsed.path.replace(
        str(membership.establishment_id),
        str(other_membership.establishment_id),
    )
    wrong_url = f"{wrong_path}?{parsed.query}"

    assert Client().get(wrong_url).status_code == 404


def test_preview_404_without_created_from_feed_signal(api_client):
    membership = build_api_membership()
    observation, _ = _create_observation_with_photo(
        api_client=api_client,
        membership=membership,
    )
    media = ObservationMedia.objects.get(observation_id=observation.id)
    token = sign_observation_media_preview(
        establishment_id=membership.establishment_id,
        media_id=media.id,
    )
    path = reverse(
        "observation-media-preview",
        kwargs={
            "establishment_id": membership.establishment_id,
            "media_id": media.id,
        },
    )
    preview_url = f"{path}?token={token}"

    assert Client().get(preview_url).status_code == 404


@pytest.mark.slow
@override_settings(HOUSTON_OBSERVATION_MEDIA_PREVIEW_TTL_SECONDS=1)
def test_preview_404_expired_token(api_client):
    membership = build_api_membership()
    observation, token = _create_observation_with_photo(
        api_client=api_client,
        membership=membership,
    )
    signal = create_minimal_v3_signal(membership, title="Preview expiry")
    _link_created_from(signal=signal, observation=observation)

    detail = api_client.get(
        signal_detail_url(membership.establishment_id, signal.id),
        **auth_headers(token),
    )
    preview_url = detail.json()["media_items"][0]["preview_url"]

    time.sleep(1.1)

    assert Client().get(preview_url).status_code == 404


def test_golden_split_keeps_media_until_last_active_signal_resolved(api_client):
    membership = build_api_membership()
    taxonomy = create_restaurant_v3_taxonomy(membership.establishment)
    observation, token = _create_observation_with_photo(
        api_client=api_client,
        membership=membership,
        text="La lumière clignote à l'entrée. Plus de sirop mojito au bar.",
    )
    Observation.objects.filter(id=observation.id).update(
        raw_text="La lumière clignote à l'entrée. Plus de sirop mojito au bar.",
    )
    observation.refresh_from_db()

    apply_pipeline_output(
        observation=observation,
        output=golden_two_candidate_pipeline_output(taxonomy=taxonomy),
    )
    signals = list(
        Signal.objects.filter(establishment=membership.establishment).order_by("created_at")
    )
    assert len(signals) == 2
    assert ObservationMedia.objects.filter(observation_id=observation.id).count() == 1

    first, second = signals
    resolve_signal(signal=first)
    assert ObservationMedia.objects.filter(observation_id=observation.id).exists()

    resolve_signal(signal=second)
    assert not ObservationMedia.objects.filter(observation_id=observation.id).exists()


def test_feed_media_count_uses_created_from_not_aggregated(api_client):
    membership = build_api_membership()
    created_obs, token = _create_observation_with_photo(
        api_client=api_client,
        membership=membership,
    )
    aggregated_obs, _ = _create_observation_with_photo(
        api_client=api_client,
        membership=membership,
        text="B" * 20,
    )
    signal = create_minimal_v3_signal(membership, title="Count source")
    _link_created_from(signal=signal, observation=created_obs)
    SignalSourceObservation.objects.create(
        signal=signal,
        observation=aggregated_obs,
        link_type=SignalSourceObservation.LinkType.AGGREGATED_FROM,
    )

    response = api_client.get(
        signal_detail_url(membership.establishment_id, signal.id),
        **auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["media_count"] == 1


def test_aggregate_keeps_media_when_observation_has_active_created_from(api_client):
    membership = build_api_membership()
    observation, token = _create_observation_with_photo(
        api_client=api_client,
        membership=membership,
    )
    created_signal = create_minimal_v3_signal(membership, title="Created from")
    aggregate_target = create_minimal_v3_signal(membership, title="Aggregate target")
    _link_created_from(signal=created_signal, observation=observation)

    aggregate_candidate_into_signal(signal=aggregate_target, observation=observation)

    assert ObservationMedia.objects.filter(observation_id=observation.id).exists()
    response = api_client.get(
        signal_detail_url(membership.establishment_id, created_signal.id),
        **auth_headers(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["media_count"] == 1
    assert len(body["media_items"]) == 1
    assert body["media_items"][0]["observation_id"] == str(observation.id)


def test_shared_created_from_resolve_first_keeps_media_second_deletes(api_client):
    membership = build_api_membership()
    observation, _ = _create_observation_with_photo(
        api_client=api_client,
        membership=membership,
    )
    first_signal = create_minimal_v3_signal(membership, title="First shared")
    second_signal = create_minimal_v3_signal(membership, title="Second shared")
    _link_created_from(signal=first_signal, observation=observation)
    _link_created_from(signal=second_signal, observation=observation)

    resolve_signal(signal=first_signal)
    assert ObservationMedia.objects.filter(observation_id=observation.id).exists()

    resolve_signal(signal=second_signal)
    assert not ObservationMedia.objects.filter(observation_id=observation.id).exists()


@pytest.mark.django_db(transaction=True)
def test_concurrent_resolve_shared_created_from_deletes_media(api_client):
    membership = build_api_membership()
    observation, _ = _create_observation_with_photo(
        api_client=api_client,
        membership=membership,
    )
    first_signal = create_minimal_v3_signal(membership, title="Concurrent first")
    second_signal = create_minimal_v3_signal(membership, title="Concurrent second")
    _link_created_from(signal=first_signal, observation=observation)
    _link_created_from(signal=second_signal, observation=observation)

    def try_resolve(signal_id):
        close_old_connections()
        signal = Signal.objects.get(id=signal_id)
        resolve_signal(signal=signal)

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(try_resolve, [first_signal.id, second_signal.id]))

    first_signal.refresh_from_db()
    second_signal.refresh_from_db()
    assert first_signal.status == Signal.Status.RESOLVED
    assert second_signal.status == Signal.Status.RESOLVED
    assert not ObservationMedia.objects.filter(observation_id=observation.id).exists()
