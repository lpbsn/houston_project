from __future__ import annotations

import pytest
from django.db import IntegrityError
from django.utils import timezone

from houston.action_plans.services import create_action_plan_with_execution
from houston.action_plans.tests.helpers import build_assignee_payload, build_task_payload
from houston.ai.observation_pipeline_schema import (
    ObservationPipelineOutput,
    PipelineCandidateOutput,
)
from houston.establishments.models import EstablishmentMembership
from houston.establishments.tests.taxonomy_helpers import create_membership_with_business_unit_scope
from houston.observations.models import ObservationProcessing
from houston.signals.constants import AI_OBSERVATION_PIPELINE_SCHEMA_VERSION
from houston.signals.exceptions import SignalStateError
from houston.signals.models import Signal
from houston.signals.permissions import (
    can_cancel_signal,
    can_mark_signal_interesting,
    can_pin_signal,
    can_resolve_signal,
)
from houston.signals.services import apply_pipeline_output, mark_signal_interesting, pin_signal
from houston.signals.tests.conftest import (
    auth_headers,
    build_api_membership,
    create_minimal_v3_signal,
    create_observation,
    create_restaurant_v3_taxonomy,
    login,
    signal_detail_url,
    signal_feed_url,
)
from houston.signals.tests.pipeline_helpers import setup_hotel_taxonomy
from houston.testing.factories import build_membership

pytestmark = pytest.mark.django_db


def test_mark_signal_interesting_sets_status_and_unpins():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(membership, title="Useful note")
    signal.is_pinned = True
    signal.pinned_at = timezone.now()
    signal.pinned_by_membership = membership
    signal.save(update_fields=["is_pinned", "pinned_at", "pinned_by_membership", "updated_at"])

    result = mark_signal_interesting(signal=signal)

    assert result.status == Signal.Status.INTERESTING
    assert result.is_pinned is False
    assert result.pinned_at is None
    assert result.pinned_by_membership_id is None


def test_mark_signal_interesting_rejects_non_open():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(
        membership,
        title="Already interesting",
        status=Signal.Status.INTERESTING,
    )

    with pytest.raises(SignalStateError):
        mark_signal_interesting(signal=signal)


def test_cannot_pin_interesting_signal():
    membership = build_api_membership(role=EstablishmentMembership.Role.DIRECTOR)
    signal = create_minimal_v3_signal(
        membership,
        title="Interesting",
        status=Signal.Status.INTERESTING,
    )

    assert can_pin_signal(membership, signal) is False
    with pytest.raises(SignalStateError):
        pin_signal(signal=signal, membership=membership)


def test_cannot_cancel_or_resolve_interesting_signal():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(
        membership,
        title="Interesting",
        status=Signal.Status.INTERESTING,
    )

    assert can_cancel_signal(membership, signal) is False
    assert can_resolve_signal(membership, signal) is False


def test_staff_cannot_mark_interesting():
    membership = build_api_membership(role=EstablishmentMembership.Role.STAFF)
    signal = create_minimal_v3_signal(membership, title="Open")

    assert can_mark_signal_interesting(membership, signal) is False


def test_staff_cannot_mark_interesting_api(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.STAFF)
    signal = create_minimal_v3_signal(membership, title="Open")
    token = login(api_client, user=membership.user)

    response = api_client.post(
        signal_detail_url(membership.establishment_id, signal.id) + "mark-interesting/",
        **auth_headers(token),
    )

    assert response.status_code == 403
    signal.refresh_from_db()
    assert signal.status == Signal.Status.OPEN


def test_owner_can_mark_interesting_api(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(membership, title="Open")
    token = login(api_client, user=membership.user)

    response = api_client.post(
        signal_detail_url(membership.establishment_id, signal.id) + "mark-interesting/",
        **auth_headers(token),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == Signal.Status.INTERESTING
    assert payload["is_pinned"] is False
    assert payload["permission_hints"]["can_mark_interesting"] is False
    assert payload["permission_hints"]["can_pin"] is False
    assert payload["permission_hints"]["can_cancel"] is False
    assert payload["permission_hints"]["can_resolve"] is False


def test_manager_mark_interesting_requires_scope(api_client):
    import uuid

    from houston.accounts.models import User
    from houston.establishments.tests.conftest import TEST_PASSWORD

    membership = build_api_membership(role=EstablishmentMembership.Role.MANAGER)
    signal = create_minimal_v3_signal(membership, title="Scoped")
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
        signal_detail_url(membership.establishment_id, signal.id) + "mark-interesting/",
        **auth_headers(token),
    )
    assert denied.status_code == 403

    create_membership_with_business_unit_scope(
        membership=other,
        business_unit=taxonomy.maintenance,
    )
    allowed = api_client.post(
        signal_detail_url(membership.establishment_id, signal.id) + "mark-interesting/",
        **auth_headers(token),
    )
    assert allowed.status_code == 200
    assert allowed.json()["status"] == Signal.Status.INTERESTING


def test_interesting_included_in_default_feed_and_filter(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.STAFF)
    taxonomy = create_restaurant_v3_taxonomy(membership.establishment)
    assert taxonomy.maintenance is not None
    create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=taxonomy.maintenance,
    )
    interesting = create_minimal_v3_signal(
        membership,
        title="Interesting note",
        status=Signal.Status.INTERESTING,
    )
    create_minimal_v3_signal(membership, title="Open note", status=Signal.Status.OPEN)
    token = login(api_client, user=membership.user)

    for view_mode in ("general", "personal"):
        default_feed = api_client.get(
            signal_feed_url(membership.establishment_id) + f"?view_mode={view_mode}",
            **auth_headers(token),
        )
        assert default_feed.status_code == 200
        default_ids = {item["id"] for item in default_feed.json()["items"]}
        assert str(interesting.id) in default_ids

    filtered = api_client.get(
        signal_feed_url(membership.establishment_id)
        + "?view_mode=general&statuses=interesting",
        **auth_headers(token),
    )
    assert filtered.status_code == 200
    items = filtered.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == str(interesting.id)
    assert items[0]["status"] == Signal.Status.INTERESTING


def test_interesting_before_resolved_in_feed_order(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    resolved = create_minimal_v3_signal(
        membership,
        title="Resolved",
        status=Signal.Status.RESOLVED,
    )
    interesting = create_minimal_v3_signal(
        membership,
        title="Interesting",
        status=Signal.Status.INTERESTING,
    )
    token = login(api_client, user=membership.user)

    response = api_client.get(
        signal_feed_url(membership.establishment_id) + "?view_mode=general",
        **auth_headers(token),
    )
    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert ids.index(str(interesting.id)) < ids.index(str(resolved.id))


def test_create_from_interesting_signal_sets_in_progress():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(
        membership,
        title="Interesting source",
        status=Signal.Status.INTERESTING,
    )
    pilot = signal.responsible_business_unit
    assert pilot is not None

    create_action_plan_with_execution(
        establishment_id=membership.establishment_id,
        created_by=membership,
        pilot_business_unit_id=pilot.id,
        title="From interesting",
        source_signal_id=signal.id,
        tasks=[build_task_payload(task="Follow up", business_unit=pilot)],
        assignees=[
            build_assignee_payload(
                membership=membership,
                business_unit=pilot,
            )
        ],
    )

    signal.refresh_from_db()
    assert signal.status == Signal.Status.IN_PROGRESS


def test_interesting_signal_is_aggregation_target():
    membership = build_membership()
    hotel = setup_hotel_taxonomy(membership.establishment)
    subject = hotel.activity_subjects.get()
    existing = Signal.objects.create(
        establishment=membership.establishment,
        affected_business_unit=hotel,
        responsible_business_unit=hotel,
        activity_subject=subject,
        title="Existing interesting",
        structured_summary="Keep as interesting.",
        issue_focus="climatisation",
        status=Signal.Status.INTERESTING,
        routing_status=Signal.RoutingStatus.RESOLVED,
        expected_action="inspect",
        last_activity_at=timezone.now(),
    )
    observation = create_observation(membership=membership)
    result = apply_pipeline_output(
        observation=observation,
        output=ObservationPipelineOutput(
            schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            candidates=[
                PipelineCandidateOutput(
                    title="Clim en panne",
                    structured_summary="La climatisation ne fonctionne plus.",
                    issue_focus="climatisation",
                    canonical_object="climatisation",
                    signal_kind="actionable",
                    expected_action="inspect",
                    information_type=None,
                    affected_business_unit_routing_key=hotel.routing_key,
                    responsible_business_unit_routing_key=hotel.routing_key,
                    activity_subject_routing_key=subject.routing_key,
                    operational_unit_key=None,
                    location_text=None,
                )
            ],
        ),
    )

    assert result.outcome == ObservationProcessing.Outcome.SIGNAL_AGGREGATED
    assert Signal.objects.filter(establishment=membership.establishment).count() == 1
    assert Signal.objects.get(pk=existing.id).status == Signal.Status.INTERESTING


def test_interesting_participates_in_active_uniqueness_constraint():
    membership = build_membership()
    hotel = setup_hotel_taxonomy(membership.establishment)
    subject = hotel.activity_subjects.get()
    Signal.objects.create(
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

    with pytest.raises(IntegrityError):
        Signal.objects.create(
            establishment=membership.establishment,
            affected_business_unit=hotel,
            responsible_business_unit=hotel,
            activity_subject=subject,
            title="Duplicate open",
            structured_summary="Second.",
            issue_focus="climatisation",
            status=Signal.Status.OPEN,
            routing_status=Signal.RoutingStatus.RESOLVED,
            expected_action="inspect",
            last_activity_at=timezone.now(),
        )
