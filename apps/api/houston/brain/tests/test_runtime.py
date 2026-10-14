"""Attempt lifecycle with a scripted provider. The provider stays inside the process."""

from __future__ import annotations

import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from django.db import connections
from django.utils import timezone

from houston.ai.models import AIUsageLog
from houston.brain.admission import admit_brain_work
from houston.brain.capture import capture_dossier
from houston.brain.configuration import (
    billed_input_tokens,
    digest,
    estimate_tokens,
    frozen_knowledge,
    provider_fixed_input_tokens,
    selected_knowledge,
)
from houston.brain.contract import (
    CORRECTION_KEY,
    ENGINE_RULES,
    MAX_SUBJECTS,
    SYNTHESIS_KEY,
    analysis_correction_majorant,
    correction_input_majorant,
    intermediate_result,
    minimal_analysis,
    piece_ids_of,
    synthesis_envelope,
    synthesis_input_majorant,
)
from houston.brain.errors import BrainWorkError
from houston.brain.followups import run_brain_follow_up
from houston.brain.lots import plan_lots, sections_from_payload
from houston.brain.models import (
    BrainAnalysis,
    BrainDossier,
    BrainDossierItem,
    BrainExtraction,
    BrainKnowledgeVersion,
    BrainLot,
    BrainSlot,
)
from houston.brain.provider import BrainProviderUnavailable, FakeBrainProvider, ProviderCallResult
from houston.brain.recovery import recover_brain_works
from houston.brain.runtime import (
    _dossier_context,
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
    del lot_key
    return ProviderCallResult(
        output=minimal_analysis(["s0000"]),
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
    bound = _budgeted_envelopes(analysis)
    sent = provider.calls[0]["payload"]
    assert sent == bound[0].payload
    context = _dossier_context(analysis.id)
    assert context is not None
    _dossier, items, _runs = context
    correction = analysis_correction_majorant(
        piece_ids_of(bound),
        items,
        key_slots=MAX_SUBJECTS,
        knowledge=frozen_knowledge(analysis.configuration),
    )
    assert analysis.reserved_input_tokens == (
        billed_input_tokens(estimate_tokens(sent)) + billed_input_tokens(correction)
    )
    assert [call["lot_key"] for call in provider.calls] == [bound[0].stable_key]
    stored_lot = BrainLot.objects.get(analysis=analysis)
    assert stored_lot.input_hash == digest(sent)


def test_absent_provider_usage_counts_as_the_reserved_call(monkeypatch):
    _allow_publish(monkeypatch)
    analysis = _prepare(pytest_settings(), ["Une section courte."])
    provider = ScriptedProvider(
        [
            ProviderCallResult(
                output=minimal_analysis(["s0000"]),
                truncated=False,
                input_tokens=None,
                output_tokens=1,
            )
        ]
    )
    run_brain_analysis(analysis.id, analysis.attempt_token, provider=provider)
    analysis.refresh_from_db()
    lot = BrainLot.objects.get(analysis=analysis)
    assert analysis.consumed_input_tokens == billed_input_tokens(
        estimate_tokens(provider.calls[0]["payload"])
    )
    assert analysis.consumed_input_tokens >= lot.reserved_input_tokens


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


def test_an_envelope_over_the_useful_budget_is_not_sent(monkeypatch):
    _allow_publish(monkeypatch)
    analysis = _prepare(pytest_settings(), ["Service lent en salle."])
    tokens = _budgeted_envelopes(analysis)[0].reserved_input_tokens
    configuration = dict(analysis.configuration)
    ceilings = dict(configuration["ceilings"])
    ceilings["per_call_input_tokens"] = tokens - 1 + provider_fixed_input_tokens()
    configuration["ceilings"] = ceilings
    analysis.configuration = configuration
    analysis.save(update_fields=["configuration", "updated_at"])
    provider = ScriptedProvider([_ok()])
    run_brain_analysis(analysis.id, analysis.attempt_token, provider=provider)
    analysis.refresh_from_db()
    assert provider.calls == []
    assert analysis.status == BrainAnalysis.Status.FAILED
    assert analysis.failure_code == "budget_exceeded"
    assert analysis.reserved_input_tokens == 0
    assert analysis.consumed_input_tokens == 0
    assert analysis.provider_calls_used == 0


def test_rules_that_exceed_the_useful_budget_fail_before_any_call(monkeypatch, settings):
    settings.HOUSTON_BRAIN_PER_CALL_INPUT_TOKENS = (
        provider_fixed_input_tokens() + estimate_tokens(list(ENGINE_RULES)) - 1
    )
    _allow_publish(monkeypatch)
    analysis = _prepare(settings, ["Un."])
    provider = ScriptedProvider([_ok()])
    run_brain_analysis(analysis.id, analysis.attempt_token, provider=provider)
    analysis.refresh_from_db()
    assert provider.calls == []
    assert analysis.status == BrainAnalysis.Status.FAILED
    assert analysis.failure_code == "budget_exceeded"
    assert analysis.reserved_input_tokens == 0


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


def test_validated_lot_is_reused_and_frozen_knowledge_stays_empty(monkeypatch, settings):
    _allow_publish(monkeypatch)
    analysis = _prepare(settings, ["alpha " * 30_000, "bravo " * 30_000])
    from houston.brain.provider import BrainProviderUnavailable

    provider = ScriptedProvider([_ok("one"), BrainProviderUnavailable()])
    run_brain_analysis(analysis.id, analysis.attempt_token, provider=provider)
    analysis.refresh_from_db()
    assert analysis.status == BrainAnalysis.Status.QUEUED
    assert analysis.transient_retries_used == 1
    first_lot = BrainLot.objects.get(analysis=analysis)
    writer = first_lot.attempt_token
    analysis.refresh_from_db()
    assert analysis.configuration["knowledge"]["selection"] == "none"
    assert analysis.configuration["knowledge"]["formulation"] == ""
    second = minimal_analysis(["s0001"])
    second["subjects"][0]["key"] = "suite"
    follow = ScriptedProvider(
        [
            ProviderCallResult(
                output=second,
                truncated=False,
                input_tokens=None,
                output_tokens=1,
            ),
            ProviderCallResult(
                output=_subjects_for(["sujet", "suite"]),
                truncated=False,
                input_tokens=None,
                output_tokens=1,
            ),
        ]
    )
    run_brain_analysis(analysis.id, analysis.attempt_token, provider=follow)
    analysis.refresh_from_db()
    assert analysis.status == BrainAnalysis.Status.COMPLETED
    assert [call["lot_key"] for call in follow.calls] == ["lot-0002", SYNTHESIS_KEY]
    assert first_lot.stable_key not in {call["lot_key"] for call in follow.calls}
    first_lot.refresh_from_db()
    assert first_lot.attempt_token == writer
    assert BrainLot.objects.filter(analysis=analysis).count() == 3
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
    lot = _budgeted_envelopes(analysis)[0]
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


def test_an_unknown_provider_is_refused_before_capture(monkeypatch, settings):
    _allow_publish(monkeypatch)
    settings.OPENAI_API_KEY = "sk-lot4-secret"
    analysis = _prepare(settings, ["Pas de réseau."])
    configuration = dict(analysis.configuration)
    configuration["provider"] = "anthropic"
    analysis.configuration = configuration
    analysis.save(update_fields=["configuration", "updated_at"])
    run_brain_analysis(analysis.id, analysis.attempt_token, provider=None)
    analysis.refresh_from_db()
    assert analysis.status == BrainAnalysis.Status.FAILED
    assert analysis.failure_code == "provider_not_allowed"
    assert analysis.reserved_input_tokens == 0
    assert analysis.consumed_input_tokens == 0
    assert analysis.transient_retries_used == 0
    assert not BrainDossier.objects.filter(analysis=analysis).exists()


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


def _subjects_for(keys: list[str]) -> dict:
    template = minimal_analysis([])["subjects"][0]
    body = minimal_analysis([])
    body["coverage"] = []
    body["subjects"] = []
    body["proposals"] = {"suggestions": [], "mechanisms": []}
    for key in keys:
        subject = dict(template)
        subject["key"] = key
        body["subjects"].append(subject)
    return body


def _keyed_lot(payload: dict) -> dict:
    pieces = list(payload.get("required_piece_ids") or [])
    body = minimal_analysis(pieces)
    if pieces:
        body["subjects"][0]["key"] = pieces[0]
    return body


def _budgeted_envelopes(analysis):
    """Envelopes the attempt estimates and sends, after the dossier is closed."""
    if not BrainDossier.objects.filter(analysis=analysis, closed_at__isnull=False).exists():
        capture_dossier(analysis.id)
    context = _dossier_context(analysis.id)
    assert context is not None
    _dossier, items, runs = context
    ceilings = analysis.configuration["ceilings"]
    knowledge = frozen_knowledge(analysis.configuration)
    return plan_lots(
        sections_from_payload(analysis.reporting.extractions.get().payload),
        per_call_input_tokens=ceilings["per_call_input_tokens"],
        total_input_tokens=ceilings["total_input_tokens"],
        max_calls=ceilings["max_calls"],
        knowledge=knowledge,
        searches=sorted({run.code for run in runs}),
        items=items,
    )


def test_frozen_knowledge_is_sent_and_a_later_edit_does_not_change_it(monkeypatch):
    _allow_publish(monkeypatch)
    monkeypatch.setattr("houston.brain.runtime.publish_brain_follow_up", lambda *_a, **_k: True)
    BrainKnowledgeVersion.objects.create(
        global_formulation="CONNAISSANCE-FIGEE-SERVICE",
        conditions="Plusieurs services.",
        limits="N'explique pas une cause locale.",
        uncertainty="Hypothèse générale.",
        approved_at=timezone.now(),
        is_active=True,
    )
    snapshot = selected_knowledge()
    analysis = _prepare(pytest_settings(), ["Note de service."])
    provider = ScriptedProvider(
        [
            ProviderCallResult(
                output={"schema_version": "brain_analysis_v1"},
                truncated=False,
                input_tokens=1,
                output_tokens=1,
            ),
            ProviderCallResult(
                output=minimal_analysis(["s0000"]),
                truncated=False,
                input_tokens=1,
                output_tokens=1,
            ),
        ]
    )
    run_brain_analysis(analysis.id, analysis.attempt_token, provider=provider)
    analysis.refresh_from_db()
    assert analysis.status == BrainAnalysis.Status.COMPLETED
    assert [call["lot_key"] for call in provider.calls] == ["lot-0001", CORRECTION_KEY]
    assert provider.calls[0]["payload"]["knowledge"] == snapshot
    assert provider.calls[1]["payload"]["knowledge"] == snapshot
    stored = BrainLot.objects.get(analysis=analysis, stable_key="lot-0001")
    assert stored.configuration_hash == digest(analysis.configuration)
    assert stored.input_hash == digest(provider.calls[0]["payload"])
    corrected = BrainLot.objects.get(analysis=analysis, stable_key=CORRECTION_KEY)
    assert corrected.input_hash == digest(provider.calls[1]["payload"])
    assert corrected.configuration_hash == digest(analysis.configuration)
    synthesis = synthesis_envelope(
        [],
        intermediates=[],
        required_subject_keys=[],
        knowledge=snapshot,
    )
    assert synthesis["knowledge"] == snapshot
    version = BrainKnowledgeVersion.objects.get(pk=snapshot["version_id"])
    version.global_formulation = "CONNAISSANCE-REMPLACEE"
    version.is_active = False
    version.save(update_fields=["global_formulation", "is_active", "updated_at"])
    BrainKnowledgeVersion.objects.create(
        global_formulation="AUTRE-VERSION-ACTIVEE",
        approved_at=timezone.now(),
        is_active=True,
    )
    analysis.refresh_from_db()
    assert analysis.configuration["knowledge"] == snapshot
    assert BrainLot.objects.get(pk=stored.id).configuration_hash == stored.configuration_hash
    item = BrainDossierItem.objects.filter(dossier__analysis=analysis).first()

    class _Recording(FakeBrainProvider):
        def __init__(self):
            self.calls = []

        def complete(self, *, analysis_id, lot_key, payload, timeout_seconds):
            self.calls.append(payload)
            return super().complete(
                analysis_id=analysis_id,
                lot_key=lot_key,
                payload=payload,
                timeout_seconds=timeout_seconds,
            )

    follow = _Recording()
    message = admit_brain_work(
        user=analysis.author,
        establishment_id=analysis.establishment_id,
        analysis_id=analysis.id,
        request_id="connaissance",
        body="Que dit le dossier ?",
        purpose="explain",
        cited_item_ids=[str(item.id)],
    )
    run_brain_follow_up(message.id, message.attempt_token, provider=follow)
    message.refresh_from_db()
    assert message.status == message.Status.COMPLETED
    sent = json.dumps(follow.calls[0], ensure_ascii=False)
    assert follow.calls[0]["frozen_configuration"]["knowledge"] == snapshot
    assert "CONNAISSANCE-REMPLACEE" not in sent
    assert "AUTRE-VERSION-ACTIVEE" not in sent


def test_multi_lot_synthesis_counts_frozen_knowledge_in_its_budget(monkeypatch, settings):
    _allow_publish(monkeypatch)
    version = BrainKnowledgeVersion.objects.create(
        global_formulation="CONNAISSANCE-SYNTHESE-FIGEE",
        conditions="Condition explicite figée pour la synthèse.",
        limits="Limite figée pour la synthèse.",
        uncertainty="Incertitude figée pour la synthèse.",
        approved_at=timezone.now(),
        is_active=True,
    )
    snapshot = selected_knowledge()
    analysis = _prepare(settings, ["alpha " * 30_000, "bravo " * 30_000])
    assert analysis.configuration["knowledge"] == snapshot

    class _LotsThenSynthesis:
        def __init__(self):
            self.calls = []

        def complete(self, *, analysis_id, lot_key, payload, timeout_seconds):
            del analysis_id, timeout_seconds
            self.calls.append({"lot_key": lot_key, "payload": payload})
            if len(self.calls) == 1:
                version.global_formulation = "CONNAISSANCE-REMPLACEE-AVANT-SYNTHESE"
                version.conditions = "Conditions remplacées."
                version.limits = "Limites remplacées."
                version.uncertainty = "Incertitude remplacée."
                version.is_active = False
                version.save(
                    update_fields=[
                        "global_formulation",
                        "conditions",
                        "limits",
                        "uncertainty",
                        "is_active",
                        "updated_at",
                    ]
                )
                BrainKnowledgeVersion.objects.create(
                    global_formulation="AUTRE-VERSION-ACTIVEE-POUR-SYNTHESE",
                    conditions="Autre condition vivante.",
                    limits="Autre limite vivante.",
                    uncertainty="Autre incertitude vivante.",
                    approved_at=timezone.now(),
                    is_active=True,
                )
            if lot_key == SYNTHESIS_KEY:
                output = _subjects_for(list(payload["required_subject_keys"]))
            else:
                output = _keyed_lot(payload)
            return ProviderCallResult(
                output=output,
                truncated=False,
                input_tokens=1,
                output_tokens=1,
            )

    provider = _LotsThenSynthesis()
    run_brain_analysis(analysis.id, analysis.attempt_token, provider=provider)
    analysis.refresh_from_db()
    assert analysis.status == BrainAnalysis.Status.COMPLETED
    assert [call["lot_key"] for call in provider.calls] == [
        "lot-0001",
        "lot-0002",
        SYNTHESIS_KEY,
    ]
    synthesis = provider.calls[2]["payload"]
    assert synthesis["knowledge"] == snapshot
    assert "sources" not in synthesis
    sent = json.dumps(synthesis, ensure_ascii=False)
    assert "CONNAISSANCE-REMPLACEE-AVANT-SYNTHESE" not in sent
    assert "AUTRE-VERSION-ACTIVEE-POUR-SYNTHESE" not in sent
    assert "structured_summary" not in sent
    bare = {key: value for key, value in synthesis.items() if key != "knowledge"}
    assert estimate_tokens(synthesis) > estimate_tokens(bare)
    ceilings = analysis.configuration["ceilings"]
    bound = _budgeted_envelopes(analysis)
    assert len(bound) == 2
    pieces = [piece for lot in bound for piece in lot.payload["required_piece_ids"]]
    synthesis_tokens = synthesis_input_majorant(
        pieces,
        key_slots=MAX_SUBJECTS,
        knowledge=snapshot,
        per_call_output_tokens=ceilings["per_call_output_tokens"],
        lot_count=len(bound),
    )
    correction_tokens = correction_input_majorant(
        key_slots=MAX_SUBJECTS,
        knowledge=snapshot,
        per_call_output_tokens=ceilings["per_call_output_tokens"],
    )
    lot_reserved = sum(billed_input_tokens(lot.reserved_input_tokens) for lot in bound)
    assert analysis.reserved_input_tokens == (
        lot_reserved
        + billed_input_tokens(synthesis_tokens)
        + billed_input_tokens(correction_tokens)
    )
    reading_calls = [call for call in provider.calls if call["lot_key"] != SYNTHESIS_KEY]
    assert [call["payload"] for call in reading_calls] == [lot.payload for lot in bound]
    from houston.brain.contract import intermediate_result

    intermediates = []
    keys = []
    for lot in bound:
        piece_ids = list(lot.payload["required_piece_ids"])
        output = _keyed_lot({"required_piece_ids": piece_ids})
        keys.append(piece_ids[0])
        intermediates.append(intermediate_result(lot.stable_key, output, piece_ids))
    expected_synthesis = synthesis_envelope(
        pieces,
        intermediates=intermediates,
        required_subject_keys=keys,
        knowledge=snapshot,
    )
    assert synthesis == expected_synthesis


def test_an_unassigned_document_item_is_refused_before_any_call(monkeypatch):
    _allow_publish(monkeypatch)
    analysis = _prepare(pytest_settings(), ["Une section."])
    capture_dossier(analysis.id)
    dossier = BrainDossier.objects.get(analysis=analysis)
    BrainDossierItem.objects.create(
        dossier=dossier,
        category="document",
        stable_key="document:qualitative:0007",
        role="qualitatif",
        payload={"text": "hors extraction"},
        reason="ecart",
    )
    provider = ScriptedProvider([_ok()])
    run_brain_analysis(analysis.id, analysis.attempt_token, provider=provider)
    analysis.refresh_from_db()
    assert provider.calls == []
    assert analysis.status == BrainAnalysis.Status.FAILED
    assert analysis.failure_code == "partition_incomplete"
    assert analysis.reserved_input_tokens == 0
    assert analysis.consumed_input_tokens == 0
    from houston.brain.selectors import failure_message

    assert "réparti" in failure_message(analysis.failure_code)


def test_a_large_dossier_is_partitioned_under_the_ceilings(monkeypatch):
    _allow_publish(monkeypatch)
    sections = 467
    analysis = _prepare(pytest_settings(), [f"section {index}" for index in range(sections)])
    capture_dossier(analysis.id)
    dossier = BrainDossier.objects.get(analysis=analysis)
    _load_operational_items(dossier)
    provider = _LargeCover()
    run_brain_analysis(analysis.id, analysis.attempt_token, provider=provider)
    analysis.refresh_from_db()
    assert analysis.status == BrainAnalysis.Status.COMPLETED, analysis.failure_code
    bound = _budgeted_envelopes(analysis)
    assigned = []
    for lot in bound:
        for section in lot.payload.get("sections") or []:
            assigned.extend(section.get("item_ids") or [])
        for item in lot.payload.get("items") or []:
            assigned.append(item["stable_key"])
    expected = list(dossier.items.values_list("stable_key", flat=True))
    assert len(assigned) == len(set(assigned))
    assert set(assigned) == set(expected)
    assert len(bound) >= 2
    ceilings = analysis.configuration["ceilings"]
    assert analysis.reserved_input_tokens <= ceilings["total_input_tokens"]
    assert analysis.reserved_input_tokens > 0
    assert len(provider.calls) <= ceilings["max_calls"]
    assert all(lot.reserved_input_tokens <= ceilings["per_call_input_tokens"] for lot in bound)
    synthesis = next(call["payload"] for call in provider.calls if call["lot_key"] == SYNTHESIS_KEY)
    blob = json.dumps(synthesis, ensure_ascii=False)
    assert "sources" not in synthesis
    assert "TITRE-CATALOGUE" not in blob
    assert "SYNTHESE-PUBLIQUE" not in blob
    split = False
    execution_lot = {}
    task_lots: dict[str, set[int]] = {}
    for index, lot in enumerate(bound):
        for item in lot.payload.get("items") or []:
            payload = item["payload"]
            if item["category"] == "execution":
                execution_lot[str(payload["source_id"])] = index
            if item["category"] == "execution_task":
                task_lots.setdefault(str(payload["execution_id"]), set()).add(index)
    for execution_id, lot_index in execution_lot.items():
        others = task_lots.get(execution_id, set()) - {lot_index}
        if not others:
            continue
        split = True
        execution_payload = next(
            item["payload"]
            for item in bound[lot_index].payload["items"]
            if item["category"] == "execution" and item["payload"]["source_id"] == execution_id
        )
        task_payload = next(
            item["payload"]
            for offset in others
            for item in bound[offset].payload["items"]
            if item["category"] == "execution_task"
            and item["payload"]["execution_id"] == execution_id
        )
        assert task_payload["execution_id"] == execution_payload["source_id"]
        break
    assert split
    stored = [entry["piece_id"] for entry in analysis.result["coverage"]]
    union = []
    for lot in BrainLot.objects.filter(analysis=analysis).order_by("stable_key"):
        union.extend(entry["piece_id"] for entry in lot.output["coverage"])
    assert stored == union
    measured = {
        "lots": len(bound),
        "reserved_input_tokens": analysis.reserved_input_tokens,
        "provider_calls": len(provider.calls),
        "items": len(expected),
    }
    print(measured)
    assert measured["lots"] >= 2


class _LargeCover:
    def __init__(self):
        self.calls = []

    def complete(self, *, analysis_id, lot_key, payload, timeout_seconds):
        del analysis_id, timeout_seconds
        self.calls.append({"lot_key": lot_key, "payload": payload})
        if lot_key == SYNTHESIS_KEY:
            output = _subjects_for(list(payload["required_subject_keys"]))
        else:
            output = _keyed_lot(payload)
            if not payload.get("required_piece_ids"):
                output["subjects"][0]["key"] = lot_key
        return ProviderCallResult(
            output=output,
            truncated=False,
            input_tokens=1,
            output_tokens=1,
        )


def _load_operational_items(dossier) -> None:
    signals = 137
    executions = 316
    tasks = 1302
    plans = 20
    fat_tasks = 600
    rows = []
    signal_ids = [f"signal-{index:04d}" for index in range(signals)]
    execution_ids = [f"execution-{index:04d}" for index in range(executions)]
    for index, signal_id in enumerate(signal_ids):
        rows.append(
            BrainDossierItem(
                id=uuid.uuid4(),
                dossier=dossier,
                category="signal",
                stable_key=f"signal:{signal_id}",
                role="chevauchement",
                payload={
                    "source_id": signal_id,
                    "title": f"TITRE-CATALOGUE {index}",
                    "structured_summary": "SYNTHESE-PUBLIQUE",
                },
                reason="chevauchement_periode",
            )
        )
    for index, execution_id in enumerate(execution_ids):
        signal_id = signal_ids[index % signals]
        rows.append(
            BrainDossierItem(
                id=uuid.uuid4(),
                dossier=dossier,
                category="execution",
                stable_key=f"execution:{execution_id}",
                role="chevauchement",
                payload={
                    "source_id": execution_id,
                    "source_signal_id": signal_id,
                    "title": f"Execution {index}",
                },
                reason="chevauchement",
            )
        )
    for index in range(tasks):
        execution_id = execution_ids[0] if index < fat_tasks else execution_ids[index % executions]
        payload = {
            "source_id": f"task-{index:04d}",
            "execution_id": execution_id,
            "task": f"tache {index}",
        }
        if index < fat_tasks:
            payload["note"] = "x" * 700
        rows.append(
            BrainDossierItem(
                id=uuid.uuid4(),
                dossier=dossier,
                category="execution_task",
                stable_key=f"execution-task:{index:04d}",
                role="chevauchement",
                payload=payload,
                reason="chevauchement",
            )
        )
    for index in range(plans):
        signal_id = signal_ids[index]
        rows.append(
            BrainDossierItem(
                id=uuid.uuid4(),
                dossier=dossier,
                category="plan",
                stable_key=f"plan:{index:04d}",
                role="lien_direct",
                payload={
                    "source_id": f"plan-{index:04d}",
                    "source_signal_ids": [signal_id],
                    "execution_ids": [execution_ids[index]],
                    "title": f"Plan {index}",
                },
                reason="lien_direct_signal",
            )
        )
    BrainDossierItem.objects.bulk_create(rows)


def _reading_then(payload, *, output) -> ProviderCallResult:
    del payload
    return ProviderCallResult(
        output=output,
        truncated=False,
        input_tokens=1,
        output_tokens=1,
    )


class _MultiLot:
    """Reading lots, then a synthesis built from the keys those lots declared."""

    def __init__(self, *, fail_at: str | None = None, error: Exception | None = None):
        self.calls = []
        self.fail_at = fail_at
        self.error = error

    def complete(self, *, analysis_id, lot_key, payload, timeout_seconds):
        del analysis_id, timeout_seconds
        self.calls.append({"lot_key": lot_key, "payload": payload})
        if lot_key == self.fail_at:
            raise self.error or BrainProviderUnavailable()
        if lot_key == SYNTHESIS_KEY:
            output = _subjects_for(list(payload["required_subject_keys"]))
        else:
            output = _keyed_lot(payload)
        return _reading_then(payload, output=output)


def _lose_finish_once(monkeypatch):
    import houston.brain.runtime as brain_runtime

    original = brain_runtime._finish
    gate = {"open": True}

    def _crash(*args, **kwargs):
        if gate["open"]:
            gate["open"] = False
            raise RuntimeError("worker lost")
        return original(*args, **kwargs)

    monkeypatch.setattr(brain_runtime, "_finish", _crash)


def _requeue_expired(monkeypatch, analysis) -> uuid.UUID:
    monkeypatch.setattr(
        "houston.brain.recovery.publish_brain_analysis",
        lambda *_args, **_kwargs: True,
    )
    analysis.refresh_from_db()
    original = analysis.attempt_token
    analysis.lease_expires_at = timezone.now() - timedelta(seconds=1)
    analysis.save(update_fields=["lease_expires_at", "updated_at"])
    recover_brain_works()
    analysis.refresh_from_db()
    assert analysis.status == BrainAnalysis.Status.QUEUED
    assert analysis.attempt_token != original
    assert analysis.transient_retries_used == 1
    return original


def test_a_committed_synthesis_is_not_called_again_and_the_old_token_cannot_write(
    monkeypatch, settings
):
    _allow_publish(monkeypatch)
    _lose_finish_once(monkeypatch)
    analysis = _prepare(settings, ["alpha " * 30_000, "bravo " * 30_000])
    provider = _MultiLot()
    with pytest.raises(RuntimeError, match="worker lost"):
        run_brain_analysis(analysis.id, analysis.attempt_token, provider=provider)
    analysis.refresh_from_db()
    assert analysis.status == BrainAnalysis.Status.RUNNING
    synthesis_call = next(call for call in provider.calls if call["lot_key"] == SYNTHESIS_KEY)
    payload = synthesis_call["payload"]
    assert "sources" not in payload
    expected = []
    for call in provider.calls:
        if call["lot_key"] in {SYNTHESIS_KEY, CORRECTION_KEY}:
            continue
        piece_ids = list(call["payload"]["required_piece_ids"])
        lot = BrainLot.objects.get(analysis=analysis, stable_key=call["lot_key"])
        expected.append(intermediate_result(call["lot_key"], lot.output, piece_ids))
    assert payload["intermediates"] == expected
    assert all(item is not None and item["intermediate"] is True for item in expected)
    stored = BrainLot.objects.get(analysis=analysis, stable_key=SYNTHESIS_KEY)
    assert stored.input_hash == digest(payload)
    assert stored.configuration_hash == digest(analysis.configuration)
    reserved = analysis.reserved_input_tokens
    writer = stored.attempt_token
    output = stored.output
    original = _requeue_expired(monkeypatch, analysis)
    assert original == writer
    ceilings = analysis.configuration["ceilings"]
    analysis.provider_calls_used = ceilings["max_calls"]
    analysis.consumed_input_tokens = ceilings["total_input_tokens"]
    analysis.save(update_fields=["provider_calls_used", "consumed_input_tokens", "updated_at"])
    assert write_validated_lot(
        analysis_id=analysis.id,
        attempt_token=original,
        stable_key="lot-stolen",
        input_hash="a" * 64,
        configuration_hash="b" * 64,
        output={"stolen": True},
        reserved_input_tokens=1,
    ) is False
    follow = ScriptedProvider([])
    run_brain_analysis(analysis.id, analysis.attempt_token, provider=follow)
    analysis.refresh_from_db()
    stored.refresh_from_db()
    assert follow.calls == []
    assert analysis.status == BrainAnalysis.Status.COMPLETED
    assert analysis.reserved_input_tokens == reserved
    assert analysis.consumed_input_tokens == ceilings["total_input_tokens"]
    assert analysis.provider_calls_used == ceilings["max_calls"]
    assert stored.output == output
    assert stored.attempt_token == writer
    assert not BrainLot.objects.filter(analysis=analysis, stable_key="lot-stolen").exists()


def test_a_committed_correction_is_not_called_again(monkeypatch):
    _allow_publish(monkeypatch)
    _lose_finish_once(monkeypatch)
    analysis = _prepare(pytest_settings(), ["Salle calme."])

    class _CorrectOnce:
        def __init__(self):
            self.calls = []

        def complete(self, *, analysis_id, lot_key, payload, timeout_seconds):
            del analysis_id, timeout_seconds
            self.calls.append({"lot_key": lot_key, "payload": payload})
            pieces = list(payload.get("required_piece_ids") or [])
            body = minimal_analysis(pieces)
            if len(self.calls) == 1:
                body["subjects"][0]["gaps"] = []
                body["subjects"][0]["evidence"] = [
                    {
                        "item_id": "00000000-0000-0000-0000-000000000099",
                        "locator": {"source_id": "dehors"},
                    }
                ]
            return _reading_then(payload, output=body)

    provider = _CorrectOnce()
    with pytest.raises(RuntimeError, match="worker lost"):
        run_brain_analysis(analysis.id, analysis.attempt_token, provider=provider)
    analysis.refresh_from_db()
    assert [call["lot_key"] for call in provider.calls] == ["lot-0001", CORRECTION_KEY]
    stored = BrainLot.objects.get(analysis=analysis, stable_key=CORRECTION_KEY)
    assert stored.input_hash == digest(provider.calls[1]["payload"])
    assert stored.configuration_hash == digest(analysis.configuration)
    writer = stored.attempt_token
    output = stored.output
    consumed = analysis.consumed_input_tokens
    reserved = analysis.reserved_input_tokens
    _requeue_expired(monkeypatch, analysis)
    follow = ScriptedProvider([])
    run_brain_analysis(analysis.id, analysis.attempt_token, provider=follow)
    analysis.refresh_from_db()
    stored.refresh_from_db()
    assert follow.calls == []
    assert analysis.status == BrainAnalysis.Status.COMPLETED
    assert analysis.consumed_input_tokens == consumed
    assert analysis.reserved_input_tokens == reserved
    assert stored.output == output
    assert stored.attempt_token == writer


def test_a_provider_outage_before_synthesis_commit_does_not_spend_that_call(monkeypatch, settings):
    _allow_publish(monkeypatch)
    analysis = _prepare(settings, ["alpha " * 30_000, "bravo " * 30_000])
    provider = _MultiLot(fail_at=SYNTHESIS_KEY)
    run_brain_analysis(analysis.id, analysis.attempt_token, provider=provider)
    analysis.refresh_from_db()
    assert analysis.status == BrainAnalysis.Status.QUEUED
    assert analysis.transient_retries_used == 1
    assert analysis.failure_code == ""
    assert [call["lot_key"] for call in provider.calls] == ["lot-0001", "lot-0002", SYNTHESIS_KEY]
    assert analysis.consumed_input_tokens == 2
    assert analysis.provider_calls_used == 2
    assert analysis.reserved_input_tokens > analysis.consumed_input_tokens
    assert not BrainLot.objects.filter(analysis=analysis, stable_key=SYNTHESIS_KEY).exists()
    assert BrainLot.objects.filter(analysis=analysis).count() == 2


def test_an_adapter_contract_error_is_terminal_without_a_transient_retry(monkeypatch, settings):
    _allow_publish(monkeypatch)
    analysis = _prepare(settings, ["alpha " * 30_000, "bravo " * 30_000])
    provider = _MultiLot(
        fail_at=SYNTHESIS_KEY,
        error=BrainWorkError(code="provider_not_allowed", message="Contrat refusé."),
    )
    run_brain_analysis(analysis.id, analysis.attempt_token, provider=provider)
    analysis.refresh_from_db()
    assert analysis.status == BrainAnalysis.Status.FAILED
    assert analysis.failure_code == "response_invalid"
    assert analysis.transient_retries_used == 0
    assert analysis.consumed_input_tokens == 2
    assert analysis.provider_calls_used == 2
    assert analysis.reserved_input_tokens > 0
    assert not BrainLot.objects.filter(analysis=analysis, stable_key=SYNTHESIS_KEY).exists()


def test_a_changed_reading_lot_hash_does_not_reuse_synthesis(monkeypatch):
    _allow_publish(monkeypatch)
    analysis = _prepare(pytest_settings(), ["Section unique."])
    bound = _budgeted_envelopes(analysis)
    BrainLot.objects.create(
        analysis=analysis,
        stable_key=bound[0].stable_key,
        input_hash="ab" * 32,
        configuration_hash=digest(analysis.configuration),
        status=BrainLot.Status.VALIDATED,
        output=minimal_analysis(["s0000"]),
        attempt_token=uuid.uuid4(),
        reserved_input_tokens=bound[0].reserved_input_tokens,
    )
    synthesis_output = {"kept": "synthesis"}
    BrainLot.objects.create(
        analysis=analysis,
        stable_key=SYNTHESIS_KEY,
        input_hash="cd" * 32,
        configuration_hash=digest(analysis.configuration),
        status=BrainLot.Status.VALIDATED,
        output=synthesis_output,
        attempt_token=uuid.uuid4(),
        reserved_input_tokens=1,
    )
    provider = ScriptedProvider([_ok()])
    run_brain_analysis(analysis.id, analysis.attempt_token, provider=provider)
    analysis.refresh_from_db()
    assert provider.calls == []
    assert analysis.status == BrainAnalysis.Status.FAILED
    assert analysis.failure_code == "configuration_unusable"
    assert analysis.result is None
    assert analysis.consumed_input_tokens == 0
    stored = BrainLot.objects.get(analysis=analysis, stable_key=SYNTHESIS_KEY)
    assert stored.output == synthesis_output


def test_fixed_call_cost_counts_toward_the_total_before_any_call(monkeypatch):
    _allow_publish(monkeypatch)
    analysis = _prepare(pytest_settings(), ["Service lent en salle."])
    bound = _budgeted_envelopes(analysis)
    context = _dossier_context(analysis.id)
    assert context is not None
    _dossier, items, _runs = context
    correction = analysis_correction_majorant(
        piece_ids_of(bound),
        items,
        key_slots=MAX_SUBJECTS,
        knowledge=frozen_knowledge(analysis.configuration),
    )
    fixed = provider_fixed_input_tokens()
    payload_sum = bound[0].reserved_input_tokens + correction
    configuration = dict(analysis.configuration)
    ceilings = dict(configuration["ceilings"])
    ceilings["total_input_tokens"] = payload_sum + fixed
    configuration["ceilings"] = ceilings
    analysis.configuration = configuration
    analysis.save(update_fields=["configuration", "updated_at"])
    provider = ScriptedProvider([_ok()])
    run_brain_analysis(analysis.id, analysis.attempt_token, provider=provider)
    analysis.refresh_from_db()
    assert provider.calls == []
    assert analysis.status == BrainAnalysis.Status.FAILED
    assert analysis.failure_code == "budget_exceeded"
    assert analysis.reserved_input_tokens == 0
    assert analysis.consumed_input_tokens == 0
    assert analysis.provider_calls_used == 0


def test_a_refused_later_reading_lot_keeps_the_charge_and_the_accepted_lot(
    monkeypatch, settings
):
    _allow_publish(monkeypatch)
    analysis = _prepare(settings, ["alpha " * 30_000, "bravo " * 30_000])

    class _RefuseSecond:
        def __init__(self):
            self.calls = []

        def complete(self, *, analysis_id, lot_key, payload, timeout_seconds):
            del analysis_id, timeout_seconds
            self.calls.append(lot_key)
            if len(self.calls) == 1:
                return _reading_then(payload, output=_keyed_lot(payload))
            refused = minimal_analysis([])
            refused["subjects"][0]["key"] = "manque"
            return ProviderCallResult(
                output=refused,
                truncated=False,
                input_tokens=7,
                output_tokens=1,
            )

    provider = _RefuseSecond()
    run_brain_analysis(analysis.id, analysis.attempt_token, provider=provider)
    analysis.refresh_from_db()
    assert provider.calls == ["lot-0001", "lot-0002"]
    assert analysis.status == BrainAnalysis.Status.FAILED
    assert analysis.failure_code == "insufficient_coverage"
    assert analysis.provider_calls_used == 2
    assert analysis.consumed_input_tokens == 8
    assert list(
        BrainLot.objects.filter(analysis=analysis).values_list("stable_key", flat=True)
    ) == ["lot-0001"]
    assert not BrainLot.objects.filter(analysis=analysis, stable_key=SYNTHESIS_KEY).exists()


def test_a_stored_reading_lot_that_fails_its_contract_is_not_sent_to_synthesis(
    monkeypatch, settings
):
    _allow_publish(monkeypatch)
    analysis = _prepare(settings, ["alpha " * 30_000, "bravo " * 30_000])
    bound = _budgeted_envelopes(analysis)
    assert [lot.stable_key for lot in bound] == ["lot-0001", "lot-0002"]
    pieces = list(bound[0].payload["required_piece_ids"])
    refused = minimal_analysis(pieces)
    refused["subjects"][0]["gaps"] = []
    refused["subjects"][0]["evidence"] = [
        {
            "item_id": "00000000-0000-0000-0000-000000000099",
            "locator": {"source_id": "dehors"},
        }
    ]
    BrainLot.objects.create(
        analysis=analysis,
        stable_key=bound[0].stable_key,
        input_hash=bound[0].input_hash,
        configuration_hash=digest(analysis.configuration),
        status=BrainLot.Status.VALIDATED,
        output=refused,
        attempt_token=uuid.uuid4(),
        reserved_input_tokens=bound[0].reserved_input_tokens,
    )
    provider = _MultiLot()
    run_brain_analysis(analysis.id, analysis.attempt_token, provider=provider)
    analysis.refresh_from_db()
    assert provider.calls == []
    assert analysis.status == BrainAnalysis.Status.FAILED
    assert analysis.failure_code == "invalid_reference"
    assert analysis.consumed_input_tokens == 0
    assert analysis.provider_calls_used == 0
    assert not BrainLot.objects.filter(analysis=analysis, stable_key=SYNTHESIS_KEY).exists()
    assert BrainLot.objects.filter(analysis=analysis, stable_key="lot-0001").exists()


def test_a_reading_lot_is_judged_before_it_is_stored(monkeypatch, settings):
    _allow_publish(monkeypatch)
    import houston.brain.runtime as brain_runtime

    events = []
    real_assess = brain_runtime.assess
    real_create = BrainLot.objects.create

    def assess_spy(output, **kwargs):
        events.append(("assess", tuple(kwargs.get("pieces") or ())))
        return real_assess(output, **kwargs)

    def create_spy(**kwargs):
        events.append(("create", kwargs.get("stable_key")))
        return real_create(**kwargs)

    monkeypatch.setattr(brain_runtime, "assess", assess_spy)
    monkeypatch.setattr(BrainLot.objects, "create", create_spy)
    analysis = _prepare(settings, ["alpha " * 30_000, "bravo " * 30_000])
    provider = _MultiLot()
    run_brain_analysis(analysis.id, analysis.attempt_token, provider=provider)
    analysis.refresh_from_db()
    assert analysis.status == BrainAnalysis.Status.COMPLETED
    for stable_key in ("lot-0001", "lot-0002"):
        created = next(
            index
            for index, event in enumerate(events)
            if event == ("create", stable_key)
        )
        assert any(kind == "assess" for kind, _pieces in events[:created])


def test_a_crash_before_the_reading_lot_commits_does_not_keep_the_charge(monkeypatch, settings):
    _allow_publish(monkeypatch)
    analysis = _prepare(settings, ["alpha " * 30_000, "bravo " * 30_000])
    real_create = BrainLot.objects.create
    gate = {"open": True}

    def create_spy(**kwargs):
        if gate["open"] and kwargs.get("stable_key") == "lot-0001":
            gate["open"] = False
            raise RuntimeError("lost before commit")
        return real_create(**kwargs)

    monkeypatch.setattr(BrainLot.objects, "create", create_spy)
    provider = _MultiLot()
    with pytest.raises(RuntimeError, match="lost before commit"):
        run_brain_analysis(analysis.id, analysis.attempt_token, provider=provider)
    analysis.refresh_from_db()
    assert analysis.status == BrainAnalysis.Status.RUNNING
    assert analysis.consumed_input_tokens == 0
    assert analysis.provider_calls_used == 0
    assert BrainLot.objects.filter(analysis=analysis).count() == 0
    assert [call["lot_key"] for call in provider.calls] == ["lot-0001"]
    _requeue_expired(monkeypatch, analysis)
    follow = _MultiLot()
    run_brain_analysis(analysis.id, analysis.attempt_token, provider=follow)
    analysis.refresh_from_db()
    assert analysis.status == BrainAnalysis.Status.COMPLETED
    assert [call["lot_key"] for call in follow.calls] == ["lot-0001", "lot-0002", SYNTHESIS_KEY]
    assert BrainLot.objects.filter(analysis=analysis, stable_key="lot-0001").exists()
