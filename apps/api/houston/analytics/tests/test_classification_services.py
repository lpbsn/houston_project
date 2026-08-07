from __future__ import annotations

import threading
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from django.db import IntegrityError, close_old_connections, connections
from django.utils import timezone

from houston.ai.models import AIUsageLog
from houston.analytics.classifier import (
    FakePatternClassifierProvider,
    OpenAIPatternClassifierProvider,
    PatternClassifierInvalidOutputError,
    PatternClassifierTimeoutError,
    parse_pattern_classifier_response,
)
from houston.analytics.exceptions import AnalyticsValidationError
from houston.analytics.models import OperationalPattern, SignalPatternAssignment
from houston.analytics.scheduling import schedule_reclassification_if_signature_changed
from houston.analytics.services import (
    PatternClassificationRetryableError,
    claim_signal_pattern_classification,
    classify_signal_pattern,
    create_operational_pattern,
    mark_assignment_processing,
    mark_assignment_succeeded,
)
from houston.analytics.signature import (
    build_signal_pattern_payload,
    build_signal_pattern_signature,
)
from houston.establishments.models import OperationalUnit
from houston.establishments.tests.taxonomy_helpers import (
    create_activity_subject,
    create_business_unit,
)
from houston.signals.models import Signal
from houston.testing.factories import build_membership

pytestmark = pytest.mark.django_db


def create_signal_for_membership(membership, *, title="Clim en panne"):
    bar = create_business_unit(
        establishment=membership.establishment,
        key="bar",
        label="Bar",
    )
    maintenance = create_business_unit(
        establishment=membership.establishment,
        key="maintenance",
        label="Maintenance",
    )
    subject = create_activity_subject(
        establishment=membership.establishment,
        business_unit=maintenance,
        label="Equipment",
    )
    return Signal.objects.create(
        establishment=membership.establishment,
        affected_business_unit=bar,
        responsible_business_unit=maintenance,
        activity_subject=subject,
        routing_status=Signal.RoutingStatus.RESOLVED,
        title=title,
        structured_summary="La climatisation ne fonctionne plus dans la chambre.",
        issue_focus="climatisation",
        last_activity_at=timezone.now(),
    )


def create_pattern_for_signal(signal, *, label="Climatisation défaillante"):
    return create_operational_pattern(
        organization=signal.establishment.organization,
        label=label,
    )


def test_payload_is_limited_to_structured_phenomenon_fields():
    membership = build_membership()
    signal = create_signal_for_membership(membership)

    payload = build_signal_pattern_payload(signal)

    assert payload["signal"]["operational_unit"] is None
    assert payload["signal"]["title"] == "Clim en panne"
    assert "affected_business_unit" in payload["context"]
    assert "responsible_business_unit" in payload["context"]

    serialized = str(payload)
    assert "routing_status" not in serialized
    assert "expected_action" not in serialized
    assert "location_text" not in serialized
    assert "raw_text" not in serialized
    assert "submitted_at" not in serialized


def test_signature_is_deterministic():
    membership = build_membership()
    signal = create_signal_for_membership(membership)

    assert build_signal_pattern_signature(signal) == build_signal_pattern_signature(signal)


def test_signature_ignores_business_unit_context_changes():
    membership = build_membership()
    signal = create_signal_for_membership(membership)
    other_affected = create_business_unit(
        establishment=membership.establishment,
        key="spa",
        label="Spa",
    )
    other_responsible = create_business_unit(
        establishment=membership.establishment,
        key="security",
        label="Security",
    )
    before = build_signal_pattern_signature(signal)

    signal.affected_business_unit = other_affected
    signal.responsible_business_unit = other_responsible
    signal.save(
        update_fields=[
            "affected_business_unit",
            "responsible_business_unit",
            "updated_at",
        ]
    )

    assert build_signal_pattern_signature(signal) == before


@pytest.mark.parametrize(
    "field_name,value_factory",
    [
        ("title", lambda membership: "Nouvelle panne clim"),
        ("structured_summary", lambda membership: "La climatisation fuit maintenant."),
        ("issue_focus", lambda membership: "fuite climatisation"),
        (
            "activity_subject",
            lambda membership: create_activity_subject(
                establishment=membership.establishment,
                business_unit=create_business_unit(
                    establishment=membership.establishment,
                    key="housekeeping",
                    label="Housekeeping",
                ),
                label="Cleaning",
            ),
        ),
        (
            "operational_unit",
            lambda membership: OperationalUnit.objects.create(
                establishment=membership.establishment,
                key="room-101",
                label="Room 101",
            ),
        ),
    ],
)
def test_signature_changes_for_phenomenon_identity_fields(field_name, value_factory):
    membership = build_membership()
    signal = create_signal_for_membership(membership)
    before = build_signal_pattern_signature(signal)
    value = value_factory(membership)

    setattr(signal, field_name, value)
    signal.save(update_fields=[field_name, "updated_at"])

    assert build_signal_pattern_signature(signal) != before


def test_reclassification_scheduler_noops_when_signature_is_unchanged():
    membership = build_membership()
    signal = create_signal_for_membership(membership)
    before = build_signal_pattern_signature(signal)

    with (
        patch("houston.analytics.scheduling.transaction.on_commit") as on_commit,
        patch("houston.analytics.tasks.classify_signal_pattern_task.delay") as delay,
    ):
        scheduled = schedule_reclassification_if_signature_changed(
            signal=signal,
            before_signature=before,
        )

    assert scheduled is False
    on_commit.assert_not_called()
    delay.assert_not_called()


def test_reclassification_scheduler_enqueues_when_signature_changes():
    membership = build_membership()
    signal = create_signal_for_membership(membership)
    before = build_signal_pattern_signature(signal)
    signal.issue_focus = "fuite climatisation"
    signal.save(update_fields=["issue_focus", "updated_at"])

    with (
        patch(
            "houston.analytics.scheduling.transaction.on_commit",
            side_effect=lambda callback: callback(),
        ),
        patch("houston.analytics.tasks.classify_signal_pattern_task.delay") as delay,
    ):
        scheduled = schedule_reclassification_if_signature_changed(
            signal=signal,
            before_signature=before,
        )

    assert scheduled is True
    delay.assert_called_once_with(str(signal.id))


def test_claim_returns_already_succeeded_before_processing():
    membership = build_membership()
    signal = create_signal_for_membership(membership)
    pattern = create_pattern_for_signal(signal)
    signature = "sig-v1"
    classifier_version = "classifier-v1"
    processing = mark_assignment_processing(
        signal=signal,
        pending_signature=signature,
        pending_classifier_version=classifier_version,
    )
    mark_assignment_succeeded(
        signal=signal,
        pattern=pattern,
        assigned_signature=signature,
        assigned_classifier_version=classifier_version,
        expected_attempt_count=processing.attempt_count,
    )

    claim = claim_signal_pattern_classification(
        signal=signal,
        signature=signature,
        classifier_version=classifier_version,
    )

    assert claim.status == "already_succeeded"


def test_claim_recent_processing_blocks_second_provider_call(settings):
    settings.HOUSTON_ANALYTICS_PATTERN_PROCESSING_STALE_SECONDS = 60
    membership = build_membership()
    signal = create_signal_for_membership(membership)

    first = claim_signal_pattern_classification(
        signal=signal,
        signature="sig-v1",
        classifier_version="classifier-v1",
    )
    second = claim_signal_pattern_classification(
        signal=signal,
        signature="sig-v1",
        classifier_version="classifier-v1",
    )

    assert first.status == "claimed"
    assert second.status == "already_processing"
    assert second.attempt_count == first.attempt_count


def test_claim_new_signature_during_processing_obsoletes_previous_attempt(settings):
    settings.HOUSTON_ANALYTICS_PATTERN_PROCESSING_STALE_SECONDS = 60
    membership = build_membership()
    signal = create_signal_for_membership(membership)
    first = claim_signal_pattern_classification(
        signal=signal,
        signature="sig-v1",
        classifier_version="classifier-v1",
    )

    second = claim_signal_pattern_classification(
        signal=signal,
        signature="sig-v2",
        classifier_version="classifier-v1",
    )

    assert first.status == "claimed"
    assert second.status == "claimed"
    assert second.attempt_count == first.attempt_count + 1
    assignment = SignalPatternAssignment.objects.get(signal=signal)
    assert assignment.pending_signature == "sig-v2"


def test_claim_stale_processing_recovers_attempt(settings):
    settings.HOUSTON_ANALYTICS_PATTERN_PROCESSING_STALE_SECONDS = 60
    membership = build_membership()
    signal = create_signal_for_membership(membership)
    processing = mark_assignment_processing(
        signal=signal,
        pending_signature="old",
        pending_classifier_version="classifier-v1",
    )
    stale_at = timezone.now() - timedelta(minutes=10)
    SignalPatternAssignment.objects.filter(pk=processing.pk).update(
        last_attempted_at=stale_at,
    )

    claim = claim_signal_pattern_classification(
        signal=signal,
        signature="new",
        classifier_version="classifier-v1",
    )

    assert claim.status == "claimed"
    assert claim.attempt_count == processing.attempt_count + 1
    assert claim.assignment.pending_signature == "new"
    assert claim.assignment.last_error_code == ""
    assert claim.assignment.next_retry_at is None


@pytest.mark.django_db(transaction=True)
def test_concurrent_claim_allows_one_processing_attempt(settings):
    settings.HOUSTON_ANALYTICS_PATTERN_PROCESSING_STALE_SECONDS = 60
    membership = build_membership()
    signal = create_signal_for_membership(membership)
    results: list[str] = []

    def _claim():
        close_old_connections()
        try:
            claim = claim_signal_pattern_classification(
                signal=signal,
                signature="sig-v1",
                classifier_version="classifier-v1",
            )
            results.append(claim.status)
        finally:
            connections.close_all()

    first = threading.Thread(target=_claim)
    second = threading.Thread(target=_claim)
    first.start()
    second.start()
    first.join()
    second.join()
    connections.close_all()

    assert sorted(results) == ["already_processing", "claimed"]
    assert SignalPatternAssignment.objects.get(signal=signal).attempt_count == 1


def test_classify_attaches_existing_active_candidate():
    membership = build_membership()
    signal = create_signal_for_membership(membership)
    pattern = create_pattern_for_signal(signal)
    provider = FakePatternClassifierProvider(
        payload={"result_type": "existing_pattern", "pattern_id": str(pattern.id)}
    )

    assignment = classify_signal_pattern(signal.id, provider=provider)

    assert assignment.classification_status == (
        SignalPatternAssignment.ClassificationStatus.SUCCEEDED
    )
    assert assignment.pattern_id == pattern.id
    assert AIUsageLog.objects.filter(ai_domain=AIUsageLog.Domain.ANALYTICS_PATTERN).count() == 1


def test_classify_merged_signal_noops_without_provider_call():
    membership = build_membership()
    survivor = create_signal_for_membership(membership, title="Survivor")
    source = Signal.objects.create(
        establishment=membership.establishment,
        routing_status=Signal.RoutingStatus.UNASSIGNED,
        title="Source",
        structured_summary="Structured issue summary",
        status=Signal.Status.ARCHIVED,
        merged_into=survivor,
        last_activity_at=timezone.now(),
    )
    provider = FakePatternClassifierProvider(
        payload={"result_type": "new_pattern", "canonical_label": "Défaillance climatisation"}
    )

    assignment = classify_signal_pattern(source.id, provider=provider)

    assert assignment is None
    assert provider.calls == []
    assert not SignalPatternAssignment.objects.filter(signal=source).exists()


def test_classify_creates_new_canonical_pattern():
    membership = build_membership()
    signal = create_signal_for_membership(membership)
    provider = FakePatternClassifierProvider(
        payload={"result_type": "new_pattern", "canonical_label": "Défaillance climatisation"}
    )

    assignment = classify_signal_pattern(signal.id, provider=provider)

    assert assignment.classification_status == (
        SignalPatternAssignment.ClassificationStatus.SUCCEEDED
    )
    assert assignment.pattern.label == "Défaillance climatisation"


@pytest.mark.parametrize(
    "label",
    [
        "",
        "Clim en panne",
        "Establishment",
        "Bar",
        "x" * 256,
    ],
)
def test_new_pattern_rejects_invalid_canonical_label(label):
    membership = build_membership()
    membership.establishment.name = "Establishment"
    membership.establishment.save(update_fields=["name", "updated_at"])
    signal = create_signal_for_membership(membership)
    provider = FakePatternClassifierProvider(
        payload={"result_type": "new_pattern", "canonical_label": label}
    )

    assignment = classify_signal_pattern(signal.id, provider=provider)

    assert assignment.classification_status == (
        SignalPatternAssignment.ClassificationStatus.PERMANENTLY_FAILED
    )
    assert assignment.pattern is None


def test_concurrent_new_pattern_creation_reloads_existing_label_after_integrity_error():
    membership = build_membership()
    signal = create_signal_for_membership(membership)
    existing = create_pattern_for_signal(signal, label="Défaillance climatisation")
    provider = FakePatternClassifierProvider(
        payload={"result_type": "new_pattern", "canonical_label": "défaillance climatisation"}
    )

    with patch(
        "houston.analytics.services.create_operational_pattern",
        side_effect=IntegrityError,
    ):
        assignment = classify_signal_pattern(signal.id, provider=provider)

    assert assignment.classification_status == (
        SignalPatternAssignment.ClassificationStatus.SUCCEEDED
    )
    assert assignment.pattern_id == existing.id


def test_ambiguous_response_is_refused():
    with pytest.raises(PatternClassifierInvalidOutputError):
        parse_pattern_classifier_response(
            {
                "result_type": "existing_pattern",
                "pattern_id": "not-a-uuid",
                "canonical_label": "Label",
            }
        )


def test_unknown_candidate_pattern_is_permanently_failed():
    membership = build_membership()
    signal = create_signal_for_membership(membership)
    other = build_membership()
    other_pattern = create_operational_pattern(
        organization=other.establishment.organization,
        label="Other",
    )
    provider = FakePatternClassifierProvider(
        payload={"result_type": "existing_pattern", "pattern_id": str(other_pattern.id)}
    )

    assignment = classify_signal_pattern(signal.id, provider=provider)

    assert assignment.classification_status == (
        SignalPatternAssignment.ClassificationStatus.PERMANENTLY_FAILED
    )
    assert assignment.pattern is None


def test_merged_pattern_is_followed_to_active_target():
    membership = build_membership()
    signal = create_signal_for_membership(membership)
    target = create_pattern_for_signal(signal, label="Canonical")
    merged = OperationalPattern.objects.create(
        organization=signal.establishment.organization,
        label="Merged",
        status=OperationalPattern.Status.MERGED,
        merged_into=target,
    )
    candidates = [
        {
            "id": str(merged.id),
            "label": merged.label,
            "normalized_label": merged.normalized_label,
        }
    ]

    with patch(
        "houston.analytics.services._active_pattern_candidates",
        return_value=candidates,
    ):
        provider = FakePatternClassifierProvider(
            payload={"result_type": "existing_pattern", "pattern_id": str(merged.id)}
        )
        assignment = classify_signal_pattern(signal.id, provider=provider)

    assert assignment.pattern_id == target.id


def test_retryable_provider_error_raises_without_finalizing():
    membership = build_membership()
    signal = create_signal_for_membership(membership)
    provider = FakePatternClassifierProvider(exc=PatternClassifierTimeoutError("timeout"))

    with pytest.raises(PatternClassificationRetryableError) as exc_info:
        classify_signal_pattern(signal.id, provider=provider)

    assignment = SignalPatternAssignment.objects.get(signal=signal)
    assert assignment.classification_status == (
        SignalPatternAssignment.ClassificationStatus.PROCESSING
    )
    assert exc_info.value.attempt_count == assignment.attempt_count


def test_obsolete_success_attempt_is_refused():
    membership = build_membership()
    signal = create_signal_for_membership(membership)
    pattern = create_pattern_for_signal(signal)
    processing = mark_assignment_processing(
        signal=signal,
        pending_signature="sig-v1",
        pending_classifier_version="classifier-v1",
    )
    SignalPatternAssignment.objects.filter(pk=processing.pk).update(attempt_count=2)

    with pytest.raises(AnalyticsValidationError):
        mark_assignment_succeeded(
            signal=signal,
            pattern=pattern,
            assigned_signature="sig-v1",
            assigned_classifier_version="classifier-v1",
            expected_attempt_count=processing.attempt_count,
        )


def test_ai_usage_log_written_only_when_provider_called():
    membership = build_membership()
    signal = create_signal_for_membership(membership)
    pattern = create_pattern_for_signal(signal)
    provider = FakePatternClassifierProvider(
        payload={"result_type": "existing_pattern", "pattern_id": str(pattern.id)}
    )
    classify_signal_pattern(signal.id, provider=provider)

    provider.calls.clear()
    classify_signal_pattern(signal.id, provider=provider)

    assert provider.calls == []
    assert AIUsageLog.objects.filter(ai_domain=AIUsageLog.Domain.ANALYTICS_PATTERN).count() == 1


@pytest.mark.allow_openai_pattern_classify
def test_openai_pattern_provider_uses_strict_json_response_format():
    provider = OpenAIPatternClassifierProvider(
        api_key="test-key",
        model="test-model",
        timeout_seconds=1,
        max_retries=0,
    )
    create = MagicMock(
        return_value=SimpleNamespace(
            id="response-id",
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content='{"result_type":"new_pattern","pattern_id":null,'
                        '"canonical_label":"Défaillance climatisation"}'
                    )
                )
            ],
            usage=SimpleNamespace(prompt_tokens=3, completion_tokens=5, total_tokens=8),
        )
    )
    provider._client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )

    response = provider.classify(input_payload={"signal": {}, "active_patterns": []})

    assert response.payload["result_type"] == "new_pattern"
    assert response.input_tokens == 3
    call_kwargs = create.call_args.kwargs
    assert call_kwargs["response_format"]["type"] == "json_schema"
    assert call_kwargs["response_format"]["json_schema"]["strict"] is True
