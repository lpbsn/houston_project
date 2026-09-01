from __future__ import annotations

import uuid
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from houston.accounts.deletion_constants import REMOVED_COMMENT_BODY, REMOVED_OBSERVATION_TEXT
from houston.accounts.deletion_services import delete_authenticated_account
from houston.accounts.display import DELETED_ACCOUNT_DISPLAY_NAME, user_display_name
from houston.accounts.models import User, UserSession
from houston.accounts.tests.helpers import ensure_csrf, post_register, registration_payload
from houston.chat.api.serializers import membership_display_name as chat_membership_display_name
from houston.chat.models import ChatConversation, ChatMessage
from houston.comments.api.serializers import serialize_comment
from houston.comments.models import Comment
from houston.establishments.models import Establishment, EstablishmentMembership
from houston.establishments.services import (
    DirectorCoverageInvariantError,
    deactivate_membership_for_management,
)
from houston.establishments.tests.membership_api_helpers import (
    auth_headers,
    create_membership,
    create_user,
    login,
)
from houston.notifications.constants import DEFAULT_ACTOR_DISPLAY_NAME
from houston.notifications.models import Notification, PushDevice
from houston.observations.models import ObservationMedia
from houston.organizations.models import Organization
from houston.signals.models import Signal
from houston.testing.auth import TEST_PASSWORD
from houston.testing.pipeline import create_observation
from houston.uploads.models import TemporaryUpload

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


def _delete_payload(*, close_organizations: bool = False, password: str = TEST_PASSWORD) -> dict:
    return {
        "password": password,
        "close_organizations": close_organizations,
        "refresh_token_transport": "cookie",
    }


def test_staff_can_delete_account_and_reregister_email(api_client):
    user = create_user(username="staff_delete", email="staff.delete@example.com")
    user.first_name = "Ada"
    user.last_name = "Lovelace"
    user.save(update_fields=["first_name", "last_name", "updated_at"])
    membership = create_membership(user=user, role=EstablishmentMembership.Role.STAFF)
    observation = create_observation(membership=membership, text="Fuite visible dans la chambre 12")
    access_token = login(api_client, identifier=user.email)

    preview = api_client.get(
        "/api/v1/auth/me/deletion-preview/",
        **auth_headers(access_token),
    )
    assert preview.status_code == 200
    assert preview.json()["requires_organization_closure"] is False
    assert preview.json()["leaves_establishments_without_director"] == []

    csrf = api_client.cookies["csrftoken"].value
    response = api_client.post(
        "/api/v1/auth/me/delete/",
        _delete_payload(),
        format="json",
        HTTP_X_CSRFTOKEN=csrf,
        **auth_headers(access_token),
    )
    assert response.status_code == 204

    user.refresh_from_db()
    membership.refresh_from_db()
    observation.refresh_from_db()
    assert user.status == User.Status.ANONYMIZED
    assert user.email is None
    assert user.first_name == ""
    assert not user.check_password(TEST_PASSWORD)
    assert membership.status == EstablishmentMembership.Status.DEACTIVATED
    assert observation.raw_text == REMOVED_OBSERVATION_TEXT
    assert UserSession.objects.filter(user=user).count() == 0
    assert user_display_name(user) == DELETED_ACCOUNT_DISPLAY_NAME

    login_response = api_client.post(
        "/api/v1/auth/login/",
        {
            "identifier": "staff.delete@example.com",
            "password": TEST_PASSWORD,
            "refresh_token_transport": "cookie",
        },
        format="json",
        HTTP_X_CSRFTOKEN=api_client.get("/api/v1/auth/csrf/").json()["csrf_token"],
    )
    assert login_response.status_code == 401

    assert not User.objects.filter(email__iexact="staff.delete@example.com").exists()


def test_wrong_password_does_not_delete_account(api_client):
    user = create_user(username="staff_bad_pw")
    create_membership(user=user, role=EstablishmentMembership.Role.STAFF)
    access_token = login(api_client, identifier=user.email)
    csrf = api_client.cookies["csrftoken"].value
    response = api_client.post(
        "/api/v1/auth/me/delete/",
        _delete_payload(password="wrong-password"),
        format="json",
        HTTP_X_CSRFTOKEN=csrf,
        **auth_headers(access_token),
    )
    assert response.status_code == 403
    assert response.json()["code"] == "invalid_credentials"
    user.refresh_from_db()
    assert user.status == User.Status.ACTIVE


def test_last_owner_requires_organization_closure(api_client):
    user = create_user(username="solo_owner")
    membership = create_membership(user=user, role=EstablishmentMembership.Role.OWNER)
    access_token = login(api_client, identifier=user.email)
    preview = api_client.get(
        "/api/v1/auth/me/deletion-preview/",
        **auth_headers(access_token),
    )
    assert preview.json()["requires_organization_closure"] is True
    assert preview.json()["organizations"][0]["name"] == membership.establishment.organization.name

    csrf = api_client.cookies["csrftoken"].value
    blocked = api_client.post(
        "/api/v1/auth/me/delete/",
        _delete_payload(close_organizations=False),
        format="json",
        HTTP_X_CSRFTOKEN=csrf,
        **auth_headers(access_token),
    )
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "organization_closure_required"

    csrf = api_client.cookies["csrftoken"].value
    deleted = api_client.post(
        "/api/v1/auth/me/delete/",
        _delete_payload(close_organizations=True),
        format="json",
        HTTP_X_CSRFTOKEN=csrf,
        **auth_headers(access_token),
    )
    assert deleted.status_code == 204
    membership.establishment.organization.refresh_from_db()
    membership.establishment.refresh_from_db()
    membership.refresh_from_db()
    assert membership.establishment.organization.status == Organization.Status.ARCHIVED
    assert membership.establishment.status == Establishment.Status.DEACTIVATED
    assert membership.status == EstablishmentMembership.Status.DEACTIVATED


def test_last_director_can_delete_without_blocking_and_team_still_guards(api_client):
    owner = create_user(username="site_owner")
    owner_membership = create_membership(user=owner, role=EstablishmentMembership.Role.OWNER)
    director = create_user(username="site_director")
    director_membership = EstablishmentMembership.objects.create(
        user=director,
        establishment=owner_membership.establishment,
        role=EstablishmentMembership.Role.DIRECTOR,
        status=EstablishmentMembership.Status.ACTIVE,
    )

    with pytest.raises(DirectorCoverageInvariantError):
        deactivate_membership_for_management(
            current_membership=owner_membership,
            establishment_id=owner_membership.establishment_id,
            membership_id=director_membership.id,
        )

    access_token = login(api_client, identifier=director.email)
    preview = api_client.get(
        "/api/v1/auth/me/deletion-preview/",
        **auth_headers(access_token),
    )
    body = preview.json()
    assert body["requires_organization_closure"] is False
    assert body["leaves_establishments_without_director"][0]["id"] == str(
        director_membership.establishment_id
    )

    csrf = api_client.cookies["csrftoken"].value
    response = api_client.post(
        "/api/v1/auth/me/delete/",
        _delete_payload(),
        format="json",
        HTTP_X_CSRFTOKEN=csrf,
        **auth_headers(access_token),
    )
    assert response.status_code == 204
    director.refresh_from_db()
    director_membership.refresh_from_db()
    owner_membership.establishment.refresh_from_db()
    assert director.status == User.Status.ANONYMIZED
    assert director_membership.status == EstablishmentMembership.Status.DEACTIVATED
    assert owner_membership.establishment.status == Establishment.Status.ACTIVE
    owner.refresh_from_db()
    assert owner.status == User.Status.ACTIVE


def test_non_last_owner_does_not_archive_organization(api_client):
    first = create_user(username="owner_one")
    first_membership = create_membership(user=first, role=EstablishmentMembership.Role.OWNER)
    second = create_user(username="owner_two")
    EstablishmentMembership.objects.create(
        user=second,
        establishment=first_membership.establishment,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    access_token = login(api_client, identifier=first.email)
    preview = api_client.get(
        "/api/v1/auth/me/deletion-preview/",
        **auth_headers(access_token),
    )
    assert preview.json()["requires_organization_closure"] is False

    csrf = api_client.cookies["csrftoken"].value
    response = api_client.post(
        "/api/v1/auth/me/delete/",
        _delete_payload(),
        format="json",
        HTTP_X_CSRFTOKEN=csrf,
        **auth_headers(access_token),
    )
    assert response.status_code == 204
    first_membership.establishment.organization.refresh_from_db()
    first_membership.establishment.refresh_from_db()
    assert first_membership.establishment.organization.status == Organization.Status.ACTIVE
    assert first_membership.establishment.status == Establishment.Status.ACTIVE


def test_deleted_email_can_register_a_new_account(api_client):
    email = "reuse.after.delete@example.com"
    user = create_user(username="reuse_delete", email=email)
    create_membership(user=user, role=EstablishmentMembership.Role.STAFF)
    access_token = login(api_client, identifier=user.email)
    csrf = api_client.cookies["csrftoken"].value
    response = api_client.post(
        "/api/v1/auth/me/delete/",
        _delete_payload(),
        format="json",
        HTTP_X_CSRFTOKEN=csrf,
        **auth_headers(access_token),
    )
    assert response.status_code == 204
    deleted_id = user.id

    api_client.cookies.clear()
    csrf_token = ensure_csrf(api_client)
    with override_settings(HOUSTON_REGISTRATION_INVITE_CODES=["valid-code"]):
        register = post_register(
            api_client,
            csrf_token,
            registration_payload(email=email, first_name="Neo", last_name="User"),
        )
    assert register.status_code == 201, register.json()
    new_user = User.objects.get(email__iexact=email)
    assert new_user.id != deleted_id
    assert new_user.status == User.Status.ACTIVE


def test_wrong_password_does_not_alter_memberships_ugc_or_organization(api_client):
    user = create_user(username="bad_pw_ugc")
    membership = create_membership(user=user, role=EstablishmentMembership.Role.STAFF)
    observation = create_observation(membership=membership, text="Secret observation text")
    device = PushDevice.objects.create(
        user=user, token="tok-wrong-pw", platform=PushDevice.Platform.ANDROID
    )
    access_token = login(api_client, identifier=user.email)
    organization = membership.establishment.organization
    csrf = api_client.cookies["csrftoken"].value
    response = api_client.post(
        "/api/v1/auth/me/delete/",
        _delete_payload(password="wrong-password"),
        format="json",
        HTTP_X_CSRFTOKEN=csrf,
        **auth_headers(access_token),
    )
    assert response.status_code == 403
    user.refresh_from_db()
    membership.refresh_from_db()
    observation.refresh_from_db()
    organization.refresh_from_db()
    membership.establishment.refresh_from_db()
    assert user.status == User.Status.ACTIVE
    assert membership.status == EstablishmentMembership.Status.ACTIVE
    assert observation.raw_text == "Secret observation text"
    assert organization.status == Organization.Status.ACTIVE
    assert membership.establishment.status == Establishment.Status.ACTIVE
    assert UserSession.objects.filter(user=user).count() >= 1
    assert PushDevice.objects.filter(id=device.id, revoked_at__isnull=True).exists()


def test_last_owner_409_does_not_partially_close_or_scrub(api_client):
    user = create_user(username="solo_owner_guard")
    membership = create_membership(user=user, role=EstablishmentMembership.Role.OWNER)
    observation = create_observation(membership=membership, text="Owner observation")
    access_token = login(api_client, identifier=user.email)
    csrf = api_client.cookies["csrftoken"].value
    blocked = api_client.post(
        "/api/v1/auth/me/delete/",
        _delete_payload(close_organizations=False),
        format="json",
        HTTP_X_CSRFTOKEN=csrf,
        **auth_headers(access_token),
    )
    assert blocked.status_code == 409
    user.refresh_from_db()
    membership.refresh_from_db()
    observation.refresh_from_db()
    membership.establishment.organization.refresh_from_db()
    membership.establishment.refresh_from_db()
    assert user.status == User.Status.ACTIVE
    assert user.check_password(TEST_PASSWORD)
    assert membership.status == EstablishmentMembership.Status.ACTIVE
    assert observation.raw_text == "Owner observation"
    assert membership.establishment.organization.status == Organization.Status.ACTIVE
    assert membership.establishment.status == Establishment.Status.ACTIVE


def test_deletion_scrubs_submitted_ugc_chat_notifications_and_display(api_client):
    author = create_user(username="ugc_author")
    author.first_name = "Marie"
    author.last_name = "Curie"
    author.save(update_fields=["first_name", "last_name", "updated_at"])
    peer = create_user(username="ugc_peer")
    membership = create_membership(user=author, role=EstablishmentMembership.Role.STAFF)
    peer_membership = EstablishmentMembership.objects.create(
        user=peer,
        establishment=membership.establishment,
        role=EstablishmentMembership.Role.STAFF,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    observation = create_observation(membership=membership, text="Photo-backed observation")
    signal = Signal.objects.create(
        establishment=membership.establishment,
        routing_status=Signal.RoutingStatus.UNASSIGNED,
        title="Signal stays",
        structured_summary="Summary stays",
        last_activity_at=timezone.now(),
    )
    own_comment = Comment.objects.create(
        establishment=membership.establishment,
        signal=signal,
        author_membership=membership,
        body="I wrote this",
    )
    other_comment = Comment.objects.create(
        establishment=membership.establishment,
        signal=signal,
        author_membership=peer_membership,
        body="Peer wrote this",
    )
    upload = TemporaryUpload(
        establishment=membership.establishment,
        uploaded_by=author,
        content_type="image/png",
        stored_extension="png",
        size_bytes=8,
        status=TemporaryUpload.Status.LINKED,
        expires_at=timezone.now() + timedelta(hours=24),
        linked_at=timezone.now(),
    )
    upload.file.save(
        "photo.png",
        SimpleUploadedFile("photo.png", b"\x89PNG\r\n\x1a\n", content_type="image/png"),
        save=False,
    )
    upload.save()
    media = ObservationMedia.objects.create(
        observation=observation,
        temporary_upload=upload,
        content_type="image/png",
        size_bytes=8,
        position=1,
        storage_key=upload.file.name,
    )
    conversation = ChatConversation.objects.create(
        establishment=membership.establishment,
        type=ChatConversation.Type.GROUP,
        title="Ops",
        created_by_membership=membership,
    )
    message = ChatMessage.objects.create(
        conversation=conversation,
        author_membership=membership,
        body="secret chat",
        client_message_id=uuid.uuid4(),
    )
    inbox = Notification.objects.create(
        establishment_id=membership.establishment_id,
        recipient_membership=membership,
        actor_membership=peer_membership,
        event_key=Notification.EventKey.SIGNAL_CREATED,
        subject_type=Notification.SubjectType.SIGNAL,
        subject_id=signal.id,
        priority=Notification.Priority.INFO,
        title="Inbox item",
        body="for author",
    )
    chat_notif = Notification.objects.create(
        establishment_id=membership.establishment_id,
        recipient_membership=peer_membership,
        actor_membership=membership,
        event_key=Notification.EventKey.CHAT_MESSAGE_RECEIVED,
        subject_type=Notification.SubjectType.CHAT_CONVERSATION,
        subject_id=conversation.id,
        priority=Notification.Priority.INFO,
        title="Message reçu de Marie Curie",
        body="secret chat",
    )
    PushDevice.objects.create(user=author, token="tok-ugc", platform=PushDevice.Platform.IOS)

    access_token = login(api_client, identifier=author.email)
    csrf = api_client.cookies["csrftoken"].value
    response = api_client.post(
        "/api/v1/auth/me/delete/",
        _delete_payload(),
        format="json",
        HTTP_X_CSRFTOKEN=csrf,
        **auth_headers(access_token),
    )
    assert response.status_code == 204

    observation.refresh_from_db()
    own_comment.refresh_from_db()
    other_comment.refresh_from_db()
    signal.refresh_from_db()
    chat_notif.refresh_from_db()
    membership = EstablishmentMembership.objects.select_related("user").get(id=membership.id)
    assert observation.raw_text == REMOVED_OBSERVATION_TEXT
    assert own_comment.body == REMOVED_COMMENT_BODY
    assert other_comment.body == "Peer wrote this"
    assert signal.title == "Signal stays"
    assert not ObservationMedia.objects.filter(id=media.id).exists()
    assert not ChatMessage.objects.filter(id=message.id).exists()
    assert not Notification.objects.filter(id=inbox.id).exists()
    assert chat_notif.title == f"Message reçu de {DEFAULT_ACTOR_DISPLAY_NAME}"
    assert PushDevice.objects.filter(user=author).count() == 0
    assert serialize_comment(own_comment)["author"]["display_name"] == DELETED_ACCOUNT_DISPLAY_NAME
    assert chat_membership_display_name(membership) == DELETED_ACCOUNT_DISPLAY_NAME
    bootstrap = api_client.get("/api/v1/auth/bootstrap/", **auth_headers(access_token))
    assert bootstrap.status_code == 401


def test_anonymize_failure_rolls_back_including_unlinked_upload():
    user = create_user(username="rollback_user")
    membership = create_membership(user=user, role=EstablishmentMembership.Role.STAFF)
    observation = create_observation(membership=membership, text="Must stay")
    unlinked = TemporaryUpload(
        establishment=membership.establishment,
        uploaded_by=user,
        content_type="image/png",
        stored_extension="png",
        size_bytes=8,
        status=TemporaryUpload.Status.VALIDATED,
        expires_at=timezone.now() + timedelta(hours=24),
    )
    unlinked.file.save(
        "tmp.png",
        SimpleUploadedFile("tmp.png", b"\x89PNG\r\n\x1a\n", content_type="image/png"),
        save=False,
    )
    unlinked.save()
    file_name = unlinked.file.name
    with patch(
        "houston.accounts.deletion_services._anonymize_user",
        side_effect=RuntimeError("boom"),
    ):
        with pytest.raises(RuntimeError):
            delete_authenticated_account(
                user=user,
                password=TEST_PASSWORD,
                close_organizations=False,
            )
    user.refresh_from_db()
    membership.refresh_from_db()
    observation.refresh_from_db()
    unlinked.refresh_from_db()
    assert user.status == User.Status.ACTIVE
    assert user.email == "rollback_user@example.com"
    assert membership.status == EstablishmentMembership.Status.ACTIVE
    assert observation.raw_text == "Must stay"
    assert unlinked.status == TemporaryUpload.Status.VALIDATED
    assert unlinked.file.name == file_name
    assert unlinked.file.storage.exists(file_name)


def test_last_owner_close_org_rolls_back_on_anonymize_failure():
    user = create_user(username="rollback_owner")
    membership = create_membership(user=user, role=EstablishmentMembership.Role.OWNER)
    with patch(
        "houston.accounts.deletion_services._anonymize_user",
        side_effect=RuntimeError("boom"),
    ):
        with pytest.raises(RuntimeError):
            delete_authenticated_account(
                user=user,
                password=TEST_PASSWORD,
                close_organizations=True,
            )
    membership.establishment.organization.refresh_from_db()
    membership.establishment.refresh_from_db()
    membership.refresh_from_db()
    user.refresh_from_db()
    assert membership.establishment.organization.status == Organization.Status.ACTIVE
    assert membership.establishment.status == Establishment.Status.ACTIVE
    assert membership.status == EstablishmentMembership.Status.ACTIVE
    assert user.status == User.Status.ACTIVE
