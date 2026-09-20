from __future__ import annotations

import io
import uuid
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone
from houston.chat.models import ChatMessage, ChatMessageAttachment, ChatUpload
from houston.chat.tests.conftest import create_establishment, create_membership, create_user, login
from houston.chat.tests.helpers import chat_url, create_dm, send_message
from houston.chat.upload_services import generate_chat_upload_thumbnail
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
    return establishment, sender, receiver, sender_membership, receiver_membership, token, conversation_id


def _reserve(api_client, *, token, establishment_id, conversation_id, filename, content_type, size_bytes):
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


def test_orphan_cleanup_deletes_expired_reserved(settings, tmp_path):
    settings.HOUSTON_PRIVATE_MEDIA_BACKEND = "filesystem"
    settings.HOUSTON_CHAT_PRIVATE_MEDIA_ROOT = str(tmp_path)
    from houston.chat.tasks import cleanup_chat_upload_orphans_task
    from houston.chat.tests.helpers import create_dm as create_dm_helper

    establishment = create_establishment()
    sender = create_user(username="chat_orphan_sender")
    peer = create_user(username="chat_orphan_peer")
    sender_membership = create_membership(user=sender, establishment=establishment)
    peer_membership = create_membership(user=peer, establishment=establishment)
    from houston.chat.services import create_or_get_dm_conversation

    conversation, _ = create_or_get_dm_conversation(
        actor_membership=sender_membership,
        target_membership_id=peer_membership.id,
    )
    upload = ChatUpload.objects.create(
        establishment=establishment,
        conversation=conversation,
        uploaded_by_membership=sender_membership,
        original_filename="gone.png",
        declared_content_type="image/png",
        declared_size_bytes=10,
        storage_key="establishments/x/chat/y/z/original.png",
        expires_at=timezone.now() - timedelta(hours=1),
    )
    deleted = cleanup_chat_upload_orphans_task.run()
    assert deleted >= 1
    assert not ChatUpload.objects.filter(id=upload.id).exists()
    _ = create_dm_helper


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
