"""Follow-ups stay on the closed dossier and on the same admission, slot, and token."""

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
from houston.brain.configuration import admission_configuration
from houston.brain.contract import minimal_analysis
from houston.brain.errors import BrainAccessDenied, BrainCapacityUnavailable, BrainWorkError
from houston.brain.followups import run_brain_follow_up, write_follow_up_lot
from houston.brain.models import (
    BrainAnalysis,
    BrainDossier,
    BrainDossierItem,
    BrainLot,
    BrainMessage,
    BrainSlot,
)
from houston.brain.provider import FakeBrainProvider
from houston.brain.recovery import recover_brain_works
from houston.brain.runtime import claim_message
from houston.brain.tests.test_admission import _admit, _reporting
from houston.establishments.models import Establishment, EstablishmentMembership
from houston.testing.factories import create_establishment, create_membership

pytestmark = pytest.mark.django_db


def _silence_publish(monkeypatch):
    monkeypatch.setattr(
        "houston.brain.runtime.publish_brain_follow_up",
        lambda *args, **kwargs: True,
    )
    monkeypatch.setattr(
        "houston.brain.runtime.publish_brain_analysis",
        lambda *args, **kwargs: True,
    )
    monkeypatch.setattr(
        "houston.brain.recovery.publish_brain_follow_up",
        lambda *args, **kwargs: True,
    )
    monkeypatch.setattr(
        "houston.brain.recovery.publish_brain_analysis",
        lambda *args, **kwargs: True,
    )


def _completed(*, knowledge: str = "k-figee"):
    establishment = create_establishment(name=f"Brain suivi {uuid.uuid4().hex[:8]}")
    owner = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    reporting = _reporting(establishment, owner.user)
    extraction = reporting.extractions.get()
    analysis = BrainAnalysis.objects.create(
        establishment=establishment,
        reporting=reporting,
        author=owner.user,
        idempotency_key=f"analyse-{uuid.uuid4().hex[:8]}",
        status=BrainAnalysis.Status.COMPLETED,
        configuration=admission_configuration(extraction),
        result=minimal_analysis(["s0000"]),
    )
    configuration = dict(analysis.configuration)
    configuration["knowledge_version"] = knowledge
    analysis.configuration = configuration
    analysis.save(update_fields=["configuration", "updated_at"])
    dossier = BrainDossier.objects.create(
        analysis=analysis,
        establishment=establishment,
        timezone="Europe/Paris",
        period_start=reporting.period_start,
        period_end=reporting.period_end,
        capture_started_at=timezone.now(),
        closed_at=timezone.now(),
    )
    item = BrainDossierItem.objects.create(
        dossier=dossier,
        category="document",
        stable_key="piece-figee",
        role="reporting",
        payload={"text": "PREUVE-INTACTE-SALLE"},
        reason="reporting",
    )
    return establishment, owner, analysis, item


def _ask(owner, analysis, request_id, purpose="explain", body="Explique le constat.", cited=None):
    return admit_brain_work(
        user=owner.user,
        establishment_id=analysis.establishment_id,
        analysis_id=analysis.id,
        request_id=request_id,
        body=body,
        purpose=purpose,
        cited_item_ids=cited,
    )


def _run(message, provider=None):
    run_brain_follow_up(message.id, message.attempt_token, provider=provider)


def _snapshot(analysis):
    analysis.refresh_from_db()
    items = list(
        BrainDossierItem.objects.filter(dossier__analysis=analysis).values_list(
            "id",
            "payload",
            "stable_key",
        )
    )
    return {
        "status": analysis.status,
        "result": analysis.result,
        "calls": analysis.provider_calls_used,
        "consumed": analysis.consumed_input_tokens,
        "items": items,
        "analyses": BrainAnalysis.objects.filter(
            establishment_id=analysis.establishment_id
        ).count(),
    }


class RecordingProvider(FakeBrainProvider):
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


def test_explanation_and_hypothesis_use_the_frozen_dossier(settings):
    settings.HOUSTON_BRAIN_KNOWLEDGE_VERSION = "k-vivant"
    establishment, owner, analysis, item = _completed()
    extraction = analysis.reporting.extractions.get()
    extraction.payload = {"measures": [], "qualitative": [{"text": "FORBIDDEN_LIVE"}]}
    extraction.save(update_fields=["payload", "updated_at"])
    before = _snapshot(analysis)
    provider = RecordingProvider()
    message = _ask(owner, analysis, "explique", cited=[str(item.id)])
    _run(message, provider)
    message.refresh_from_db()
    analysis.refresh_from_db()
    assert message.status == BrainMessage.Status.COMPLETED
    assert message.result["mode"] == "explanation"
    assert message.result["hypothesis_label"] is None
    assert message.result["reanalysis"] is None
    assert message.result["citations"] == [{"item_id": str(item.id)}]
    assert message.provider_calls_used == 1
    body = json.dumps(provider.calls[0], ensure_ascii=False)
    assert "PREUVE-INTACTE-SALLE" in body
    assert "FORBIDDEN_LIVE" not in body
    assert provider.calls[0]["frozen_configuration"]["knowledge_version"] == "k-figee"
    assert "k-vivant" not in body
    slot_free = _ask(
        owner,
        analysis,
        "hypothese",
        purpose="hypothesis",
        body="Et si la salle avait fermé plus tôt ?",
        cited=[str(item.id)],
    )
    _run(slot_free, provider)
    slot_free.refresh_from_db()
    assert slot_free.sequence == 2
    assert slot_free.status == BrainMessage.Status.COMPLETED
    assert slot_free.result["mode"] == "hypothesis"
    assert slot_free.result["hypothesis_label"] == "Hypothèse"
    assert _snapshot(analysis) == before
    log = AIUsageLog.objects.get(correlation_id=message.id)
    assert log.ai_domain == AIUsageLog.Domain.BRAIN_FOLLOW_UP
    assert log.establishment_id == establishment.id


def test_same_request_is_returned_before_a_capacity_refusal(settings):
    settings.HOUSTON_BRAIN_MAX_QUEUED_AND_RUNNING = 1
    _establishment, owner, analysis, _item = _completed()
    other = create_establishment(name="Brain suivi autre")
    other_owner = create_membership(
        establishment=other,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    other_reporting = _reporting(other, other_owner.user)
    first = _ask(owner, analysis, "meme-demande")
    assert _ask(owner, analysis, "meme-demande").id == first.id
    with pytest.raises(BrainCapacityUnavailable):
        _admit(other_owner.user, other, other_reporting, key="ailleurs")
    active = _ask(owner, analysis, "autre-demande", body="Une autre question.")
    assert active.id == first.id
    assert BrainMessage.objects.filter(analysis=analysis).count() == 1
    provider = RecordingProvider()
    _run(first, provider)
    first.refresh_from_db()
    assert first.status == BrainMessage.Status.COMPLETED
    assert not BrainSlot.objects.filter(establishment_id=analysis.establishment_id).exists()
    _admit(other_owner.user, other, other_reporting, key="occupe")
    assert _ask(owner, analysis, "meme-demande").id == first.id
    with pytest.raises(BrainCapacityUnavailable):
        _ask(owner, analysis, "troisieme", body="Encore.")
    assert BrainMessage.objects.filter(analysis=analysis).count() == 1


def test_a_queued_analysis_is_returned_instead_of_a_follow_up():
    establishment = create_establishment(name="Brain slot suivi")
    owner = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    reporting = _reporting(establishment, owner.user)
    queued = _admit(owner.user, establishment, reporting, key="analyse-active")
    refused = admit_brain_work(
        user=owner.user,
        establishment_id=establishment.id,
        analysis_id=queued.id,
        request_id="trop-tot",
        body="Déjà en cours.",
        purpose="explain",
    )
    assert refused.id == queued.id
    assert isinstance(refused, BrainAnalysis)
    assert BrainMessage.objects.count() == 0


def test_follow_up_slot_blocks_a_second_analysis():
    _establishment, owner, analysis, item = _completed()
    message = _ask(owner, analysis, "en-cours", cited=[str(item.id)])
    again = _admit(owner.user, analysis.establishment, analysis.reporting, key="nouvelle-analyse")
    assert again.id == message.id
    assert BrainAnalysis.objects.filter(establishment=analysis.establishment).count() == 1
    assert BrainSlot.objects.get().kind == BrainSlot.Kind.FOLLOW_UP


def test_access_is_denied_without_revealing_the_follow_up():
    establishment, owner, analysis, _item = _completed()
    staff = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    outsider_home = create_establishment(name="Brain suivi exterieur")
    outsider = create_membership(
        establishment=outsider_home,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    _ask(owner, analysis, "prive")
    for user in (staff.user, outsider.user):
        with pytest.raises(BrainAccessDenied):
            admit_brain_work(
                user=user,
                establishment_id=establishment.id,
                analysis_id=analysis.id,
                request_id="prive",
                body="Explique.",
                purpose="explain",
            )
    with pytest.raises(BrainWorkError) as missing:
        admit_brain_work(
            user=outsider.user,
            establishment_id=outsider_home.id,
            analysis_id=analysis.id,
            request_id="prive",
            body="Explique.",
            purpose="explain",
        )
    assert missing.value.code == "follow_up_unavailable"
    assert BrainMessage.objects.count() == 1


def test_failed_analysis_has_no_follow_up():
    _establishment, owner, analysis, _item = _completed()
    analysis.status = BrainAnalysis.Status.FAILED
    analysis.save(update_fields=["status", "updated_at"])
    with pytest.raises(BrainWorkError) as refused:
        _ask(owner, analysis, "trop-tard")
    assert refused.value.code == "follow_up_unavailable"
    assert BrainMessage.objects.count() == 0


@pytest.mark.django_db(transaction=True)
def test_concurrent_follow_ups_insert_one_message(monkeypatch):
    _silence_publish(monkeypatch)
    _establishment, owner, analysis, _item = _completed()

    def ask(request_id):
        try:
            work = _ask(owner, analysis, request_id, body=request_id)
            return work.id
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(ask, ("course-a", "course-b")))
    assert results[0] == results[1]
    assert BrainMessage.objects.filter(analysis=analysis).count() == 1
    assert BrainSlot.objects.filter(establishment=analysis.establishment).count() == 1


@pytest.mark.django_db(transaction=True)
def test_two_claims_of_one_follow_up_token_succeed_once(monkeypatch):
    _silence_publish(monkeypatch)
    _establishment, owner, analysis, _item = _completed()
    message = _ask(owner, analysis, "claim")

    def claim(_):
        try:
            return claim_message(message.id, str(message.attempt_token))
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(claim, (1, 2)))
    assert results.count(True) == 1
    message.refresh_from_db()
    assert message.status == BrainMessage.Status.RUNNING
    assert message.attempt_count == 1
    analysis.refresh_from_db()
    assert analysis.status == BrainAnalysis.Status.COMPLETED


def test_long_conversation_keeps_required_evidence_and_orders_turns(settings):
    settings.HOUSTON_BRAIN_FOLLOW_UP_TOTAL_INPUT_TOKENS = 1
    settings.HOUSTON_BRAIN_PER_CALL_INPUT_TOKENS = 1
    _establishment, owner, analysis, item = _completed()
    item.payload = {"text": "PREUVE-INTACTE-" + ("preuve-" * 30)}
    item.save(update_fields=["payload", "updated_at"])
    proof = item.payload["text"]
    for index in range(1, 7):
        declaration = None
        if index == 1:
            declaration = {
                "kind": "correction",
                "text": "CORRECTION-A-GARDER",
                "applied": False,
            }
        BrainMessage.objects.create(
            analysis=analysis,
            author=owner.user,
            request_id=f"ancien-{index}",
            sequence=index,
            purpose=BrainMessage.Purpose.EXPLAIN,
            body=f"TOUR-{index}-" + ("x" * 12000),
            status=BrainMessage.Status.COMPLETED,
            declaration=declaration,
            result={"answer": f"reponse-{index}"},
        )
    configuration = dict(analysis.configuration)
    configuration["ceilings"] = dict(configuration["ceilings"])
    configuration["ceilings"]["follow_up_total_input_tokens"] = 4000
    configuration["ceilings"]["per_call_input_tokens"] = 4000
    analysis.configuration = configuration
    analysis.save(update_fields=["configuration", "updated_at"])
    provider = RecordingProvider()
    message = _ask(owner, analysis, "longue", cited=[str(item.id)])
    assert message.sequence == 7
    _run(message, provider)
    message.refresh_from_db()
    assert message.status == BrainMessage.Status.COMPLETED, message.failure_code
    payload = provider.calls[0]
    stored = payload["required_items"][0]["payload"]["text"]
    assert stored == proof
    summary = payload["history"]["summary"]
    assert summary["derived"] is True
    assert 1 in summary["covers_sequences"]
    full = [view["sequence"] for view in payload["history"]["messages"]]
    assert full == sorted(full)
    assert set(full).isdisjoint(summary["covers_sequences"])
    if full:
        assert max(summary["covers_sequences"]) < min(full)
    assert payload["declarations"] == [
        {
            "sequence": 1,
            "kind": "correction",
            "text": "CORRECTION-A-GARDER",
            "applied": False,
        }
    ]
    assert message.result["context"]["derived_summary"] is True
    assert "TOUR-1-" not in json.dumps(payload["history"]["messages"])
    analysis.refresh_from_db()
    assert analysis.status == BrainAnalysis.Status.COMPLETED


def test_a_reference_outside_the_dossier_proposes_reanalysis_without_launch():
    _establishment, owner, analysis, item = _completed()
    before = _snapshot(analysis)
    outside = str(uuid.uuid4())
    provider = RecordingProvider()
    message = _ask(owner, analysis, "dehors", cited=[outside, str(item.id)])
    _run(message, provider)
    message.refresh_from_db()
    assert provider.calls == []
    assert message.status == BrainMessage.Status.COMPLETED
    assert message.result["mode"] == "reanalysis_proposed"
    assert message.result["reanalysis"]["launched"] is False
    assert message.result["reanalysis"]["linked_analysis_id"] == str(analysis.id)
    assert outside in message.result["unknown_item_ids"]
    assert message.declaration is None
    assert _snapshot(analysis) == before
    assert BrainDossierItem.objects.get(id=item.id).payload["text"] == "PREUVE-INTACTE-SALLE"


def test_exhausted_budget_fails_the_message_and_leaves_the_analysis(settings):
    settings.HOUSTON_BRAIN_FOLLOW_UP_TOTAL_INPUT_TOKENS = 80_000
    settings.HOUSTON_BRAIN_PER_CALL_INPUT_TOKENS = 80_000
    _establishment, owner, analysis, item = _completed()
    configuration = dict(analysis.configuration)
    configuration["ceilings"] = dict(configuration["ceilings"])
    configuration["ceilings"]["follow_up_total_input_tokens"] = 1
    analysis.configuration = configuration
    analysis.save(update_fields=["configuration", "updated_at"])
    before = _snapshot(analysis)
    provider = RecordingProvider()
    message = _ask(owner, analysis, "budget", cited=[str(item.id)])
    _run(message, provider)
    message.refresh_from_db()
    assert provider.calls == []
    assert message.status == BrainMessage.Status.FAILED
    assert message.failure_code == "budget_exceeded"
    assert message.result["reanalysis"]["launched"] is False
    assert message.result["reanalysis"]["linked_analysis_id"] == str(analysis.id)
    assert message.provider_calls_used == 0
    assert _snapshot(analysis) == before
    assert not BrainSlot.objects.filter(message=message).exists()


def test_expired_token_cannot_write_and_the_validated_lot_is_reread(monkeypatch):
    _silence_publish(monkeypatch)
    _establishment, owner, analysis, item = _completed()
    section = BrainLot.objects.create(
        analysis=analysis,
        stable_key="lot-0001",
        input_hash="a" * 64,
        configuration_hash="b" * 64,
        status=BrainLot.Status.VALIDATED,
        output={"kept": True},
        attempt_token=analysis.attempt_token,
        reserved_input_tokens=2,
    )
    provider = RecordingProvider()
    message = _ask(owner, analysis, "reprise", cited=[str(item.id)])
    _run(message, provider)
    message.refresh_from_db()
    assert message.status == BrainMessage.Status.COMPLETED
    assert len(provider.calls) == 1
    original = message.attempt_token
    lot = BrainLot.objects.get(analysis=analysis, stable_key=f"fu-{message.id}")
    assert lot.attempt_token == original
    now = timezone.now()
    message.status = BrainMessage.Status.RUNNING
    message.claimed_at = now - timedelta(seconds=300)
    message.lease_expires_at = now - timedelta(seconds=1)
    message.transient_retries_used = 0
    message.save()
    BrainSlot.objects.create(
        establishment_id=analysis.establishment_id,
        analysis=analysis,
        message=message,
        kind=BrainSlot.Kind.FOLLOW_UP,
        status=BrainSlot.Status.RUNNING,
        token=original,
    )
    before = _snapshot(analysis)
    recover_brain_works(now=now)
    message.refresh_from_db()
    analysis.refresh_from_db()
    assert message.status == BrainMessage.Status.QUEUED
    assert message.attempt_token != original
    assert message.transient_retries_used == 1
    assert analysis.status == BrainAnalysis.Status.COMPLETED
    assert write_follow_up_lot(
        message_id=message.id,
        attempt_token=original,
        stable_key="fu-stolen",
        input_hash="c" * 64,
        configuration_hash="d" * 64,
        output={"stolen": True},
        reserved_input_tokens=1,
    ) is False
    lot.refresh_from_db()
    assert lot.output["schema_version"] == "brain_follow_up_v1"
    assert lot.attempt_token == original
    assert BrainLot.objects.filter(stable_key="fu-stolen").count() == 0
    _run(message, provider)
    message.refresh_from_db()
    section.refresh_from_db()
    assert len(provider.calls) == 1
    assert message.status == BrainMessage.Status.COMPLETED
    assert message.provider_calls_used == 1
    assert section.output == {"kept": True}
    assert _snapshot(analysis) == before


def test_provider_unavailable_requeues_the_follow_up_only(monkeypatch):
    _silence_publish(monkeypatch)
    monkeypatch.setenv("HOUSTON_BRAIN_FAKE_MODE", "unavailable")
    _establishment, owner, analysis, item = _completed()
    before = _snapshot(analysis)
    message = _ask(owner, analysis, "coupure", cited=[str(item.id)])
    original = message.attempt_token
    _run(message)
    message.refresh_from_db()
    analysis.refresh_from_db()
    assert message.status == BrainMessage.Status.QUEUED
    assert message.attempt_token != original
    assert message.transient_retries_used == 1
    assert analysis.status == BrainAnalysis.Status.COMPLETED
    assert _snapshot(analysis) == before


def test_lost_rights_cancel_the_follow_up_only():
    _establishment, owner, analysis, item = _completed()
    before = _snapshot(analysis)
    message = _ask(owner, analysis, "revoque", cited=[str(item.id)])
    Establishment.objects.filter(id=analysis.establishment_id).update(
        status=Establishment.Status.DEACTIVATED
    )
    provider = RecordingProvider()
    _run(message, provider)
    message.refresh_from_db()
    assert provider.calls == []
    assert message.status == BrainMessage.Status.CANCELED
    assert message.failure_code == "author_rights_lost"
    assert not BrainSlot.objects.filter(message=message).exists()
    assert _snapshot(analysis) == before


def test_correction_fact_and_document_do_not_launch_or_edit_the_dossier():
    _establishment, owner, analysis, item = _completed()
    before = _snapshot(analysis)
    provider = RecordingProvider()
    cases = (
        ("correction", "correction", "Le chiffre de mars était 12, pas 10."),
        ("new_fact", "new_fact", "Un incident de cuisine a eu lieu le 3 mars."),
        ("new_document", "new_document", "Nouveau fichier mars-corrige.csv"),
    )
    for request_id, purpose, body in cases:
        message = _ask(owner, analysis, request_id, purpose=purpose, body=body)
        _run(message, provider)
        message.refresh_from_db()
        assert message.status == BrainMessage.Status.COMPLETED
        assert message.declaration["applied"] is False
        assert message.declaration["text"] == body
        assert message.result["mode"] == "reanalysis_proposed"
        assert message.result["reanalysis"]["launched"] is False
        assert message.result["reanalysis"]["linked_analysis_id"] == str(analysis.id)
        assert message.result["reanalysis"]["reason"] == purpose
        expects_file = purpose in {"correction", "new_document"}
        assert message.result["reanalysis"]["requires_new_reporting"] is expects_file
        assert "suggestion" not in message.result
    assert provider.calls == []
    assert _snapshot(analysis) == before
    assert BrainDossierItem.objects.get(id=item.id).payload == {"text": "PREUVE-INTACTE-SALLE"}


def test_unusable_configuration_proposes_reanalysis_without_replacing_it(settings):
    settings.HOUSTON_BRAIN_KNOWLEDGE_VERSION = "k-remplace"
    settings.HOUSTON_BRAIN_FOLLOW_UP_MAX_CALLS = 4
    _establishment, owner, analysis, _item = _completed()
    configuration = dict(analysis.configuration)
    ceilings = dict(configuration["ceilings"])
    ceilings.pop("follow_up_max_calls")
    configuration["ceilings"] = ceilings
    analysis.configuration = configuration
    analysis.save(update_fields=["configuration", "updated_at"])
    before = _snapshot(analysis)
    provider = RecordingProvider()
    message = _ask(owner, analysis, "config")
    _run(message, provider)
    message.refresh_from_db()
    analysis.refresh_from_db()
    assert provider.calls == []
    assert message.status == BrainMessage.Status.FAILED
    assert message.failure_code == "configuration_unusable"
    assert message.result["reanalysis"]["launched"] is False
    assert analysis.configuration["knowledge_version"] == "k-figee"
    assert "follow_up_max_calls" not in analysis.configuration["ceilings"]
    assert _snapshot(analysis) == before


def test_model_output_cannot_publish_a_decision_or_an_unknown_source(monkeypatch):
    _establishment, owner, analysis, item = _completed()
    before = _snapshot(analysis)
    cited = [str(item.id)]
    monkeypatch.setenv("HOUSTON_BRAIN_FAKE_MODE", "unknown_citation")
    unknown = _ask(owner, analysis, "citation", cited=cited)
    _run(unknown)
    unknown.refresh_from_db()
    assert unknown.status == BrainMessage.Status.FAILED
    assert unknown.failure_code == "unknown_reference"
    assert unknown.result is None
    assert BrainLot.objects.filter(stable_key=f"fu-{unknown.id}").count() == 0

    monkeypatch.setenv("HOUSTON_BRAIN_FAKE_MODE", "decision_object")
    decision = _ask(owner, analysis, "decision", cited=cited)
    _run(decision)
    decision.refresh_from_db()
    assert decision.status == BrainMessage.Status.FAILED
    assert decision.failure_code == "response_invalid"
    assert decision.result is None

    monkeypatch.setenv("HOUSTON_BRAIN_FAKE_MODE", "unlabeled_hypothesis")
    unlabeled = _ask(
        owner,
        analysis,
        "sans-etiquette",
        purpose="hypothesis",
        body="Et si ?",
        cited=cited,
    )
    _run(unlabeled)
    unlabeled.refresh_from_db()
    assert unlabeled.status == BrainMessage.Status.FAILED
    assert unlabeled.failure_code == "response_invalid"
    assert _snapshot(analysis) == before


def test_follow_up_transport_loss_does_not_change_the_completed_analysis(monkeypatch, settings):
    _silence_publish(monkeypatch)
    settings.HOUSTON_BRAIN_TRANSPORT_STALL_SECONDS = 120
    settings.HOUSTON_BRAIN_TRANSPORT_REPUBLISH_MAX = 5
    settings.HOUSTON_BRAIN_WORKER_BEAT_STALE_SECONDS = 1_000
    _establishment, owner, analysis, _item = _completed()
    before = _snapshot(analysis)
    message = _ask(owner, analysis, "transport")
    start = timezone.now()
    message.transport_republish_count = 5
    message.transport_stall_since = start - timedelta(seconds=120)
    message.save(update_fields=["transport_republish_count", "transport_stall_since", "updated_at"])
    from houston.brain.models import BrainWorkerBeat

    BrainWorkerBeat.objects.update_or_create(
        process_name="follow-up-child",
        defaults={"beat_at": start, "concurrency": 1, "in_flight": 0},
    )
    recover_brain_works(now=start)
    message.refresh_from_db()
    assert message.status == BrainMessage.Status.FAILED
    assert message.failure_code == "transport_lost"
    assert message.transient_retries_used == 0
    assert not BrainSlot.objects.filter(message=message).exists()
    assert _snapshot(analysis) == before
