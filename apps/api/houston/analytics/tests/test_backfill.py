from __future__ import annotations

import json
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from houston.ai.models import AIUsageLog
from houston.analytics.backfill import (
    backfill_analytics_patterns,
    backfill_report_to_dict,
)
from houston.analytics.classifier import (
    FakePatternClassifierProvider,
    PatternClassifierProviderResponse,
    PatternClassifierTimeoutError,
    classifier_version_for_provider,
)
from houston.analytics.models import (
    OperationalPattern,
    PatternLifecycleEvent,
    SignalPatternAssignment,
)
from houston.analytics.payload_safety import provider_payload_safety_errors
from houston.analytics.services import (
    create_operational_pattern,
    mark_assignment_processing,
    mark_assignment_succeeded,
    move_signals_between_patterns,
)
from houston.analytics.signature import build_signal_pattern_signature
from houston.establishments.models import EstablishmentMembership
from houston.signals.models import Signal
from houston.testing.factories import build_membership

pytestmark = pytest.mark.django_db


class MixedProvider:
    provider = "fake"
    model = "fake"

    def __init__(self):
        self.calls = 0

    def classify(self, *, input_payload):
        self.calls += 1
        if self.calls == 1:
            return PatternClassifierProviderResponse(
                payload={
                    "result_type": "new_pattern",
                    "pattern_id": None,
                    "canonical_label": "Operational backfill issue",
                },
                model=self.model,
            )
        raise RuntimeError("unexpected provider failure")

    def assess_duplicate(self, *, input_payload):
        return PatternClassifierProviderResponse(
            payload={"result_type": "create_new_pattern", "pattern_id": None},
            model=self.model,
        )


class SuccessFailureSuccessProvider:
    provider = "fake"
    model = "fake"

    def __init__(self):
        self.calls = 0

    def classify(self, *, input_payload):
        self.calls += 1
        if self.calls == 2:
            raise PatternClassifierTimeoutError("middle provider timeout")
        return PatternClassifierProviderResponse(
            payload={
                "result_type": "new_pattern",
                "pattern_id": None,
                "canonical_label": f"Operational backfill issue {self.calls}",
            },
            model=self.model,
        )

    def assess_duplicate(self, *, input_payload):
        return PatternClassifierProviderResponse(
            payload={"result_type": "create_new_pattern", "pattern_id": None},
            model=self.model,
        )


class UnsafeInputPayloadProvider:
    provider = "fake"
    model = "fake"

    def classify(self, *, input_payload):
        input_payload["raw_text"] = "secret"
        return PatternClassifierProviderResponse(
            payload={
                "result_type": "new_pattern",
                "pattern_id": None,
                "canonical_label": "Unsafe payload issue",
            },
            model=self.model,
        )

    def assess_duplicate(self, *, input_payload):
        return PatternClassifierProviderResponse(
            payload={"result_type": "create_new_pattern", "pattern_id": None},
            model=self.model,
        )


def create_signal_for_membership(membership, *, title="Issue", status=Signal.Status.OPEN):
    return Signal.objects.create(
        establishment=membership.establishment,
        routing_status=Signal.RoutingStatus.UNASSIGNED,
        title=title,
        structured_summary="Structured issue summary",
        issue_focus="issue",
        status=status,
        last_activity_at=timezone.now(),
    )


def create_pattern_for_membership(membership, *, label="Pattern"):
    return create_operational_pattern(
        organization=membership.establishment.organization,
        label=label,
        created_by_membership=membership,
    )


def assign_signal_current_for_provider(*, signal, pattern, provider):
    signature = build_signal_pattern_signature(signal)
    version = classifier_version_for_provider(provider)
    processing = mark_assignment_processing(
        signal=signal,
        pending_signature=signature,
        pending_classifier_version=version,
    )
    return mark_assignment_succeeded(
        signal=signal,
        pattern=pattern,
        assigned_signature=signature,
        assigned_classifier_version=version,
        expected_attempt_count=processing.attempt_count,
    )


def test_backfill_persists_and_replay_is_idempotent(settings):
    settings.DEBUG = True
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_signal_for_membership(owner)

    first = backfill_analytics_patterns(
        establishment_id=owner.establishment_id,
        provider_name="fake",
        limit=10,
    )
    first_payload = backfill_report_to_dict(first)

    assignment = signal.pattern_assignment
    assert (
        assignment.classification_status
        == SignalPatternAssignment.ClassificationStatus.SUCCEEDED
    )
    assert first_payload["metrics"]["signals_claimed_count"] == 1
    assert first_payload["metrics"]["outcomes"] == {"succeeded": 1}
    assert first_payload["next_scan_cursor"] == str(signal.id)

    second = backfill_analytics_patterns(
        signal_ids=[signal.id],
        provider_name="fake",
        limit=10,
    )
    second_payload = backfill_report_to_dict(second)

    assert second_payload["mode"] == "explicit_signal_ids"
    assert second_payload["next_scan_cursor"] == ""
    assert second_payload["metrics"]["assignments_already_current_count"] == 1
    assert second_payload["metrics"]["provider_calls"]["classification_count"] == 0


def test_backfill_selection_includes_canceled_excludes_merged_and_tracks_cursor(settings):
    settings.DEBUG = True
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    open_signal = create_signal_for_membership(owner, title="Open")
    canceled = create_signal_for_membership(
        owner,
        title="Canceled",
        status=Signal.Status.CANCELED,
    )
    target = create_signal_for_membership(owner, title="Target")
    merged = create_signal_for_membership(owner, title="Merged")
    merged.merged_into = target
    merged.status = Signal.Status.ARCHIVED
    merged.save(update_fields=["merged_into", "status", "updated_at"])

    report = backfill_analytics_patterns(
        establishment_id=owner.establishment_id,
        start_after_signal_id=open_signal.id,
        provider_name="fake",
        limit=10,
    )
    payload = backfill_report_to_dict(report)

    assert payload["metrics"]["signals_inspected_count"] == 2
    assert payload["exclusions"] == {"merged": 1}
    assert payload["start_after_signal_id"] == str(open_signal.id)
    assert payload["next_scan_cursor"] == str(target.id)
    assert Signal.Status.CANCELED in {
        signal_result["signal_status"] for signal_result in payload["signals"]
    }
    assert str(canceled.id) in {signal_result["signal_id"] for signal_result in payload["signals"]}


def test_explicit_signal_ids_are_deduped_bounded_scoped_and_do_not_advance_cursor(settings):
    settings.DEBUG = True
    settings.HOUSTON_ANALYTICS_PATTERN_BACKFILL_MAX_LIMIT = 1
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    other = build_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_signal_for_membership(owner, title="Scoped")
    other_signal = create_signal_for_membership(other, title="Other")
    extra = create_signal_for_membership(owner, title="Extra")

    report = backfill_analytics_patterns(
        establishment_id=owner.establishment_id,
        signal_ids=[signal.id, signal.id],
        provider_name="fake",
        limit=1,
    )
    payload = backfill_report_to_dict(report)

    assert payload["mode"] == "explicit_signal_ids"
    assert payload["metrics"]["signals_inspected_count"] == 1
    assert payload["next_scan_cursor"] == ""

    with pytest.raises(ValueError, match="selected scope"):
        backfill_analytics_patterns(
            establishment_id=owner.establishment_id,
            signal_ids=[other_signal.id],
            provider_name="fake",
            limit=1,
        )
    with pytest.raises(ValueError, match="effective limit"):
        backfill_analytics_patterns(
            establishment_id=owner.establishment_id,
            signal_ids=[signal.id, extra.id],
            provider_name="fake",
            limit=1,
        )


def test_remaining_signal_ids_only_include_replayable_non_terminal_outcomes(settings):
    settings.DEBUG = True
    settings.HOUSTON_ANALYTICS_PATTERN_PROCESSING_STALE_SECONDS = 60
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    temp_signal = create_signal_for_membership(owner, title="Temporary")
    processing_signal = create_signal_for_membership(owner, title="Processing")
    permanent_signal = create_signal_for_membership(owner, title="Permanent")
    mark_assignment_processing(
        signal=processing_signal,
        pending_signature=build_signal_pattern_signature(processing_signal),
        pending_classifier_version=classifier_version_for_provider(FakePatternClassifierProvider()),
    )

    temp_report = backfill_analytics_patterns(
        signal_ids=[temp_signal.id],
        provider_name="fake",
        provider=FakePatternClassifierProvider(exc=PatternClassifierTimeoutError("timeout")),
        limit=10,
    )
    permanent_provider = FakePatternClassifierProvider(
        payload={"result_type": "new_pattern", "pattern_id": None, "canonical_label": ""},
    )
    permanent_report = backfill_analytics_patterns(
        signal_ids=[processing_signal.id, permanent_signal.id],
        provider_name="fake",
        provider=permanent_provider,
        limit=10,
    )

    temp_payload = backfill_report_to_dict(temp_report)
    permanent_payload = backfill_report_to_dict(permanent_report)

    assert temp_payload["metrics"]["remaining_signal_ids"] == [str(temp_signal.id)]
    assert temp_payload["metrics"]["remaining_by_reason"] == {"temporary_failed": 1}
    assert str(processing_signal.id) in permanent_payload["metrics"]["remaining_signal_ids"]
    assert str(permanent_signal.id) not in permanent_payload["metrics"]["remaining_signal_ids"]
    assert permanent_payload["metrics"]["terminal_outcomes"] == {"permanently_failed": 1}


def test_owner_correction_is_protected_until_signature_changes(settings):
    settings.DEBUG = True
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    provider = FakePatternClassifierProvider()
    source = create_pattern_for_membership(owner, label="Source")
    target = create_pattern_for_membership(owner, label="Owner target")
    protected = create_signal_for_membership(owner, title="Protected")
    reopened = create_signal_for_membership(owner, title="Reopened")
    assign_signal_current_for_provider(signal=protected, pattern=source, provider=provider)
    assign_signal_current_for_provider(signal=reopened, pattern=source, provider=provider)
    move_signals_between_patterns(
        actor_membership=owner,
        source_pattern=source,
        target_pattern=target,
        signal_ids=[protected.id, reopened.id],
    )
    reopened.title = "Changed semantic identity"
    reopened.save(update_fields=["title", "updated_at"])

    report = backfill_analytics_patterns(
        signal_ids=[protected.id, reopened.id],
        provider_name="fake",
        provider=provider,
        limit=10,
    )
    payload = backfill_report_to_dict(report)

    assert payload["metrics"]["owner_correction_protected_count"] == 1
    assert payload["metrics"]["owner_correction_reopened_count"] == 1
    protected.pattern_assignment.refresh_from_db()
    assert protected.pattern_assignment.pattern_id == target.id
    reopened.pattern_assignment.refresh_from_db()
    assert (
        reopened.pattern_assignment.assignment_source
        == SignalPatternAssignment.AssignmentSource.CLASSIFIER
    )


def test_retryable_replays_use_attempt_count_until_retry_exhausted(settings):
    settings.DEBUG = True
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_signal_for_membership(owner)
    provider = FakePatternClassifierProvider(exc=PatternClassifierTimeoutError("timeout"))

    outcomes = []
    for _ in range(4):
        report = backfill_analytics_patterns(
            signal_ids=[signal.id],
            provider_name="fake",
            provider=provider,
            limit=10,
        )
        outcomes.append(backfill_report_to_dict(report)["signals"][0]["outcome"])

    assert outcomes == [
        "temporary_failed",
        "temporary_failed",
        "temporary_failed",
        "retry_exhausted",
    ]
    final_payload = backfill_report_to_dict(report)
    assert final_payload["metrics"]["remaining_signal_ids"] == []
    assert final_payload["metrics"]["terminal_outcomes"] == {"retry_exhausted": 1}


def test_fail_on_error_does_not_rollback_successful_signals(settings, monkeypatch):
    settings.DEBUG = True
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    first = create_signal_for_membership(owner, title="First")
    second = create_signal_for_membership(owner, title="Second")
    monkeypatch.setenv("HOUSTON_ALLOW_FAKE_ANALYTICS_PATTERN_BACKFILL", "1")
    monkeypatch.setattr(
        "houston.analytics.backfill._provider_for_name",
        lambda provider_name: MixedProvider(),
    )
    buffer = StringIO()

    with pytest.raises(CommandError):
        call_command(
            "backfill_analytics_patterns",
            provider="fake",
            json=True,
            fail_on_error=True,
            establishment_id=str(owner.establishment_id),
            limit=10,
            stdout=buffer,
        )
    payload = json.loads(buffer.getvalue())

    assert payload["errors"] == [
        {
            "error_code": "RuntimeError",
            "signal_id": str(second.id),
            "signal_status": second.status,
        }
    ]
    assert payload["metrics"]["remaining_signal_ids"] == [str(second.id)]
    assert payload["metrics"]["remaining_by_reason"] == {"reported": 1}
    assert payload["next_scan_cursor"] == str(first.id)
    assert SignalPatternAssignment.objects.filter(
        signal=first,
        classification_status=SignalPatternAssignment.ClassificationStatus.SUCCEEDED,
    ).exists()


def test_scan_cursor_stops_before_middle_batch_failure_and_resume_replays(settings):
    settings.DEBUG = True
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    first = create_signal_for_membership(owner, title="First")
    second = create_signal_for_membership(owner, title="Second")
    third = create_signal_for_membership(owner, title="Third")

    first_report = backfill_analytics_patterns(
        establishment_id=owner.establishment_id,
        provider_name="fake",
        provider=SuccessFailureSuccessProvider(),
        limit=10,
    )
    first_payload = backfill_report_to_dict(first_report)

    assert [signal["signal_id"] for signal in first_payload["signals"]] == [
        str(first.id),
        str(second.id),
        str(third.id),
    ]
    assert first_payload["metrics"]["remaining_signal_ids"] == [str(second.id)]
    assert first_payload["next_scan_cursor"] == str(first.id)

    second_report = backfill_analytics_patterns(
        establishment_id=owner.establishment_id,
        start_after_signal_id=first_payload["next_scan_cursor"],
        provider_name="fake",
        provider=FakePatternClassifierProvider(),
        limit=10,
    )
    second_payload = backfill_report_to_dict(second_report)

    assert [signal["signal_id"] for signal in second_payload["signals"]] == [
        str(second.id),
        str(third.id),
    ]
    assert second_payload["signals"][0]["outcome"] == "succeeded"
    assert second_payload["metrics"]["remaining_signal_ids"] == []


def test_configured_provider_rejects_injected_fake_before_any_mutation(settings, monkeypatch):
    settings.DEBUG = True
    monkeypatch.setenv("HOUSTON_RUN_ANALYTICS_PATTERN_BACKFILL", "1")
    monkeypatch.setattr(settings, "HOUSTON_AI_ANALYTICS_PATTERN_PROVIDER", "openai")
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_signal_for_membership(owner)
    before_patterns = OperationalPattern.objects.count()
    before_events = PatternLifecycleEvent.objects.count()
    before_logs = AIUsageLog.objects.count()

    with pytest.raises(RuntimeError, match="non-fake effective provider"):
        backfill_analytics_patterns(
            signal_ids=[signal.id],
            provider_name="configured",
            provider=FakePatternClassifierProvider(),
            limit=10,
        )

    assert not SignalPatternAssignment.objects.filter(signal=signal).exists()
    assert OperationalPattern.objects.count() == before_patterns
    assert PatternLifecycleEvent.objects.count() == before_events
    assert AIUsageLog.objects.count() == before_logs


def test_command_guards_configured_and_fake_providers(settings, monkeypatch):
    monkeypatch.delenv("HOUSTON_RUN_ANALYTICS_PATTERN_BACKFILL", raising=False)
    monkeypatch.delenv("HOUSTON_ALLOW_FAKE_ANALYTICS_PATTERN_BACKFILL", raising=False)
    with pytest.raises(CommandError):
        call_command("backfill_analytics_patterns", provider="configured", limit=1)

    settings.DEBUG = False
    with pytest.raises(CommandError):
        call_command("backfill_analytics_patterns", provider="fake", limit=1)


def test_report_json_is_safe_and_duplicate_guard_option_is_reported(settings):
    settings.DEBUG = True
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    create_signal_for_membership(owner)

    report = backfill_analytics_patterns(
        establishment_id=owner.establishment_id,
        provider_name="fake",
        duplicate_guard_enabled=False,
        limit=10,
    )
    payload = backfill_report_to_dict(report)
    serialized = json.dumps(payload, sort_keys=True)

    assert payload["duplicate_guard"]["enabled"] is False
    assert payload["payload_safety_status"] == "pass"
    assert "raw_text" not in serialized
    assert "location_text" not in serialized
    assert "expected_action" not in serialized


def test_payload_safety_ignores_text_values_and_detects_forbidden_keys():
    assert (
        provider_payload_safety_errors(
            [
                {
                    "summary": "commentaire immediate authorisation",
                    "items": [{"label": "commentaire"}],
                }
            ]
        )
        == []
    )

    assert provider_payload_safety_errors(
        [{"allowed": [{"nested": {"raw_text": "secret"}}], "author": "forbidden"}]
    ) == ["author", "raw_text"]


def test_backfill_payload_safety_status_reports_forbidden_payload_keys(settings):
    settings.DEBUG = True
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    create_signal_for_membership(owner)

    report = backfill_analytics_patterns(
        establishment_id=owner.establishment_id,
        provider_name="fake",
        provider=UnsafeInputPayloadProvider(),
        limit=10,
    )
    payload = backfill_report_to_dict(report)

    assert payload["payload_safety_status"] == "fail"
    assert payload["payload_safety_errors"] == ["raw_text"]
