from __future__ import annotations

import json
import threading
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from django.db import IntegrityError, close_old_connections, connection, connections
from django.utils import timezone

from houston.ai.models import AIUsageLog
from houston.analytics.classifier import (
    ANALYTICS_PATTERN_DUPLICATE_GUARD_PROMPT_VERSION,
    ANALYTICS_PATTERN_DUPLICATE_GUARD_SCHEMA_VERSION,
    DUPLICATE_GUARD_REASON_CODES,
    FakePatternClassifierProvider,
    OpenAIPatternClassifierProvider,
    PatternClassifierInvalidOutputError,
    PatternClassifierTimeoutError,
    _duplicate_guard_system_prompt,
    openai_duplicate_guard_response_format,
    parse_pattern_classifier_response,
    parse_pattern_duplicate_guard_response,
)
from houston.analytics.exceptions import AnalyticsValidationError
from houston.analytics.models import OperationalPattern, SignalPatternAssignment
from houston.analytics.scheduling import schedule_reclassification_if_signature_changed
from houston.analytics.services import (
    PatternClassificationRetryableError,
    _duplicate_guard_shortlist,
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
from houston.establishments.models import EstablishmentMembership, OperationalUnit
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


def test_classify_reuses_existing_active_semantic_alias_without_duplicate_guard():
    membership = build_membership()
    signal = create_signal_for_membership(membership)
    pattern = create_pattern_for_signal(signal)
    provider = FakePatternClassifierProvider(
        payload={"canonical_label": pattern.semantic_label},
        duplicate_guard_payload={"result_type": "create_new_pattern", "pattern_id": None},
    )

    assignment = classify_signal_pattern(signal.id, provider=provider)

    assert assignment.classification_status == (
        SignalPatternAssignment.ClassificationStatus.SUCCEEDED
    )
    assert assignment.pattern_id == pattern.id
    assert provider.calls[0].get("active_patterns") is None
    assert provider.duplicate_guard_calls == []
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
        payload={"canonical_label": "Défaillance climatisation"}
    )

    assignment = classify_signal_pattern(source.id, provider=provider)

    assert assignment is None
    assert provider.calls == []
    assert not SignalPatternAssignment.objects.filter(signal=source).exists()


def test_classify_creates_new_canonical_pattern():
    membership = build_membership()
    signal = create_signal_for_membership(membership)
    provider = FakePatternClassifierProvider(
        payload={"canonical_label": "Défaillance climatisation"}
    )

    assignment = classify_signal_pattern(signal.id, provider=provider)

    assert assignment.classification_status == (
        SignalPatternAssignment.ClassificationStatus.SUCCEEDED
    )
    assert assignment.pattern.label == "Défaillance climatisation"


def test_new_pattern_strict_duplicate_reuses_without_duplicate_guard():
    membership = build_membership()
    signal = create_signal_for_membership(membership)
    existing = create_pattern_for_signal(signal, label="Défaillance climatisation")
    provider = FakePatternClassifierProvider(
        payload={"canonical_label": "défaillance climatisation"},
        duplicate_guard_payload={"result_type": "create_new_pattern", "pattern_id": None},
    )

    assignment = classify_signal_pattern(signal.id, provider=provider)

    assert assignment.pattern_id == existing.id
    assert provider.duplicate_guard_calls == []
    assert getattr(assignment, "_analytics_duplicate_guard_decision") == "skipped"
    assert AIUsageLog.objects.filter(ai_domain=AIUsageLog.Domain.ANALYTICS_PATTERN).count() == 1


def test_duplicate_guard_reuses_shortlisted_active_pattern(settings):
    settings.HOUSTON_ANALYTICS_PATTERN_DUPLICATE_GUARD_MIN_SCORE = 0.5
    membership = build_membership()
    signal = create_signal_for_membership(membership, title="Climate unit offline")
    existing = create_pattern_for_signal(signal, label="Climate equipment failure")
    provider = FakePatternClassifierProvider(
        payload={"canonical_label": "Climate equipment outage"},
        duplicate_guard_payload={
            "result_type": "reuse_existing_pattern",
            "pattern_id": str(existing.id),
        },
    )

    assignment = classify_signal_pattern(signal.id, provider=provider)

    assert assignment.pattern_id == existing.id
    assert len(provider.duplicate_guard_calls) == 1
    assert getattr(assignment, "_analytics_duplicate_guard_decision") == "reused"
    assert getattr(assignment, "_analytics_duplicate_guard_reason_code") == "same_phenomenon"
    serialized_guard_payload = str(provider.duplicate_guard_calls[0])
    assert "Bar" not in serialized_guard_payload
    assert "Maintenance" not in serialized_guard_payload
    guard_log = AIUsageLog.objects.get(
        prompt_version=ANALYTICS_PATTERN_DUPLICATE_GUARD_PROMPT_VERSION
    )
    assert guard_log.schema_version == ANALYTICS_PATTERN_DUPLICATE_GUARD_SCHEMA_VERSION
    assert guard_log.error_context == {"phase": "analytics_pattern_duplicate_guard"}


def test_duplicate_guard_shortlist_empty_creates_without_guard_call(settings):
    settings.HOUSTON_ANALYTICS_PATTERN_DUPLICATE_GUARD_MIN_SCORE = 0.9
    membership = build_membership()
    signal = create_signal_for_membership(membership, title="Climate unit offline")
    create_pattern_for_signal(signal, label="Unrelated linen shortage")
    provider = FakePatternClassifierProvider(
        payload={"canonical_label": "Climate equipment outage"},
        duplicate_guard_payload={"result_type": "create_new_pattern", "pattern_id": None},
    )

    assignment = classify_signal_pattern(signal.id, provider=provider)

    assert assignment.pattern.label == "Climate equipment outage"
    assert provider.duplicate_guard_calls == []
    assert getattr(assignment, "_analytics_duplicate_guard_decision") == "skipped"
    assert getattr(assignment, "_analytics_duplicate_guard_reason") == "no_candidates"
    assert getattr(assignment, "_analytics_duplicate_guard_reason_code") is None
    assert AIUsageLog.objects.filter(
        prompt_version=ANALYTICS_PATTERN_DUPLICATE_GUARD_PROMPT_VERSION
    ).count() == 0


def test_duplicate_guard_invalid_output_falls_back_to_create(settings):
    settings.HOUSTON_ANALYTICS_PATTERN_DUPLICATE_GUARD_MIN_SCORE = 0.5
    membership = build_membership()
    signal = create_signal_for_membership(membership, title="Climate unit offline")
    create_pattern_for_signal(signal, label="Climate equipment failure")
    provider = FakePatternClassifierProvider(
        payload={"canonical_label": "Climate equipment outage"},
        duplicate_guard_payload={
            "result_type": "reuse_existing_pattern",
            "pattern_id": str(membership.id),
        },
    )

    assignment = classify_signal_pattern(signal.id, provider=provider)

    assert assignment.pattern.label == "Climate equipment outage"
    assert getattr(assignment, "_analytics_duplicate_guard_decision") == "fallback"
    assert getattr(assignment, "_analytics_duplicate_guard_reason") == "outside_shortlist"
    assert getattr(assignment, "_analytics_duplicate_guard_reason_code") is None
    guard_log = AIUsageLog.objects.get(
        prompt_version=ANALYTICS_PATTERN_DUPLICATE_GUARD_PROMPT_VERSION
    )
    assert guard_log.status == AIUsageLog.Status.FAILED
    assert guard_log.error_code == "duplicate_guard_pattern_outside_shortlist"


def test_duplicate_guard_timeout_falls_back_without_retry(settings):
    settings.HOUSTON_ANALYTICS_PATTERN_DUPLICATE_GUARD_MIN_SCORE = 0.5
    membership = build_membership()
    signal = create_signal_for_membership(membership, title="Climate unit offline")
    create_pattern_for_signal(signal, label="Climate equipment failure")
    provider = FakePatternClassifierProvider(
        payload={"canonical_label": "Climate equipment outage"},
        duplicate_guard_exc=PatternClassifierTimeoutError("timeout"),
    )

    assignment = classify_signal_pattern(signal.id, provider=provider)

    assert assignment.classification_status == (
        SignalPatternAssignment.ClassificationStatus.SUCCEEDED
    )
    assert assignment.pattern.label == "Climate equipment outage"
    assert getattr(assignment, "_analytics_duplicate_guard_decision") == "fallback"
    assert getattr(assignment, "_analytics_duplicate_guard_reason") == "provider_timeout"
    assert getattr(assignment, "_analytics_duplicate_guard_reason_code") is None
    guard_log = AIUsageLog.objects.get(
        prompt_version=ANALYTICS_PATTERN_DUPLICATE_GUARD_PROMPT_VERSION
    )
    assert guard_log.status == AIUsageLog.Status.FAILED
    assert guard_log.error_code == "provider_timeout"


@pytest.mark.django_db(transaction=True)
def test_duplicate_guard_call_happens_outside_transaction(settings):
    settings.HOUSTON_ANALYTICS_PATTERN_DUPLICATE_GUARD_MIN_SCORE = 0.5
    membership = build_membership()
    signal = create_signal_for_membership(membership, title="Climate unit offline")
    existing = create_pattern_for_signal(signal, label="Climate equipment failure")
    in_atomic_values = []

    class RecordingProvider(FakePatternClassifierProvider):
        def assess_duplicate(self, *, input_payload):
            in_atomic_values.append(connection.in_atomic_block)
            return super().assess_duplicate(input_payload=input_payload)

    provider = RecordingProvider(
        payload={"canonical_label": "Climate equipment outage"},
        duplicate_guard_payload={
            "result_type": "reuse_existing_pattern",
            "pattern_id": str(existing.id),
        },
    )

    classify_signal_pattern(signal.id, provider=provider)

    assert in_atomic_values == [False]


def test_obsolete_attempt_cannot_leave_orphan_pattern(settings):
    settings.HOUSTON_ANALYTICS_PATTERN_DUPLICATE_GUARD_MIN_SCORE = 0.5
    membership = build_membership()
    signal = create_signal_for_membership(membership, title="Climate unit offline")
    create_pattern_for_signal(signal, label="Climate equipment failure")

    class ObsoletingProvider(FakePatternClassifierProvider):
        def assess_duplicate(self, *, input_payload):
            SignalPatternAssignment.objects.filter(signal=signal).update(attempt_count=999)
            return super().assess_duplicate(input_payload=input_payload)

    provider = ObsoletingProvider(
        payload={"canonical_label": "Climate equipment outage"},
        duplicate_guard_payload={"result_type": "create_new_pattern", "pattern_id": None},
    )
    before_patterns = OperationalPattern.objects.count()

    assignment = classify_signal_pattern(signal.id, provider=provider)

    assert assignment.classification_status == (
        SignalPatternAssignment.ClassificationStatus.PROCESSING
    )
    assert OperationalPattern.objects.count() == before_patterns


def test_duplicate_guard_reuse_resolves_merged_candidate_chain(settings):
    settings.HOUSTON_ANALYTICS_PATTERN_DUPLICATE_GUARD_MIN_SCORE = 0.5
    membership = build_membership()
    signal = create_signal_for_membership(membership, title="Climate unit offline")
    candidate = create_pattern_for_signal(signal, label="Climate equipment failure")
    target = create_pattern_for_signal(signal, label="Climate equipment outage target")

    class MergingProvider(FakePatternClassifierProvider):
        def assess_duplicate(self, *, input_payload):
            OperationalPattern.objects.filter(pk=candidate.pk).update(
                status=OperationalPattern.Status.MERGED,
                merged_into=target,
            )
            return super().assess_duplicate(input_payload=input_payload)

    provider = MergingProvider(
        payload={"canonical_label": "Climate equipment outage"},
        duplicate_guard_payload={
            "result_type": "reuse_existing_pattern",
            "pattern_id": str(candidate.id),
        },
    )

    assignment = classify_signal_pattern(signal.id, provider=provider)

    assert assignment.pattern_id == target.id
    assert getattr(assignment, "_analytics_duplicate_guard_reason_code") == "same_phenomenon"


def test_duplicate_guard_reuse_with_merged_cycle_falls_back_to_create(settings):
    settings.HOUSTON_ANALYTICS_PATTERN_DUPLICATE_GUARD_MIN_SCORE = 0.5
    membership = build_membership()
    signal = create_signal_for_membership(membership, title="Climate unit offline")
    first = create_pattern_for_signal(signal, label="Climate equipment failure")
    second = create_pattern_for_signal(signal, label="Climate equipment issue")

    class CyclingProvider(FakePatternClassifierProvider):
        def assess_duplicate(self, *, input_payload):
            OperationalPattern.objects.filter(pk=first.pk).update(
                status=OperationalPattern.Status.MERGED,
                merged_into=second,
            )
            OperationalPattern.objects.filter(pk=second.pk).update(
                status=OperationalPattern.Status.MERGED,
                merged_into=first,
            )
            return super().assess_duplicate(input_payload=input_payload)

    provider = CyclingProvider(
        payload={"canonical_label": "Climate equipment outage"},
        duplicate_guard_payload={
            "result_type": "reuse_existing_pattern",
            "pattern_id": str(first.id),
        },
    )

    assignment = classify_signal_pattern(signal.id, provider=provider)

    assert assignment.pattern.label == "Climate equipment outage"


def test_duplicate_guard_shortlist_uses_stable_functional_tie_break(settings):
    settings.HOUSTON_ANALYTICS_PATTERN_DUPLICATE_GUARD_MIN_SCORE = 0.5
    settings.HOUSTON_ANALYTICS_PATTERN_DUPLICATE_GUARD_MAX_CANDIDATES = 2
    membership = build_membership()
    signal = create_signal_for_membership(membership, title="Climate unit offline")
    create_pattern_for_signal(signal, label="Climate alpha")
    create_pattern_for_signal(signal, label="Climate beta")

    shortlist = _duplicate_guard_shortlist(
        signal=signal,
        canonical_label="Climate outage",
    )

    assert [candidate.label for candidate in shortlist] == [
        "Climate alpha",
        "Climate beta",
    ]


def test_duplicate_guard_structured_output_requires_closed_reason_code():
    schema = openai_duplicate_guard_response_format()["json_schema"]["schema"]

    assert "reason_code" in schema["required"]
    assert schema["properties"]["reason_code"]["enum"] == list(
        DUPLICATE_GUARD_REASON_CODES
    )


@pytest.mark.parametrize(
    "reason_code",
    DUPLICATE_GUARD_REASON_CODES,
)
def test_duplicate_guard_parser_accepts_reason_codes(reason_code):
    pattern_id = "00000000-0000-0000-0000-000000000001"
    payload = (
        {
            "result_type": "reuse_existing_pattern",
            "pattern_id": pattern_id,
            "reason_code": reason_code,
        }
        if reason_code == "same_phenomenon"
        else {
            "result_type": "create_new_pattern",
            "pattern_id": None,
            "reason_code": reason_code,
        }
    )

    parsed = parse_pattern_duplicate_guard_response(payload)

    assert parsed.reason_code == reason_code


@pytest.mark.parametrize(
    ("payload", "expected_branch"),
    [
        (
            {
                "result_type": "create_new_pattern",
                "pattern_id": None,
            },
            "duplicate_guard_reason_code_invalid",
        ),
        (
            {
                "result_type": "create_new_pattern",
                "pattern_id": None,
                "reason_code": "not_valid",
            },
            "duplicate_guard_reason_code_invalid",
        ),
        (
            {
                "result_type": "reuse_existing_pattern",
                "pattern_id": "00000000-0000-0000-0000-000000000001",
                "reason_code": "different_failure_mode",
            },
            "duplicate_guard_reuse_reason_code_invalid",
        ),
        (
            {
                "result_type": "create_new_pattern",
                "pattern_id": None,
                "reason_code": "same_phenomenon",
            },
            "duplicate_guard_create_reason_code_invalid",
        ),
    ],
)
def test_duplicate_guard_parser_rejects_invalid_reason_code_contract(
    payload,
    expected_branch,
):
    with pytest.raises(PatternClassifierInvalidOutputError) as exc_info:
        parse_pattern_duplicate_guard_response(payload)

    assert exc_info.value.validation_branch == expected_branch


def test_duplicate_guard_prompt_covers_specialization_without_using_score_as_decision():
    prompt = _duplicate_guard_system_prompt()

    assert "Examine tous les candidats" in prompt
    assert "meilleur candidat compatible" in prompt
    assert "Ignore les candidats incompatibles" in prompt
    assert "frontière de processus explicite empêche le reuse" in prompt
    assert "sous-type d'objet ou d'équipement" in prompt
    assert "credential" in prompt
    assert "état spécifique compatible avec le fault/anomaly" in prompt
    assert "plus spécifique" in prompt
    assert "même unité" in prompt
    assert "analytique managériale" in prompt
    assert "candidat plus général" in prompt
    assert "vraie différence opérationnelle positive" in prompt
    assert "failure mode" in prompt
    assert "processus" in prompt
    assert "cause explicitement connue" in prompt
    assert "vrai comportement ou" in prompt
    assert "frontière de processus ou d'étape" in prompt
    assert "vraie incertitude opérationnelle" in prompt
    assert "ne suffit pas à produire ambiguous" in prompt
    assert "token_overlap_v1 sert uniquement à retrouver des candidats" in prompt
    assert "ne décide" in prompt


def test_duplicate_guard_default_threshold_includes_quarter_score_candidate(settings):
    assert settings.HOUSTON_ANALYTICS_PATTERN_DUPLICATE_GUARD_MIN_SCORE == 0.25
    membership = build_membership()
    signal = create_signal_for_membership(
        membership,
        title="Slippery floor in corridor",
    )
    create_pattern_for_signal(signal, label="Wet floor slip hazard")

    shortlist = _duplicate_guard_shortlist(
        signal=signal,
        canonical_label="slippery floor in corridor",
    )

    assert [(candidate.label, candidate.score) for candidate in shortlist] == [
        ("Wet floor slip hazard", 0.25),
    ]


@pytest.mark.parametrize(
    ("canonical_label", "candidate_label", "signal_title"),
    [
        (
            "pin pad offline",
            "Card payment terminal unavailable",
            "PIN pad offline for card payments",
        ),
        (
            "fridge temperature too high for safe storage",
            "Cold storage temperature anomaly",
            "Fridge readings too warm",
        ),
        (
            "pipe dripping leak",
            "Water leak in guest area",
            "Bathroom pipe dripping",
        ),
        (
            "mobile credential rejection at access control",
            "Access badge entry failure",
            "Mobile key rejected at entry",
        ),
    ],
)
def test_duplicate_guard_can_reuse_contextual_or_specialized_candidate(
    settings,
    canonical_label,
    candidate_label,
    signal_title,
):
    settings.HOUSTON_ANALYTICS_PATTERN_DUPLICATE_GUARD_MIN_SCORE = 0.25
    membership = build_membership()
    signal = create_signal_for_membership(membership, title=signal_title)
    existing = create_pattern_for_signal(signal, label=candidate_label)
    provider = FakePatternClassifierProvider(
        payload={"canonical_label": canonical_label},
        duplicate_guard_payload={
            "result_type": "reuse_existing_pattern",
            "pattern_id": str(existing.id),
        },
    )

    assignment = classify_signal_pattern(signal.id, provider=provider)

    assert assignment.pattern_id == existing.id
    assert getattr(assignment, "_analytics_duplicate_guard_decision") == "reused"
    assert getattr(assignment, "_analytics_duplicate_guard_reason_code") == "same_phenomenon"
    assert len(provider.duplicate_guard_calls) == 1


@pytest.mark.parametrize(
    ("canonical_label", "candidate_label", "signal_title", "reason_code"),
    [
        (
            "ticket scanner battery empty",
            "Ticket scan validation failure",
            "Ticket scanner battery empty",
            "different_failure_mode",
        ),
        (
            "security screening delay due to bag check",
            "Ticket scan entry delay",
            "Bag checks slowing venue entry",
            "different_process_or_stage",
        ),
        (
            "fridge warm because door seal torn",
            "fridge warm from overloaded shelf",
            "Fridge too warm due to torn door seal",
            "different_known_cause",
        ),
    ],
)
def test_duplicate_guard_can_create_for_real_operational_difference(
    settings,
    canonical_label,
    candidate_label,
    signal_title,
    reason_code,
):
    settings.HOUSTON_ANALYTICS_PATTERN_DUPLICATE_GUARD_MIN_SCORE = 0.25
    membership = build_membership()
    signal = create_signal_for_membership(membership, title=signal_title)
    existing = create_pattern_for_signal(signal, label=candidate_label)
    provider = FakePatternClassifierProvider(
        payload={"canonical_label": canonical_label},
        duplicate_guard_payload={
            "result_type": "create_new_pattern",
            "pattern_id": None,
            "reason_code": reason_code,
        },
    )

    assignment = classify_signal_pattern(signal.id, provider=provider)

    assert assignment.pattern_id != existing.id
    assert assignment.pattern.label == canonical_label
    assert getattr(assignment, "_analytics_duplicate_guard_decision") == "created"
    assert getattr(assignment, "_analytics_duplicate_guard_reason_code") == reason_code
    assert len(provider.duplicate_guard_calls) == 1


@pytest.mark.parametrize(
    ("label", "expected_branch"),
    [
        ("", "new_pattern_label_empty"),
        ("Establishment", "new_pattern_label_includes_context"),
        ("Bar", "new_pattern_label_includes_context"),
        ("x" * 256, "new_pattern_label_too_long"),
    ],
)
def test_new_pattern_invalid_canonical_label_is_retryable_with_safe_diagnostic(
    label,
    expected_branch,
):
    membership = build_membership()
    membership.establishment.name = "Establishment"
    membership.establishment.save(update_fields=["name", "updated_at"])
    signal = create_signal_for_membership(membership)
    provider = FakePatternClassifierProvider(
        payload={"canonical_label": label}
    )

    with pytest.raises(PatternClassificationRetryableError) as exc_info:
        classify_signal_pattern(signal.id, provider=provider)

    assert exc_info.value.error_code == "invalid_structured_output"
    assert exc_info.value.validation_branch == expected_branch
    assignment = SignalPatternAssignment.objects.get(signal=signal)
    assert assignment.classification_status == (
        SignalPatternAssignment.ClassificationStatus.PROCESSING
    )
    assert assignment.pattern is None
    log = AIUsageLog.objects.get(ai_domain=AIUsageLog.Domain.ANALYTICS_PATTERN)
    assert log.status == AIUsageLog.Status.FAILED
    assert log.error_code == "invalid_structured_output"
    assert log.error_context["validation_branch"] == expected_branch
    serialized_context = json.dumps(log.error_context, sort_keys=True)
    assert "payload" not in serialized_context
    assert "raw_text" not in serialized_context


def test_canonical_label_can_match_signal_title_when_valid():
    membership = build_membership()
    signal = create_signal_for_membership(membership, title="Clim en panne")
    provider = FakePatternClassifierProvider(payload={"canonical_label": "Clim en panne"})

    assignment = classify_signal_pattern(signal.id, provider=provider)

    assert assignment.classification_status == (
        SignalPatternAssignment.ClassificationStatus.SUCCEEDED
    )
    assert assignment.pattern.label == "Clim en panne"


def test_concurrent_new_pattern_creation_reloads_existing_label_after_integrity_error():
    membership = build_membership()
    signal = create_signal_for_membership(membership)
    existing = create_pattern_for_signal(signal, label="Défaillance climatisation")
    provider = FakePatternClassifierProvider(
        payload={"canonical_label": "défaillance climatisation"}
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


def test_legacy_classifier_shape_is_refused():
    with pytest.raises(PatternClassifierInvalidOutputError) as exc_info:
        parse_pattern_classifier_response(
            {
                "result_type": "existing_pattern",
                "pattern_id": "not-a-uuid",
                "canonical_label": "Label",
            }
        )
    assert exc_info.value.validation_branch == "classifier_response_shape_invalid"


def test_merged_semantic_alias_is_followed_to_active_target_without_duplicate_guard():
    membership = build_membership()
    signal = create_signal_for_membership(membership)
    source = create_pattern_for_signal(signal, label="Climate equipment failure")
    target = create_pattern_for_signal(signal, label="Climate equipment target")
    OperationalPattern.objects.filter(pk=source.pk).update(
        status=OperationalPattern.Status.MERGED,
        merged_into=target,
    )
    provider = FakePatternClassifierProvider(
        payload={"canonical_label": "Climate equipment failure"},
        duplicate_guard_payload={"result_type": "create_new_pattern", "pattern_id": None},
    )

    assignment = classify_signal_pattern(signal.id, provider=provider)

    assert assignment.pattern_id == target.id
    assert provider.duplicate_guard_calls == []


def test_merged_semantic_alias_chain_is_followed_to_terminal_active_target():
    membership = build_membership()
    signal = create_signal_for_membership(membership)
    first = create_pattern_for_signal(signal, label="Climate equipment failure")
    middle = create_pattern_for_signal(signal, label="Climate equipment middle")
    target = create_pattern_for_signal(signal, label="Climate equipment target")
    OperationalPattern.objects.filter(pk=first.pk).update(
        status=OperationalPattern.Status.MERGED,
        merged_into=middle,
    )
    OperationalPattern.objects.filter(pk=middle.pk).update(
        status=OperationalPattern.Status.MERGED,
        merged_into=target,
    )
    provider = FakePatternClassifierProvider(
        payload={"canonical_label": "Climate equipment failure"},
        duplicate_guard_payload={"result_type": "create_new_pattern", "pattern_id": None},
    )

    assignment = classify_signal_pattern(signal.id, provider=provider)

    assert assignment.pattern_id == target.id
    assert provider.duplicate_guard_calls == []


def test_ambiguous_exact_semantic_alias_falls_through_to_duplicate_guard(settings):
    settings.HOUSTON_ANALYTICS_PATTERN_DUPLICATE_GUARD_MIN_SCORE = 0.1
    membership = build_membership()
    signal = create_signal_for_membership(membership)
    first = create_pattern_for_signal(signal, label="Shared first target")
    second = create_pattern_for_signal(signal, label="Shared second target")
    first_alias = create_pattern_for_signal(signal, label="Shared alias one")
    second_alias = create_pattern_for_signal(signal, label="Shared alias two")
    OperationalPattern.objects.filter(pk=first_alias.pk).update(
        status=OperationalPattern.Status.MERGED,
        merged_into=first,
        semantic_label="Shared alias",
        normalized_semantic_label="shared alias",
    )
    OperationalPattern.objects.filter(pk=second_alias.pk).update(
        status=OperationalPattern.Status.MERGED,
        merged_into=second,
        semantic_label="Shared alias",
        normalized_semantic_label="shared alias",
    )
    provider = FakePatternClassifierProvider(
        payload={"canonical_label": "Shared alias"},
        duplicate_guard_payload={
            "result_type": "reuse_existing_pattern",
            "pattern_id": str(second.id),
        },
    )

    assignment = classify_signal_pattern(signal.id, provider=provider)

    assert assignment.pattern_id == second.id
    assert len(provider.duplicate_guard_calls) == 1


def test_owner_split_can_explicitly_recreate_active_alias_after_merge():
    membership = build_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_signal_for_membership(membership)
    source = create_pattern_for_signal(signal, label="Shared alias")
    merged_target = create_pattern_for_signal(signal, label="Merged target")
    OperationalPattern.objects.filter(pk=source.pk).update(
        status=OperationalPattern.Status.MERGED,
        merged_into=merged_target,
    )
    owner_active = create_operational_pattern(
        organization=signal.establishment.organization,
        label="Shared alias restored",
        semantic_label="Shared alias",
        created_by_membership=membership,
    )
    provider = FakePatternClassifierProvider(
        payload={"canonical_label": "Shared alias"},
        duplicate_guard_payload={"result_type": "create_new_pattern", "pattern_id": None},
    )

    assignment = classify_signal_pattern(signal.id, provider=provider)

    assert assignment.pattern_id == owner_active.id
    assert provider.duplicate_guard_calls == []


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
        payload={"canonical_label": pattern.semantic_label}
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
                        content='{"canonical_label":"Défaillance climatisation"}'
                    )
                )
            ],
            usage=SimpleNamespace(prompt_tokens=3, completion_tokens=5, total_tokens=8),
        )
    )
    provider._client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )

    response = provider.classify(input_payload={"signal": {}})

    assert response.payload["canonical_label"] == "Défaillance climatisation"
    assert response.input_tokens == 3
    call_kwargs = create.call_args.kwargs
    assert call_kwargs["response_format"]["type"] == "json_schema"
    assert call_kwargs["response_format"]["json_schema"]["strict"] is True
