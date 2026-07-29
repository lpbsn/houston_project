from __future__ import annotations

import io
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import close_old_connections
from django.utils import timezone
from PIL import Image

from houston.accounts.models import User
from houston.action_plans.exceptions import ActionPlanValidationError
from houston.action_plans.models import ActionPlanExecution
from houston.action_plans.services import create_action_plan_with_execution
from houston.action_plans.tests.helpers import build_assignee_payload, build_task_payload
from houston.establishments.models import EstablishmentMembership
from houston.establishments.tests.conftest import TEST_PASSWORD
from houston.establishments.tests.taxonomy_helpers import create_membership_with_business_unit_scope
from houston.observations.models import Observation, ObservationMedia
from houston.signals.exceptions import SignalStateError
from houston.signals.models import Signal, SignalSourceObservation
from houston.signals.permissions import can_archive_signal
from houston.signals.services import archive_signal
from houston.signals.tests.conftest import (
    auth_headers,
    build_api_membership,
    create_minimal_v3_signal,
    create_restaurant_v3_taxonomy,
    login,
    signal_detail_url,
    signal_feed_url,
)
from houston.signals.tests.pipeline_helpers import setup_hotel_taxonomy
from houston.testing.factories import build_membership

pytestmark = pytest.mark.django_db


def _png_upload() -> SimpleUploadedFile:
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), color="red").save(buffer, format="PNG")
    buffer.seek(0)
    return SimpleUploadedFile("photo.png", buffer.read(), content_type="image/png")


def _create_observation_with_photo(*, api_client, membership, text: str = "A" * 20):
    token = login(api_client, user=membership.user)
    upload_response = api_client.post(
        f"/api/v1/establishments/{membership.establishment_id}/temporary-uploads/",
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
    observation = Observation.objects.get(id=submit_response.json()["id"])
    return observation, token


def _link_created_from(*, signal: Signal, observation: Observation) -> None:
    SignalSourceObservation.objects.create(
        signal=signal,
        observation=observation,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
    )


def _create_linked_ap(*, membership, signal: Signal):
    pilot = signal.responsible_business_unit
    assert pilot is not None
    return create_action_plan_with_execution(
        establishment_id=membership.establishment_id,
        created_by=membership,
        pilot_business_unit_id=pilot.id,
        title="Linked from archive race",
        source_signal_id=signal.id,
        tasks=[build_task_payload(task="Follow up", business_unit=pilot)],
        assignees=[
            build_assignee_payload(
                membership=membership,
                business_unit=pilot,
            )
        ],
    )


def test_archive_signal_sets_archived_and_keeps_merged_into_null():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(
        membership,
        title="Interesting",
        status=Signal.Status.INTERESTING,
    )

    result = archive_signal(signal=signal)

    assert result.status == Signal.Status.ARCHIVED
    assert result.merged_into_id is None
    signal.refresh_from_db()
    assert signal.status == Signal.Status.ARCHIVED
    assert signal.merged_into_id is None


def test_archive_signal_rejects_in_progress_and_non_interesting():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    in_progress = create_minimal_v3_signal(
        membership,
        title="In progress",
        status=Signal.Status.IN_PROGRESS,
    )
    open_signal = create_minimal_v3_signal(membership, title="Open")

    with pytest.raises(SignalStateError):
        archive_signal(signal=in_progress)
    with pytest.raises(SignalStateError):
        archive_signal(signal=open_signal)

    in_progress.refresh_from_db()
    open_signal.refresh_from_db()
    assert in_progress.status == Signal.Status.IN_PROGRESS
    assert open_signal.status == Signal.Status.OPEN


def test_staff_cannot_archive():
    membership = build_api_membership(role=EstablishmentMembership.Role.STAFF)
    signal = create_minimal_v3_signal(
        membership,
        title="Interesting",
        status=Signal.Status.INTERESTING,
    )

    assert can_archive_signal(membership, signal) is False


def test_staff_cannot_archive_api(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.STAFF)
    signal = create_minimal_v3_signal(
        membership,
        title="Interesting",
        status=Signal.Status.INTERESTING,
    )
    token = login(api_client, user=membership.user)

    response = api_client.post(
        signal_detail_url(membership.establishment_id, signal.id) + "archive/",
        **auth_headers(token),
    )

    assert response.status_code == 403
    signal.refresh_from_db()
    assert signal.status == Signal.Status.INTERESTING


def test_owner_can_archive_api(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(
        membership,
        title="Interesting",
        status=Signal.Status.INTERESTING,
    )
    token = login(api_client, user=membership.user)

    response = api_client.post(
        signal_detail_url(membership.establishment_id, signal.id) + "archive/",
        **auth_headers(token),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == Signal.Status.ARCHIVED
    assert payload["permission_hints"]["can_archive"] is False
    assert payload["permission_hints"]["can_create_linked_action_plan"] is False
    signal.refresh_from_db()
    assert signal.merged_into_id is None


def test_archive_in_progress_api_returns_403(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(
        membership,
        title="In progress",
        status=Signal.Status.IN_PROGRESS,
    )
    token = login(api_client, user=membership.user)

    response = api_client.post(
        signal_detail_url(membership.establishment_id, signal.id) + "archive/",
        **auth_headers(token),
    )

    assert response.status_code == 403
    signal.refresh_from_db()
    assert signal.status == Signal.Status.IN_PROGRESS


def test_manager_archive_requires_scope(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.MANAGER)
    signal = create_minimal_v3_signal(
        membership,
        title="Scoped",
        status=Signal.Status.INTERESTING,
    )
    taxonomy = create_restaurant_v3_taxonomy(membership.establishment)
    assert taxonomy.maintenance is not None

    user2 = User.objects.create_user(
        username=f"mgr_{uuid.uuid4().hex[:6]}",
        email=f"mgr_{uuid.uuid4().hex[:6]}@example.com",
        password=TEST_PASSWORD,
        status=User.Status.ACTIVE,
    )
    other = EstablishmentMembership.objects.create(
        user=user2,
        establishment=membership.establishment,
        role=EstablishmentMembership.Role.MANAGER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    token = login(api_client, user=other.user)

    denied = api_client.post(
        signal_detail_url(membership.establishment_id, signal.id) + "archive/",
        **auth_headers(token),
    )
    assert denied.status_code == 403

    create_membership_with_business_unit_scope(
        membership=other,
        business_unit=taxonomy.maintenance,
    )
    allowed = api_client.post(
        signal_detail_url(membership.establishment_id, signal.id) + "archive/",
        **auth_headers(token),
    )
    assert allowed.status_code == 200
    assert allowed.json()["status"] == Signal.Status.ARCHIVED


def test_archived_detail_returns_404(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(
        membership,
        title="Interesting",
        status=Signal.Status.INTERESTING,
    )
    archive_signal(signal=signal)
    token = login(api_client, user=membership.user)

    response = api_client.get(
        signal_detail_url(membership.establishment_id, signal.id),
        **auth_headers(token),
    )

    assert response.status_code == 404


def test_archived_excluded_from_feed_and_interesting_filter(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    archived = create_minimal_v3_signal(
        membership,
        title="To archive",
        status=Signal.Status.INTERESTING,
    )
    still_interesting = create_minimal_v3_signal(
        membership,
        title="Keep interesting",
        status=Signal.Status.INTERESTING,
    )
    archive_signal(signal=archived)
    token = login(api_client, user=membership.user)

    default_feed = api_client.get(
        signal_feed_url(membership.establishment_id) + "?view_mode=general",
        **auth_headers(token),
    )
    assert default_feed.status_code == 200
    default_ids = {item["id"] for item in default_feed.json()["items"]}
    assert str(archived.id) not in default_ids
    assert str(still_interesting.id) in default_ids

    interesting_feed = api_client.get(
        signal_feed_url(membership.establishment_id)
        + "?view_mode=general&statuses=interesting",
        **auth_headers(token),
    )
    assert interesting_feed.status_code == 200
    interesting_ids = {item["id"] for item in interesting_feed.json()["items"]}
    assert str(archived.id) not in interesting_ids
    assert str(still_interesting.id) in interesting_ids


def test_feed_still_rejects_archived_status_filter(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    token = login(api_client, user=membership.user)

    response = api_client.get(
        signal_feed_url(membership.establishment_id)
        + "?view_mode=general&statuses=archived",
        **auth_headers(token),
    )

    assert response.status_code == 400


def test_create_linked_ap_rejected_on_archived():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(
        membership,
        title="Interesting",
        status=Signal.Status.INTERESTING,
    )
    archive_signal(signal=signal)

    with pytest.raises(ActionPlanValidationError):
        _create_linked_ap(membership=membership, signal=signal)

    assert not ActionPlanExecution.objects.filter(source_signal_id=signal.id).exists()


def test_archive_deletes_created_from_media_when_last_active(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    observation, _token = _create_observation_with_photo(
        api_client=api_client,
        membership=membership,
    )
    signal = create_minimal_v3_signal(
        membership,
        title="Interesting with photo",
        status=Signal.Status.INTERESTING,
    )
    _link_created_from(signal=signal, observation=observation)
    assert ObservationMedia.objects.filter(observation_id=observation.id).exists()

    archive_signal(signal=signal)

    assert not ObservationMedia.objects.filter(observation_id=observation.id).exists()


def test_archive_keeps_media_when_sibling_still_active(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    observation, _token = _create_observation_with_photo(
        api_client=api_client,
        membership=membership,
    )
    interesting = create_minimal_v3_signal(
        membership,
        title="Interesting sibling",
        status=Signal.Status.INTERESTING,
    )
    open_sibling = create_minimal_v3_signal(membership, title="Open sibling")
    _link_created_from(signal=interesting, observation=observation)
    _link_created_from(signal=open_sibling, observation=observation)

    archive_signal(signal=interesting)

    interesting.refresh_from_db()
    assert interesting.status == Signal.Status.ARCHIVED
    assert ObservationMedia.objects.filter(observation_id=observation.id).exists()


def test_archive_releases_active_uniqueness_for_new_signal():
    membership = build_membership()
    hotel = setup_hotel_taxonomy(membership.establishment)
    subject = hotel.activity_subjects.get()
    first = Signal.objects.create(
        establishment=membership.establishment,
        affected_business_unit=hotel,
        responsible_business_unit=hotel,
        activity_subject=subject,
        title="Interesting",
        structured_summary="First.",
        issue_focus="climatisation",
        status=Signal.Status.INTERESTING,
        routing_status=Signal.RoutingStatus.RESOLVED,
        expected_action="inspect",
        last_activity_at=timezone.now(),
    )
    archive_signal(signal=first)

    second = Signal.objects.create(
        establishment=membership.establishment,
        affected_business_unit=hotel,
        responsible_business_unit=hotel,
        activity_subject=subject,
        title="Recurrence",
        structured_summary="Second.",
        issue_focus="climatisation",
        status=Signal.Status.OPEN,
        routing_status=Signal.RoutingStatus.RESOLVED,
        expected_action="inspect",
        last_activity_at=timezone.now(),
    )

    assert second.status == Signal.Status.OPEN
    first.refresh_from_db()
    assert first.status == Signal.Status.ARCHIVED


def test_archive_hint_true_only_for_interesting_commandable(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    interesting = create_minimal_v3_signal(
        membership,
        title="Interesting",
        status=Signal.Status.INTERESTING,
    )
    open_signal = create_minimal_v3_signal(membership, title="Open")
    token = login(api_client, user=membership.user)

    interesting_detail = api_client.get(
        signal_detail_url(membership.establishment_id, interesting.id),
        **auth_headers(token),
    )
    open_detail = api_client.get(
        signal_detail_url(membership.establishment_id, open_signal.id),
        **auth_headers(token),
    )

    assert interesting_detail.status_code == 200
    assert interesting_detail.json()["permission_hints"]["can_archive"] is True
    assert open_detail.status_code == 200
    assert open_detail.json()["permission_hints"]["can_archive"] is False


@pytest.mark.django_db(transaction=True)
def test_concurrent_archive_vs_linked_ap_create():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(
        membership,
        title="Race target",
        status=Signal.Status.INTERESTING,
    )
    signal_id = signal.id

    def try_archive():
        close_old_connections()
        try:
            archive_signal(signal=Signal.objects.get(id=signal_id))
            return "archive_ok"
        except SignalStateError:
            return "archive_fail"

    def try_ap():
        close_old_connections()
        try:
            _create_linked_ap(
                membership=membership,
                signal=Signal.objects.get(id=signal_id),
            )
            return "ap_ok"
        except ActionPlanValidationError:
            return "ap_fail"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda fn: fn(), [try_archive, try_ap]))

    signal.refresh_from_db()
    assert results.count("archive_ok") + results.count("ap_ok") == 1
    assert "archive_fail" in results or "ap_fail" in results

    if "archive_ok" in results:
        assert signal.status == Signal.Status.ARCHIVED
        assert not ActionPlanExecution.objects.filter(source_signal_id=signal.id).exists()
    else:
        assert signal.status == Signal.Status.IN_PROGRESS
        assert ActionPlanExecution.objects.filter(source_signal_id=signal.id).exists()
        with pytest.raises(SignalStateError):
            archive_signal(signal=signal)
        signal.refresh_from_db()
        assert signal.status == Signal.Status.IN_PROGRESS


@pytest.mark.django_db(transaction=True)
def test_concurrent_archive_vs_ap_with_shared_created_from_keeps_media(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    observation, _token = _create_observation_with_photo(
        api_client=api_client,
        membership=membership,
    )
    interesting = create_minimal_v3_signal(
        membership,
        title="Interesting race",
        status=Signal.Status.INTERESTING,
    )
    sibling = create_minimal_v3_signal(membership, title="Open sibling")
    _link_created_from(signal=interesting, observation=observation)
    _link_created_from(signal=sibling, observation=observation)
    signal_id = interesting.id

    def try_archive():
        close_old_connections()
        try:
            archive_signal(signal=Signal.objects.get(id=signal_id))
            return "archive_ok"
        except SignalStateError:
            return "archive_fail"

    def try_ap():
        close_old_connections()
        try:
            _create_linked_ap(
                membership=membership,
                signal=Signal.objects.get(id=signal_id),
            )
            return "ap_ok"
        except ActionPlanValidationError:
            return "ap_fail"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda fn: fn(), [try_archive, try_ap]))

    interesting.refresh_from_db()
    sibling.refresh_from_db()
    assert results.count("archive_ok") + results.count("ap_ok") == 1
    assert ObservationMedia.objects.filter(observation_id=observation.id).exists()
    assert sibling.status == Signal.Status.OPEN
    assert interesting.status in {
        Signal.Status.ARCHIVED,
        Signal.Status.IN_PROGRESS,
    }
    if interesting.status == Signal.Status.ARCHIVED:
        assert interesting.merged_into_id is None
        assert not ActionPlanExecution.objects.filter(
            source_signal_id=interesting.id,
        ).exists()
    else:
        assert ActionPlanExecution.objects.filter(source_signal_id=interesting.id).exists()


@pytest.mark.django_db(transaction=True)
def test_archive_last_active_shared_created_from_deletes_media(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    observation, _token = _create_observation_with_photo(
        api_client=api_client,
        membership=membership,
    )
    interesting = create_minimal_v3_signal(
        membership,
        title="Last interesting",
        status=Signal.Status.INTERESTING,
    )
    resolved_sibling = create_minimal_v3_signal(
        membership,
        title="Already resolved",
        status=Signal.Status.RESOLVED,
    )
    _link_created_from(signal=interesting, observation=observation)
    _link_created_from(signal=resolved_sibling, observation=observation)

    archive_signal(signal=interesting)

    interesting.refresh_from_db()
    assert interesting.status == Signal.Status.ARCHIVED
    assert not ObservationMedia.objects.filter(observation_id=observation.id).exists()
