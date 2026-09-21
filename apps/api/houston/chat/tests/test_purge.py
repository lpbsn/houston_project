from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from django.utils import timezone
from houston.chat.account_deletion import delete_messages_authored_by_memberships
from houston.chat.models import ChatConversation, ChatMessage, ChatUpload
from houston.chat.purge import purge_chat_messages
from houston.chat.tasks import purge_chat_messages_task
from houston.chat.tests.conftest import create_establishment, create_membership, create_user, login
from houston.chat.tests.helpers import create_dm
from houston.chat.upload_services import chat_upload_storage_key


@pytest.mark.django_db
def test_purge_deletes_messages_older_than_retention_window(api_client):
    establishment = create_establishment()
    sender = create_user(username="chat_purge_sender")
    receiver = create_user(username="chat_purge_receiver")
    sender_membership = create_membership(user=sender, establishment=establishment)
    receiver_membership = create_membership(user=receiver, establishment=establishment)
    token = login(api_client, user=sender)

    dm_response = create_dm(
        api_client,
        token=token,
        establishment_id=establishment.id,
        target_membership_id=receiver_membership.id,
    )
    conversation = ChatConversation.objects.get(id=dm_response.json()["conversation"]["id"])

    old_message = ChatMessage.objects.create(
        conversation=conversation,
        author_membership=sender_membership,
        body="old",
        client_message_id=uuid.uuid4(),
    )
    recent_message = ChatMessage.objects.create(
        conversation=conversation,
        author_membership=sender_membership,
        body="recent",
        client_message_id=uuid.uuid4(),
    )
    old_created_at = timezone.now() - timedelta(days=31)
    recent_created_at = timezone.now() - timedelta(days=2)
    ChatMessage.objects.filter(id=old_message.id).update(created_at=old_created_at)
    ChatMessage.objects.filter(id=recent_message.id).update(created_at=recent_created_at)
    conversation.last_message_at = recent_created_at
    conversation.save(update_fields=["last_message_at", "updated_at"])

    dry_run = purge_chat_messages(dry_run=True)
    assert dry_run.deleted_count == 1
    assert dry_run.dry_run is True
    assert ChatMessage.objects.filter(id=old_message.id).exists()
    assert ChatMessage.objects.filter(id=recent_message.id).exists()

    result = purge_chat_messages(dry_run=False)
    assert result.deleted_count == 1
    assert result.batch_count == 1
    assert not ChatMessage.objects.filter(id=old_message.id).exists()
    assert ChatMessage.objects.filter(id=recent_message.id).exists()

    conversation.refresh_from_db()
    assert conversation.last_message_at == recent_created_at


@pytest.mark.django_db
def test_purge_can_be_scoped_to_establishment():
    establishment_a = create_establishment()
    establishment_b = create_establishment()
    user_a = create_user(username="chat_purge_a")
    user_a_peer = create_user(username="chat_purge_a_peer")
    user_b = create_user(username="chat_purge_b")
    user_b_peer = create_user(username="chat_purge_b_peer")
    membership_a = create_membership(user=user_a, establishment=establishment_a)
    membership_a_peer = create_membership(user=user_a_peer, establishment=establishment_a)
    membership_b = create_membership(user=user_b, establishment=establishment_b)
    membership_b_peer = create_membership(user=user_b_peer, establishment=establishment_b)

    conversation_a = ChatConversation.objects.create(
        establishment=establishment_a,
        type=ChatConversation.Type.DM,
        created_by_membership=membership_a,
        dm_membership_a=membership_a,
        dm_membership_b=membership_a_peer,
    )
    conversation_b = ChatConversation.objects.create(
        establishment=establishment_b,
        type=ChatConversation.Type.DM,
        created_by_membership=membership_b,
        dm_membership_a=membership_b,
        dm_membership_b=membership_b_peer,
    )

    message_a = ChatMessage.objects.create(
        conversation=conversation_a,
        author_membership=membership_a,
        body="a",
        client_message_id=uuid.uuid4(),
    )
    message_b = ChatMessage.objects.create(
        conversation=conversation_b,
        author_membership=membership_b,
        body="b",
        client_message_id=uuid.uuid4(),
    )
    old_created_at = timezone.now() - timedelta(days=31)
    ChatMessage.objects.filter(id=message_a.id).update(created_at=old_created_at)
    ChatMessage.objects.filter(id=message_b.id).update(created_at=old_created_at)

    result = purge_chat_messages(establishment_id=establishment_a.id, dry_run=False)
    assert result.deleted_count == 1
    assert not ChatMessage.objects.filter(id=message_a.id).exists()
    assert ChatMessage.objects.filter(id=message_b.id).exists()


@pytest.mark.django_db
def test_purge_chat_messages_task_deletes_old_messages():
    establishment = create_establishment()
    sender = create_user(username="chat_purge_task_sender")
    receiver = create_user(username="chat_purge_task_receiver")
    sender_membership = create_membership(user=sender, establishment=establishment)
    receiver_membership = create_membership(user=receiver, establishment=establishment)
    conversation = ChatConversation.objects.create(
        establishment=establishment,
        type=ChatConversation.Type.DM,
        created_by_membership=sender_membership,
        dm_membership_a=sender_membership,
        dm_membership_b=receiver_membership,
    )
    old_message = ChatMessage.objects.create(
        conversation=conversation,
        author_membership=sender_membership,
        body="old",
        client_message_id=uuid.uuid4(),
    )
    old_created_at = timezone.now() - timedelta(days=31)
    ChatMessage.objects.filter(id=old_message.id).update(created_at=old_created_at)

    deleted_count = purge_chat_messages_task.run()
    assert deleted_count == 1
    assert not ChatMessage.objects.filter(id=old_message.id).exists()


@pytest.mark.django_db
def test_purge_respects_retention_setting(settings):
    settings.HOUSTON_CHAT_MESSAGE_RETENTION_DAYS = 7
    establishment = create_establishment()
    sender = create_user(username="chat_purge_setting_sender")
    receiver = create_user(username="chat_purge_setting_receiver")
    sender_membership = create_membership(user=sender, establishment=establishment)
    receiver_membership = create_membership(user=receiver, establishment=establishment)
    conversation = ChatConversation.objects.create(
        establishment=establishment,
        type=ChatConversation.Type.DM,
        created_by_membership=sender_membership,
        dm_membership_a=sender_membership,
        dm_membership_b=receiver_membership,
    )
    old_message = ChatMessage.objects.create(
        conversation=conversation,
        author_membership=sender_membership,
        body="old",
        client_message_id=uuid.uuid4(),
    )
    ChatMessage.objects.filter(id=old_message.id).update(
        created_at=timezone.now() - timedelta(days=8)
    )

    result = purge_chat_messages(dry_run=False)
    assert result.deleted_count == 1
    assert not ChatMessage.objects.filter(id=old_message.id).exists()


@pytest.mark.django_db(transaction=True)
def test_purge_deletes_attachment_storage(settings, tmp_path, monkeypatch):
    settings.HOUSTON_PRIVATE_MEDIA_BACKEND = "filesystem"
    settings.HOUSTON_CHAT_PRIVATE_MEDIA_ROOT = str(tmp_path)
    establishment = create_establishment()
    sender = create_user(username="chat_purge_attach_sender")
    receiver = create_user(username="chat_purge_attach_receiver")
    sender_membership = create_membership(user=sender, establishment=establishment)
    receiver_membership = create_membership(user=receiver, establishment=establishment)
    conversation = ChatConversation.objects.create(
        establishment=establishment,
        type=ChatConversation.Type.DM,
        created_by_membership=sender_membership,
        dm_membership_a=sender_membership,
        dm_membership_b=receiver_membership,
    )
    message = ChatMessage.objects.create(
        conversation=conversation,
        author_membership=sender_membership,
        body="",
        client_message_id=uuid.uuid4(),
    )
    ChatMessage.objects.filter(id=message.id).update(
        created_at=timezone.now() - timedelta(days=31)
    )
    storage_key = chat_upload_storage_key(
        establishment_id=establishment.id,
        conversation_id=conversation.id,
        upload_id=uuid.uuid4(),
        filename="old.png",
    )
    upload = ChatUpload.objects.create(
        establishment=establishment,
        conversation=conversation,
        uploaded_by_membership=sender_membership,
        original_filename="old.png",
        declared_content_type="image/png",
        declared_size_bytes=4,
        storage_key=storage_key,
        expires_at=timezone.now() + timedelta(hours=1),
        status=ChatUpload.Status.LINKED,
    )
    from houston.chat.models import ChatMessageAttachment

    ChatMessageAttachment.objects.create(
        message=message,
        upload=upload,
        position=0,
        kind="image",
        content_type="image/png",
        size_bytes=4,
        original_filename="old.png",
    )
    deleted_keys: list[str] = []
    monkeypatch.setattr(
        "houston.chat.purge.delete_chat_storage_keys",
        lambda keys: deleted_keys.extend(keys),
    )

    from django.db import transaction

    with transaction.atomic():
        result = purge_chat_messages(dry_run=False)
    assert result.deleted_count >= 1
    assert not ChatMessage.objects.filter(id=message.id).exists()
    assert not ChatUpload.objects.filter(id=upload.id).exists()
    assert storage_key in deleted_keys


@pytest.mark.django_db(transaction=True)
def test_account_deletion_deletes_chat_storage(settings, tmp_path, monkeypatch):
    settings.HOUSTON_PRIVATE_MEDIA_BACKEND = "filesystem"
    settings.HOUSTON_CHAT_PRIVATE_MEDIA_ROOT = str(tmp_path)
    establishment = create_establishment()
    sender = create_user(username="chat_delete_attach_sender")
    receiver = create_user(username="chat_delete_attach_receiver")
    sender_membership = create_membership(user=sender, establishment=establishment)
    receiver_membership = create_membership(user=receiver, establishment=establishment)
    conversation = ChatConversation.objects.create(
        establishment=establishment,
        type=ChatConversation.Type.DM,
        created_by_membership=sender_membership,
        dm_membership_a=sender_membership,
        dm_membership_b=receiver_membership,
    )
    message = ChatMessage.objects.create(
        conversation=conversation,
        author_membership=sender_membership,
        body="bye",
        client_message_id=uuid.uuid4(),
    )
    storage_key = chat_upload_storage_key(
        establishment_id=establishment.id,
        conversation_id=conversation.id,
        upload_id=uuid.uuid4(),
        filename="bye.png",
    )
    upload = ChatUpload.objects.create(
        establishment=establishment,
        conversation=conversation,
        uploaded_by_membership=sender_membership,
        original_filename="bye.png",
        declared_content_type="image/png",
        declared_size_bytes=4,
        storage_key=storage_key,
        expires_at=timezone.now() + timedelta(hours=1),
        status=ChatUpload.Status.LINKED,
    )
    from houston.chat.models import ChatMessageAttachment

    ChatMessageAttachment.objects.create(
        message=message,
        upload=upload,
        position=0,
        kind="image",
        content_type="image/png",
        size_bytes=4,
        original_filename="bye.png",
    )
    deleted_keys: list[str] = []
    monkeypatch.setattr(
        "houston.chat.account_deletion.delete_chat_storage_keys",
        lambda keys: deleted_keys.extend(keys),
    )

    from django.db import transaction

    with transaction.atomic():
        delete_messages_authored_by_memberships(membership_ids=[sender_membership.id])
    assert not ChatMessage.objects.filter(id=message.id).exists()
    assert not ChatUpload.objects.filter(id=upload.id).exists()
    assert storage_key in deleted_keys


def test_beat_schedule_includes_chat_purge_and_orphans():
    from django.conf import settings as django_settings

    tasks = {
        entry["task"] for entry in django_settings.CELERY_BEAT_SCHEDULE.values()
    }
    assert "houston.chat.tasks.purge_chat_messages_task" in tasks
    assert "houston.chat.tasks.cleanup_chat_upload_orphans_task" in tasks
