"""HTTP access, idempotence, and the desktop contract. Services keep the rules."""

from __future__ import annotations

import time
import uuid
from datetime import date
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.utils import timezone
from rest_framework.test import APIClient

from houston.brain.configuration import admission_configuration
from houston.brain.followups import run_brain_follow_up
from houston.brain.models import (
    BrainAnalysis,
    BrainDossier,
    BrainDossierItem,
    BrainKnowledgeVersion,
    BrainMechanismCandidate,
    BrainMessage,
    BrainObjective,
    BrainObjectiveRevision,
    BrainReporting,
    BrainSlot,
    BrainSuggestion,
    BrainSuggestionRevision,
)
from houston.brain.preview import sign_brain_reporting_preview
from houston.brain.tests.test_admission import _reporting
from houston.establishments.models import EstablishmentMembership
from houston.platform.services import grant_platform_operator
from houston.testing.auth import auth_headers, login
from houston.testing.factories import create_establishment, create_membership, create_user

pytestmark = pytest.mark.django_db

_CSV = (
    "Reporting mars\n"
    "\n"
    "Libellé;CA HT;Commentaire\n"
    "Restaurant;1200;Service lent\n"
).encode()
_DOC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"WordDocument"
_PRIVATE = "PREUVE-PRIVEE-CLIENT-NE-DOIT-PAS-SORTIR"


def _client_for(user) -> tuple[APIClient, dict]:
    client = APIClient()
    token = login(client, user=user)
    return client, auth_headers(token)


def _url(establishment_id, suffix: str) -> str:
    return f"/api/v1/establishments/{establishment_id}/brain/{suffix}"


def test_doc_is_refused_and_a_csv_period_can_be_confirmed_then_launched():
    establishment = create_establishment(name="Brain API", timezone="Europe/Paris")
    owner = create_membership(establishment=establishment, role=EstablishmentMembership.Role.OWNER)
    client, headers = _client_for(owner.user)
    refused = client.post(
        _url(establishment.id, "reportings/"),
        {"file": SimpleUploadedFile("rapport.doc", _DOC, content_type="application/msword")},
        format="multipart",
        **headers,
    )
    assert refused.status_code == 400
    assert refused.json()["code"] == "doc_not_supported"
    assert "DOCX" in refused.json()["detail"]
    assert BrainReporting.objects.filter(establishment=establishment).count() == 0

    created = client.post(
        _url(establishment.id, "reportings/"),
        {"file": SimpleUploadedFile("mars.csv", _CSV, content_type="text/csv")},
        format="multipart",
        **headers,
    )
    assert created.status_code == 201
    reporting = created.json()
    assert reporting["status"] == "ready"
    assert reporting["period_confirmed"] is False
    assert reporting["extraction"]["measure_count"] >= 1
    assert "preview_url" in reporting
    preview = Client().get(reporting["preview_url"])
    assert preview.status_code == 200
    assert preview["Cache-Control"] == "private, no-store"
    assert b"Restaurant" in b"".join(preview.streaming_content)

    confirmed = client.post(
        _url(establishment.id, f"reportings/{reporting['id']}/period/"),
        {"period_start": "2026-03-01", "period_end": "2026-04-01"},
        format="json",
        **headers,
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["period_confirmed"] is True
    changed = client.post(
        _url(establishment.id, f"reportings/{reporting['id']}/period/"),
        {"period_start": "2026-02-01", "period_end": "2026-03-01"},
        format="json",
        **headers,
    )
    assert changed.status_code == 400
    assert changed.json()["code"] == "period_already_confirmed"

    launched = client.post(
        _url(establishment.id, "analyses/"),
        {"reporting_id": reporting["id"], "idempotency_key": "demande-mars"},
        format="json",
        **headers,
    )
    assert launched.status_code == 200
    assert launched.json()["matched"] == "request"
    analysis_id = launched.json()["work"]["id"]
    assert launched.json()["work"]["status"] == "queued"
    replay = client.post(
        _url(establishment.id, "analyses/"),
        {"reporting_id": reporting["id"], "idempotency_key": "demande-mars"},
        format="json",
        **headers,
    )
    assert replay.json()["matched"] == "request"
    assert replay.json()["work"]["id"] == analysis_id
    other = client.post(
        _url(establishment.id, "analyses/"),
        {"reporting_id": reporting["id"], "idempotency_key": "autre-demande"},
        format="json",
        **headers,
    )
    assert other.json()["matched"] == "active"
    assert other.json()["work"]["id"] == analysis_id
    detail = client.get(_url(establishment.id, f"analyses/{analysis_id}/"), **headers)
    assert detail.status_code == 200
    body = detail.json()
    assert body["status"] == "queued"
    assert body["result"] is None
    assert "configuration" not in body
    assert body["failure_message"] == ""


def test_staff_and_another_establishment_cannot_see_the_work_or_the_file():
    establishment = create_establishment(name="Brain privé", timezone="Europe/Paris")
    owner = create_membership(establishment=establishment, role=EstablishmentMembership.Role.OWNER)
    staff = create_membership(establishment=establishment, role=EstablishmentMembership.Role.STAFF)
    outsider = create_membership(
        establishment=create_establishment(name="Autre site"),
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    reporting = _reporting(establishment, owner.user)
    analysis = BrainAnalysis.objects.create(
        establishment=establishment,
        reporting=reporting,
        author=owner.user,
        idempotency_key="privee",
        status=BrainAnalysis.Status.QUEUED,
        configuration=admission_configuration(reporting.extractions.get()),
    )
    owner_client, owner_headers = _client_for(owner.user)
    visible = owner_client.get(
        _url(establishment.id, f"reportings/{reporting.id}/"),
        **owner_headers,
    )
    assert visible.status_code == 200
    preview_url = visible.json()["preview_url"]
    for user in (staff.user, outsider.user):
        client, headers = _client_for(user)
        listing = client.get(_url(establishment.id, "analyses/"), **headers)
        assert listing.status_code == 404
        assert listing.json() == {"detail": "Not found."}
        detail = client.get(_url(establishment.id, f"analyses/{analysis.id}/"), **headers)
        assert detail.status_code == 404
        assert str(analysis.id) not in detail.content.decode()
        same_key = client.post(
            _url(establishment.id, "analyses/"),
            {"reporting_id": str(reporting.id), "idempotency_key": "privee"},
            format="json",
            **headers,
        )
        assert same_key.status_code == 404
        assert "privee" not in same_key.content.decode()
    owner.status = EstablishmentMembership.Status.DEACTIVATED
    owner.save(update_fields=["status"])
    assert Client().get(preview_url).status_code == 404
    wrong = preview_url.replace(str(establishment.id), str(outsider.establishment_id), 1)
    assert Client().get(wrong).status_code == 404


def test_a_new_key_is_refused_when_capacity_is_full(settings):
    settings.HOUSTON_BRAIN_MAX_QUEUED_AND_RUNNING = 1
    first_establishment = create_establishment(name="Brain capacité", timezone="Europe/Paris")
    first_owner = create_membership(
        establishment=first_establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    second_establishment = create_establishment(name="Brain capacité 2", timezone="Europe/Paris")
    second_owner = create_membership(
        establishment=second_establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    first_reporting = _reporting(first_establishment, first_owner.user)
    second_reporting = _reporting(second_establishment, second_owner.user)
    first_client, first_headers = _client_for(first_owner.user)
    second_client, second_headers = _client_for(second_owner.user)
    first = first_client.post(
        _url(first_establishment.id, "analyses/"),
        {"reporting_id": str(first_reporting.id), "idempotency_key": "une"},
        format="json",
        **first_headers,
    )
    assert first.status_code == 200
    second = second_client.post(
        _url(second_establishment.id, "analyses/"),
        {"reporting_id": str(second_reporting.id), "idempotency_key": "deux"},
        format="json",
        **second_headers,
    )
    assert second.status_code == 409
    assert second.json()["code"] == "brain_capacity_unavailable"
    replay = first_client.post(
        _url(first_establishment.id, "analyses/"),
        {"reporting_id": str(first_reporting.id), "idempotency_key": "une"},
        format="json",
        **first_headers,
    )
    assert replay.status_code == 200
    assert replay.json()["work"]["id"] == first.json()["work"]["id"]


def test_follow_up_declaration_is_not_applied_and_reanalysis_stays_unlaunched():
    establishment = create_establishment(name="Brain suivi API", timezone="Europe/Paris")
    owner = create_membership(establishment=establishment, role=EstablishmentMembership.Role.OWNER)
    reporting = _reporting(establishment, owner.user)
    analysis = BrainAnalysis.objects.create(
        establishment=establishment,
        reporting=reporting,
        author=owner.user,
        idempotency_key="terminee",
        status=BrainAnalysis.Status.COMPLETED,
        configuration=admission_configuration(reporting.extractions.get()),
        result={"schema_version": "brain_analysis_v1", "subjects": []},
    )
    dossier = BrainDossier.objects.create(
        analysis=analysis,
        establishment=establishment,
        timezone="Europe/Paris",
        period_start=date(2026, 3, 1),
        period_end=date(2026, 4, 1),
        capture_started_at=timezone.now(),
        closed_at=timezone.now(),
    )
    BrainDossierItem.objects.create(
        dossier=dossier,
        category="document",
        stable_key="piece",
        role="reporting",
        payload={"text": "PREUVE-INTACTE"},
        reason="reporting",
    )
    client, headers = _client_for(owner.user)
    asked = client.post(
        _url(establishment.id, f"analyses/{analysis.id}/messages/"),
        {
            "request_id": "correction-1",
            "purpose": "correction",
            "body": "Le chiffre de mars était 12, pas 10.",
            "cited_item_ids": [],
        },
        format="json",
        **headers,
    )
    assert asked.status_code == 200
    assert asked.json()["matched"] == "request"
    assert asked.json()["work"]["kind"] == "follow_up"
    message = BrainMessage.objects.get(request_id="correction-1")
    run_brain_follow_up(message.id, message.attempt_token)
    detail = client.get(_url(establishment.id, f"analyses/{analysis.id}/"), **headers)
    assert detail.status_code == 200
    body = detail.json()
    assert body["status"] == "completed"
    follow_up = body["messages"][0]
    assert follow_up["declaration"]["applied"] is False
    assert follow_up["result"]["reanalysis"]["launched"] is False
    assert follow_up["result"]["reanalysis"]["linked_analysis_id"] == str(analysis.id)
    assert BrainAnalysis.objects.get(pk=analysis.id).status == BrainAnalysis.Status.COMPLETED
    assert BrainDossierItem.objects.get(dossier=dossier).payload["text"] == "PREUVE-INTACTE"

    again = client.post(
        _url(establishment.id, f"analyses/{analysis.id}/messages/"),
        {
            "request_id": "explication",
            "purpose": "explain",
            "body": "Explique le constat.",
        },
        format="json",
        **headers,
    )
    assert again.status_code == 200
    assert again.json()["matched"] == "request"
    canceled = client.post(
        _url(establishment.id, f"messages/{again.json()['work']['id']}/cancel/"),
        **headers,
    )
    assert canceled.status_code == 200
    assert canceled.json()["status"] == "canceled"
    assert BrainAnalysis.objects.get(pk=analysis.id).status == BrainAnalysis.Status.COMPLETED
    assert not BrainSlot.objects.filter(message_id=again.json()["work"]["id"]).exists()


def test_suggestion_conflict_and_platform_review_do_not_activate_or_leak():
    establishment = create_establishment(name="Brain décisions API", timezone="Europe/Paris")
    owner = create_membership(establishment=establishment, role=EstablishmentMembership.Role.OWNER)
    reporting = _reporting(establishment, owner.user)
    analysis = BrainAnalysis.objects.create(
        establishment=establishment,
        reporting=reporting,
        author=owner.user,
        idempotency_key="suggestions",
        status=BrainAnalysis.Status.COMPLETED,
        configuration=admission_configuration(reporting.extractions.get()),
    )
    suggestion = BrainSuggestion.objects.create(
        establishment=establishment,
        analysis=analysis,
        stable_key="froid",
    )
    revision = BrainSuggestionRevision.objects.create(
        suggestion=suggestion,
        number=1,
        title="Reprendre le froid",
        edited_by=owner.user,
    )
    suggestion.current_revision = revision
    suggestion.save(update_fields=["current_revision", "updated_at"])
    client, headers = _client_for(owner.user)
    revised = client.post(
        _url(establishment.id, f"suggestions/{suggestion.id}/revisions/"),
        {"expected_revision_id": str(revision.id), "title": "Contrôler le groupe froid"},
        format="json",
        **headers,
    )
    assert revised.status_code == 200
    stale = client.post(
        _url(establishment.id, f"suggestions/{suggestion.id}/revisions/"),
        {"expected_revision_id": str(revision.id), "title": "Ancien titre"},
        format="json",
        **headers,
    )
    assert stale.status_code == 400
    assert stale.json()["code"] == "suggestion_revision_conflict"
    kept = BrainSuggestionRevision.objects.filter(suggestion=suggestion, title="Ancien titre")
    assert kept.count() == 0

    candidate = BrainMechanismCandidate.objects.create(
        analysis=analysis,
        establishment=establishment,
        stable_key="salle",
        formulation=_PRIVATE,
        global_formulation="Un effectif trop juste en salle peut dégrader le service du soir.",
        private_evidence=[_PRIVATE],
        global_representation={
            "formulation": "Un effectif trop juste en salle peut dégrader le service du soir.",
            "conditions": "",
            "limits": "",
            "uncertainty": "",
            "withheld": {},
        },
    )
    operator = create_user(username=f"operator_{uuid.uuid4().hex[:8]}")
    grant_platform_operator(user=operator)
    director_client, director_headers = _client_for(owner.user)
    denied = director_client.get("/api/v1/platform/brain/mechanisms/", **director_headers)
    assert denied.status_code == 403
    operator_client, operator_headers = _client_for(operator)
    listed = operator_client.get("/api/v1/platform/brain/mechanisms/", **operator_headers)
    assert listed.status_code == 200
    encoded = listed.content.decode()
    assert _PRIVATE not in encoded
    assert "private_evidence" not in encoded
    assert listed.json()["results"][0]["is_active"] is False
    approved = operator_client.post(
        f"/api/v1/platform/brain/mechanisms/{candidate.id}/decision/",
        {"decision": "approve"},
        format="json",
        **operator_headers,
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert approved.json()["is_active"] is False
    assert _PRIVATE not in approved.content.decode()
    version_id = approved.json()["knowledge_version_id"]
    assert BrainKnowledgeVersion.objects.get(pk=version_id).is_active is False
    activated = operator_client.post(
        f"/api/v1/platform/brain/knowledge/versions/{version_id}/activate/",
        **operator_headers,
    )
    assert activated.status_code == 200
    assert activated.json()["is_active"] is True
    assert BrainKnowledgeVersion.objects.get(pk=version_id).is_active is True


def test_preview_token_rejects_forgery_expiry_substitution_and_lost_rights():
    establishment = create_establishment(name="Brain aperçu", timezone="Europe/Paris")
    owner = create_membership(establishment=establishment, role=EstablishmentMembership.Role.OWNER)
    client, headers = _client_for(owner.user)
    first = client.post(
        _url(establishment.id, "reportings/"),
        {
            "file": SimpleUploadedFile(
                "alpha.csv",
                b"Libelle;CA\nRestaurant;1;ALPHA-FILE\n",
                content_type="text/csv",
            )
        },
        format="multipart",
        **headers,
    )
    second = client.post(
        _url(establishment.id, "reportings/"),
        {
            "file": SimpleUploadedFile(
                "beta.csv",
                b"Libelle;CA\nRestaurant;2;BETA-FILE\n",
                content_type="text/csv",
            )
        },
        format="multipart",
        **headers,
    )
    assert first.status_code == 201
    assert second.status_code == 201
    first_body = first.json()
    second_body = second.json()
    original = Client().get(first_body["preview_url"])
    assert original.status_code == 200
    assert b"ALPHA-FILE" in b"".join(original.streaming_content)

    first_parts = urlsplit(first_body["preview_url"])
    second_parts = urlsplit(second_body["preview_url"])
    first_token = parse_qs(first_parts.query)["token"][0]
    forged = Client().get(f"{first_parts.path}?token=forged")
    assert forged.status_code == 404
    tampered = first_token.replace(first_body["id"], second_body["id"], 1)
    assert Client().get(f"{second_parts.path}?token={tampered}").status_code == 404
    substituted = Client().get(f"{second_parts.path}?token={first_token}")
    assert substituted.status_code == 404
    assert b"BETA-FILE" not in substituted.content
    assert b"ALPHA-FILE" not in substituted.content

    past = time.time() - 400
    with patch("houston.brain.preview.time.time", return_value=past):
        expired = sign_brain_reporting_preview(
            establishment_id=establishment.id,
            reporting_id=uuid.UUID(first_body["id"]),
            user_id=owner.user.id,
        )
    assert Client().get(f"{first_parts.path}?token={expired}").status_code == 404

    owner.status = EstablishmentMembership.Status.DEACTIVATED
    owner.save(update_fields=["status", "updated_at"])
    assert Client().get(first_body["preview_url"]).status_code == 404


def test_another_establishment_url_cannot_read_or_change_private_objects():
    home = create_establishment(name="Brain maison", timezone="Europe/Paris")
    other = create_establishment(name="Brain voisin", timezone="Europe/Paris")
    owner = create_membership(establishment=home, role=EstablishmentMembership.Role.OWNER)
    create_membership(
        establishment=other,
        user=owner.user,
        role=EstablishmentMembership.Role.OWNER,
    )
    reporting = _reporting(other, owner.user)
    analysis = BrainAnalysis.objects.create(
        establishment=other,
        reporting=reporting,
        author=owner.user,
        idempotency_key="voisin",
        status=BrainAnalysis.Status.COMPLETED,
        configuration=admission_configuration(reporting.extractions.get()),
        result={"schema_version": "brain_analysis_v1", "subjects": []},
    )
    dossier = BrainDossier.objects.create(
        analysis=analysis,
        establishment=other,
        timezone="Europe/Paris",
        period_start=date(2026, 3, 1),
        period_end=date(2026, 4, 1),
        capture_started_at=timezone.now(),
        closed_at=timezone.now(),
    )
    item = BrainDossierItem.objects.create(
        dossier=dossier,
        category="document",
        stable_key="preuve",
        role="reporting",
        payload={"text": "MARQUEUR-DOSSIER-VOISIN"},
        reason="reporting",
    )
    suggestion = BrainSuggestion.objects.create(
        establishment=other,
        analysis=analysis,
        stable_key="suggestion-voisin",
    )
    revision = BrainSuggestionRevision.objects.create(
        suggestion=suggestion,
        number=1,
        title="MARQUEUR-SUGGESTION-VOISIN",
        edited_by=owner.user,
    )
    suggestion.current_revision = revision
    suggestion.save(update_fields=["current_revision", "updated_at"])
    objective = BrainObjective.objects.create(establishment=other)
    objective_revision = BrainObjectiveRevision.objects.create(
        objective=objective,
        establishment=other,
        indicator="MARQUEUR-OBJECTIF-VOISIN",
        content_hash="c" * 64,
    )
    objective.current_revision = objective_revision
    objective.save(update_fields=["current_revision", "updated_at"])
    message = BrainMessage.objects.create(
        analysis=analysis,
        author=owner.user,
        request_id="voisin-message",
        sequence=1,
        purpose=BrainMessage.Purpose.EXPLAIN,
        body="MARQUEUR-MESSAGE-VOISIN",
    )
    candidate = BrainMechanismCandidate.objects.create(
        analysis=analysis,
        establishment=other,
        stable_key="mecanisme-voisin",
        formulation="MARQUEUR-MECANISME-VOISIN",
        private_evidence=["MARQUEUR-PREUVE-VOISIN"],
    )
    client, headers = _client_for(owner.user)
    visible = client.get(_url(other.id, f"analyses/{analysis.id}/"), **headers)
    assert visible.status_code == 200
    assert "MARQUEUR-SUGGESTION-VOISIN" in visible.content.decode()

    hidden_paths = [
        f"analyses/{analysis.id}/",
        f"analyses/{analysis.id}/sources/",
        f"dossier-items/{item.id}/",
        f"analyses/{analysis.id}/cancel/",
        f"messages/{message.id}/cancel/",
    ]
    for suffix in hidden_paths:
        method = client.post if suffix.endswith("cancel/") else client.get
        response = method(_url(home.id, suffix), **headers)
        assert response.status_code == 404, suffix
        assert b"MARQUEUR" not in response.content
    revised = client.post(
        _url(home.id, f"suggestions/{suggestion.id}/revisions/"),
        {"expected_revision_id": str(revision.id), "title": "Titre volé"},
        format="json",
        **headers,
    )
    assert revised.status_code == 404
    assert b"MARQUEUR" not in revised.content
    decided = client.post(
        _url(home.id, f"objectives/{objective.id}/decisions/"),
        {
            "expected_revision_id": str(objective_revision.id),
            "decision": "accepted",
        },
        format="json",
        **headers,
    )
    assert decided.status_code == 404
    assert b"MARQUEUR" not in decided.content
    represented = client.post(
        _url(home.id, f"mechanisms/{candidate.id}/representation/"),
        {"formulation": "Texte global neutre"},
        format="json",
        **headers,
    )
    assert represented.status_code == 404
    assert b"MARQUEUR" not in represented.content
    suggestion.refresh_from_db()
    message.refresh_from_db()
    candidate.refresh_from_db()
    objective_revision.refresh_from_db()
    assert suggestion.current_revision_id == revision.id
    assert message.status == BrainMessage.Status.QUEUED
    assert candidate.global_formulation == ""
    assert objective_revision.decision == "recorded"
