from __future__ import annotations

import uuid

from django.db import transaction
from houston.chat.models import ChatMessage, ChatUpload
from houston.chat.purge import _refresh_last_message_at
from houston.chat.upload_services import chat_object_keys_for_uploads, delete_chat_storage_keys


def delete_messages_authored_by_memberships(*, membership_ids: list[uuid.UUID]) -> None:
    if not membership_ids:
        return
    conversation_ids = list(
        ChatMessage.objects.filter(author_membership_id__in=membership_ids)
        .values_list("conversation_id", flat=True)
        .distinct()
    )
    uploads = list(
        ChatUpload.objects.filter(uploaded_by_membership_id__in=membership_ids)
    )
    storage_keys = chat_object_keys_for_uploads(uploads)
    upload_ids = [upload.id for upload in uploads]
    ChatMessage.objects.filter(author_membership_id__in=membership_ids).delete()
    if upload_ids:
        ChatUpload.objects.filter(id__in=upload_ids).delete()
    if storage_keys:
        captured_keys = list(storage_keys)
        transaction.on_commit(lambda: delete_chat_storage_keys(captured_keys))
    if conversation_ids:
        _refresh_last_message_at(conversation_ids=conversation_ids)
