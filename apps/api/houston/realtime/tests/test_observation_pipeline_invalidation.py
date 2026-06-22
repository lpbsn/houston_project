from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from django.db import transaction
from django.utils import timezone
from houston.ai.observation_pipeline import FakeObservationPipelineProvider
from houston.ai.observation_pipeline_schema import (
    ObservationPipelineOutput,
    PipelineCandidateOutput,
)
from houston.realtime.ws_payloads import build_invalidate_payload
from houston.signals.constants import AI_OBSERVATION_PIPELINE_SCHEMA_VERSION
from houston.signals.models import Signal
from houston.signals.services import apply_pipeline_output, run_observation_pipeline
from houston.signals.tests.conftest import create_observation
from houston.signals.tests.test_legacy_issue_focus_aggregation import (
    _mojito_candidate,
    _setup_bar_taxonomy,
)
from houston.signals.tests.test_pipeline_validation import (
    _fake_provider_payload,
    _setup_hotel_taxonomy,
)
from houston.testing.factories import build_membership

pytestmark = pytest.mark.django_db(transaction=True)

ALLOWED_PAYLOAD_KEYS = frozenset(
    {
        "type",
        "subject_type",
        "reason",
        "establishment_id",
        "entity_id",
        "occurred_at",
    }
)

FORBIDDEN_PAYLOAD_KEYS = frozenset(
    {
        "title",
        "structured_summary",
        "body",
        "raw_text",
        "location_text",
        "issue_focus",
    }
)


def _count_notify_calls(mock_notify, *, reason: str) -> int:
    return sum(
        1 for call in mock_notify.call_args_list if call.kwargs.get("reason") == reason
    )


def _assert_invalidate_payload_allowlist(
    *,
    subject_type: str,
    reason: str,
    establishment_id: uuid.UUID,
    entity_id: uuid.UUID,
) -> None:
    payload = build_invalidate_payload(
        subject_type=subject_type,
        reason=reason,
        establishment_id=establishment_id,
        entity_id=entity_id,
    )
    assert set(payload.keys()) == ALLOWED_PAYLOAD_KEYS
    assert not FORBIDDEN_PAYLOAD_KEYS & set(payload.keys())


def test_run_observation_pipeline_emits_signal_created_after_commit():
    membership = build_membership()
    _setup_hotel_taxonomy(membership.establishment)
    observation = create_observation(membership=membership)

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        run_observation_pipeline(observation.id, provider=FakeObservationPipelineProvider())

        signal = Signal.objects.get(establishment=membership.establishment)
        assert _count_notify_calls(mock_notify, reason="signal.created") == 1
        mock_notify.assert_called_with(
            establishment_id=signal.establishment_id,
            subject_type="signal",
            reason="signal.created",
            entity_id=signal.id,
        )


def test_apply_pipeline_output_aggregate_emits_signal_updated():
    membership = build_membership()
    bar = _setup_bar_taxonomy(membership.establishment)
    subject = bar.activity_subjects.get()
    existing = Signal.objects.create(
        establishment=membership.establishment,
        affected_business_unit=bar,
        responsible_business_unit=bar,
        activity_subject=subject,
        title="Rupture sirop mojito",
        structured_summary="Sirop mojito manquant.",
        issue_focus="sirop mojito",
        last_activity_at=timezone.now(),
    )
    observation = create_observation(membership=membership)

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        apply_pipeline_output(
            observation=observation,
            output=ObservationPipelineOutput(
                schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
                candidates=[_mojito_candidate()],
            ),
        )

        assert _count_notify_calls(mock_notify, reason="signal.updated") == 1
        mock_notify.assert_called_with(
            establishment_id=existing.establishment_id,
            subject_type="signal",
            reason="signal.updated",
            entity_id=existing.id,
        )


def test_apply_pipeline_output_rollback_does_not_emit_invalidation():
    membership = build_membership()
    _setup_hotel_taxonomy(membership.establishment)
    observation = create_observation(membership=membership)
    output = ObservationPipelineOutput(
        schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        candidates=[
            PipelineCandidateOutput(
                title="Clim en panne",
                structured_summary="La climatisation ne fonctionne plus.",
                issue_focus="climatisation",
                affected_business_unit_key="hotel",
                responsible_business_unit_key="hotel",
                activity_subject_key="maintenance",
                operational_unit_key=None,
                location_text=None,
                aggregate_into_signal_id=None,
            )
        ],
    )

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        with pytest.raises(RuntimeError, match="force rollback"):
            with transaction.atomic():
                apply_pipeline_output(observation=observation, output=output)
                raise RuntimeError("force rollback")

        mock_notify.assert_not_called()


@pytest.mark.parametrize(
    ("reason",),
    [
        ("signal.created",),
        ("signal.updated",),
    ],
)
def test_signal_invalidate_payload_allowlist(reason: str):
    establishment_id = uuid.uuid4()
    entity_id = uuid.uuid4()
    _assert_invalidate_payload_allowlist(
        subject_type="signal",
        reason=reason,
        establishment_id=establishment_id,
        entity_id=entity_id,
    )


def test_run_observation_pipeline_payload_does_not_leak_observation_text():
    membership = build_membership()
    _setup_hotel_taxonomy(membership.establishment)
    sensitive_text = "Sensitive observation body must not leak"
    observation = create_observation(membership=membership, text=sensitive_text)
    provider = FakeObservationPipelineProvider(payload=_fake_provider_payload())

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        run_observation_pipeline(observation.id, provider=provider)

        for call in mock_notify.call_args_list:
            serialized = str(call.kwargs)
            assert sensitive_text not in serialized
            assert "structured_summary" not in call.kwargs
