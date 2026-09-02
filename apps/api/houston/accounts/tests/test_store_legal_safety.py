from __future__ import annotations

import uuid

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from houston.accounts.deletion_services import _anonymize_user
from houston.accounts.legal_constants import CURRENT_AI_CONSENT_VERSION, CURRENT_TERMS_VERSION
from houston.accounts.legal_services import grant_current_legal_defaults
from houston.accounts.models import User
from houston.analytics.classifier import PatternClassifierProviderResponse
from houston.analytics.models import SignalPatternAssignment
from houston.analytics.services import classify_signal_pattern
from houston.chat.exceptions import ChatPermissionError
from houston.chat.services import (
    create_group_conversation,
    create_message,
    create_or_get_dm_conversation,
)
from houston.comments.exceptions import CommentValidationError
from houston.comments.services import create_signal_comment
from houston.establishments.models import ContentReport, EstablishmentMembership
from houston.establishments.report_email import send_content_report_operator_email
from houston.establishments.safety_services import (
    block_membership,
    create_content_report,
)
from houston.observations.services import submit_observation
from houston.signals.models import SignalSourceObservation
from houston.testing.auth import TEST_PASSWORD, auth_headers, build_api_membership, login
from houston.testing.pipeline import create_observation
from houston.testing.taxonomy import create_signal_v3_for_membership, hotel_maintenance_setup

pytestmark = pytest.mark.django_db


def _clear_legal(user: User) -> None:
    user.terms_version = None
    user.terms_accepted_at = None
    user.ai_consent_version = None
    user.ai_processing_consented_at = None
    user.save(
        update_fields=[
            "terms_version",
            "terms_accepted_at",
            "ai_consent_version",
            "ai_processing_consented_at",
            "updated_at",
        ]
    )


def test_submit_observation_requires_terms_then_ai_consent():
    membership = build_api_membership(role=EstablishmentMembership.Role.STAFF)
    _clear_legal(membership.user)
    with pytest.raises(Exception) as exc_info:
        submit_observation(membership=membership, text="A" * 20, temporary_upload_ids=[])
    assert exc_info.value.code == "terms_acceptance_required"

    membership.user.terms_version = CURRENT_TERMS_VERSION
    membership.user.terms_accepted_at = timezone.now()
    membership.user.save(update_fields=["terms_version", "terms_accepted_at", "updated_at"])
    with pytest.raises(Exception) as exc_info:
        submit_observation(membership=membership, text="A" * 20, temporary_upload_ids=[])
    assert exc_info.value.code == "ai_consent_required"


def test_comment_requires_terms_not_ai_consent():
    membership = build_api_membership(role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = hotel_maintenance_setup(membership.establishment)
    signal = create_signal_v3_for_membership(
        membership,
        affected_business_unit=hotel,
        responsible_business_unit=maintenance,
        activity_subject=electricite,
    )
    _clear_legal(membership.user)
    membership.user.ai_consent_version = CURRENT_AI_CONSENT_VERSION
    membership.user.ai_processing_consented_at = timezone.now()
    membership.user.save(
        update_fields=["ai_consent_version", "ai_processing_consented_at", "updated_at"]
    )
    with pytest.raises(Exception) as exc_info:
        create_signal_comment(
            author_membership=membership,
            signal=signal,
            body="Hello team",
        )
    assert exc_info.value.code == "terms_acceptance_required"


def test_block_stops_new_dm_messages_and_mentions_but_keeps_existing_conversation():
    actor = build_api_membership(role=EstablishmentMembership.Role.STAFF)
    actor.establishment.chat_enabled = True
    actor.establishment.save(update_fields=["chat_enabled", "updated_at"])
    target_user = User.objects.create_user(
        username="blocked_peer",
        password=TEST_PASSWORD,
        status=User.Status.ACTIVE,
    )
    grant_current_legal_defaults(user=target_user)
    target = EstablishmentMembership.objects.create(
        user=target_user,
        establishment=actor.establishment,
        role=EstablishmentMembership.Role.STAFF,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    conversation, created = create_or_get_dm_conversation(
        actor_membership=actor,
        target_membership_id=target.id,
    )
    assert created is True
    create_message(
        author_membership=actor,
        establishment_id=actor.establishment_id,
        conversation_id=conversation.id,
        client_message_id=uuid.uuid4(),
        body="hello",
    )
    block_membership(actor_membership=actor, target_membership=target)
    existing, created_again = create_or_get_dm_conversation(
        actor_membership=actor,
        target_membership_id=target.id,
    )
    assert created_again is False
    assert existing.id == conversation.id
    with pytest.raises(ChatPermissionError) as exc_info:
        create_message(
            author_membership=actor,
            establishment_id=actor.establishment_id,
            conversation_id=conversation.id,
            client_message_id=uuid.uuid4(),
            body="still hello",
        )
    assert exc_info.value.code == "membership_blocked"

    hotel, maintenance, electricite = hotel_maintenance_setup(actor.establishment)
    signal = create_signal_v3_for_membership(
        actor,
        affected_business_unit=hotel,
        responsible_business_unit=maintenance,
        activity_subject=electricite,
    )
    with pytest.raises(CommentValidationError):
        create_signal_comment(
            author_membership=actor,
            signal=signal,
            body="ping",
            mentioned_membership_ids=[target.id],
        )


def test_content_report_persists_and_email_skips_without_resend(settings):
    settings.RESEND_API_KEY = ""
    actor = build_api_membership(role=EstablishmentMembership.Role.STAFF)
    target_user = User.objects.create_user(
        username="reported_peer",
        password=TEST_PASSWORD,
        status=User.Status.ACTIVE,
    )
    grant_current_legal_defaults(user=target_user)
    target = EstablishmentMembership.objects.create(
        user=target_user,
        establishment=actor.establishment,
        role=EstablishmentMembership.Role.STAFF,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    report = create_content_report(
        actor_membership=actor,
        content_kind=ContentReport.ContentKind.USER,
        reason="Harassment in DM",
        target_membership_id=target.id,
    )
    assert ContentReport.objects.filter(id=report.id).exists()
    send_content_report_operator_email(report_id=str(report.id))


def test_terms_and_ai_consent_http_roundtrip():
    membership = build_api_membership(role=EstablishmentMembership.Role.STAFF)
    _clear_legal(membership.user)
    client = APIClient()
    token = login(client, user=membership.user)
    headers = auth_headers(token)
    terms = client.post(
        "/api/v1/auth/me/terms/",
        {"version": CURRENT_TERMS_VERSION},
        format="json",
        **headers,
    )
    assert terms.status_code == 200
    assert terms.json()["user"]["needs_terms_acceptance"] is False
    ai = client.post(
        "/api/v1/auth/me/ai-consent/",
        {"version": CURRENT_AI_CONSENT_VERSION},
        format="json",
        **headers,
    )
    assert ai.status_code == 200
    assert ai.json()["user"]["needs_ai_consent"] is False
    withdraw = client.post("/api/v1/auth/me/ai-consent/withdraw/", **headers)
    assert withdraw.status_code == 200
    assert withdraw.json()["user"]["needs_ai_consent"] is True


def test_account_anonymization_clears_legal_fields():
    membership = build_api_membership(role=EstablishmentMembership.Role.STAFF)
    user = membership.user
    assert user.terms_version == CURRENT_TERMS_VERSION
    _anonymize_user(user=user)
    user.refresh_from_db()
    assert user.terms_version is None
    assert user.terms_accepted_at is None
    assert user.ai_consent_version is None
    assert user.ai_processing_consented_at is None


def test_openai_pattern_classifier_skips_without_source_author_ai_consent():
    membership = build_api_membership(role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = hotel_maintenance_setup(membership.establishment)
    signal = create_signal_v3_for_membership(
        membership,
        affected_business_unit=hotel,
        responsible_business_unit=maintenance,
        activity_subject=electricite,
        title="Clim en panne",
        issue_focus="climatisation",
    )
    observation = create_observation(membership=membership)
    SignalSourceObservation.objects.create(
        signal=signal,
        observation=observation,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
    )
    membership.user.ai_consent_version = None
    membership.user.ai_processing_consented_at = None
    membership.user.save(
        update_fields=["ai_consent_version", "ai_processing_consented_at", "updated_at"]
    )

    class RecordingOpenAIProvider:
        provider = "openai"
        model = "test-model"

        def __init__(self):
            self.classify_calls: list[dict] = []

        def classify(self, *, input_payload):
            self.classify_calls.append(input_payload)
            return PatternClassifierProviderResponse(
                payload={"canonical_label": "Climatisation défaillante"},
                model=self.model,
            )

        def assess_duplicate(self, *, input_payload):
            raise AssertionError("duplicate guard must not run without classify")

    provider = RecordingOpenAIProvider()
    skipped = classify_signal_pattern(signal.id, provider=provider)
    assert skipped is None
    assert provider.classify_calls == []

    grant_current_legal_defaults(user=membership.user)
    assigned = classify_signal_pattern(signal.id, provider=provider)
    assert assigned is not None
    assert assigned.classification_status == SignalPatternAssignment.ClassificationStatus.SUCCEEDED
    assert len(provider.classify_calls) == 1
    payload = provider.classify_calls[0]
    assert payload["signal"]["title"] == "Clim en panne"
    assert "structured_summary" in payload["signal"]
    assert "raw_text" not in payload["signal"]


def test_group_chat_and_comment_without_mention_survive_membership_block():
    actor = build_api_membership(role=EstablishmentMembership.Role.DIRECTOR)
    actor.establishment.chat_enabled = True
    actor.establishment.save(update_fields=["chat_enabled", "updated_at"])
    target_user = User.objects.create_user(
        username="blocked_group_peer",
        password=TEST_PASSWORD,
        status=User.Status.ACTIVE,
    )
    grant_current_legal_defaults(user=target_user)
    target = EstablishmentMembership.objects.create(
        user=target_user,
        establishment=actor.establishment,
        role=EstablishmentMembership.Role.STAFF,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    group = create_group_conversation(
        actor_membership=actor,
        title="Service",
        membership_ids=[actor.id, target.id],
    )
    block_membership(actor_membership=actor, target_membership=target)
    sent = create_message(
        author_membership=actor,
        establishment_id=actor.establishment_id,
        conversation_id=group.id,
        client_message_id=uuid.uuid4(),
        body="groupe toujours ok",
    )
    assert sent.message.body == "groupe toujours ok"

    hotel, maintenance, electricite = hotel_maintenance_setup(actor.establishment)
    signal = create_signal_v3_for_membership(
        actor,
        affected_business_unit=hotel,
        responsible_business_unit=maintenance,
        activity_subject=electricite,
    )
    comment = create_signal_comment(
        author_membership=actor,
        signal=signal,
        body="commentaire sans mention",
    )
    assert comment.body == "commentaire sans mention"
