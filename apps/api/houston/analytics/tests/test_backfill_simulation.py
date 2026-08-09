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
from houston.analytics.backfill_simulation import (
    backfill_simulation_report_to_dict,
    simulate_analytics_pattern_backfill,
)
from houston.analytics.classifier import (
    FakePatternClassifierProvider,
    PatternClassifierInvalidOutputError,
    PatternClassifierTimeoutError,
    classifier_version_for_provider,
)
from houston.analytics.models import (
    OperationalPattern,
    PatternLifecycleEvent,
    SignalPatternAssignment,
)
from houston.analytics.services import (
    create_operational_pattern,
    mark_assignment_processing,
    mark_assignment_succeeded,
    move_signals_between_patterns,
)
from houston.analytics.signature import build_signal_pattern_signature
from houston.analytics.tasks import classify_signal_pattern_task
from houston.establishments.models import EstablishmentMembership
from houston.signals.models import Signal
from houston.testing.factories import build_membership

pytestmark = pytest.mark.django_db


class OpenAIReportedFakeProvider(FakePatternClassifierProvider):
    provider = "openai"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.model = "openai-test"


class UnsafeInputPayloadProvider(FakePatternClassifierProvider):
    def classify(self, *, input_payload):
        input_payload["raw_text"] = "secret"
        return super().classify(input_payload=input_payload)


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


def test_backfill_simulation_rolls_back_assignments_patterns_events_and_usage_logs():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_signal_for_membership(owner)
    before_patterns = OperationalPattern.objects.count()
    before_events = PatternLifecycleEvent.objects.count()
    before_logs = AIUsageLog.objects.count()

    report = simulate_analytics_pattern_backfill(
        establishment_id=owner.establishment_id,
        provider_name="fake",
        limit=10,
    )
    payload = backfill_simulation_report_to_dict(report)

    assert payload["metrics"]["signals_inspected_count"] == 1
    assert payload["metrics"]["signals_claimed_for_simulation_count"] == 1
    assert not hasattr(signal, "pattern_assignment")
    assert OperationalPattern.objects.count() == before_patterns
    assert PatternLifecycleEvent.objects.count() == before_events
    assert AIUsageLog.objects.count() == before_logs


def test_backfill_selection_includes_canceled_and_excludes_merged_sources():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    create_signal_for_membership(owner, title="Open")
    create_signal_for_membership(owner, title="Canceled", status=Signal.Status.CANCELED)
    target = create_signal_for_membership(owner, title="Target")
    merged = create_signal_for_membership(owner, title="Merged")
    merged.merged_into = target
    merged.status = Signal.Status.ARCHIVED
    merged.save(update_fields=["merged_into", "status", "updated_at"])

    report = simulate_analytics_pattern_backfill(
        establishment_id=owner.establishment_id,
        provider_name="fake",
        limit=10,
    )
    payload = backfill_simulation_report_to_dict(report)

    assert payload["metrics"]["signals_inspected_count"] == 3
    assert payload["exclusions"] == {"merged": 1}
    assert Signal.Status.CANCELED in {
        signal_result["signal_status"] for signal_result in payload["signals"]
    }


def test_backfill_scope_limit_and_cursor_are_deterministic(settings):
    settings.HOUSTON_ANALYTICS_PATTERN_BACKFILL_SIMULATION_MAX_LIMIT = 2
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    other = build_membership(role=EstablishmentMembership.Role.OWNER)
    first = create_signal_for_membership(owner, title="First")
    second = create_signal_for_membership(owner, title="Second")
    create_signal_for_membership(owner, title="Third")
    create_signal_for_membership(other, title="Other org")

    report = simulate_analytics_pattern_backfill(
        establishment_id=owner.establishment_id,
        start_after_signal_id=first.id,
        provider_name="fake",
        limit=1,
    )
    payload = backfill_simulation_report_to_dict(report)

    assert payload["effective_limit"] == 1
    assert payload["max_limit"] == 2
    assert payload["start_after_signal_id"] == str(first.id)
    assert [signal_result["signal_id"] for signal_result in payload["signals"]] == [
        str(second.id)
    ]
    with pytest.raises(ValueError):
        simulate_analytics_pattern_backfill(
            establishment_id=owner.establishment_id,
            provider_name="fake",
            limit=3,
        )


def test_backfill_uses_claim_for_current_owner_and_processing_decisions(settings):
    settings.HOUSTON_ANALYTICS_PATTERN_PROCESSING_STALE_SECONDS = 60
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    provider = FakePatternClassifierProvider()
    classifier_pattern = create_pattern_for_membership(owner, label="Classifier")
    source = create_pattern_for_membership(owner, label="Source")
    owner_target = create_pattern_for_membership(owner, label="Owner target")
    current = create_signal_for_membership(owner, title="Current")
    owner_protected = create_signal_for_membership(owner, title="Owner")
    owner_reopened = create_signal_for_membership(owner, title="Owner reopened")
    processing_signal = create_signal_for_membership(owner, title="Processing")
    assign_signal_current_for_provider(
        signal=current,
        pattern=classifier_pattern,
        provider=provider,
    )
    assign_signal_current_for_provider(signal=owner_protected, pattern=source, provider=provider)
    assign_signal_current_for_provider(signal=owner_reopened, pattern=source, provider=provider)
    move_signals_between_patterns(
        actor_membership=owner,
        source_pattern=source,
        target_pattern=owner_target,
        signal_ids=[owner_protected.id, owner_reopened.id],
    )
    owner_reopened.title = "Changed semantic identity"
    owner_reopened.save(update_fields=["title", "updated_at"])
    mark_assignment_processing(
        signal=processing_signal,
        pending_signature=build_signal_pattern_signature(processing_signal),
        pending_classifier_version=classifier_version_for_provider(provider),
    )

    report = simulate_analytics_pattern_backfill(
        establishment_id=owner.establishment_id,
        provider_name="fake",
        provider=provider,
        limit=10,
    )
    payload = backfill_simulation_report_to_dict(report)

    assert payload["metrics"]["assignments_already_current_count"] == 1
    assert payload["metrics"]["owner_correction_protected_count"] == 1
    assert payload["metrics"]["owner_correction_reopened_count"] == 1
    assert payload["metrics"]["signals_claimed_for_simulation_count"] == 1
    assert payload["metrics"]["outcomes"]["already_processing"] == 1
    assert payload["metrics"]["technical_state_policy_observed"]["processing"] == {
        "already_processing": 1
    }
    owner_assignment = owner_reopened.pattern_assignment
    owner_assignment.refresh_from_db()
    assert owner_assignment.pattern_id == owner_target.id


def test_backfill_retryable_errors_finalize_without_persisting_processing():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_signal_for_membership(owner)
    provider = FakePatternClassifierProvider(
        exc=PatternClassifierTimeoutError("timeout"),
    )

    report = simulate_analytics_pattern_backfill(
        establishment_id=owner.establishment_id,
        provider_name="fake",
        provider=provider,
        limit=10,
    )
    payload = backfill_simulation_report_to_dict(report)

    assert payload["metrics"]["outcomes"] == {"retry_exhausted": 1}
    assert payload["metrics"]["technical_error_count"] == 1
    assert not hasattr(signal, "pattern_assignment")


def test_backfill_simulation_and_real_backfill_share_task_retry_policy(
    settings,
    monkeypatch,
):
    settings.DEBUG = True
    monkeypatch.setattr(classify_signal_pattern_task, "max_retries", 0)
    monkeypatch.setattr(classify_signal_pattern_task, "default_retry_delay", 0)
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    simulation_signal = create_signal_for_membership(owner, title="Simulation")
    backfill_signal = create_signal_for_membership(owner, title="Backfill")

    simulation_report = simulate_analytics_pattern_backfill(
        establishment_id=owner.establishment_id,
        provider_name="fake",
        provider=FakePatternClassifierProvider(
            exc=PatternClassifierTimeoutError("timeout"),
        ),
        limit=1,
    )
    backfill_report = backfill_analytics_patterns(
        signal_ids=[backfill_signal.id],
        provider_name="fake",
        provider=FakePatternClassifierProvider(
            exc=PatternClassifierTimeoutError("timeout"),
        ),
        limit=10,
    )
    simulation_payload = backfill_simulation_report_to_dict(simulation_report)
    backfill_payload = backfill_report_to_dict(backfill_report)

    assert simulation_payload["signals"][0]["signal_id"] == str(simulation_signal.id)
    assert simulation_payload["metrics"]["outcomes"] == {"retry_exhausted": 1}
    assert backfill_payload["metrics"]["outcomes"] == {"retry_exhausted": 1}
    assert simulation_payload["metrics"]["provider_calls"]["classification_count"] == 1
    assert backfill_payload["metrics"]["provider_calls"]["classification_count"] == 1


def test_backfill_permanent_provider_errors_report_failure_without_persisting_processing():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_signal_for_membership(owner)
    before_patterns = OperationalPattern.objects.count()
    before_events = PatternLifecycleEvent.objects.count()
    before_logs = AIUsageLog.objects.count()
    provider = FakePatternClassifierProvider(
        exc=PatternClassifierInvalidOutputError("invalid structured output"),
    )

    report = simulate_analytics_pattern_backfill(
        establishment_id=owner.establishment_id,
        provider_name="fake",
        provider=provider,
        limit=10,
    )
    payload = backfill_simulation_report_to_dict(report)

    assert payload["metrics"]["outcomes"] == {"permanently_failed": 1}
    assert payload["metrics"]["technical_error_count"] == 1
    assert payload["signals"][0]["final_error_code"] == "invalid_structured_output"
    assert not SignalPatternAssignment.objects.filter(
        signal=signal,
        classification_status=SignalPatternAssignment.ClassificationStatus.PROCESSING,
    ).exists()
    assert not hasattr(signal, "pattern_assignment")
    assert OperationalPattern.objects.count() == before_patterns
    assert PatternLifecycleEvent.objects.count() == before_events
    assert AIUsageLog.objects.count() == before_logs


def test_backfill_report_is_safe_and_tracks_duplicate_guard_option():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    existing = create_pattern_for_membership(owner, label="Recurring operational issue")
    create_signal_for_membership(owner)

    report = simulate_analytics_pattern_backfill(
        establishment_id=owner.establishment_id,
        provider_name="fake",
        duplicate_guard_enabled=False,
        limit=10,
    )
    payload = backfill_simulation_report_to_dict(report)
    serialized = json.dumps(payload, sort_keys=True)

    assert payload["duplicate_guard"]["enabled"] is False
    assert payload["payload_safety_status"] == "pass"
    assert "raw_text" not in serialized
    assert "location_text" not in serialized
    assert "expected_action" not in serialized
    assert existing.label in serialized


def test_backfill_simulation_payload_safety_status_reports_forbidden_payload_keys():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    create_signal_for_membership(owner)

    report = simulate_analytics_pattern_backfill(
        establishment_id=owner.establishment_id,
        provider_name="fake",
        provider=UnsafeInputPayloadProvider(),
        limit=10,
    )
    payload = backfill_simulation_report_to_dict(report)

    assert payload["payload_safety_status"] == "fail"
    assert payload["payload_safety_errors"] == ["raw_text"]


def test_configured_simulation_reports_mode_and_effective_provider(settings, monkeypatch):
    monkeypatch.setenv("HOUSTON_RUN_ANALYTICS_PATTERN_BACKFILL_SIMULATION", "1")
    monkeypatch.setattr(settings, "HOUSTON_AI_ANALYTICS_PATTERN_PROVIDER", "openai")
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    create_signal_for_membership(owner)

    report = simulate_analytics_pattern_backfill(
        establishment_id=owner.establishment_id,
        provider_name="configured",
        provider=OpenAIReportedFakeProvider(),
        limit=10,
    )
    payload = backfill_simulation_report_to_dict(report)

    assert payload["provider_mode"] == "configured"
    assert payload["provider"] == "openai"
    assert payload["provider_model"] == "openai-test"


def test_configured_simulation_rejects_injected_fake_before_pipeline(
    settings,
    monkeypatch,
):
    monkeypatch.setenv("HOUSTON_RUN_ANALYTICS_PATTERN_BACKFILL_SIMULATION", "1")
    monkeypatch.setattr(settings, "HOUSTON_AI_ANALYTICS_PATTERN_PROVIDER", "openai")
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_signal_for_membership(owner)
    provider = FakePatternClassifierProvider()
    before_patterns = OperationalPattern.objects.count()
    before_events = PatternLifecycleEvent.objects.count()
    before_logs = AIUsageLog.objects.count()

    with pytest.raises(RuntimeError, match="non-fake effective provider"):
        simulate_analytics_pattern_backfill(
            establishment_id=owner.establishment_id,
            provider_name="configured",
            provider=provider,
            limit=10,
        )

    assert provider.calls == []
    assert not SignalPatternAssignment.objects.filter(signal=signal).exists()
    assert OperationalPattern.objects.count() == before_patterns
    assert PatternLifecycleEvent.objects.count() == before_events
    assert AIUsageLog.objects.count() == before_logs


def test_backfill_command_json_and_archive(tmp_path):
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    create_signal_for_membership(owner)
    buffer = StringIO()

    call_command(
        "simulate_analytics_pattern_backfill",
        establishment_id=str(owner.establishment_id),
        provider="fake",
        json=True,
        limit=10,
        archive=True,
        archive_dir=str(tmp_path),
        stdout=buffer,
    )
    payload = json.loads(buffer.getvalue())

    assert payload["schema_version"] == "analytics_pattern_backfill_simulation_v1"
    assert len(list(tmp_path.glob("analytics-pattern-backfill-simulation-*.json"))) == 1


def test_backfill_configured_provider_requires_opt_in(monkeypatch):
    monkeypatch.delenv("HOUSTON_RUN_ANALYTICS_PATTERN_BACKFILL_SIMULATION", raising=False)

    with pytest.raises(CommandError):
        call_command(
            "simulate_analytics_pattern_backfill",
            provider="configured",
            limit=1,
        )
