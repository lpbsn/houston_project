from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from houston.analytics.models import (
    OperationalPattern,
    PatternIssueReport,
    PatternLifecycleEvent,
    SignalPatternAssignment,
)
from houston.analytics.services import (
    OWNER_CORRECTION_CLASSIFIER_VERSION,
    create_operational_pattern,
    mark_assignment_processing,
    report_pattern_assignment_issue,
)
from houston.analytics.signature import build_signal_pattern_signature
from houston.establishments.models import Establishment, EstablishmentMembership
from houston.signals.models import Signal
from houston.testing.auth import auth_headers, build_api_membership, login
from houston.testing.factories import create_membership

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


def rename_url(pattern_id) -> str:
    return f"/api/v1/analytics/patterns/{pattern_id}/rename/"


def merge_url(pattern_id) -> str:
    return f"/api/v1/analytics/patterns/{pattern_id}/merge/"


def move_url(pattern_id) -> str:
    return f"/api/v1/analytics/patterns/{pattern_id}/move-signals/"


def split_existing_url(pattern_id) -> str:
    return f"/api/v1/analytics/patterns/{pattern_id}/split-to-existing/"


def split_new_url(pattern_id) -> str:
    return f"/api/v1/analytics/patterns/{pattern_id}/split-to-new/"


def authenticated_post(api_client, user, url: str, payload: dict):
    token = login(api_client, user=user)
    return api_client.post(url, payload, format="json", **auth_headers(token))


def create_pattern(membership, *, label="Pattern"):
    return create_operational_pattern(
        organization=membership.establishment.organization,
        label=label,
        created_by_membership=membership,
    )


def create_signal(membership, *, title="Signal"):
    return Signal.objects.create(
        establishment=membership.establishment,
        routing_status=Signal.RoutingStatus.UNASSIGNED,
        title=title,
        structured_summary="Structured signal summary.",
        issue_focus=title.lower().replace(" ", "-"),
        last_activity_at=timezone.now(),
    )


def assign_signal(signal, pattern):
    return SignalPatternAssignment.objects.create(
        signal=signal,
        pattern=pattern,
        classification_status=SignalPatternAssignment.ClassificationStatus.SUCCEEDED,
        assigned_signature=f"sig-{signal.id}",
        assigned_classifier_version="classifier-v1",
        assigned_at=timezone.now(),
    )


OWNER_GOVERNANCE_SIGNAL_ENDPOINTS = (
    "move",
    "split_existing",
    "split_new",
)


def signal_endpoint_url(endpoint: str, source_pattern_id) -> str:
    if endpoint == "move":
        return move_url(source_pattern_id)
    if endpoint == "split_existing":
        return split_existing_url(source_pattern_id)
    if endpoint == "split_new":
        return split_new_url(source_pattern_id)
    raise AssertionError(f"Unknown endpoint: {endpoint}")


def signal_endpoint_payload(endpoint: str, *, target, signal_ids: list[str]) -> dict:
    if endpoint == "split_new":
        return {"label": "Blocked split", "signal_ids": signal_ids}
    return {"target_pattern_id": str(target.id), "signal_ids": signal_ids}


def cross_tenant_signal_id(kind: str):
    if kind == "missing":
        return uuid.uuid4()

    other_owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    other_signal = create_signal(other_owner, title=f"Other org {kind}")
    if kind == "with_assignment":
        other_pattern = create_pattern(other_owner, label=f"Other pattern {uuid.uuid4()}")
        assign_signal(other_signal, other_pattern)
    elif kind != "without_assignment":
        raise AssertionError(f"Unknown signal kind: {kind}")
    return other_signal.id


def test_owner_governance_requires_authentication(api_client):
    response = api_client.post(rename_url(uuid.uuid4()), {"label": "New"}, format="json")

    assert response.status_code == 401
    assert response.json()["code"] == "not_authenticated"


@pytest.mark.parametrize(
    "role",
    [
        EstablishmentMembership.Role.STAFF,
        EstablishmentMembership.Role.DIRECTOR,
        EstablishmentMembership.Role.MANAGER,
    ],
)
def test_non_owner_roles_cannot_govern_patterns(api_client, role):
    membership = build_api_membership(role=role)

    response = authenticated_post(
        api_client,
        membership.user,
        rename_url(uuid.uuid4()),
        {"label": "New"},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"


def test_rename_pattern_success_and_payload_allowlist(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    pattern = create_pattern(owner, label="Leak")

    response = authenticated_post(
        api_client,
        owner.user,
        rename_url(pattern.id),
        {"label": "Water leak"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source_pattern"]["pattern_id"] == str(pattern.id)
    assert body["source_pattern"]["label"] == "Water leak"
    assert body["target_pattern"] is None
    assert body["moved_signal_count"] == 0
    assert body["target_created"] is False
    assert "assignment_source" not in str(body)
    assert "raw_text" not in str(body)
    assert PatternLifecycleEvent.objects.filter(
        pattern=pattern,
        event_type=PatternLifecycleEvent.EventType.RENAMED,
    ).exists()


def test_current_non_owner_membership_does_not_block_owner_governance(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff_establishment = Establishment.objects.create(
        name="Staff site",
        organization=owner.establishment.organization,
        status=Establishment.Status.ACTIVE,
        timezone="UTC",
    )
    create_membership(
        establishment=staff_establishment,
        user=owner.user,
        role=EstablishmentMembership.Role.STAFF,
    )
    pattern = create_pattern(owner, label="Leak")

    response = authenticated_post(
        api_client,
        owner.user,
        rename_url(pattern.id),
        {"label": "Water leak"},
    )

    assert response.status_code == 200
    assert response.json()["source_pattern"]["label"] == "Water leak"


def test_owner_governance_is_organization_wide_across_establishments(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    second_establishment = Establishment.objects.create(
        name="Second site",
        organization=owner.establishment.organization,
        status=Establishment.Status.ACTIVE,
        timezone="UTC",
    )
    second_membership = create_membership(
        establishment=second_establishment,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    source = create_pattern(owner, label="Source")
    target = create_pattern(owner, label="Target")
    signal = create_signal(second_membership, title="Second site issue")
    assign_signal(signal, source)

    response = authenticated_post(
        api_client,
        owner.user,
        move_url(source.id),
        {"target_pattern_id": str(target.id), "signal_ids": [str(signal.id)]},
    )

    assert response.status_code == 200
    assert response.json()["moved_signal_count"] == 1
    assignment = SignalPatternAssignment.objects.get(signal=signal)
    assert assignment.pattern_id == target.id
    assert assignment.assignment_source == (
        SignalPatternAssignment.AssignmentSource.OWNER_CORRECTION
    )


def test_cross_organization_pattern_is_not_revealed(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    other_owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    other_pattern = create_pattern(other_owner)

    response = authenticated_post(
        api_client,
        owner.user,
        rename_url(other_pattern.id),
        {"label": "Hidden"},
    )

    assert response.status_code == 404
    assert response.json()["code"] == "analytics_pattern_not_found"


@pytest.mark.parametrize("endpoint", OWNER_GOVERNANCE_SIGNAL_ENDPOINTS)
@pytest.mark.parametrize(
    "signal_kind",
    [
        "missing",
        "with_assignment",
        "without_assignment",
    ],
)
def test_owner_governance_signal_ids_outside_tenant_are_non_revealing(
    api_client,
    endpoint,
    signal_kind,
):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    source = create_pattern(owner, label=f"Source {endpoint} {signal_kind}")
    target = create_pattern(owner, label=f"Target {endpoint} {signal_kind}")
    invalid_signal_id = cross_tenant_signal_id(signal_kind)

    response = authenticated_post(
        api_client,
        owner.user,
        signal_endpoint_url(endpoint, source.id),
        signal_endpoint_payload(
            endpoint,
            target=target,
            signal_ids=[str(invalid_signal_id)],
        ),
    )

    assert response.status_code == 404
    assert response.json()["code"] == "analytics_signal_not_found"


@pytest.mark.parametrize("endpoint", OWNER_GOVERNANCE_SIGNAL_ENDPOINTS)
def test_owner_governance_mixed_tenant_batch_has_no_partial_mutation(
    api_client,
    endpoint,
):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    source = create_pattern(owner, label=f"Source {endpoint}")
    target = create_pattern(owner, label=f"Target {endpoint}")
    valid_signal = create_signal(owner, title=f"Valid {endpoint}")
    assignment = assign_signal(valid_signal, source)
    invalid_signal_id = cross_tenant_signal_id("with_assignment")
    move_or_split_event_count = PatternLifecycleEvent.objects.filter(
        event_type__in=[
            PatternLifecycleEvent.EventType.SIGNALS_MOVED,
            PatternLifecycleEvent.EventType.SPLIT,
        ],
    ).count()

    response = authenticated_post(
        api_client,
        owner.user,
        signal_endpoint_url(endpoint, source.id),
        signal_endpoint_payload(
            endpoint,
            target=target,
            signal_ids=[str(valid_signal.id), str(invalid_signal_id)],
        ),
    )

    assert response.status_code == 404
    assert response.json()["code"] == "analytics_signal_not_found"
    assignment.refresh_from_db()
    assert assignment.pattern_id == source.id
    assert assignment.assignment_source != (
        SignalPatternAssignment.AssignmentSource.OWNER_CORRECTION
    )
    assert (
        PatternLifecycleEvent.objects.filter(
            event_type__in=[
                PatternLifecycleEvent.EventType.SIGNALS_MOVED,
                PatternLifecycleEvent.EventType.SPLIT,
            ],
        ).count()
        == move_or_split_event_count
    )
    assert not OperationalPattern.objects.filter(
        organization=owner.establishment.organization,
        label="Blocked split",
    ).exists()


def test_rename_validation_and_conflict_mapping(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    pattern = create_pattern(owner, label="Leak")
    create_pattern(owner, label="Water leak")

    blank_response = authenticated_post(
        api_client,
        owner.user,
        rename_url(pattern.id),
        {"label": "   "},
    )
    conflict_response = authenticated_post(
        api_client,
        owner.user,
        rename_url(pattern.id),
        {"label": " water leak "},
    )

    assert blank_response.status_code == 400
    assert blank_response.json()["code"] == "analytics_pattern_label_blank"
    assert conflict_response.status_code == 409
    assert conflict_response.json()["code"] == "analytics_pattern_label_conflict"


def test_merge_success_and_terminal_idempotence(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    source = create_pattern(owner, label="Source")
    target = create_pattern(owner, label="Target")
    signal = create_signal(owner)
    assign_signal(signal, source)

    first = authenticated_post(
        api_client,
        owner.user,
        merge_url(source.id),
        {"target_pattern_id": str(target.id)},
    )
    second = authenticated_post(
        api_client,
        owner.user,
        merge_url(source.id),
        {"target_pattern_id": str(target.id)},
    )

    assert first.status_code == 200
    assert first.json()["source_pattern"]["status"] == OperationalPattern.Status.MERGED
    assert first.json()["moved_signal_count"] == 1
    assert second.status_code == 200
    assert second.json()["moved_signal_count"] == 0
    source.refresh_from_db()
    assert source.merged_into_id == target.id


def test_merge_to_different_terminal_target_is_conflict(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    source = create_pattern(owner, label="Source")
    target = create_pattern(owner, label="Target")
    other = create_pattern(owner, label="Other")
    authenticated_post(
        api_client,
        owner.user,
        merge_url(source.id),
        {"target_pattern_id": str(target.id)},
    )

    response = authenticated_post(
        api_client,
        owner.user,
        merge_url(source.id),
        {"target_pattern_id": str(other.id)},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "analytics_pattern_already_merged"


def test_move_assignment_errors_are_conflicts(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    source = create_pattern(owner, label="Source")
    target = create_pattern(owner, label="Target")
    other = create_pattern(owner, label="Other")
    no_assignment = create_signal(owner, title="No assignment")
    wrong_pattern = create_signal(owner, title="Wrong pattern")
    assign_signal(wrong_pattern, other)

    missing_response = authenticated_post(
        api_client,
        owner.user,
        move_url(source.id),
        {"target_pattern_id": str(target.id), "signal_ids": [str(no_assignment.id)]},
    )
    wrong_response = authenticated_post(
        api_client,
        owner.user,
        move_url(source.id),
        {"target_pattern_id": str(target.id), "signal_ids": [str(wrong_pattern.id)]},
    )

    assert missing_response.status_code == 409
    assert missing_response.json()["code"] == "analytics_assignment_missing"
    assert wrong_response.status_code == 409
    assert wrong_response.json()["code"] == "analytics_assignment_wrong_pattern"


def test_split_to_existing_and_new_return_target_metadata(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    source = create_pattern(owner, label="Source")
    existing_target = create_pattern(owner, label="Existing")
    first = create_signal(owner, title="First")
    second = create_signal(owner, title="Second")
    assign_signal(first, source)
    assign_signal(second, source)

    existing_response = authenticated_post(
        api_client,
        owner.user,
        split_existing_url(source.id),
        {"target_pattern_id": str(existing_target.id), "signal_ids": [str(first.id)]},
    )
    new_response = authenticated_post(
        api_client,
        owner.user,
        split_new_url(source.id),
        {"label": "New split", "signal_ids": [str(second.id)]},
    )

    assert existing_response.status_code == 200
    assert existing_response.json()["target_created"] is False
    assert existing_response.json()["moved_signal_count"] == 1
    assert new_response.status_code == 200
    assert new_response.json()["target_created"] is True
    assert new_response.json()["target_pattern"]["label"] == "New split"
    assert PatternLifecycleEvent.objects.filter(
        pattern=source,
        event_type=PatternLifecycleEvent.EventType.SPLIT,
    ).count() == 2


def test_owner_governance_invalidates_processing_attempt(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    source = create_pattern(owner, label="Source")
    target = create_pattern(owner, label="Target")
    signal = create_signal(owner)
    assign_signal(signal, source)
    processing = mark_assignment_processing(
        signal=signal,
        pending_signature="pending",
        pending_classifier_version="classifier-v2",
    )

    response = authenticated_post(
        api_client,
        owner.user,
        move_url(source.id),
        {"target_pattern_id": str(target.id), "signal_ids": [str(signal.id)]},
    )

    assert response.status_code == 200
    assignment = SignalPatternAssignment.objects.get(signal=signal)
    assert assignment.attempt_count == processing.attempt_count + 1
    assert assignment.pattern_id == target.id
    assert assignment.assigned_signature == build_signal_pattern_signature(signal)
    assert assignment.assigned_classifier_version == OWNER_CORRECTION_CLASSIFIER_VERSION


def test_owner_governance_does_not_close_issue_reports(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    director = create_membership(
        establishment=owner.establishment,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    source = create_pattern(owner, label="Source")
    target = create_pattern(owner, label="Target")
    signal = create_signal(director)
    assign_signal(signal, source)
    report = report_pattern_assignment_issue(
        director.user,
        signal_id=signal.id,
        pattern_id=source.id,
    )

    response = authenticated_post(
        api_client,
        owner.user,
        move_url(source.id),
        {"target_pattern_id": str(target.id), "signal_ids": [str(signal.id)]},
    )

    assert response.status_code == 200
    report.refresh_from_db()
    assert report.status == PatternIssueReport.Status.OPEN


def test_openapi_contains_owner_governance_endpoints():
    schema_text = (Path(__file__).resolve().parents[3] / "schema.yml").read_text()

    assert "/api/v1/analytics/patterns/{pattern_id}/rename/" in schema_text
    assert "/api/v1/analytics/patterns/{pattern_id}/merge/" in schema_text
    assert "/api/v1/analytics/patterns/{pattern_id}/move-signals/" in schema_text
    assert "/api/v1/analytics/patterns/{pattern_id}/split-to-existing/" in schema_text
    assert "/api/v1/analytics/patterns/{pattern_id}/split-to-new/" in schema_text
    assert "AnalyticsOwnerGovernanceResponse:" in schema_text
