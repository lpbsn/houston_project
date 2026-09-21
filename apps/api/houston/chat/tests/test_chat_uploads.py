from __future__ import annotations

import io
import json
import uuid
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core.files.base import ContentFile
from django.utils import timezone
from houston.chat.models import ChatMessage, ChatMessageAttachment, ChatUpload
from houston.chat.services import create_message
from houston.chat.tests.conftest import create_establishment, create_membership, create_user, login
from houston.chat.tests.helpers import chat_url, create_dm, send_message
from houston.chat.upload_services import (
    cleanup_expired_chat_uploads,
    generate_chat_upload_thumbnail,
)
from houston.chat.ws_payloads import build_message_created_payload
from houston.uploads.private_storage import get_chat_private_media_storage
from PIL import Image

pytestmark = pytest.mark.django_db


def _png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), color=(12, 80, 160)).save(buffer, format="PNG")
    return buffer.getvalue()


def _pdf_bytes() -> bytes:
    return b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def _setup(api_client):
    establishment = create_establishment()
    sender = create_user(username=f"chat_up_{uuid.uuid4().hex[:8]}")
    receiver = create_user(username=f"chat_up_peer_{uuid.uuid4().hex[:8]}")
    sender_membership = create_membership(user=sender, establishment=establishment)
    receiver_membership = create_membership(user=receiver, establishment=establishment)
    token = login(api_client, user=sender)
    dm = create_dm(
        api_client,
        token=token,
        establishment_id=establishment.id,
        target_membership_id=receiver_membership.id,
    )
    conversation_id = uuid.UUID(dm.json()["conversation"]["id"])
    return (
        establishment,
        sender,
        receiver,
        sender_membership,
        receiver_membership,
        token,
        conversation_id,
    )


def _reserve(
    api_client, *, token, establishment_id, conversation_id, filename, content_type, size_bytes
):
    return api_client.post(
        chat_url(establishment_id, "uploads/"),
        {
            "conversation_id": str(conversation_id),
            "filename": filename,
            "content_type": content_type,
            "size_bytes": size_bytes,
        },
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )


def _put_and_complete(api_client, *, token, establishment_id, upload_id, payload):
    put = api_client.put(
        chat_url(establishment_id, f"uploads/{upload_id}/content/"),
        data=payload,
        content_type="application/octet-stream",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    complete = api_client.post(
        chat_url(establishment_id, f"uploads/{upload_id}/complete/"),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    return put, complete


def _create_upload_with_file(
    *,
    status=ChatUpload.Status.RESERVED,
    expired=True,
    kind="",
    content_type="",
    size_bytes=None,
    filename="gone.png",
    payload=b"orphan",
):
    from houston.chat.services import create_or_get_dm_conversation

    establishment = create_establishment()
    sender = create_user(username=f"chat_orphan_{uuid.uuid4().hex[:8]}")
    peer = create_user(username=f"chat_orphan_peer_{uuid.uuid4().hex[:8]}")
    sender_membership = create_membership(user=sender, establishment=establishment)
    peer_membership = create_membership(user=peer, establishment=establishment)
    conversation, _ = create_or_get_dm_conversation(
        actor_membership=sender_membership,
        target_membership_id=peer_membership.id,
    )
    storage_key = (
        f"establishments/{establishment.id}/chat/{conversation.id}/"
        f"{uuid.uuid4()}/original.png"
    )
    expires_at = timezone.now() - timedelta(hours=1)
    if not expired:
        expires_at = timezone.now() + timedelta(hours=1)
    upload = ChatUpload.objects.create(
        establishment=establishment,
        conversation=conversation,
        uploaded_by_membership=sender_membership,
        original_filename=filename,
        declared_content_type="image/png",
        declared_size_bytes=len(payload),
        storage_key=storage_key,
        expires_at=expires_at,
        status=status,
        kind=kind,
        content_type=content_type,
        size_bytes=size_bytes,
    )
    storage = get_chat_private_media_storage()
    storage.save(storage_key, ContentFile(payload))
    return upload, sender_membership, conversation, storage


@pytest.mark.django_db(transaction=True)
def test_complete_validates_and_enqueues_thumb_not_on_message(api_client, settings, tmp_path):
    settings.HOUSTON_PRIVATE_MEDIA_BACKEND = "filesystem"
    settings.HOUSTON_CHAT_PRIVATE_MEDIA_ROOT = str(tmp_path)
    establishment, _sender, _receiver, _sm, _rm, token, conversation_id = _setup(api_client)
    payload = _png_bytes()
    reserved = _reserve(
        api_client,
        token=token,
        establishment_id=establishment.id,
        conversation_id=conversation_id,
        filename="shot.png",
        content_type="image/png",
        size_bytes=len(payload),
    )
    assert reserved.status_code == 201
    assert reserved.json()["put_url"] == ""
    upload_id = reserved.json()["upload_id"]

    with patch("houston.chat.tasks.generate_chat_upload_thumbnail_task.delay") as mock_delay:
        put, complete = _put_and_complete(
            api_client,
            token=token,
            establishment_id=establishment.id,
            upload_id=upload_id,
            payload=payload,
        )
        assert put.status_code == 204
        assert complete.status_code == 200
        assert complete.json()["kind"] == "image"
        mock_delay.assert_called_once_with(upload_id)

    with patch("houston.chat.tasks.generate_chat_upload_thumbnail_task.delay") as mock_delay:
        response = api_client.post(
            chat_url(establishment.id, f"conversations/{conversation_id}/messages/"),
            {
                "client_message_id": str(uuid.uuid4()),
                "body": "",
                "attachment_ids": [upload_id],
            },
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
    assert response.status_code == 201
    mock_delay.assert_not_called()


def test_body_empty_with_attachment_ok_and_reuse_rejected(api_client, settings, tmp_path):
    settings.HOUSTON_PRIVATE_MEDIA_BACKEND = "filesystem"
    settings.HOUSTON_CHAT_PRIVATE_MEDIA_ROOT = str(tmp_path)
    establishment, _s, _r, _sm, _rm, token, conversation_id = _setup(api_client)
    payload = _pdf_bytes()
    reserved = _reserve(
        api_client,
        token=token,
        establishment_id=establishment.id,
        conversation_id=conversation_id,
        filename="note.pdf",
        content_type="application/pdf",
        size_bytes=len(payload),
    )
    upload_id = reserved.json()["upload_id"]
    put, complete = _put_and_complete(
        api_client,
        token=token,
        establishment_id=establishment.id,
        upload_id=upload_id,
        payload=payload,
    )
    assert complete.status_code == 200
    assert complete.json()["kind"] == "document"

    first = send_message(
        api_client,
        token=token,
        establishment_id=establishment.id,
        conversation_id=conversation_id,
        body="",
        client_message_id=uuid.uuid4(),
    )
    # helper does not pass attachment_ids yet
    response = api_client.post(
        chat_url(establishment.id, f"conversations/{conversation_id}/messages/"),
        {
            "client_message_id": str(uuid.uuid4()),
            "body": "",
            "attachment_ids": [upload_id],
        },
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert response.status_code == 201
    assert response.json()["message"]["body"] == ""
    assert len(response.json()["message"]["attachments"]) == 1
    assert ChatMessageAttachment.objects.count() == 1

    reuse = api_client.post(
        chat_url(establishment.id, f"conversations/{conversation_id}/messages/"),
        {
            "client_message_id": str(uuid.uuid4()),
            "body": "",
            "attachment_ids": [upload_id],
        },
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert reuse.status_code == 400
    _ = first


def test_complete_rejects_unknown_type(api_client, settings, tmp_path):
    settings.HOUSTON_PRIVATE_MEDIA_BACKEND = "filesystem"
    settings.HOUSTON_CHAT_PRIVATE_MEDIA_ROOT = str(tmp_path)
    establishment, _s, _r, _sm, _rm, token, conversation_id = _setup(api_client)
    payload = b"not-a-real-file"
    reserved = _reserve(
        api_client,
        token=token,
        establishment_id=establishment.id,
        conversation_id=conversation_id,
        filename="x.bin",
        content_type="application/octet-stream",
        size_bytes=len(payload),
    )
    _put, complete = _put_and_complete(
        api_client,
        token=token,
        establishment_id=establishment.id,
        upload_id=reserved.json()["upload_id"],
        payload=payload,
    )
    assert complete.status_code == 400


def test_reply_survives_parent_purge_without_parent_content(api_client, settings, tmp_path):
    settings.HOUSTON_PRIVATE_MEDIA_BACKEND = "filesystem"
    settings.HOUSTON_CHAT_PRIVATE_MEDIA_ROOT = str(tmp_path)
    establishment, _s, _r, sender_membership, _rm, token, conversation_id = _setup(api_client)
    parent = send_message(
        api_client,
        token=token,
        establishment_id=establishment.id,
        conversation_id=conversation_id,
        body="parent body",
    )
    parent_id = uuid.UUID(parent.json()["message"]["id"])
    child = send_message(
        api_client,
        token=token,
        establishment_id=establishment.id,
        conversation_id=conversation_id,
        body="child",
        reply_to_id=parent_id,
    )
    ChatMessage.objects.filter(id=parent_id).delete()
    listed = api_client.get(
        chat_url(establishment.id, f"conversations/{conversation_id}/messages/"),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    child_payload = next(
        item for item in listed.json()["items"] if item["id"] == child.json()["message"]["id"]
    )
    assert child_payload["is_reply"] is True
    assert child_payload["reply_to"]["unavailable"] is True
    assert not child_payload["reply_to"].get("excerpt")
    _ = sender_membership


def test_gallery_and_isolation(api_client, settings, tmp_path):
    settings.HOUSTON_PRIVATE_MEDIA_BACKEND = "filesystem"
    settings.HOUSTON_CHAT_PRIVATE_MEDIA_ROOT = str(tmp_path)
    establishment, _s, receiver, _sm, _rm, token, conversation_id = _setup(api_client)
    payload = _png_bytes()
    reserved = _reserve(
        api_client,
        token=token,
        establishment_id=establishment.id,
        conversation_id=conversation_id,
        filename="pic.png",
        content_type="image/png",
        size_bytes=len(payload),
    )
    upload_id = reserved.json()["upload_id"]
    _put_and_complete(
        api_client,
        token=token,
        establishment_id=establishment.id,
        upload_id=upload_id,
        payload=payload,
    )
    generate_chat_upload_thumbnail(upload_id=uuid.UUID(upload_id))
    api_client.post(
        chat_url(establishment.id, f"conversations/{conversation_id}/messages/"),
        {
            "client_message_id": str(uuid.uuid4()),
            "body": "",
            "attachment_ids": [upload_id],
        },
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    gallery = api_client.get(
        chat_url(establishment.id, f"conversations/{conversation_id}/shared-media/"),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert gallery.status_code == 200
    assert gallery.json()["has_more"] is False
    assert len(gallery.json()["items"]) == 1
    item = gallery.json()["items"][0]
    sent = ChatMessage.objects.get(conversation_id=conversation_id)
    assert item["message_id"] == str(sent.id)
    assert item["kind"] == "image"
    assert item["author_display_name"]
    media_only = api_client.get(
        chat_url(establishment.id, f"conversations/{conversation_id}/shared-media/?kind=image"),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    documents_only = api_client.get(
        chat_url(establishment.id, f"conversations/{conversation_id}/shared-media/?kind=document"),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert len(media_only.json()["items"]) == 1
    assert documents_only.json()["items"] == []

    outsider = create_user(username="chat_gallery_out")
    create_membership(user=outsider, establishment=establishment)
    outsider_token = login(api_client, user=outsider)
    denied = api_client.get(
        chat_url(establishment.id, f"conversations/{conversation_id}/shared-media/"),
        HTTP_AUTHORIZATION=f"Bearer {outsider_token}",
    )
    assert denied.status_code == 404
    _ = receiver


def test_gallery_and_preview_respect_history_cutoff(api_client, settings, tmp_path):
    settings.HOUSTON_PRIVATE_MEDIA_BACKEND = "filesystem"
    settings.HOUSTON_CHAT_PRIVATE_MEDIA_ROOT = str(tmp_path)
    (
        establishment,
        sender,
        receiver,
        sender_membership,
        receiver_membership,
        token,
        conversation_id,
    ) = _setup(api_client)
    payload = _png_bytes()
    reserved = _reserve(
        api_client,
        token=token,
        establishment_id=establishment.id,
        conversation_id=conversation_id,
        filename="old.png",
        content_type="image/png",
        size_bytes=len(payload),
    )
    upload_id = reserved.json()["upload_id"]
    _put_and_complete(
        api_client,
        token=token,
        establishment_id=establishment.id,
        upload_id=upload_id,
        payload=payload,
    )
    sent = api_client.post(
        chat_url(establishment.id, f"conversations/{conversation_id}/messages/"),
        {
            "client_message_id": str(uuid.uuid4()),
            "body": "",
            "attachment_ids": [upload_id],
        },
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert sent.status_code == 201
    attachment_id = sent.json()["message"]["attachments"][0]["id"]
    receiver_token = login(api_client, user=receiver)
    hide = api_client.post(
        chat_url(establishment.id, f"conversations/{conversation_id}/hide/"),
        HTTP_AUTHORIZATION=f"Bearer {receiver_token}",
    )
    assert hide.status_code == 204

    hidden_gallery = api_client.get(
        chat_url(establishment.id, f"conversations/{conversation_id}/shared-media/"),
        HTTP_AUTHORIZATION=f"Bearer {receiver_token}",
    )
    assert hidden_gallery.status_code == 200
    assert hidden_gallery.json()["items"] == []
    hidden_preview = api_client.get(
        chat_url(establishment.id, f"attachments/{attachment_id}/preview/"),
        HTTP_AUTHORIZATION=f"Bearer {receiver_token}",
    )
    assert hidden_preview.status_code == 404

    peer_gallery = api_client.get(
        chat_url(establishment.id, f"conversations/{conversation_id}/shared-media/"),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert len(peer_gallery.json()["items"]) == 1
    peer_preview = api_client.get(
        chat_url(establishment.id, f"attachments/{attachment_id}/preview/"),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert peer_preview.status_code == 200

    later = _reserve(
        api_client,
        token=token,
        establishment_id=establishment.id,
        conversation_id=conversation_id,
        filename="new.png",
        content_type="image/png",
        size_bytes=len(payload),
    )
    later_id = later.json()["upload_id"]
    _put_and_complete(
        api_client,
        token=token,
        establishment_id=establishment.id,
        upload_id=later_id,
        payload=payload,
    )
    later_sent = api_client.post(
        chat_url(establishment.id, f"conversations/{conversation_id}/messages/"),
        {
            "client_message_id": str(uuid.uuid4()),
            "body": "",
            "attachment_ids": [later_id],
        },
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert later_sent.status_code == 201
    visible_gallery = api_client.get(
        chat_url(establishment.id, f"conversations/{conversation_id}/shared-media/"),
        HTTP_AUTHORIZATION=f"Bearer {receiver_token}",
    )
    assert len(visible_gallery.json()["items"]) == 1
    later_attachment_id = later_sent.json()["message"]["attachments"][0]["id"]
    assert visible_gallery.json()["items"][0]["id"] == later_attachment_id
    _ = sender
    _ = sender_membership
    _ = receiver_membership


def test_notify_message_created_applies_cutoff_per_recipient(api_client, monkeypatch):
    (
        establishment,
        sender,
        receiver,
        sender_membership,
        receiver_membership,
        _token,
        conversation_id,
    ) = _setup(api_client)
    parent = create_message(
        author_membership=sender_membership,
        establishment_id=establishment.id,
        conversation_id=conversation_id,
        client_message_id=uuid.uuid4(),
        body="hidden parent",
    ).message
    cutoff = timezone.now()
    from houston.chat.models import ChatParticipant

    ChatParticipant.objects.filter(
        conversation_id=conversation_id,
        membership=receiver_membership,
    ).update(history_cutoff_at=cutoff)
    ChatMessage.objects.filter(id=parent.id).update(created_at=cutoff - timedelta(minutes=1))
    child = create_message(
        author_membership=sender_membership,
        establishment_id=establishment.id,
        conversation_id=conversation_id,
        client_message_id=uuid.uuid4(),
        body="visible reply",
        reply_to_id=parent.id,
    ).message
    captured: list[tuple[str, dict]] = []

    class DummyLayer:
        def group_send(self, group, event):
            captured.append((group, event["payload"]))

    monkeypatch.setattr("houston.chat.ws_notify.get_channel_layer", lambda: DummyLayer())
    monkeypatch.setattr("houston.chat.ws_notify.async_to_sync", lambda fn: fn)
    from houston.chat.groups import membership_group_name
    from houston.chat.ws_notify import notify_message_created

    message = (
        ChatMessage.objects.select_related(
            "author_membership",
            "author_membership__user",
            "conversation",
        )
        .prefetch_related("mentions__membership__user", "attachments__upload")
        .get(id=child.id)
    )
    notify_message_created(
        establishment_id=establishment.id,
        conversation_id=conversation_id,
        message=message,
        recipient_membership_ids=[sender_membership.id, receiver_membership.id],
    )
    payloads = {group: payload for group, payload in captured}
    hider_payload = payloads[
        membership_group_name(
            establishment_id=establishment.id,
            membership_id=receiver_membership.id,
        )
    ]
    peer_payload = payloads[
        membership_group_name(
            establishment_id=establishment.id,
            membership_id=sender_membership.id,
        )
    ]
    assert hider_payload["message"]["reply_to"]["unavailable"] is True
    assert "excerpt" not in hider_payload["message"]["reply_to"]
    assert peer_payload["message"]["reply_to"]["unavailable"] is False
    assert peer_payload["message"]["reply_to"]["excerpt"] == "hidden parent"
    _ = sender
    _ = receiver


def test_orphan_cleanup_deletes_expired_reserved(settings, tmp_path):
    settings.HOUSTON_PRIVATE_MEDIA_BACKEND = "filesystem"
    settings.HOUSTON_CHAT_PRIVATE_MEDIA_ROOT = str(tmp_path)
    from houston.chat.tasks import cleanup_chat_upload_orphans_task

    upload, _membership, _conversation, storage = _create_upload_with_file()
    storage_key = upload.storage_key
    result = cleanup_chat_upload_orphans_task.apply()
    assert result.successful()
    assert result.result >= 1
    assert not ChatUpload.objects.filter(id=upload.id).exists()
    assert not storage.exists(storage_key)


def test_put_rejects_expired_reservation(api_client, settings, tmp_path):
    settings.HOUSTON_PRIVATE_MEDIA_BACKEND = "filesystem"
    settings.HOUSTON_CHAT_PRIVATE_MEDIA_ROOT = str(tmp_path)
    establishment, _s, _r, _sm, _rm, token, conversation_id = _setup(api_client)
    reserved = _reserve(
        api_client,
        token=token,
        establishment_id=establishment.id,
        conversation_id=conversation_id,
        filename="shot.png",
        content_type="image/png",
        size_bytes=12,
    )
    upload_id = reserved.json()["upload_id"]
    ChatUpload.objects.filter(id=upload_id).update(
        expires_at=timezone.now() - timedelta(hours=1)
    )
    put = api_client.put(
        chat_url(establishment.id, f"uploads/{upload_id}/content/"),
        data=b"not-stored",
        content_type="application/octet-stream",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert put.status_code == 400
    upload = ChatUpload.objects.get(id=upload_id)
    assert upload.status == ChatUpload.Status.RESERVED
    storage = get_chat_private_media_storage()
    assert not storage.exists(upload.storage_key)


def test_orphan_cleanup_deletes_expired_status_and_file(settings, tmp_path):
    settings.HOUSTON_PRIVATE_MEDIA_BACKEND = "filesystem"
    settings.HOUSTON_CHAT_PRIVATE_MEDIA_ROOT = str(tmp_path)
    upload, _membership, _conversation, storage = _create_upload_with_file(
        status=ChatUpload.Status.EXPIRED,
    )
    storage_key = upload.storage_key
    deleted = cleanup_expired_chat_uploads()
    assert deleted >= 1
    assert not ChatUpload.objects.filter(id=upload.id).exists()
    assert not storage.exists(storage_key)


def test_orphan_cleanup_deletes_expired_validated(settings, tmp_path):
    settings.HOUSTON_PRIVATE_MEDIA_BACKEND = "filesystem"
    settings.HOUSTON_CHAT_PRIVATE_MEDIA_ROOT = str(tmp_path)
    upload, _membership, _conversation, storage = _create_upload_with_file(
        status=ChatUpload.Status.VALIDATED,
        kind=ChatUpload.Kind.IMAGE,
        content_type="image/png",
        size_bytes=6,
    )
    storage_key = upload.storage_key
    deleted = cleanup_expired_chat_uploads()
    assert deleted >= 1
    assert not ChatUpload.objects.filter(id=upload.id).exists()
    assert not storage.exists(storage_key)


def test_orphan_cleanup_keeps_row_on_storage_failure_then_retries(settings, tmp_path):
    settings.HOUSTON_PRIVATE_MEDIA_BACKEND = "filesystem"
    settings.HOUSTON_CHAT_PRIVATE_MEDIA_ROOT = str(tmp_path)
    upload, _membership, _conversation, storage = _create_upload_with_file()
    storage_key = upload.storage_key
    with patch(
        "houston.chat.upload_services.delete_chat_storage_keys_or_raise",
        side_effect=RuntimeError("storage unavailable"),
    ):
        with pytest.raises(RuntimeError, match="storage unavailable"):
            cleanup_expired_chat_uploads()
    leftover = ChatUpload.objects.get(id=upload.id)
    assert leftover.status == ChatUpload.Status.EXPIRED
    assert storage.exists(storage_key)
    deleted = cleanup_expired_chat_uploads()
    assert deleted >= 1
    assert not ChatUpload.objects.filter(id=upload.id).exists()
    assert not storage.exists(storage_key)


@pytest.mark.django_db(transaction=True)
def test_storage_failure_is_best_effort_after_committed_delete(settings, tmp_path, monkeypatch):
    settings.HOUSTON_PRIVATE_MEDIA_BACKEND = "filesystem"
    settings.HOUSTON_CHAT_PRIVATE_MEDIA_ROOT = str(tmp_path)
    from django.db import transaction
    from houston.chat.account_deletion import delete_messages_authored_by_memberships
    from houston.uploads.private_storage import PrivateMediaStorage

    linked, sender_membership, conversation, _storage = _create_upload_with_file(
        status=ChatUpload.Status.LINKED,
        expired=False,
        kind=ChatUpload.Kind.DOCUMENT,
        content_type="application/pdf",
        size_bytes=6,
        filename="note.pdf",
    )
    message = ChatMessage.objects.create(
        conversation=conversation,
        author_membership=sender_membership,
        body="with file",
        client_message_id=uuid.uuid4(),
    )
    ChatMessageAttachment.objects.create(
        message=message,
        upload=linked,
        position=0,
        kind=ChatUpload.Kind.DOCUMENT,
        content_type="application/pdf",
        size_bytes=6,
        original_filename="note.pdf",
    )
    orphan, _membership, _conversation, _orphan_storage = _create_upload_with_file()

    def _boom(_self, _name):
        raise RuntimeError("storage unavailable")

    monkeypatch.setattr(PrivateMediaStorage, "delete", _boom)

    with transaction.atomic():
        delete_messages_authored_by_memberships(membership_ids=[sender_membership.id])
    assert not ChatUpload.objects.filter(id=linked.id).exists()
    assert not ChatMessage.objects.filter(id=message.id).exists()

    with pytest.raises(RuntimeError, match="storage unavailable"):
        cleanup_expired_chat_uploads()
    leftover = ChatUpload.objects.get(id=orphan.id)
    assert leftover.status == ChatUpload.Status.EXPIRED


def test_orphan_cleanup_skips_linked_past_ttl(settings, tmp_path):
    settings.HOUSTON_PRIVATE_MEDIA_BACKEND = "filesystem"
    settings.HOUSTON_CHAT_PRIVATE_MEDIA_ROOT = str(tmp_path)
    upload, sender_membership, conversation, storage = _create_upload_with_file(
        status=ChatUpload.Status.LINKED,
        kind=ChatUpload.Kind.DOCUMENT,
        content_type="application/pdf",
        size_bytes=6,
        filename="note.pdf",
    )
    message = ChatMessage.objects.create(
        conversation=conversation,
        author_membership=sender_membership,
        body="with file",
        client_message_id=uuid.uuid4(),
    )
    ChatMessageAttachment.objects.create(
        message=message,
        upload=upload,
        position=0,
        kind=ChatUpload.Kind.DOCUMENT,
        content_type="application/pdf",
        size_bytes=6,
        original_filename="note.pdf",
    )
    storage_key = upload.storage_key
    deleted = cleanup_expired_chat_uploads()
    assert deleted == 0
    assert ChatUpload.objects.filter(id=upload.id, status=ChatUpload.Status.LINKED).exists()
    assert ChatMessageAttachment.objects.filter(upload_id=upload.id).exists()
    assert storage.exists(storage_key)


def test_orphan_cleanup_skips_validated_not_expired(settings, tmp_path):
    settings.HOUSTON_PRIVATE_MEDIA_BACKEND = "filesystem"
    settings.HOUSTON_CHAT_PRIVATE_MEDIA_ROOT = str(tmp_path)
    upload, _membership, _conversation, storage = _create_upload_with_file(
        status=ChatUpload.Status.VALIDATED,
        expired=False,
        kind=ChatUpload.Kind.IMAGE,
        content_type="image/png",
        size_bytes=6,
    )
    storage_key = upload.storage_key
    deleted = cleanup_expired_chat_uploads()
    assert deleted == 0
    leftover = ChatUpload.objects.get(id=upload.id)
    assert leftover.status == ChatUpload.Status.VALIDATED
    assert storage.exists(storage_key)


def test_orphan_cleanup_task_retries_on_storage_error():
    from houston.chat.tasks import cleanup_chat_upload_orphans_task

    with patch(
        "houston.chat.tasks.cleanup_expired_chat_uploads",
        side_effect=RuntimeError("storage unavailable"),
    ):
        with patch.object(
            cleanup_chat_upload_orphans_task,
            "retry",
            side_effect=RuntimeError("retry-called"),
        ) as mock_retry:
            with pytest.raises(RuntimeError, match="retry-called"):
                cleanup_chat_upload_orphans_task.run()
    mock_retry.assert_called_once()


def test_refresh_presign_reuses_upload_id(api_client, settings, tmp_path):
    settings.HOUSTON_PRIVATE_MEDIA_BACKEND = "filesystem"
    settings.HOUSTON_CHAT_PRIVATE_MEDIA_ROOT = str(tmp_path)
    establishment, _s, _r, _sm, _rm, token, conversation_id = _setup(api_client)
    reserved = _reserve(
        api_client,
        token=token,
        establishment_id=establishment.id,
        conversation_id=conversation_id,
        filename="shot.png",
        content_type="image/png",
        size_bytes=12,
    )
    upload_id = reserved.json()["upload_id"]
    refreshed = api_client.post(
        chat_url(establishment.id, f"uploads/{upload_id}/presign/"),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["upload_id"] == upload_id
    assert refreshed.json()["put_url"] == ""
    assert ChatUpload.objects.filter(id=upload_id).count() == 1


def test_send_accepts_missing_body_with_attachment(api_client, settings, tmp_path):
    settings.HOUSTON_PRIVATE_MEDIA_BACKEND = "filesystem"
    settings.HOUSTON_CHAT_PRIVATE_MEDIA_ROOT = str(tmp_path)
    establishment, _s, _r, _sm, _rm, token, conversation_id = _setup(api_client)
    payload = _pdf_bytes()
    reserved = _reserve(
        api_client,
        token=token,
        establishment_id=establishment.id,
        conversation_id=conversation_id,
        filename="note.pdf",
        content_type="application/pdf",
        size_bytes=len(payload),
    )
    upload_id = reserved.json()["upload_id"]
    _put_and_complete(
        api_client,
        token=token,
        establishment_id=establishment.id,
        upload_id=upload_id,
        payload=payload,
    )
    response = api_client.post(
        chat_url(establishment.id, f"conversations/{conversation_id}/messages/"),
        {
            "client_message_id": str(uuid.uuid4()),
            "attachment_ids": [upload_id],
        },
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert response.status_code == 201
    assert response.json()["message"]["body"] == ""


@pytest.mark.django_db(transaction=True)
def test_attachment_send_is_json_safe_and_idempotent_on_retry(api_client, settings, tmp_path):
    settings.HOUSTON_PRIVATE_MEDIA_BACKEND = "filesystem"
    settings.HOUSTON_CHAT_PRIVATE_MEDIA_ROOT = str(tmp_path)
    establishment, _s, _r, sender_membership, _rm, token, conversation_id = _setup(api_client)
    payload = _pdf_bytes()
    reserved = _reserve(
        api_client,
        token=token,
        establishment_id=establishment.id,
        conversation_id=conversation_id,
        filename="note.pdf",
        content_type="application/pdf",
        size_bytes=len(payload),
    )
    upload_id = reserved.json()["upload_id"]
    _put_and_complete(
        api_client,
        token=token,
        establishment_id=establishment.id,
        upload_id=upload_id,
        payload=payload,
    )
    client_message_id = uuid.uuid4()

    first = api_client.post(
        chat_url(establishment.id, f"conversations/{conversation_id}/messages/"),
        {
            "client_message_id": str(client_message_id),
            "body": "",
            "attachment_ids": [upload_id],
        },
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert first.status_code == 201
    assert first.json()["created"] is True
    message_id = first.json()["message"]["id"]

    message = (
        ChatMessage.objects.select_related(
            "author_membership",
            "author_membership__user",
            "conversation",
        )
        .prefetch_related("attachments__upload")
        .get(id=message_id)
    )
    json.dumps(build_message_created_payload(conversation_id=conversation_id, message=message))

    retry = api_client.post(
        chat_url(establishment.id, f"conversations/{conversation_id}/messages/"),
        {
            "client_message_id": str(client_message_id),
            "body": "",
            "attachment_ids": [upload_id],
        },
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert retry.status_code == 200
    assert retry.json()["created"] is False
    assert retry.json()["message"]["id"] == message_id
    assert ChatMessage.objects.filter(conversation_id=conversation_id).count() == 1
    assert ChatUpload.objects.get(id=upload_id).status == ChatUpload.Status.LINKED
    assert ChatMessageAttachment.objects.filter(message_id=message_id).count() == 1

    lookups = {"n": 0}

    def miss_then_hit(**kwargs):
        lookups["n"] += 1
        if lookups["n"] == 1:
            return None
        return ChatMessage.objects.select_related(
            "author_membership",
            "author_membership__user",
        ).get(
            conversation_id=kwargs["conversation_id"],
            author_membership_id=kwargs["author_membership_id"],
            client_message_id=kwargs["client_message_id"],
        )

    with patch("houston.chat.services._existing_client_message", side_effect=miss_then_hit):
        result = create_message(
            author_membership=sender_membership,
            establishment_id=establishment.id,
            conversation_id=conversation_id,
            client_message_id=client_message_id,
            body="",
            attachment_ids=[uuid.UUID(upload_id)],
        )
    assert result.created is False
    assert str(result.message.id) == message_id
    assert lookups["n"] == 2


def test_attachment_position_follows_client_attachment_ids(api_client, settings, tmp_path):
    settings.HOUSTON_PRIVATE_MEDIA_BACKEND = "filesystem"
    settings.HOUSTON_CHAT_PRIVATE_MEDIA_ROOT = str(tmp_path)
    establishment, _s, _r, _sm, _rm, token, conversation_id = _setup(api_client)
    payload = _pdf_bytes()
    first = _reserve(
        api_client,
        token=token,
        establishment_id=establishment.id,
        conversation_id=conversation_id,
        filename="first.pdf",
        content_type="application/pdf",
        size_bytes=len(payload),
    )
    first_id = first.json()["upload_id"]
    _put_and_complete(
        api_client,
        token=token,
        establishment_id=establishment.id,
        upload_id=first_id,
        payload=payload,
    )
    second = _reserve(
        api_client,
        token=token,
        establishment_id=establishment.id,
        conversation_id=conversation_id,
        filename="second.pdf",
        content_type="application/pdf",
        size_bytes=len(payload),
    )
    second_id = second.json()["upload_id"]
    _put_and_complete(
        api_client,
        token=token,
        establishment_id=establishment.id,
        upload_id=second_id,
        payload=payload,
    )
    older = timezone.now() - timedelta(minutes=5)
    ChatUpload.objects.filter(id=second_id).update(created_at=older)
    sent = api_client.post(
        chat_url(establishment.id, f"conversations/{conversation_id}/messages/"),
        {
            "client_message_id": str(uuid.uuid4()),
            "body": "",
            "attachment_ids": [first_id, second_id],
        },
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert sent.status_code == 201
    stored = list(
        ChatMessageAttachment.objects.filter(message_id=sent.json()["message"]["id"]).order_by(
            "position"
        )
    )
    assert [str(item.upload_id) for item in stored] == [first_id, second_id]
    assert [item.position for item in stored] == [0, 1]
