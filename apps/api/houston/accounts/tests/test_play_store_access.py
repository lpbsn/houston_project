from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from houston.accounts.deletion_services import _anonymize_user
from houston.accounts.models import PlayStoreAccessRequest
from houston.accounts.play_store_access import (
    PLAY_CLOSED_TESTING_INSTALL_URL,
    PLAY_CLOSED_TESTING_JOIN_URL,
    SUBJECT_CORRECTION,
    SUBJECT_RETRANSMISSION,
    PlayStoreAccessNotAccepted,
    PlayStoreAccessSuperseded,
    PlayStoreAccessUnavailable,
    submit_play_store_access,
)
from houston.establishments.models import Establishment
from houston.establishments.resend_client import (
    InvitationEmailPermanentError,
    InvitationEmailTemporaryError,
)
from houston.establishments.tests.membership_api_helpers import (
    auth_headers,
    create_membership,
    create_user,
    login,
)

pytestmark = pytest.mark.django_db

OPERATOR_EMAIL = "operator@example.com"
FROM_EMAIL = "Spore <invitation@example.com>"
SPORE_EMAIL = "spore.user@example.com"
PLAY_EMAIL = "play.user@example.com"


@pytest.fixture(autouse=True)
def play_delivery_settings(settings):
    settings.RESEND_API_KEY = "re_test_key"
    settings.HOUSTON_OPERATOR_EMAIL = OPERATOR_EMAIL
    settings.HOUSTON_INVITATION_EMAIL_FROM = FROM_EMAIL


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


def _accepting_send(calls):
    def send(**kwargs):
        calls.append(kwargs)

    return send


def _failing_send(calls, error):
    def send(**kwargs):
        calls.append(kwargs)
        raise error

    return send


def _user(email=SPORE_EMAIL):
    return create_user(username=f"play-{email.split('@')[0]}", email=email)


def _submit(user, email, *, establishment_id=None, session=None, send):
    return submit_play_store_access(
        user=user,
        google_play_email=email,
        establishment_id=establishment_id,
        session=session,
        send=send,
    )


def test_uncertain_retry_keeps_the_frozen_payload_and_key(settings):
    user = _user()
    membership = create_membership(user=user, name="Hôtel des Mésanges")
    calls = []
    error = InvitationEmailPermanentError("invalid_idempotent_request")
    with pytest.raises(PlayStoreAccessNotAccepted):
        _submit(
            user,
            PLAY_EMAIL,
            establishment_id=membership.establishment_id,
            send=_failing_send(calls, error),
        )

    record = PlayStoreAccessRequest.objects.get(user=user)
    frozen_key = record.idempotency_key
    assert record.provider_accepted_at is None
    assert record.is_address_correction is False
    assert record.mail_subject != SUBJECT_CORRECTION

    user.email = "changed.spore@example.com"
    user.save(update_fields=["email", "updated_at"])
    settings.HOUSTON_OPERATOR_EMAIL = "other-operator@example.com"
    settings.HOUSTON_INVITATION_EMAIL_FROM = "Spore <other@example.com>"

    with pytest.raises(PlayStoreAccessNotAccepted):
        _submit(
            user,
            PLAY_EMAIL.upper(),
            establishment_id=membership.establishment_id,
            send=_failing_send(calls, InvitationEmailTemporaryError("timeout")),
        )

    record.refresh_from_db()
    assert record.idempotency_key == frozen_key
    assert record.provider_accepted_at is None
    assert record.mail_to == OPERATOR_EMAIL
    assert len(calls) == 2
    for field in ("to_email", "from_email", "subject", "html_body", "text_body", "idempotency_key"):
        assert calls[0][field] == calls[1][field]
    assert calls[0]["to_email"] == OPERATOR_EMAIL
    assert calls[0]["from_email"] == FROM_EMAIL
    assert calls[0]["idempotency_key"] == str(frozen_key)
    assert "changed.spore@example.com" not in calls[1]["text_body"]
    assert "other-operator@example.com" not in calls[1]["text_body"]


def test_late_success_of_a_replaced_key_does_not_change_the_current_request():
    user = _user()
    membership = create_membership(user=user, name="Hôtel des Mésanges")
    calls = []

    def send(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            _submit(
                user,
                "second.play@example.com",
                establishment_id=membership.establishment_id,
                send=_accepting_send(calls),
            )

    with pytest.raises(PlayStoreAccessSuperseded):
        _submit(
            user,
            PLAY_EMAIL,
            establishment_id=membership.establishment_id,
            send=send,
        )

    record = PlayStoreAccessRequest.objects.get(user=user)
    assert record.google_play_email == "second.play@example.com"
    assert record.provider_accepted_at is not None
    assert str(record.idempotency_key) != calls[0]["idempotency_key"]
    assert PLAY_EMAIL not in record.mail_subject
    assert PLAY_EMAIL not in record.mail_html
    assert PLAY_EMAIL not in record.mail_text
    assert PlayStoreAccessRequest.objects.filter(user=user).count() == 1


def test_late_failure_does_not_write_the_replaced_request():
    user = _user()
    membership = create_membership(user=user, name="Hôtel des Mésanges")

    def send(**kwargs):
        with pytest.raises(PlayStoreAccessNotAccepted):
            _submit(
                user,
                "second.play@example.com",
                establishment_id=membership.establishment_id,
                send=_failing_send([], InvitationEmailTemporaryError("timeout")),
            )
        raise InvitationEmailTemporaryError("late")

    with pytest.raises(PlayStoreAccessNotAccepted):
        _submit(
            user,
            PLAY_EMAIL,
            establishment_id=membership.establishment_id,
            send=send,
        )

    record = PlayStoreAccessRequest.objects.get(user=user)
    assert record.google_play_email == "second.play@example.com"
    assert record.provider_accepted_at is None
    assert PLAY_EMAIL not in record.mail_text
    assert record.is_address_correction is True


def test_replay_of_the_current_key_stays_one_accepted_row():
    user = _user()
    membership = create_membership(user=user, name="Hôtel des Mésanges")
    calls = []

    def send(**kwargs):
        calls.append(kwargs["idempotency_key"])
        if len(calls) == 1:
            _submit(
                user,
                PLAY_EMAIL,
                establishment_id=membership.establishment_id,
                send=lambda **inner: calls.append(inner["idempotency_key"]),
            )

    record = _submit(
        user,
        PLAY_EMAIL,
        establishment_id=membership.establishment_id,
        send=send,
    )
    assert calls[0] == calls[1]
    assert record.provider_accepted_at is not None
    assert PlayStoreAccessRequest.objects.filter(user=user).count() == 1

    again = _submit(
        user,
        PLAY_EMAIL,
        establishment_id=membership.establishment_id,
        send=lambda **kwargs: calls.append("unexpected"),
    )
    assert again.provider_accepted_at is not None
    assert "unexpected" not in calls


def test_same_address_after_24_hours_allocates_a_new_transmission_key():
    user = _user()
    membership = create_membership(user=user, name="Hôtel des Mésanges")
    calls = []
    clock = {"now": timezone.now()}

    def fake_now():
        return clock["now"]

    with patch("houston.accounts.play_store_access.timezone.now", side_effect=fake_now):
        with pytest.raises(PlayStoreAccessNotAccepted):
            _submit(
                user,
                PLAY_EMAIL,
                establishment_id=membership.establishment_id,
                send=_failing_send(calls, InvitationEmailTemporaryError("timeout")),
            )
        assert len(calls) == 1
        clock["now"] = clock["now"] + timedelta(hours=24)
        assert len(calls) == 1
        _submit(
            user,
            PLAY_EMAIL,
            establishment_id=membership.establishment_id,
            send=_accepting_send(calls),
        )

    record = PlayStoreAccessRequest.objects.get(user=user)
    assert len(calls) == 2
    assert calls[0]["idempotency_key"] != calls[1]["idempotency_key"]
    assert str(record.idempotency_key) != calls[0]["idempotency_key"]
    assert record.mail_subject == SUBJECT_RETRANSMISSION
    assert record.is_address_correction is False
    assert "Correction" not in record.mail_subject
    assert "remplace la précédente" not in record.mail_text
    assert "pas été confirmée" in record.mail_text
    assert record.provider_accepted_at is not None


def test_address_correction_replaces_the_previous_request_without_the_old_address():
    user = _user()
    membership = create_membership(user=user, name="Hôtel des Mésanges")
    calls = []
    with pytest.raises(PlayStoreAccessNotAccepted):
        _submit(
            user,
            "previous.play@example.com",
            establishment_id=membership.establishment_id,
            send=_failing_send(calls, InvitationEmailTemporaryError("timeout")),
        )
    pending = PlayStoreAccessRequest.objects.get(user=user)
    assert pending.provider_accepted_at is None

    _submit(
        user,
        "second.play@example.com",
        establishment_id=membership.establishment_id,
        send=_accepting_send(calls),
    )

    record = PlayStoreAccessRequest.objects.get(user=user)
    assert record.is_address_correction is True
    assert record.mail_subject == SUBJECT_CORRECTION
    assert record.mail_text.count("Hôtel des Mésanges") == 1
    assert record.mail_html.count("Hôtel des Mésanges") == 1
    assert "second.play@example.com" in record.mail_text
    assert "previous.play@example.com" not in record.mail_subject
    assert "previous.play@example.com" not in record.mail_html
    assert "previous.play@example.com" not in record.mail_text
    assert "Cette demande remplace la précédente pour le même compte SPORE." in record.mail_text


def test_first_request_is_not_a_correction_and_emails_only_the_operator():
    user = _user()
    membership = create_membership(user=user, name="Hôtel des Mésanges")
    calls = []
    _submit(
        user,
        PLAY_EMAIL,
        establishment_id=membership.establishment_id,
        send=_accepting_send(calls),
    )

    record = PlayStoreAccessRequest.objects.get(user=user)
    assert record.is_address_correction is False
    assert "Correction" not in record.mail_subject
    assert "remplace la précédente" not in record.mail_text
    assert calls[0]["to_email"] == OPERATOR_EMAIL
    assert calls[0]["to_email"] != user.email
    assert SPORE_EMAIL in record.mail_text
    assert PLAY_CLOSED_TESTING_JOIN_URL in record.mail_text
    assert PLAY_CLOSED_TESTING_INSTALL_URL in record.mail_text
    assert PLAY_CLOSED_TESTING_JOIN_URL in record.mail_html
    assert PLAY_CLOSED_TESTING_INSTALL_URL in record.mail_html
    assert "même compte Google" in record.mail_text
    assert user.email not in calls[0]["to_email"]


def test_missing_operator_or_api_key_does_not_accept(settings):
    user = _user()
    create_membership(user=user, name="Hôtel des Mésanges")
    settings.HOUSTON_OPERATOR_EMAIL = ""
    with pytest.raises(PlayStoreAccessUnavailable):
        _submit(user, PLAY_EMAIL, send=_accepting_send([]))
    assert not PlayStoreAccessRequest.objects.filter(user=user).exists()

    settings.HOUSTON_OPERATOR_EMAIL = OPERATOR_EMAIL
    settings.RESEND_API_KEY = ""
    with pytest.raises(PlayStoreAccessUnavailable):
        _submit(user, PLAY_EMAIL, send=_accepting_send([]))
    assert not PlayStoreAccessRequest.objects.filter(user=user).exists()


def test_establishment_name_uses_the_verified_membership_or_is_omitted():
    user = _user()
    first = create_membership(
        user=user,
        name="Hôtel des Mésanges",
        establishment_status=Establishment.Status.DRAFT,
    )
    second = create_membership(
        user=user,
        name="Hôtel du Port",
        establishment_status=Establishment.Status.DRAFT,
    )
    calls = []
    _submit(user, PLAY_EMAIL, send=_accepting_send(calls))
    omitted = PlayStoreAccessRequest.objects.get(user=user)
    assert first.establishment.name not in omitted.mail_text
    assert second.establishment.name not in omitted.mail_text
    assert "Établissement" not in omitted.mail_text

    _submit(
        user,
        "second.play@example.com",
        establishment_id=first.establishment_id,
        send=_accepting_send(calls),
    )
    named = PlayStoreAccessRequest.objects.get(user=user)
    assert named.mail_text.count("Hôtel des Mésanges") == 1
    assert "Hôtel du Port" not in named.mail_text

    active = create_membership(user=user, name="Hôtel Actif")
    stranger = create_user(username="play-stranger", email="stranger@example.com")
    hidden = create_membership(user=stranger, name="Hôtel Secret")
    _submit(
        user,
        "third.play@example.com",
        establishment_id=hidden.establishment_id,
        session=SimpleNamespace(selected_establishment_id=active.establishment_id),
        send=_accepting_send(calls),
    )
    fallback = PlayStoreAccessRequest.objects.get(user=user)
    assert "Hôtel Secret" not in fallback.mail_text
    assert fallback.mail_text.count("Hôtel Actif") == 1


def test_anonymization_deletes_the_play_store_request():
    user = _user()
    _submit(user, PLAY_EMAIL, send=_accepting_send([]))
    assert PlayStoreAccessRequest.objects.filter(user=user).exists()
    _anonymize_user(user=user)
    assert not PlayStoreAccessRequest.objects.filter(user=user).exists()


def test_api_accepts_the_current_key_without_a_provider_identifier(api_client, monkeypatch):
    user = _user()
    membership = create_membership(user=user, name="Hôtel des Mésanges")
    access_token = login(api_client, identifier=user.email)
    headers = auth_headers(access_token)
    anonymous = api_client.get("/api/v1/auth/me/play-store-access/")
    assert anonymous.status_code == 401

    current = api_client.get("/api/v1/auth/me/play-store-access/", **headers)
    assert current.status_code == 200
    assert current.json() == {"status": "none"}

    calls = []
    monkeypatch.setattr(
        "houston.accounts.play_store_access.send_invitation_email_via_resend",
        _accepting_send(calls),
    )
    created = api_client.post(
        "/api/v1/auth/me/play-store-access/",
        {
            "google_play_email": PLAY_EMAIL,
            "establishment_id": str(membership.establishment_id),
        },
        format="json",
        **headers,
    )
    assert created.status_code == 200
    assert created.json() == {"status": "accepted"}
    assert calls[0]["to_email"] == OPERATOR_EMAIL
    assert PLAY_CLOSED_TESTING_JOIN_URL not in str(created.json())
    assert PLAY_CLOSED_TESTING_INSTALL_URL not in str(created.json())

    monkeypatch.setattr(
        "houston.accounts.play_store_access.send_invitation_email_via_resend",
        _failing_send([], InvitationEmailTemporaryError("timeout")),
    )
    retried = api_client.post(
        "/api/v1/auth/me/play-store-access/",
        {"google_play_email": "other.play@example.com"},
        format="json",
        **headers,
    )
    assert retried.status_code == 503
    assert retried.json()["code"] == "play_store_access_not_accepted"
    pending = api_client.get("/api/v1/auth/me/play-store-access/", **headers)
    assert pending.json() == {"status": "pending"}
