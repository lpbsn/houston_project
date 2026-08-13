from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from houston.analytics.models import (
    PATTERN_ISSUE_COMMENT_MAX_LENGTH,
    OperationalPattern,
    PatternIssueReport,
    PatternLifecycleEvent,
    SignalPatternAssignment,
)
from houston.analytics.services import (
    PATTERN_ISSUE_REPORT_TYPE_WRONG_PATTERN,
    create_operational_pattern,
)
from houston.establishments.models import Establishment, EstablishmentMembership
from houston.signals.models import Signal
from houston.testing.auth import auth_headers, build_api_membership, login
from houston.testing.factories import create_membership, create_user

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


def issue_report_url(pattern_id, signal_id) -> str:
    return (
        f"/api/v1/analytics/patterns/{pattern_id}/signals/{signal_id}/"
        "issue-report/"
    )


def authenticated_post(api_client, user, url: str, payload: dict):
    token = login(api_client, user=user)
    return api_client.post(url, payload, format="json", **auth_headers(token))


def create_pattern(membership, *, label="Pattern"):
    return create_operational_pattern(
        organization=membership.establishment.organization,
        label=label,
        created_by_membership=membership,
    )


def create_signal(
    membership,
    *,
    title="Signal",
    status=Signal.Status.OPEN,
    merged_into=None,
):
    return Signal.objects.create(
        establishment=membership.establishment,
        status=status,
        routing_status=Signal.RoutingStatus.RESOLVED,
        title=title,
        structured_summary="Structured signal summary.",
        issue_focus=title.lower().replace(" ", "-"),
        merged_into=merged_into,
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


def test_pattern_issue_report_requires_authentication(api_client):
    response = api_client.post(
        issue_report_url(uuid.uuid4(), uuid.uuid4()),
        {"reason": "wrong_pattern", "comment": ""},
        format="json",
    )

    assert response.status_code == 401
    assert response.json()["code"] == "not_authenticated"


def test_director_creates_pattern_issue_report_with_minimal_payload(api_client):
    director = build_api_membership(role=EstablishmentMembership.Role.DIRECTOR)
    pattern = create_pattern(director, label="Noise")
    signal = create_signal(director, title="Terrace noise")
    assignment = assign_signal(signal, pattern)
    lifecycle_count = PatternLifecycleEvent.objects.count()

    response = authenticated_post(
        api_client,
        director.user,
        issue_report_url(pattern.id, signal.id),
        {"reason": "wrong_pattern", "comment": "  mauvais regroupement  "},
    )

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {
        "report_id",
        "pattern_id",
        "signal_id",
        "status",
        "report_type",
        "comment",
        "created_at",
    }
    assert body["pattern_id"] == str(pattern.id)
    assert body["signal_id"] == str(signal.id)
    assert body["status"] == PatternIssueReport.Status.OPEN
    assert body["report_type"] == PATTERN_ISSUE_REPORT_TYPE_WRONG_PATTERN
    assert body["comment"] == "mauvais regroupement"
    report = PatternIssueReport.objects.get(id=body["report_id"])
    assert report.organization_id == pattern.organization_id
    assert report.reported_by_membership_id == director.id
    assignment.refresh_from_db()
    pattern.refresh_from_db()
    assert assignment.pattern_id == pattern.id
    assert assignment.assignment_source == SignalPatternAssignment.AssignmentSource.CLASSIFIER
    assert pattern.status == OperationalPattern.Status.ACTIVE
    assert PatternLifecycleEvent.objects.count() == lifecycle_count
    assert "raw_text" not in str(body)
    assert "assignment_source" not in str(body)


def test_manager_without_selected_establishment_can_report_authorized_signal(api_client):
    user = create_user(username="manager-no-selected-establishment")
    staff_site = Establishment.objects.create(
        name="Staff site",
        organization=build_api_membership().establishment.organization,
        status=Establishment.Status.ACTIVE,
        timezone="UTC",
    )
    create_membership(
        establishment=staff_site,
        user=user,
        role=EstablishmentMembership.Role.STAFF,
    )
    director_seed = build_api_membership(role=EstablishmentMembership.Role.DIRECTOR)
    manager_site = Establishment.objects.create(
        name="Manager site",
        organization=director_seed.establishment.organization,
        status=Establishment.Status.ACTIVE,
        timezone="UTC",
    )
    manager = create_membership(
        establishment=manager_site,
        user=user,
        role=EstablishmentMembership.Role.MANAGER,
    )
    pattern = create_pattern(director_seed)
    signal = create_signal(manager, title="Unassigned manager signal")
    signal.routing_status = Signal.RoutingStatus.UNASSIGNED
    signal.save(update_fields=["routing_status", "updated_at"])
    assign_signal(signal, pattern)

    response = authenticated_post(
        api_client,
        user,
        issue_report_url(pattern.id, signal.id),
        {"comment": ""},
    )

    assert response.status_code == 201
    assert PatternIssueReport.objects.get().reported_by_membership_id == manager.id


@pytest.mark.parametrize(
    "role",
    [EstablishmentMembership.Role.STAFF, EstablishmentMembership.Role.OWNER],
)
def test_staff_and_owner_only_cannot_report(api_client, role):
    membership = build_api_membership(role=role)

    response = authenticated_post(
        api_client,
        membership.user,
        issue_report_url(uuid.uuid4(), uuid.uuid4()),
        {"reason": "wrong_pattern"},
    )

    assert response.status_code == 403


def test_cross_tenant_or_missing_target_is_not_revealed(api_client):
    director = build_api_membership(role=EstablishmentMembership.Role.DIRECTOR)
    other_director = build_api_membership(role=EstablishmentMembership.Role.DIRECTOR)
    other_pattern = create_pattern(other_director)
    other_signal = create_signal(other_director)
    assign_signal(other_signal, other_pattern)

    response = authenticated_post(
        api_client,
        director.user,
        issue_report_url(other_pattern.id, other_signal.id),
        {"reason": "wrong_pattern"},
    )
    missing_response = authenticated_post(
        api_client,
        director.user,
        issue_report_url(uuid.uuid4(), uuid.uuid4()),
        {"reason": "wrong_pattern"},
    )

    assert response.status_code == 404
    assert response.json()["code"] == "analytics_pattern_issue_target_not_found"
    assert missing_response.status_code == 404
    assert missing_response.json()["code"] == "analytics_pattern_issue_target_not_found"


def test_assignment_missing_and_mismatch_are_conflicts(api_client):
    director = build_api_membership(role=EstablishmentMembership.Role.DIRECTOR)
    old_pattern = create_pattern(director, label="Old")
    new_pattern = create_pattern(director, label="New")
    missing_assignment_signal = create_signal(director, title="Missing")
    mismatched_signal = create_signal(director, title="Mismatch")
    assign_signal(mismatched_signal, new_pattern)

    missing_response = authenticated_post(
        api_client,
        director.user,
        issue_report_url(old_pattern.id, missing_assignment_signal.id),
        {"reason": "wrong_pattern"},
    )
    mismatch_response = authenticated_post(
        api_client,
        director.user,
        issue_report_url(old_pattern.id, mismatched_signal.id),
        {"reason": "wrong_pattern"},
    )

    assert missing_response.status_code == 409
    assert missing_response.json()["code"] == "analytics_pattern_assignment_missing"
    assert mismatch_response.status_code == 409
    assert mismatch_response.json()["code"] == "analytics_pattern_assignment_mismatch"
    assert PatternIssueReport.objects.count() == 0


@pytest.mark.parametrize(
    ("payload", "expected_code"),
    [
        ({"reason": "duplicate"}, "analytics_pattern_issue_reason_invalid"),
        (
            {"comment": "x" * (PATTERN_ISSUE_COMMENT_MAX_LENGTH + 1)},
            "analytics_pattern_issue_comment_too_long",
        ),
    ],
)
def test_reason_and_comment_validation_errors_are_controlled(
    api_client,
    payload,
    expected_code,
):
    director = build_api_membership(role=EstablishmentMembership.Role.DIRECTOR)
    pattern = create_pattern(director)
    signal = create_signal(director)
    assign_signal(signal, pattern)

    response = authenticated_post(
        api_client,
        director.user,
        issue_report_url(pattern.id, signal.id),
        payload,
    )

    assert response.status_code == 400
    assert response.json()["code"] == expected_code
    assert PatternIssueReport.objects.count() == 0


def test_issue_report_schema_documents_comment_limit():
    schema_text = (Path(__file__).resolve().parents[3] / "schema.yml").read_text()
    request_schema = schema_text.split("AnalyticsPatternIssueReportRequest:", 1)[1].split(
        "AnalyticsPatternIssueReportResponse:",
        1,
    )[0]

    assert "comment:" in request_schema
    assert "maxLength: 500" in request_schema


def test_duplicate_submissions_create_distinct_open_reports(api_client):
    director = build_api_membership(role=EstablishmentMembership.Role.DIRECTOR)
    pattern = create_pattern(director)
    signal = create_signal(director)
    assign_signal(signal, pattern)

    first = authenticated_post(
        api_client,
        director.user,
        issue_report_url(pattern.id, signal.id),
        {"reason": "wrong_pattern"},
    )
    second = authenticated_post(
        api_client,
        director.user,
        issue_report_url(pattern.id, signal.id),
        {"reason": "wrong_pattern"},
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["report_id"] != second.json()["report_id"]
    assert PatternIssueReport.objects.filter(
        pattern=pattern,
        signal=signal,
        status=PatternIssueReport.Status.OPEN,
    ).count() == 2
