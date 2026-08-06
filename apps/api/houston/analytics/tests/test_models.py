from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from houston.analytics.exceptions import AnalyticsValidationError
from houston.analytics.labels import normalize_pattern_label
from houston.analytics.models import (
    OperationalPattern,
    PatternIssueReport,
    PatternLifecycleEvent,
)
from houston.analytics.services import create_operational_pattern
from houston.signals.models import Signal
from houston.testing.factories import build_membership

pytestmark = pytest.mark.django_db


def create_signal_for_membership(membership):
    return Signal.objects.create(
        establishment=membership.establishment,
        routing_status=Signal.RoutingStatus.UNASSIGNED,
        title="Issue",
        structured_summary="Structured issue summary",
        last_activity_at=timezone.now(),
    )


def test_normalize_pattern_label_is_deterministic():
    assert normalize_pattern_label("  Guest   Bathroom  ") == "guest bathroom"
    assert normalize_pattern_label("CAFÉ") == "café"
    assert normalize_pattern_label("") == ""
    assert normalize_pattern_label("   ") == ""


def test_create_operational_pattern_calculates_normalized_label_and_event():
    membership = build_membership()

    pattern = create_operational_pattern(
        organization=membership.establishment.organization,
        label="  Guest   Bathroom  ",
        created_by_membership=membership,
        metadata_safe={"source": "manual"},
    )

    assert pattern.normalized_label == "guest bathroom"
    event = pattern.lifecycle_events.get()
    assert event.event_type == PatternLifecycleEvent.EventType.CREATED
    assert event.organization == pattern.organization
    assert event.actor_membership == membership
    assert event.metadata_safe == {"source": "manual"}


def test_create_operational_pattern_rejects_blank_normalized_label():
    membership = build_membership()

    with pytest.raises(AnalyticsValidationError):
        create_operational_pattern(
            organization=membership.establishment.organization,
            label="   ",
            created_by_membership=membership,
        )


def test_save_update_fields_refreshes_normalized_label():
    membership = build_membership()
    pattern = OperationalPattern.objects.create(
        organization=membership.establishment.organization,
        label="Guest Bathroom",
    )

    pattern.label = "Lobby Spill"
    pattern.save(update_fields=["label"])

    pattern.refresh_from_db()
    assert pattern.normalized_label == "lobby spill"


def test_active_pattern_normalized_label_is_unique_within_organization():
    membership = build_membership()
    organization = membership.establishment.organization
    OperationalPattern.objects.create(organization=organization, label="Guest Bathroom")

    with pytest.raises(IntegrityError), transaction.atomic():
        OperationalPattern.objects.create(
            organization=organization,
            label="  guest   bathroom ",
        )


def test_active_pattern_normalized_label_can_repeat_across_organizations():
    first = build_membership()
    second = build_membership()

    OperationalPattern.objects.create(
        organization=first.establishment.organization,
        label="Guest Bathroom",
    )
    other = OperationalPattern.objects.create(
        organization=second.establishment.organization,
        label=" guest bathroom ",
    )

    assert other.normalized_label == "guest bathroom"


def test_inactive_patterns_can_keep_historical_normalized_label():
    membership = build_membership()
    organization = membership.establishment.organization
    target = OperationalPattern.objects.create(
        organization=organization,
        label="Canonical pattern",
    )
    OperationalPattern.objects.create(
        organization=organization,
        label="Guest Bathroom",
        status=OperationalPattern.Status.RETIRED,
    )
    OperationalPattern.objects.create(
        organization=organization,
        label=" guest bathroom ",
        status=OperationalPattern.Status.MERGED,
        merged_into=target,
    )

    active = OperationalPattern.objects.create(
        organization=organization,
        label="GUEST BATHROOM",
    )

    assert active.normalized_label == "guest bathroom"


def test_pattern_rejects_invalid_merged_target():
    membership = build_membership()
    organization = membership.establishment.organization
    pattern = OperationalPattern.objects.create(
        organization=organization,
        label="Guest Bathroom",
    )

    pattern.status = OperationalPattern.Status.MERGED
    pattern.merged_into = pattern

    with pytest.raises(ValidationError) as exc_info:
        pattern.full_clean()
    assert "merged_into" in exc_info.value.message_dict


def test_pattern_rejects_cross_organization_merged_target():
    source_membership = build_membership()
    target_membership = build_membership()
    source = OperationalPattern.objects.create(
        organization=source_membership.establishment.organization,
        label="Guest Bathroom",
    )
    target = OperationalPattern.objects.create(
        organization=target_membership.establishment.organization,
        label="Canonical pattern",
    )
    source.status = OperationalPattern.Status.MERGED
    source.merged_into = target

    with pytest.raises(ValidationError) as exc_info:
        source.full_clean()
    assert "merged_into" in exc_info.value.message_dict


def test_pattern_rejects_non_active_merged_target():
    membership = build_membership()
    organization = membership.establishment.organization
    source = OperationalPattern.objects.create(
        organization=organization,
        label="Guest Bathroom",
    )
    target = OperationalPattern.objects.create(
        organization=organization,
        label="Canonical pattern",
        status=OperationalPattern.Status.RETIRED,
    )
    source.status = OperationalPattern.Status.MERGED
    source.merged_into = target

    with pytest.raises(ValidationError) as exc_info:
        source.full_clean()
    assert "merged_into" in exc_info.value.message_dict


def test_pattern_rejects_creator_membership_from_other_organization():
    pattern_membership = build_membership()
    other_membership = build_membership()
    pattern = OperationalPattern(
        organization=pattern_membership.establishment.organization,
        label="Guest Bathroom",
        created_by_membership=other_membership,
    )

    with pytest.raises(ValidationError) as exc_info:
        pattern.full_clean()
    assert "created_by_membership" in exc_info.value.message_dict


def test_lifecycle_event_rejects_actor_from_other_organization():
    membership = build_membership()
    other_membership = build_membership()
    pattern = OperationalPattern.objects.create(
        organization=membership.establishment.organization,
        label="Guest Bathroom",
    )
    event = PatternLifecycleEvent(
        pattern=pattern,
        organization=pattern.organization,
        event_type=PatternLifecycleEvent.EventType.CREATED,
        actor_membership=other_membership,
        occurred_at=timezone.now(),
    )

    with pytest.raises(ValidationError) as exc_info:
        event.full_clean()
    assert "actor_membership" in exc_info.value.message_dict


def test_issue_report_rejects_reporter_and_signal_from_other_organization():
    membership = build_membership()
    other_membership = build_membership()
    pattern = OperationalPattern.objects.create(
        organization=membership.establishment.organization,
        label="Guest Bathroom",
    )
    other_signal = create_signal_for_membership(other_membership)
    report = PatternIssueReport(
        pattern=pattern,
        organization=pattern.organization,
        signal=other_signal,
        reported_by_membership=other_membership,
        report_type="duplicate",
    )

    with pytest.raises(ValidationError) as exc_info:
        report.full_clean()
    assert "reported_by_membership" in exc_info.value.message_dict
    assert "signal" in exc_info.value.message_dict
