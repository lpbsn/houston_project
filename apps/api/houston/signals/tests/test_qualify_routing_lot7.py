from __future__ import annotations

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest
from django.db import close_old_connections, connections
from django.utils import timezone

from houston.accounts.models import User
from houston.establishments.models import EstablishmentMembership
from houston.establishments.tests.conftest import TEST_PASSWORD
from houston.establishments.tests.taxonomy_helpers import (
    create_membership_with_business_unit_scope,
)
from houston.signals.models import (
    CandidateSignal,
    ExpectedAction,
    Signal,
    SignalSourceObservation,
)
from houston.signals.permissions import can_qualify_routing
from houston.signals.routing_resolver import resolve_materialized_routing
from houston.signals.services import (
    apply_expected_action_on_aggregation,
    normalize_issue_focus,
    qualify_signal_routing,
    record_source_observation_link,
)
from houston.signals.tests.conftest import (
    auth_headers,
    build_api_membership,
    create_minimal_v3_signal,
    create_observation,
    create_restaurant_v3_taxonomy,
    login,
    signal_detail_url,
)
from houston.testing.factories import build_membership
from houston.testing.taxonomy import create_v3_signal

pytestmark = pytest.mark.django_db


def _qualify_url(establishment_id, signal_id) -> str:
    return signal_detail_url(establishment_id, signal_id) + "qualify-routing/"


def _unassigned_signal(membership, *, title: str = "Unassigned") -> Signal:
    return Signal.objects.create(
        establishment=membership.establishment,
        title=title,
        structured_summary="Needs qualification.",
        status=Signal.Status.OPEN,
        routing_status=Signal.RoutingStatus.UNASSIGNED,
        issue_focus="",
        last_activity_at=timezone.now(),
    )


def _full_patch(taxonomy, *, issue_focus: str = "lampe hs") -> dict:
    assert taxonomy.maintenance is not None
    assert taxonomy.lighting_subject is not None
    return {
        "affected_business_unit_id": str(taxonomy.restaurant.id),
        "responsible_business_unit_id": str(taxonomy.maintenance.id),
        "activity_subject_id": str(taxonomy.lighting_subject.id),
        "issue_focus": issue_focus,
        "expected_action": ExpectedAction.REPAIR,
    }


def test_staff_cannot_qualify(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.STAFF)
    signal = _unassigned_signal(membership)
    token = login(api_client, user=membership.user)

    response = api_client.post(
        _qualify_url(membership.establishment_id, signal.id),
        data={},
        format="json",
        **auth_headers(token),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"


def test_owner_partial_stays_unassigned_lifecycle_unchanged(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    taxonomy = create_restaurant_v3_taxonomy(membership.establishment)
    signal = _unassigned_signal(membership)
    token = login(api_client, user=membership.user)

    response = api_client.post(
        _qualify_url(membership.establishment_id, signal.id),
        data={"affected_business_unit_id": str(taxonomy.restaurant.id)},
        format="json",
        **auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["qualification_outcome"] == "updated"
    assert body["status"] == Signal.Status.OPEN
    signal.refresh_from_db()
    assert signal.routing_status == Signal.RoutingStatus.UNASSIGNED
    assert signal.affected_business_unit_id == taxonomy.restaurant.id
    assert signal.status == Signal.Status.OPEN


def test_owner_full_routing_resolved(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    taxonomy = create_restaurant_v3_taxonomy(membership.establishment)
    signal = _unassigned_signal(membership)
    token = login(api_client, user=membership.user)

    response = api_client.post(
        _qualify_url(membership.establishment_id, signal.id),
        data=_full_patch(taxonomy),
        format="json",
        **auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["qualification_outcome"] == "updated"
    signal.refresh_from_db()
    assert signal.routing_status == Signal.RoutingStatus.RESOLVED
    assert signal.issue_focus == normalize_issue_focus("lampe hs")
    assert signal.expected_action == ExpectedAction.REPAIR


def test_patch_omitted_keeps_null_clears(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    taxonomy = create_restaurant_v3_taxonomy(membership.establishment)
    signal = _unassigned_signal(membership)
    signal.affected_business_unit = taxonomy.restaurant
    signal.responsible_business_unit = taxonomy.maintenance
    signal.save(
        update_fields=["affected_business_unit", "responsible_business_unit", "updated_at"]
    )
    token = login(api_client, user=membership.user)

    keep = api_client.post(
        _qualify_url(membership.establishment_id, signal.id),
        data={},
        format="json",
        **auth_headers(token),
    )
    assert keep.status_code == 200
    signal.refresh_from_db()
    assert signal.affected_business_unit_id == taxonomy.restaurant.id

    clear = api_client.post(
        _qualify_url(membership.establishment_id, signal.id),
        data={"affected_business_unit_id": None},
        format="json",
        **auth_headers(token),
    )
    assert clear.status_code == 200
    signal.refresh_from_db()
    assert signal.affected_business_unit_id is None


def test_invalid_uuid_inactive_and_cross_establishment_rejected(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    taxonomy = create_restaurant_v3_taxonomy(membership.establishment)
    signal = _unassigned_signal(membership)
    token = login(api_client, user=membership.user)

    unknown = api_client.post(
        _qualify_url(membership.establishment_id, signal.id),
        data={"affected_business_unit_id": str(uuid.uuid4())},
        format="json",
        **auth_headers(token),
    )
    assert unknown.status_code == 400
    assert unknown.json()["code"] == "invalid_business_unit"

    taxonomy.restaurant.active = False
    taxonomy.restaurant.save(update_fields=["active", "updated_at"])
    inactive = api_client.post(
        _qualify_url(membership.establishment_id, signal.id),
        data={"affected_business_unit_id": str(taxonomy.restaurant.id)},
        format="json",
        **auth_headers(token),
    )
    assert inactive.status_code == 400
    assert inactive.json()["code"] == "inactive_business_unit"

    other = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    other_taxonomy = create_restaurant_v3_taxonomy(other.establishment)
    cross = api_client.post(
        _qualify_url(membership.establishment_id, signal.id),
        data={"affected_business_unit_id": str(other_taxonomy.restaurant.id)},
        format="json",
        **auth_headers(token),
    )
    assert cross.status_code == 400
    assert cross.json()["code"] == "invalid_business_unit"


def test_subject_corrects_responsible(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    taxonomy = create_restaurant_v3_taxonomy(membership.establishment)
    assert taxonomy.maintenance is not None
    assert taxonomy.lighting_subject is not None
    assert taxonomy.stock_subject is not None
    signal = _unassigned_signal(membership)
    token = login(api_client, user=membership.user)

    response = api_client.post(
        _qualify_url(membership.establishment_id, signal.id),
        data={
            "affected_business_unit_id": str(taxonomy.restaurant.id),
            "responsible_business_unit_id": str(taxonomy.bar.id),
            "activity_subject_id": str(taxonomy.lighting_subject.id),
            "issue_focus": "neon",
        },
        format="json",
        **auth_headers(token),
    )

    assert response.status_code == 200
    signal.refresh_from_db()
    assert signal.responsible_business_unit_id == taxonomy.maintenance.id
    assert signal.activity_subject_id == taxonomy.lighting_subject.id
    assert signal.routing_status == Signal.RoutingStatus.RESOLVED


def test_manager_in_scope_can_qualify_out_of_scope_denied(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    assert taxonomy.maintenance is not None

    manager_user = User.objects.create_user(
        username=f"mgr_{uuid.uuid4().hex[:6]}",
        email=f"mgr_{uuid.uuid4().hex[:6]}@example.com",
        password=TEST_PASSWORD,
        status=User.Status.ACTIVE,
    )
    manager = EstablishmentMembership.objects.create(
        user=manager_user,
        establishment=owner.establishment,
        role=EstablishmentMembership.Role.MANAGER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    create_membership_with_business_unit_scope(
        membership=manager,
        business_unit=taxonomy.restaurant,
    )

    signal = _unassigned_signal(owner)
    signal.affected_business_unit = taxonomy.restaurant
    signal.save(update_fields=["affected_business_unit", "updated_at"])
    token = login(api_client, user=manager.user)

    ok = api_client.post(
        _qualify_url(manager.establishment_id, signal.id),
        data={"affected_business_unit_id": str(taxonomy.restaurant.id)},
        format="json",
        **auth_headers(token),
    )
    assert ok.status_code == 200

    denied = api_client.post(
        _qualify_url(manager.establishment_id, signal.id),
        data={"affected_business_unit_id": str(taxonomy.bar.id)},
        format="json",
        **auth_headers(token),
    )
    assert denied.status_code == 403


def test_manager_out_of_source_scope_denied(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    manager_user = User.objects.create_user(
        username=f"mgr2_{uuid.uuid4().hex[:6]}",
        email=f"mgr2_{uuid.uuid4().hex[:6]}@example.com",
        password=TEST_PASSWORD,
        status=User.Status.ACTIVE,
    )
    manager = EstablishmentMembership.objects.create(
        user=manager_user,
        establishment=owner.establishment,
        role=EstablishmentMembership.Role.MANAGER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    create_membership_with_business_unit_scope(
        membership=manager,
        business_unit=taxonomy.bar,
    )
    signal = _unassigned_signal(owner)
    signal.affected_business_unit = taxonomy.restaurant
    signal.save(update_fields=["affected_business_unit", "updated_at"])
    token = login(api_client, user=manager.user)

    response = api_client.post(
        _qualify_url(manager.establishment_id, signal.id),
        data={"affected_business_unit_id": str(taxonomy.bar.id)},
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 403


def test_collision_merges_without_third_signal_or_duplicate_links(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    taxonomy = create_restaurant_v3_taxonomy(membership.establishment)
    assert taxonomy.maintenance is not None
    assert taxonomy.lighting_subject is not None
    focus = normalize_issue_focus("collision focus")
    survivor = create_v3_signal(
        membership.establishment,
        affected_business_unit=taxonomy.restaurant,
        responsible_business_unit=taxonomy.maintenance,
        activity_subject=taxonomy.lighting_subject,
        routing_status=Signal.RoutingStatus.RESOLVED,
        issue_focus=focus,
        title="Survivor",
    )
    survivor.expected_action = ExpectedAction.INSPECT
    survivor.save(update_fields=["expected_action", "updated_at"])

    source = _unassigned_signal(membership, title="Source")
    observation = create_observation(membership=membership)
    record_source_observation_link(
        signal=source,
        observation=observation,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
    )
    candidate = CandidateSignal.objects.create(
        observation=observation,
        establishment=membership.establishment,
        title="cand",
        structured_summary="cand",
        issue_focus=focus,
        expected_action=ExpectedAction.REPAIR,
        outcome=CandidateSignal.Outcome.CREATED_SIGNAL,
        result_signal=source,
        resolution_audit={},
    )

    token = login(api_client, user=membership.user)
    response = api_client.post(
        _qualify_url(membership.establishment_id, source.id),
        data=_full_patch(taxonomy, issue_focus=focus),
        format="json",
        **auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["qualification_outcome"] == "merged"
    assert body["surviving_signal_id"] == str(survivor.id)
    assert body["merged_signal_id"] == str(source.id)
    assert body["id"] == str(survivor.id)

    source.refresh_from_db()
    survivor.refresh_from_db()
    assert source.status == Signal.Status.ARCHIVED
    assert source.merged_into_id == survivor.id
    assert Signal.objects.filter(establishment=membership.establishment).count() == 2
    assert Signal.objects.filter(
        establishment=membership.establishment,
        status__in={"open", "in_progress"},
    ).count() == 1

    assert SignalSourceObservation.objects.filter(
        signal=source,
        observation=observation,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
    ).exists()
    assert (
        SignalSourceObservation.objects.filter(
            signal=survivor,
            observation=observation,
            link_type=SignalSourceObservation.LinkType.MERGED_FROM,
        ).count()
        == 1
    )
    candidate.refresh_from_db()
    assert candidate.result_signal_id == survivor.id
    assert survivor.expected_action == ExpectedAction.INSPECT

    # Idempotent merged_from creation
    from houston.signals.services import merge_signal_into_resolved

    merge_signal_into_resolved(
        source=source,
        target=survivor,
        resolution_audit={},
        candidate_expected_action=ExpectedAction.REPAIR,
    )
    assert (
        SignalSourceObservation.objects.filter(
            signal=survivor,
            observation=observation,
            link_type=SignalSourceObservation.LinkType.MERGED_FROM,
        ).count()
        == 1
    )


def test_idempotent_compatible_on_archived_merged_source(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    taxonomy = create_restaurant_v3_taxonomy(membership.establishment)
    assert taxonomy.maintenance is not None
    assert taxonomy.lighting_subject is not None
    focus = normalize_issue_focus("idem focus")
    survivor = create_v3_signal(
        membership.establishment,
        affected_business_unit=taxonomy.restaurant,
        responsible_business_unit=taxonomy.maintenance,
        activity_subject=taxonomy.lighting_subject,
        routing_status=Signal.RoutingStatus.RESOLVED,
        issue_focus=focus,
    )
    survivor.expected_action = ExpectedAction.REPAIR
    survivor.save(update_fields=["expected_action", "updated_at"])
    source = _unassigned_signal(membership)
    source.status = Signal.Status.ARCHIVED
    source.merged_into = survivor
    source.save(update_fields=["status", "merged_into", "updated_at"])
    token = login(api_client, user=membership.user)

    compatible = api_client.post(
        _qualify_url(membership.establishment_id, source.id),
        data=_full_patch(taxonomy, issue_focus=focus),
        format="json",
        **auth_headers(token),
    )
    assert compatible.status_code == 200
    assert compatible.json()["surviving_signal_id"] == str(survivor.id)
    assert compatible.json()["qualification_outcome"] == "merged"

    omit_only = api_client.post(
        _qualify_url(membership.establishment_id, source.id),
        data={},
        format="json",
        **auth_headers(token),
    )
    assert omit_only.status_code == 200
    assert omit_only.json()["surviving_signal_id"] == str(survivor.id)

    incompatible = api_client.post(
        _qualify_url(membership.establishment_id, source.id),
        data={"issue_focus": "other focus"},
        format="json",
        **auth_headers(token),
    )
    assert incompatible.status_code == 409
    assert incompatible.json()["code"] == "already_merged"


def test_qualify_uses_resolve_materialized_routing(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    taxonomy = create_restaurant_v3_taxonomy(membership.establishment)
    signal = _unassigned_signal(membership)
    token = login(api_client, user=membership.user)

    with patch(
        "houston.signals.services.resolve_materialized_routing",
        wraps=resolve_materialized_routing,
    ) as mocked:
        response = api_client.post(
            _qualify_url(membership.establishment_id, signal.id),
            data=_full_patch(taxonomy),
            format="json",
            **auth_headers(token),
        )

    assert response.status_code == 200
    assert mocked.call_count == 1


def test_can_qualify_routing_hint_false_when_merged():
    membership = build_membership(role=EstablishmentMembership.Role.OWNER)
    taxonomy = create_restaurant_v3_taxonomy(membership.establishment)
    survivor = create_minimal_v3_signal(membership)
    source = _unassigned_signal(membership)
    source.status = Signal.Status.ARCHIVED
    source.merged_into = survivor
    source.save(update_fields=["status", "merged_into", "updated_at"])
    assert (
        can_qualify_routing(
            membership,
            source,
            proposed_affected_business_unit=taxonomy.restaurant,
        )
        is False
    )


def test_d3_helper_used_on_merge(monkeypatch):
    membership = build_membership(role=EstablishmentMembership.Role.OWNER)
    taxonomy = create_restaurant_v3_taxonomy(membership.establishment)
    assert taxonomy.maintenance is not None
    assert taxonomy.lighting_subject is not None
    focus = normalize_issue_focus("d3 focus")
    survivor = create_v3_signal(
        membership.establishment,
        affected_business_unit=taxonomy.restaurant,
        responsible_business_unit=taxonomy.maintenance,
        activity_subject=taxonomy.lighting_subject,
        routing_status=Signal.RoutingStatus.RESOLVED,
        issue_focus=focus,
    )
    survivor.expected_action = ExpectedAction.INSPECT
    survivor.save(update_fields=["expected_action", "updated_at"])
    source = _unassigned_signal(membership)
    calls: list[str | None] = []

    original = apply_expected_action_on_aggregation

    def tracking(**kwargs):
        calls.append(kwargs.get("candidate_expected_action"))
        return original(**kwargs)

    monkeypatch.setattr(
        "houston.signals.services.apply_expected_action_on_aggregation",
        tracking,
    )
    result = qualify_signal_routing(
        signal=source,
        membership=membership,
        patch={
            "affected_business_unit_id": taxonomy.restaurant.id,
            "responsible_business_unit_id": taxonomy.maintenance.id,
            "activity_subject_id": taxonomy.lighting_subject.id,
            "issue_focus": focus,
            "expected_action": ExpectedAction.REPAIR,
        },
    )
    assert result.qualification_outcome == "merged"
    assert ExpectedAction.REPAIR in calls
    survivor.refresh_from_db()
    assert survivor.expected_action == ExpectedAction.INSPECT


@pytest.mark.django_db(transaction=True)
def test_concurrent_qualify_collision_single_survivor():
    membership = build_membership(role=EstablishmentMembership.Role.OWNER)
    taxonomy = create_restaurant_v3_taxonomy(membership.establishment)
    assert taxonomy.maintenance is not None
    assert taxonomy.lighting_subject is not None
    focus = normalize_issue_focus("concurrent qualify")
    target = create_v3_signal(
        membership.establishment,
        affected_business_unit=taxonomy.restaurant,
        responsible_business_unit=taxonomy.maintenance,
        activity_subject=taxonomy.lighting_subject,
        routing_status=Signal.RoutingStatus.RESOLVED,
        issue_focus=focus,
        title="Target",
    )
    source_a = _unassigned_signal(membership, title="A")
    source_b = _unassigned_signal(membership, title="B")
    patch = {
        "affected_business_unit_id": taxonomy.restaurant.id,
        "responsible_business_unit_id": taxonomy.maintenance.id,
        "activity_subject_id": taxonomy.lighting_subject.id,
        "issue_focus": focus,
        "expected_action": ExpectedAction.REPAIR,
    }
    barrier = threading.Barrier(2, timeout=10)

    def run(signal_id):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            signal = Signal.objects.get(id=signal_id)
            qualify_signal_routing(signal=signal, membership=membership, patch=patch)
        finally:
            connections.close_all()

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            list(executor.map(run, [source_a.id, source_b.id]))
    finally:
        connections.close_all()

    active = Signal.objects.filter(
        establishment=membership.establishment,
        status__in={"open", "in_progress"},
        routing_status=Signal.RoutingStatus.RESOLVED,
        issue_focus=focus,
    )
    assert active.count() == 1
    assert active.get().id == target.id
    assert (
        SignalSourceObservation.objects.filter(
            signal=target,
            link_type=SignalSourceObservation.LinkType.MERGED_FROM,
        ).count()
        >= 0
    )
    # No duplicate merged_from for same observation pairs
    links = SignalSourceObservation.objects.filter(
        signal=target,
        link_type=SignalSourceObservation.LinkType.MERGED_FROM,
    )
    pairs = [(link.observation_id, link.link_type) for link in links]
    assert len(pairs) == len(set(pairs))
