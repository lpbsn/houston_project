from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from django.utils import timezone
from houston.chat.models import (
    ChatConversation,
    ChatMessage,
    ChatMessageAttachment,
    ChatParticipant,
    ChatUpload,
)
from houston.chat.tests.conftest import create_establishment, create_membership, create_user, login
from houston.chat.tests.helpers import chat_url, create_dm, create_group
from houston.chat.upload_services import chat_upload_storage_key
from houston.establishments.models import EstablishmentMembership
from houston.establishments.services import (
    MembershipManagementForbiddenError,
    deactivate_membership_for_management,
)
from houston.testing.taxonomy import (
    create_business_unit,
    create_membership_with_business_unit_scope,
)


@pytest.mark.django_db
def test_membership_deactivation_deletes_dm_conversations(api_client):
    establishment = create_establishment()
    owner = create_user(username="chat_deactivate_owner")
    staff = create_user(username="chat_deactivate_staff")
    owner_membership = create_membership(
        user=owner,
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    staff_membership = create_membership(
        user=staff,
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    token = login(api_client, user=staff)

    dm_response = create_dm(
        api_client,
        token=token,
        establishment_id=establishment.id,
        target_membership_id=owner_membership.id,
    )
    conversation_id = dm_response.json()["conversation"]["id"]
    assert ChatConversation.objects.filter(id=conversation_id).exists()

    deactivate_membership_for_management(
        current_membership=owner_membership,
        establishment_id=establishment.id,
        membership_id=staff_membership.id,
    )

    assert not ChatConversation.objects.filter(id=conversation_id).exists()


@pytest.mark.django_db(transaction=True)
def test_membership_deactivation_deletes_dm_with_attachment(api_client, monkeypatch):
    establishment = create_establishment()
    owner = create_user(username="chat_deactivate_attach_owner")
    staff = create_user(username="chat_deactivate_attach_staff")
    owner_membership = create_membership(
        user=owner,
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    staff_membership = create_membership(
        user=staff,
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    token = login(api_client, user=staff)
    dm_response = create_dm(
        api_client,
        token=token,
        establishment_id=establishment.id,
        target_membership_id=owner_membership.id,
    )
    conversation = ChatConversation.objects.get(id=dm_response.json()["conversation"]["id"])
    message = ChatMessage.objects.create(
        conversation=conversation,
        author_membership=staff_membership,
        body="",
        client_message_id=uuid.uuid4(),
    )
    storage_key = chat_upload_storage_key(
        establishment_id=establishment.id,
        conversation_id=conversation.id,
        upload_id=uuid.uuid4(),
        filename="note.pdf",
    )
    upload = ChatUpload.objects.create(
        establishment=establishment,
        conversation=conversation,
        uploaded_by_membership=staff_membership,
        original_filename="note.pdf",
        declared_content_type="application/pdf",
        declared_size_bytes=4,
        storage_key=storage_key,
        expires_at=timezone.now() + timedelta(hours=1),
        status=ChatUpload.Status.LINKED,
    )
    ChatMessageAttachment.objects.create(
        message=message,
        upload=upload,
        position=0,
        kind="document",
        content_type="application/pdf",
        size_bytes=4,
        original_filename="note.pdf",
    )
    deleted_keys: list[str] = []
    monkeypatch.setattr(
        "houston.chat.upload_services.delete_chat_storage_keys",
        lambda keys: deleted_keys.extend(keys),
    )

    deactivate_membership_for_management(
        current_membership=owner_membership,
        establishment_id=establishment.id,
        membership_id=staff_membership.id,
    )

    assert not ChatConversation.objects.filter(id=conversation.id).exists()
    assert not ChatUpload.objects.filter(id=upload.id).exists()
    assert not ChatMessage.objects.filter(id=message.id).exists()
    assert not ChatMessageAttachment.objects.filter(message_id=message.id).exists()
    assert storage_key in deleted_keys


@pytest.mark.django_db
def test_membership_deactivation_removes_group_participant(api_client):
    establishment = create_establishment()
    manager = create_user(username="chat_deactivate_manager")
    staff = create_user(username="chat_deactivate_group_staff")
    manager_membership = create_membership(
        user=manager,
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
    )
    staff_membership = create_membership(
        user=staff,
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    housekeeping = create_business_unit(
        establishment=establishment,
        key="housekeeping",
        label="Housekeeping",
    )
    create_membership_with_business_unit_scope(
        membership=manager_membership,
        business_unit=housekeeping,
    )
    create_membership_with_business_unit_scope(
        membership=staff_membership,
        business_unit=housekeeping,
    )
    token = login(api_client, user=manager)

    group_response = create_group(
        api_client,
        token=token,
        establishment_id=establishment.id,
        title="Ops",
        membership_ids=[staff_membership.id],
    )
    conversation_id = group_response.json()["conversation"]["id"]

    deactivate_membership_for_management(
        current_membership=manager_membership,
        establishment_id=establishment.id,
        membership_id=staff_membership.id,
    )

    participant = ChatParticipant.objects.get(
        conversation_id=conversation_id,
        membership=staff_membership,
    )
    assert participant.left_at is not None
    assert ChatConversation.objects.filter(id=conversation_id).exists()


@pytest.mark.django_db
def test_membership_deactivation_forbidden_leaves_chat_unchanged(api_client):
    establishment = create_establishment()
    manager = create_user(username="chat_forbidden_manager")
    staff = create_user(username="chat_forbidden_staff")
    manager_membership = create_membership(
        user=manager,
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
    )
    staff_membership = create_membership(
        user=staff,
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    actor_unit = create_business_unit(
        establishment=establishment,
        key="housekeeping",
        label="Housekeeping",
    )
    foreign_unit = create_business_unit(
        establishment=establishment,
        key="security",
        label="Security",
    )
    create_membership_with_business_unit_scope(
        membership=manager_membership,
        business_unit=actor_unit,
    )
    create_membership_with_business_unit_scope(
        membership=staff_membership,
        business_unit=foreign_unit,
    )
    token = login(api_client, user=manager)

    group_response = create_group(
        api_client,
        token=token,
        establishment_id=establishment.id,
        title="Ops",
        membership_ids=[staff_membership.id],
    )
    conversation_id = group_response.json()["conversation"]["id"]

    with pytest.raises(MembershipManagementForbiddenError):
        deactivate_membership_for_management(
            current_membership=manager_membership,
            establishment_id=establishment.id,
            membership_id=staff_membership.id,
        )

    participant = ChatParticipant.objects.get(
        conversation_id=conversation_id,
        membership=staff_membership,
    )
    assert participant.left_at is None
    assert ChatConversation.objects.filter(id=conversation_id).exists()


@pytest.mark.django_db
def test_group_promotes_new_admin_when_last_admin_leaves(api_client):
    establishment = create_establishment()
    manager = create_user(username="chat_admin_manager")
    staff = create_user(username="chat_admin_staff")
    create_membership(
        user=manager,
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
    )
    staff_membership = create_membership(
        user=staff,
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    token = login(api_client, user=manager)

    group_response = create_group(
        api_client,
        token=token,
        establishment_id=establishment.id,
        title="Shift",
        membership_ids=[staff_membership.id],
    )
    conversation_id = group_response.json()["conversation"]["id"]

    leave_response = api_client.post(
        chat_url(establishment.id, f"conversations/{conversation_id}/leave/"),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert leave_response.status_code == 204

    staff_participant = ChatParticipant.objects.get(
        conversation_id=conversation_id,
        membership=staff_membership,
    )
    assert staff_participant.role == ChatParticipant.Role.ADMIN
