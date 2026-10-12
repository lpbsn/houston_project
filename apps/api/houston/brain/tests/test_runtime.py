"""Attempt lifecycle with a scripted provider. The provider stays inside the process."""

from __future__ import annotations

import json
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from django.db import connections

from houston.ai.models import AIUsageLog
from houston.brain.admission import admit_brain_work
from houston.brain.configuration import digest, estimate_tokens
from houston.brain.lots import plan_lots, sections_from_payload
from houston.brain.models import BrainAnalysis, BrainDossier, BrainExtraction, BrainLot, BrainSlot
from houston.brain.provider import ProviderCallResult
from houston.brain.runtime import (
    claim_analysis,
    request_analysis_cancel,
    run_brain_analysis,
    write_validated_lot,
)
from houston.brain.tests.test_admission import _admit, _reporting
from houston.establishments.models import Establishment, EstablishmentMembership
from houston.testing.factories import create_establishment, create_membership

pytestmark = pytest.mark.django_db(transaction=True)

_PUBLISH = "houston.brain.runtime.publish_brain_analysis"


def _allow_publish(monkeypatch):
    monkeypatch.setattr(_PUBLISH, lambda *args, **kwargs: True)


class ScriptedProvider:
    def __init__(self, results):
        self._results = list(results)
        self.calls = []

    def complete(self, *, analysis_id, lot_key, payload, timeout_seconds):
        del analysis_id, timeout_seconds
        self.calls.append({"lot_key": lot_key, "payload": payload})
        step = self._results.pop(0)
        if isinstance(step, Exception):
            raise step
        return step


def _ok(lot_key: str = "lot") -> ProviderCallResult:
    return ProviderCallResult(
        output={"lot_key": lot_key, "section_markers": ["ok"]},
        truncated=False,
        input_tokens=None,
        output_tokens=1,
    )


def _prepare(settings, texts: list[str], *, per_call: int | None = None, total: int | None = None):
    if per_call is not None:
        settings.HOUSTON_BRAIN_PER_CALL_INPUT_TOKENS = per_call
    if total is not None:
        settings.HOUSTON_BRAIN_TOTAL_INPUT_TOKENS = total
    establishment = create_establishment(name=f"Brain run {uuid.uuid4().hex[:8]}")
    owner = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    reporting = _reporting(establishment, owner.user)
    extraction = reporting.extractions.get()
    extraction.payload = {
        "measures": [],
        "qualitative": [
            {
                "kind": "paragraph",
                "text": text,
                "locator": {"block": index},
            }
            for index, text in enumerate(texts)
        ],
    }
    extraction.save(update_fields=["payload", "updated_at"])
    analysis = _admit(owner.user, establishment, reporting, key=uuid.uuid4().hex)
    return analysis


def test_a_fitting_dossier_completes_and_records_usage(monkeypatch):
    _allow_publish(monkeypatch)
    analysis = _prepare(pytest_settings(), ["Service lent en salle."])
    provider = ScriptedProvider([_ok()])
    run_brain_analysis(analysis.id, analysis.attempt_token, provider=provider)
    analysis.refresh_from_db()
    assert analysis.status == BrainAnalysis.Status.COMPLETED
    assert analysis.failure_code == ""
    assert BrainDossier.objects.get(analysis=analysis).closed_at is not None
    assert BrainLot.objects.filter(analysis=analysis, status=BrainLot.Status.VALIDATED).count() == 1
    assert not BrainSlot.objects.filter(analysis=analysis).exists()
    log = AIUsageLog.objects.get(correlation_id=analysis.id)
    assert log.ai_domain == AIUsageLog.Domain.BRAIN_ANALYSIS
    assert log.provider == "fake"
    assert log.observation_id is None
    body = json.dumps(provider.calls[0]["payload"])
    assert "Service lent en salle." in body
    assert "storage_key" not in body


def test_absent_provider_usage_counts_as_the_reserved_call(monkeypatch):
    _allow_publish(monkeypatch)
    analysis = _prepare(pytest_settings(), ["Une section courte."])
    provider = ScriptedProvider(
        [
            ProviderCallResult(
                output={"lot_key": "lot-0001"},
                truncated=False,
                input_tokens=None,
                output_tokens=1,
            )
        ]
    )
    run_brain_analysis(analysis.id, analysis.attempt_token, provider=provider)
    analysis.refresh_from_db()
    lot = BrainLot.objects.get(analysis=analysis)
    assert analysis.consumed_input_tokens == lot.reserved_input_tokens
    assert analysis.consumed_input_tokens > 0


def test_truncated_output_is_not_a_validated_lot(monkeypatch):
    _allow_publish(monkeypatch)
    analysis = _prepare(pytest_settings(), ["Section."])
    provider = ScriptedProvider(
        [
            ProviderCallResult(
                output={"lot_key": "lot-0001"},
                truncated=True,
                input_tokens=1,
                output_tokens=1,
            )
        ]
    )
    run_brain_analysis(analysis.id, analysis.attempt_token, provider=provider)
    analysis.refresh_from_db()
    assert analysis.status == BrainAnalysis.Status.FAILED
    assert analysis.failure_code == "provider_output_rejected"
    assert BrainLot.objects.filter(analysis=analysis).count() == 0


def test_empty_extraction_does_not_complete(monkeypatch):
    _allow_publish(monkeypatch)
    analysis = _prepare(pytest_settings(), [])
    extraction = BrainExtraction.objects.get(reporting=analysis.reporting)
    extraction.payload = {"measures": [], "qualitative": []}
    extraction.save(update_fields=["payload", "updated_at"])
    provider = ScriptedProvider([])
    run_brain_analysis(analysis.id, analysis.attempt_token, provider=provider)
    analysis.refresh_from_db()
    assert analysis.status == BrainAnalysis.Status.FAILED
    assert analysis.failure_code == "empty_document"
    assert provider.calls == []


def test_validated_lot_is_reused_after_a_knowledge_setting_change(monkeypatch, settings):
    _allow_publish(monkeypatch)
    first, _both = _two_section_ceilings()
    settings.HOUSTON_BRAIN_PER_CALL_INPUT_TOKENS = first
    settings.HOUSTON_BRAIN_TOTAL_INPUT_TOKENS = first * 4
    settings.HOUSTON_BRAIN_MAX_CALLS = 4
    analysis = _prepare(settings, ["alpha " * 40, "bravo " * 40], per_call=first, total=first * 4)
    from houston.brain.provider import BrainProviderUnavailable

    provider = ScriptedProvider([_ok("one"), BrainProviderUnavailable()])
    run_brain_analysis(analysis.id, analysis.attempt_token, provider=provider)
    analysis.refresh_from_db()
    assert analysis.status == BrainAnalysis.Status.QUEUED
    assert analysis.transient_retries_used == 1
    first_lot = BrainLot.objects.get(analysis=analysis)
    writer = first_lot.attempt_token
    settings.HOUSTON_BRAIN_KNOWLEDGE_VERSION = "knowledge-activated"
    analysis.refresh_from_db()
    assert analysis.configuration["knowledge_version"] is None
    follow = ScriptedProvider([_ok("two")])
    run_brain_analysis(analysis.id, analysis.attempt_token, provider=follow)
    analysis.refresh_from_db()
    assert analysis.status == BrainAnalysis.Status.COMPLETED
    assert len(follow.calls) == 1
    assert follow.calls[0]["lot_key"] != first_lot.stable_key
    first_lot.refresh_from_db()
    assert first_lot.attempt_token == writer
    assert BrainLot.objects.filter(analysis=analysis).count() == 2
    assert write_validated_lot(
        analysis_id=analysis.id,
        attempt_token=writer,
        stable_key="lot-9999",
        input_hash="a" * 64,
        configuration_hash="b" * 64,
        output={"changed": True},
        reserved_input_tokens=1,
    ) is False


def test_input_hash_and_configuration_hash_are_compared_separately(monkeypatch):
    _allow_publish(monkeypatch)
    analysis = _prepare(pytest_settings(), ["Section unique."])
    sections = sections_from_payload(analysis.reporting.extractions.get().payload)
    ceilings = analysis.configuration["ceilings"]
    planned = plan_lots(
        sections,
        per_call_input_tokens=ceilings["per_call_input_tokens"],
        total_input_tokens=ceilings["total_input_tokens"],
        max_calls=ceilings["max_calls"],
    )
    lot = planned[0]
    BrainLot.objects.create(
        analysis=analysis,
        stable_key=lot.stable_key,
        input_hash=lot.input_hash,
        configuration_hash="c" * 64,
        status=BrainLot.Status.VALIDATED,
        output={"kept": True},
        attempt_token=uuid.uuid4(),
        reserved_input_tokens=lot.reserved_input_tokens,
    )
    provider = ScriptedProvider([_ok()])
    run_brain_analysis(analysis.id, analysis.attempt_token, provider=provider)
    analysis.refresh_from_db()
    assert provider.calls == []
    assert analysis.status == BrainAnalysis.Status.FAILED
    assert analysis.failure_code == "configuration_unusable"
    stored = BrainLot.objects.get(analysis=analysis)
    assert stored.output == {"kept": True}
    assert stored.configuration_hash == "c" * 64
    assert digest(analysis.configuration) != stored.configuration_hash


@pytest.mark.django_db(transaction=True)
def test_two_workers_cannot_both_claim_the_same_token(monkeypatch):
    _allow_publish(monkeypatch)
    analysis = _prepare(pytest_settings(), ["Course de claim."])

    def claim(_):
        try:
            return claim_analysis(analysis.id, str(analysis.attempt_token))
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(claim, (1, 2)))
    assert results.count(True) == 1
    analysis.refresh_from_db()
    assert analysis.status == BrainAnalysis.Status.RUNNING
    assert analysis.attempt_count == 1


def test_cancel_and_finalize_leave_one_terminal_state(monkeypatch):
    _allow_publish(monkeypatch)
    analysis = _prepare(pytest_settings(), ["Annulation."])
    assert claim_analysis(analysis.id, analysis.attempt_token) is True
    assert request_analysis_cancel(analysis.id) == BrainAnalysis.Status.CANCELED
    from houston.brain.runtime import _complete

    assert _complete(analysis.id, analysis.attempt_token) is False
    analysis.refresh_from_db()
    assert analysis.status == BrainAnalysis.Status.CANCELED
    assert not BrainSlot.objects.filter(analysis=analysis).exists()

    other = _prepare(pytest_settings(), ["Finalisation."])
    assert claim_analysis(other.id, other.attempt_token) is True
    assert _complete(other.id, other.attempt_token) is True
    assert request_analysis_cancel(other.id) == BrainAnalysis.Status.COMPLETED
    other.refresh_from_db()
    assert other.status == BrainAnalysis.Status.COMPLETED


def test_lost_rights_cancel_before_the_provider_call(monkeypatch):
    _allow_publish(monkeypatch)
    analysis = _prepare(pytest_settings(), ["Droits."])
    Establishment.objects.filter(id=analysis.establishment_id).update(
        status=Establishment.Status.DEACTIVATED
    )
    provider = ScriptedProvider([_ok()])
    run_brain_analysis(analysis.id, analysis.attempt_token, provider=provider)
    analysis.refresh_from_db()
    assert analysis.status == BrainAnalysis.Status.CANCELED
    assert analysis.failure_code == "author_rights_lost"
    assert provider.calls == []
    assert not BrainSlot.objects.filter(analysis=analysis).exists()


def test_a_non_fake_provider_is_not_called(monkeypatch):
    _allow_publish(monkeypatch)
    analysis = _prepare(pytest_settings(), ["Pas de réseau."])
    configuration = dict(analysis.configuration)
    configuration["provider"] = "openai"
    analysis.configuration = configuration
    analysis.save(update_fields=["configuration", "updated_at"])
    provider = ScriptedProvider([_ok()])
    run_brain_analysis(analysis.id, analysis.attempt_token, provider=None)
    analysis.refresh_from_db()
    assert analysis.status == BrainAnalysis.Status.FAILED
    assert analysis.failure_code == "provider_not_allowed"
    assert provider.calls == []


def test_admission_publishes_only_a_new_analysis(monkeypatch):
    published = []

    def _publish(analysis_id, attempt_token):
        published.append((analysis_id, str(attempt_token)))
        return True

    monkeypatch.setattr("houston.brain.runtime.publish_brain_analysis", _publish)
    establishment = create_establishment(name="Brain publish")
    owner = create_membership(establishment=establishment, role=EstablishmentMembership.Role.OWNER)
    reporting = _reporting(establishment, owner.user)
    first = admit_brain_work(
        user=owner.user,
        establishment_id=establishment.id,
        reporting_id=reporting.id,
        idempotency_key="meme",
    )
    again = admit_brain_work(
        user=owner.user,
        establishment_id=establishment.id,
        reporting_id=reporting.id,
        idempotency_key="meme",
    )
    assert again.id == first.id
    assert published == [(first.id, str(first.attempt_token))]


def pytest_settings():
    from django.conf import settings

    return settings


def _two_section_ceilings() -> tuple[int, int]:
    one = {"kind": "paragraph", "text": "alpha " * 40, "locator": {"block": 0}}
    two = {"kind": "paragraph", "text": "bravo " * 40, "locator": {"block": 1}}
    single = estimate_tokens({"sections": [one]})
    both = estimate_tokens({"sections": [one, two]})
    per_call = max(single, both - 1)
    assert estimate_tokens({"sections": [one]}) <= per_call
    assert estimate_tokens({"sections": [one, two]}) > per_call
    return per_call, both
