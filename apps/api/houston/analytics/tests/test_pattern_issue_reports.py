from __future__ import annotations

import uuid

import pytest
from django.utils import timezone

from houston.accounts.models import User
from houston.analytics.exceptions import AnalyticsValidationError
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
    move_signals_between_patterns,
    report_pattern_assignment_issue,
)
from houston.establishments.models import Establishment, EstablishmentMembership
from houston.organizations.models import Organization
from houston.signals.models import Signal
from houston.testing.factories import build_membership, create_membership
from houston.testing.taxonomy import (
    create_business_unit,
    create_membership_with_business_unit_scope,
)

pytestmark = pytest.mark.django_db


def create_signal(
    membership,
    *,
    title="Signal",
    status=Signal.Status.OPEN,
    routing_status=Signal.RoutingStatus.RESOLVED,
    merged_into=None,
    affected_business_unit=None,
    responsible_business_unit=None,
):
    return Signal.objects.create(
        establishment=membership.establishment,
        affected_business_unit=affected_business_unit,
        responsible_business_unit=responsible_business_unit,
        routing_status=routing_status,
        status=status,
        title=title,
        structured_summary="Structured signal summary.",
        issue_focus=title.lower().replace(" ", "-"),
        merged_into=merged_into,
        last_activity_at=timezone.now(),
    )


def create_pattern(membership, *, label="Pattern"):
    return create_operational_pattern(
        organization=membership.establishment.organization,
        label=label,
        created_by_membership=membership,
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


def report_for(membership, *, signal=None, pattern=None, comment=""):
    if signal is None:
        signal = create_signal(membership)
    if pattern is None:
        pattern = create_pattern(membership)
    assignment = assign_signal(signal, pattern)
    report = report_pattern_assignment_issue(
        membership.user,
        signal_id=signal.id,
        pattern_id=pattern.id,
        comment=comment,
    )
    return report, signal, pattern, assignment


def assert_report_error(code, *, user, signal_id, pattern_id, **kwargs):
    with pytest.raises(AnalyticsValidationError) as exc_info:
        report_pattern_assignment_issue(
            user,
            signal_id=signal_id,
            pattern_id=pattern_id,
            **kwargs,
        )
    assert exc_info.value.code == code


def test_director_can_report_visible_signal_assignment():
    director = build_membership(role=EstablishmentMembership.Role.DIRECTOR)

    report, signal, pattern, _assignment = report_for(
        director,
        comment="  wrong grouping  ",
    )

    assert report.signal_id == signal.id
    assert report.pattern_id == pattern.id
    assert report.organization_id == pattern.organization_id
    assert report.reported_by_membership_id == director.id
    assert report.report_type == PATTERN_ISSUE_REPORT_TYPE_WRONG_PATTERN
    assert report.comment == "wrong grouping"
    assert report.status == PatternIssueReport.Status.OPEN


def test_manager_can_report_business_unit_scoped_and_unassigned_signals():
    manager = build_membership(role=EstablishmentMembership.Role.MANAGER)
    pattern = create_pattern(manager)
    in_scope_bu = create_business_unit(establishment=manager.establishment, key="bar")
    out_scope_bu = create_business_unit(
        establishment=manager.establishment,
        key="kitchen",
    )
    create_membership_with_business_unit_scope(
        membership=manager,
        business_unit=in_scope_bu,
    )
    scoped_signal = create_signal(
        manager,
        affected_business_unit=in_scope_bu,
        responsible_business_unit=in_scope_bu,
    )
    unassigned_signal = create_signal(
        manager,
        routing_status=Signal.RoutingStatus.UNASSIGNED,
        affected_business_unit=out_scope_bu,
        responsible_business_unit=out_scope_bu,
    )
    assign_signal(scoped_signal, pattern)
    assign_signal(unassigned_signal, pattern)

    scoped_report = report_pattern_assignment_issue(
        manager.user,
        signal_id=scoped_signal.id,
        pattern_id=pattern.id,
    )
    unassigned_report = report_pattern_assignment_issue(
        manager.user,
        signal_id=unassigned_signal.id,
        pattern_id=pattern.id,
    )

    assert scoped_report.reported_by_membership_id == manager.id
    assert unassigned_report.reported_by_membership_id == manager.id


@pytest.mark.parametrize(
    "role",
    [EstablishmentMembership.Role.STAFF, EstablishmentMembership.Role.OWNER],
)
def test_staff_only_and_owner_only_are_refused_before_target_lookup(role):
    membership = build_membership(role=role)

    assert_report_error(
        "analytics_pattern_issue_permission_denied",
        user=membership.user,
        signal_id="not-a-signal-id",
        pattern_id="not-a-pattern-id",
    )


def test_owner_membership_never_authorizes_report_for_multi_role_user():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    manager_establishment = Establishment.objects.create(
        name="Manager site",
        organization=owner.establishment.organization,
        status=Establishment.Status.ACTIVE,
        timezone="UTC",
    )
    manager = create_membership(
        establishment=manager_establishment,
        user=owner.user,
        role=EstablishmentMembership.Role.MANAGER,
    )
    manager_bu = create_business_unit(
        establishment=manager.establishment,
        key="bar",
    )
    create_membership_with_business_unit_scope(
        membership=manager,
        business_unit=manager_bu,
    )
    pattern = create_pattern(owner)
    owner_only_signal = create_signal(owner)
    manager_signal = create_signal(
        manager,
        affected_business_unit=manager_bu,
        responsible_business_unit=manager_bu,
    )
    assign_signal(owner_only_signal, pattern)
    assign_signal(manager_signal, pattern)

    assert_report_error(
        "analytics_pattern_issue_target_not_found",
        user=owner.user,
        signal_id=owner_only_signal.id,
        pattern_id=pattern.id,
    )
    report = report_pattern_assignment_issue(
        owner.user,
        signal_id=manager_signal.id,
        pattern_id=pattern.id,
    )

    assert report.reported_by_membership_id == manager.id
    assert report.signal_id == manager_signal.id


def test_manager_cannot_report_signal_outside_business_unit_scope():
    manager = build_membership(role=EstablishmentMembership.Role.MANAGER)
    pattern = create_pattern(manager)
    out_scope_bu = create_business_unit(
        establishment=manager.establishment,
        key="kitchen",
    )
    signal = create_signal(
        manager,
        affected_business_unit=out_scope_bu,
        responsible_business_unit=out_scope_bu,
    )
    assign_signal(signal, pattern)

    assert_report_error(
        "analytics_pattern_issue_target_not_found",
        user=manager.user,
        signal_id=signal.id,
        pattern_id=pattern.id,
    )


def test_cross_tenant_target_is_not_revealed():
    director = build_membership(role=EstablishmentMembership.Role.DIRECTOR)
    other_director = build_membership(role=EstablishmentMembership.Role.DIRECTOR)
    other_pattern = create_pattern(other_director)
    other_signal = create_signal(other_director)
    assign_signal(other_signal, other_pattern)

    assert_report_error(
        "analytics_pattern_issue_target_not_found",
        user=director.user,
        signal_id=other_signal.id,
        pattern_id=other_pattern.id,
    )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"membership_status": EstablishmentMembership.Status.DEACTIVATED},
        {"user_status": User.Status.SUSPENDED},
        {"establishment_status": Establishment.Status.DEACTIVATED},
        {"organization_status": Organization.Status.SUSPENDED},
    ],
)
def test_inactive_user_membership_establishment_or_organization_is_refused(kwargs):
    membership = build_membership(
        role=EstablishmentMembership.Role.DIRECTOR,
        **kwargs,
    )

    assert_report_error(
        "analytics_pattern_issue_permission_denied",
        user=membership.user,
        signal_id="not-a-signal-id",
        pattern_id="not-a-pattern-id",
    )


def test_canceled_and_merged_signals_are_not_valid_targets():
    director = build_membership(role=EstablishmentMembership.Role.DIRECTOR)
    pattern = create_pattern(director)
    survivor = create_signal(director, title="Survivor")
    canceled = create_signal(director, status=Signal.Status.CANCELED)
    merged = create_signal(director, merged_into=survivor)
    assign_signal(canceled, pattern)
    assign_signal(merged, pattern)

    for signal in (canceled, merged):
        assert_report_error(
            "analytics_pattern_issue_target_not_found",
            user=director.user,
            signal_id=signal.id,
            pattern_id=pattern.id,
        )


def test_signal_without_assignment_or_without_pattern_is_rejected():
    director = build_membership(role=EstablishmentMembership.Role.DIRECTOR)
    pattern = create_pattern(director)
    missing_assignment_signal = create_signal(director, title="Missing assignment")
    no_pattern_signal = create_signal(director, title="No pattern")
    SignalPatternAssignment.objects.create(signal=no_pattern_signal)

    assert_report_error(
        "analytics_pattern_assignment_missing",
        user=director.user,
        signal_id=missing_assignment_signal.id,
        pattern_id=pattern.id,
    )
    assert_report_error(
        "analytics_pattern_assignment_missing",
        user=director.user,
        signal_id=no_pattern_signal.id,
        pattern_id=pattern.id,
    )


def test_mismatched_pattern_is_rejected_after_assignment_changes():
    director = build_membership(role=EstablishmentMembership.Role.DIRECTOR)
    old_pattern = create_pattern(director, label="Old")
    new_pattern = create_pattern(director, label="New")
    signal = create_signal(director)
    assignment = assign_signal(signal, old_pattern)
    assignment.pattern = new_pattern
    assignment.save(update_fields=["pattern", "updated_at"])

    assert_report_error(
        "analytics_pattern_assignment_mismatch",
        user=director.user,
        signal_id=signal.id,
        pattern_id=old_pattern.id,
    )
    report = report_pattern_assignment_issue(
        director.user,
        signal_id=signal.id,
        pattern_id=new_pattern.id,
    )

    assert report.pattern_id == new_pattern.id


def test_report_does_not_modify_assignment_pattern_classification_or_lifecycle_events():
    director = build_membership(role=EstablishmentMembership.Role.DIRECTOR)
    pattern = create_pattern(director)
    signal = create_signal(director)
    assignment = assign_signal(signal, pattern)
    before = {
        "pattern_id": assignment.pattern_id,
        "classification_status": assignment.classification_status,
        "assignment_source": assignment.assignment_source,
        "owner_correction_signature": assignment.owner_correction_signature,
        "assigned_signature": assignment.assigned_signature,
        "assigned_classifier_version": assignment.assigned_classifier_version,
        "attempt_count": assignment.attempt_count,
    }
    event_count = PatternLifecycleEvent.objects.count()

    report_pattern_assignment_issue(
        director.user,
        signal_id=signal.id,
        pattern_id=pattern.id,
    )

    assignment.refresh_from_db()
    after = {
        "pattern_id": assignment.pattern_id,
        "classification_status": assignment.classification_status,
        "assignment_source": assignment.assignment_source,
        "owner_correction_signature": assignment.owner_correction_signature,
        "assigned_signature": assignment.assigned_signature,
        "assigned_classifier_version": assignment.assigned_classifier_version,
        "attempt_count": assignment.attempt_count,
    }
    pattern.refresh_from_db()
    assert after == before
    assert pattern.status == OperationalPattern.Status.ACTIVE
    assert PatternLifecycleEvent.objects.count() == event_count


def test_report_remains_traceable_after_owner_move():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
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

    move_signals_between_patterns(
        actor_membership=owner,
        source_pattern=source,
        target_pattern=target,
        signal_ids=[signal.id],
    )
    report.refresh_from_db()

    assert report.signal_id == signal.id
    assert report.pattern_id == source.id
    assert report.organization_id == source.organization_id


def test_duplicate_reports_are_allowed():
    director = build_membership(role=EstablishmentMembership.Role.DIRECTOR)
    pattern = create_pattern(director)
    signal = create_signal(director)
    assign_signal(signal, pattern)

    first = report_pattern_assignment_issue(
        director.user,
        signal_id=signal.id,
        pattern_id=pattern.id,
    )
    second = report_pattern_assignment_issue(
        director.user,
        signal_id=signal.id,
        pattern_id=pattern.id,
    )

    assert first.id != second.id
    assert PatternIssueReport.objects.filter(
        signal=signal,
        pattern=pattern,
        status=PatternIssueReport.Status.OPEN,
    ).count() == 2


def test_reason_and_comment_validation():
    director = build_membership(role=EstablishmentMembership.Role.DIRECTOR)
    pattern = create_pattern(director)
    signal = create_signal(director)
    assign_signal(signal, pattern)

    assert_report_error(
        "analytics_pattern_issue_reason_invalid",
        user=director.user,
        signal_id=signal.id,
        pattern_id=pattern.id,
        reason="duplicate",
    )
    assert_report_error(
        "analytics_pattern_issue_comment_too_long",
        user=director.user,
        signal_id=signal.id,
        pattern_id=pattern.id,
        comment="x" * (PATTERN_ISSUE_COMMENT_MAX_LENGTH + 1),
    )
    empty_comment = report_pattern_assignment_issue(
        director.user,
        signal_id=signal.id,
        pattern_id=pattern.id,
        comment=None,
    )

    assert empty_comment.comment == ""


def test_invalid_signal_or_pattern_id_is_not_found_for_authorized_user():
    director = build_membership(role=EstablishmentMembership.Role.DIRECTOR)

    assert_report_error(
        "analytics_pattern_issue_target_not_found",
        user=director.user,
        signal_id="not-a-signal-id",
        pattern_id=uuid.uuid4(),
    )
    assert_report_error(
        "analytics_pattern_issue_target_not_found",
        user=director.user,
        signal_id=uuid.uuid4(),
        pattern_id="not-a-pattern-id",
    )
