from __future__ import annotations

import uuid

import pytest
from houston.accounts.models import User
from houston.chat.models import ChatConversation, ChatMessage, ChatParticipant
from houston.chat.tests.conftest import (
    create_establishment,
    create_membership,
    create_user,
    login,
)
from houston.establishments.models import EstablishmentMembership

pytestmark = pytest.mark.django_db


def chat_url(establishment_id, suffix: str) -> str:
    return f"/api/v1/establishments/{establishment_id}/chat/{suffix}"


def create_dm(api_client, *, token: str, establishment_id, target_membership_id):
    return api_client.post(
        chat_url(establishment_id, "conversations/dm/"),
        {"membership_id": str(target_membership_id)},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )


def create_group(
    api_client,
    *,
    token: str,
    establishment_id,
    title: str,
    membership_ids: list,
):
    return api_client.post(
        chat_url(establishment_id, "conversations/groups/"),
        {"title": title, "membership_ids": [str(item) for item in membership_ids]},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )


@pytest.mark.parametrize(
    "role",
    [
        EstablishmentMembership.Role.MANAGER,
        EstablishmentMembership.Role.DIRECTOR,
        EstablishmentMembership.Role.OWNER,
    ],
)
def test_privileged_roles_can_create_group(api_client, role):
    establishment = create_establishment()
    creator = create_user(username=f"chat_group_{role}")
    other = create_user(username=f"chat_group_peer_{role}")
    create_membership(user=creator, establishment=establishment, role=role)
    other_membership = create_membership(user=other, establishment=establishment)
    token = login(api_client, user=creator)

    response = create_group(
        api_client,
        token=token,
        establishment_id=establishment.id,
        title=f"Group {role}",
        membership_ids=[other_membership.id],
    )

    assert response.status_code == 201
    assert response.json()["conversation"]["type"] == "group"


def test_dm_uses_canonical_membership_order(api_client):
    establishment = create_establishment()
    first = create_user(username="chat_dm_order_a")
    second = create_user(username="chat_dm_order_b")
    first_membership = create_membership(user=first, establishment=establishment)
    second_membership = create_membership(user=second, establishment=establishment)
    token = login(api_client, user=first)

    response = create_dm(
        api_client,
        token=token,
        establishment_id=establishment.id,
        target_membership_id=second_membership.id,
    )
    assert response.status_code == 201

    conversation = ChatConversation.objects.get(id=response.json()["conversation"]["id"])
    assert conversation.dm_membership_a_id == min(first_membership.id, second_membership.id)
    assert conversation.dm_membership_b_id == max(first_membership.id, second_membership.id)


def test_dm_rejects_foreign_establishment_membership(api_client):
    first_establishment = create_establishment()
    second_establishment = create_establishment()
    actor = create_user(username="chat_dm_foreign_actor")
    foreign_target = create_user(username="chat_dm_foreign_target")
    create_membership(user=actor, establishment=first_establishment)
    foreign_membership = create_membership(user=foreign_target, establishment=second_establishment)
    token = login(api_client, user=actor)

    response = create_dm(
        api_client,
        token=token,
        establishment_id=first_establishment.id,
        target_membership_id=foreign_membership.id,
    )

    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"


@pytest.mark.parametrize(
    "membership_status",
    [
        EstablishmentMembership.Status.INVITED,
        EstablishmentMembership.Status.DEACTIVATED,
    ],
)
def test_dm_rejects_ineligible_target_membership(api_client, membership_status):
    establishment = create_establishment()
    actor = create_user(username=f"chat_dm_actor_{membership_status}")
    target = create_user(username=f"chat_dm_target_{membership_status}")
    create_membership(user=actor, establishment=establishment)
    target_membership = create_membership(
        user=target,
        establishment=establishment,
        status=membership_status,
    )
    token = login(api_client, user=actor)

    response = create_dm(
        api_client,
        token=token,
        establishment_id=establishment.id,
        target_membership_id=target_membership.id,
    )

    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"


def test_dm_rejects_suspended_target_user(api_client):
    establishment = create_establishment()
    actor = create_user(username="chat_dm_actor_suspended")
    target = create_user(username="chat_dm_target_suspended", status=User.Status.SUSPENDED)
    create_membership(user=actor, establishment=establishment)
    target_membership = create_membership(user=target, establishment=establishment)
    token = login(api_client, user=actor)

    response = create_dm(
        api_client,
        token=token,
        establishment_id=establishment.id,
        target_membership_id=target_membership.id,
    )

    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"


def test_chat_disabled_blocks_access_endpoints(api_client):
    establishment = create_establishment(chat_enabled=False)
    user = create_user(username="chat_disabled_access")
    other = create_user(username="chat_disabled_other")
    create_membership(user=user, establishment=establishment)
    other_membership = create_membership(user=other, establishment=establishment)
    token = login(api_client, user=user)

    for suffix, method, payload in [
        ("conversations/", "get", None),
        ("conversations/dm/", "post", {"membership_id": str(other_membership.id)}),
        ("eligible-memberships/", "get", None),
    ]:
        request = getattr(api_client, method)
        kwargs = {"HTTP_AUTHORIZATION": f"Bearer {token}"}
        if payload is not None:
            response = request(chat_url(establishment.id, suffix), payload, format="json", **kwargs)
        else:
            response = request(chat_url(establishment.id, suffix), **kwargs)
        assert response.status_code == 403, suffix
        assert response.json()["code"] == "permission_denied"


def test_get_eligible_memberships_excludes_self_and_returns_peers(api_client):
    establishment = create_establishment()
    actor = create_user(username="chat_eligible_actor")
    peer = create_user(username="chat_eligible_peer")
    create_membership(user=actor, establishment=establishment)
    peer_membership = create_membership(user=peer, establishment=establishment)
    token = login(api_client, user=actor)

    response = api_client.get(
        chat_url(establishment.id, "eligible-memberships/"),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 200
    membership_ids = {item["membership_id"] for item in response.json()["items"]}
    assert str(peer_membership.id) in membership_ids
    assert len(membership_ids) == 1


def test_staff_cannot_patch_chat_settings(api_client):
    establishment = create_establishment(chat_enabled=True)
    staff = create_user(username="chat_settings_staff")
    create_membership(
        user=staff,
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    token = login(api_client, user=staff)

    response = api_client.patch(
        chat_url(establishment.id, "settings/"),
        {"chat_enabled": False},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"


def test_director_can_patch_chat_settings(api_client):
    establishment = create_establishment(chat_enabled=True)
    director = create_user(username="chat_settings_director")
    create_membership(
        user=director,
        establishment=establishment,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    token = login(api_client, user=director)

    response = api_client.patch(
        chat_url(establishment.id, "settings/"),
        {"chat_enabled": False},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 200
    assert response.json()["chat_enabled"] is False


def test_get_conversation_messages_is_read_only(api_client):
    establishment = create_establishment()
    sender = create_user(username="chat_messages_sender")
    receiver = create_user(username="chat_messages_receiver")
    sender_membership = create_membership(user=sender, establishment=establishment)
    receiver_membership = create_membership(user=receiver, establishment=establishment)
    token_sender = login(api_client, user=sender)

    dm_response = create_dm(
        api_client,
        token=token_sender,
        establishment_id=establishment.id,
        target_membership_id=receiver_membership.id,
    )
    conversation_id = dm_response.json()["conversation"]["id"]
    conversation = ChatConversation.objects.get(id=conversation_id)
    message = ChatMessage.objects.create(
        conversation=conversation,
        author_membership=sender_membership,
        body="stored via db for read test",
        client_message_id=uuid.uuid4(),
    )

    list_response = api_client.get(
        chat_url(establishment.id, f"conversations/{conversation_id}/messages/"),
        HTTP_AUTHORIZATION=f"Bearer {token_sender}",
    )
    assert list_response.status_code == 200
    items = list_response.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == str(message.id)
    assert items[0]["body"] == "stored via db for read test"

    post_response = api_client.post(
        chat_url(establishment.id, f"conversations/{conversation_id}/messages/"),
        {"body": "must not be accepted"},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token_sender}",
    )
    assert post_response.status_code == 405


def test_owner_outside_participation_cannot_delete_group(api_client):
    establishment = create_establishment()
    owner = create_user(username="chat_owner_delete_outside")
    manager = create_user(username="chat_manager_delete")
    staff = create_user(username="chat_staff_delete")
    create_membership(
        user=owner,
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
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
    token_manager = login(api_client, user=manager)

    group_response = create_group(
        api_client,
        token=token_manager,
        establishment_id=establishment.id,
        title="Ops",
        membership_ids=[staff_membership.id],
    )
    conversation_id = group_response.json()["conversation"]["id"]

    token_owner = login(api_client, user=owner)
    delete_response = api_client.delete(
        chat_url(establishment.id, f"conversations/{conversation_id}/"),
        HTTP_AUTHORIZATION=f"Bearer {token_owner}",
    )
    assert delete_response.status_code == 404


def test_group_participant_add_remove_promote_and_leave(api_client):
    establishment = create_establishment()
    manager = create_user(username="chat_group_admin")
    staff_a = create_user(username="chat_group_staff_a")
    staff_b = create_user(username="chat_group_staff_b")
    staff_c = create_user(username="chat_group_staff_c")
    create_membership(
        user=manager,
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
    )
    staff_a_membership = create_membership(
        user=staff_a,
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    staff_b_membership = create_membership(
        user=staff_b,
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    staff_c_membership = create_membership(
        user=staff_c,
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    token_manager = login(api_client, user=manager)

    group_response = create_group(
        api_client,
        token=token_manager,
        establishment_id=establishment.id,
        title="Shift",
        membership_ids=[staff_a_membership.id, staff_b_membership.id],
    )
    conversation_id = group_response.json()["conversation"]["id"]

    add_response = api_client.post(
        chat_url(establishment.id, f"conversations/{conversation_id}/participants/"),
        {"membership_id": str(staff_c_membership.id)},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token_manager}",
    )
    assert add_response.status_code == 201

    promote_response = api_client.post(
        chat_url(
            establishment.id,
            f"conversations/{conversation_id}/participants/{staff_b_membership.id}/promote/",
        ),
        HTTP_AUTHORIZATION=f"Bearer {token_manager}",
    )
    assert promote_response.status_code == 204
    promoted = ChatParticipant.objects.get(
        conversation_id=conversation_id,
        membership=staff_b_membership,
    )
    assert promoted.role == ChatParticipant.Role.ADMIN

    remove_response = api_client.delete(
        chat_url(
            establishment.id,
            f"conversations/{conversation_id}/participants/{staff_c_membership.id}/",
        ),
        HTTP_AUTHORIZATION=f"Bearer {token_manager}",
    )
    assert remove_response.status_code == 204
    removed = ChatParticipant.objects.get(
        conversation_id=conversation_id,
        membership=staff_c_membership,
    )
    assert removed.left_at is not None

    token_staff_a = login(api_client, user=staff_a)
    leave_response = api_client.post(
        chat_url(establishment.id, f"conversations/{conversation_id}/leave/"),
        HTTP_AUTHORIZATION=f"Bearer {token_staff_a}",
    )
    assert leave_response.status_code == 204
    left = ChatParticipant.objects.get(
        conversation_id=conversation_id,
        membership=staff_a_membership,
    )
    assert left.left_at is not None


def test_chat_status_when_disabled(api_client):
    establishment = create_establishment(chat_enabled=False)
    user = create_user(username="chat_status_disabled")
    create_membership(user=user, establishment=establishment)
    token = login(api_client, user=user)

    response = api_client.get(
        chat_url(establishment.id, "status/"),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["chat_enabled"] is False
    assert body["can_access"] is False


def test_staff_can_create_dm(api_client):
    establishment = create_establishment()
    staff = create_user(username="chat_staff")
    target = create_user(username="chat_target")
    create_membership(
        user=staff,
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    target_membership = create_membership(user=target, establishment=establishment)
    token = login(api_client, user=staff)

    response = api_client.post(
        chat_url(establishment.id, "conversations/dm/"),
        {"membership_id": str(target_membership.id)},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["created"] is True
    assert body["conversation"]["type"] == "dm"
    assert len(body["conversation"]["participants"]) == 2

    replay = api_client.post(
        chat_url(establishment.id, "conversations/dm/"),
        {"membership_id": str(target_membership.id)},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert replay.status_code == 200
    assert replay.json()["created"] is False


def test_staff_cannot_create_group(api_client):
    establishment = create_establishment()
    staff = create_user(username="chat_staff_group")
    other = create_user(username="chat_other")
    create_membership(
        user=staff,
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    other_membership = create_membership(user=other, establishment=establishment)
    token = login(api_client, user=staff)

    response = api_client.post(
        chat_url(establishment.id, "conversations/groups/"),
        {
            "title": "Ops",
            "membership_ids": [str(other_membership.id)],
        },
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"


def test_manager_can_create_group(api_client):
    establishment = create_establishment()
    manager = create_user(username="chat_manager")
    other = create_user(username="chat_group_other")
    create_membership(
        user=manager,
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
    )
    other_membership = create_membership(user=other, establishment=establishment)
    token = login(api_client, user=manager)

    response = api_client.post(
        chat_url(establishment.id, "conversations/groups/"),
        {
            "title": "Morning Brief",
            "membership_ids": [str(other_membership.id)],
        },
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 201
    assert response.json()["conversation"]["title"] == "Morning Brief"


def test_owner_outside_participation_gets_404(api_client):
    establishment = create_establishment()
    owner = create_user(username="chat_owner_outside")
    staff_a = create_user(username="chat_staff_a")
    staff_b = create_user(username="chat_staff_b")
    create_membership(
        user=owner,
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    create_membership(
        user=staff_a,
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    membership_b = create_membership(
        user=staff_b,
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    token_a = login(api_client, user=staff_a)

    dm_response = api_client.post(
        chat_url(establishment.id, "conversations/dm/"),
        {"membership_id": str(membership_b.id)},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token_a}",
    )
    conversation_id = dm_response.json()["conversation"]["id"]

    token_owner = login(api_client, user=owner)
    response = api_client.get(
        chat_url(establishment.id, f"conversations/{conversation_id}/"),
        HTTP_AUTHORIZATION=f"Bearer {token_owner}",
    )

    assert response.status_code == 404


def test_unread_survives_message_purge(api_client):
    establishment = create_establishment()
    sender = create_user(username="chat_sender")
    receiver = create_user(username="chat_receiver")
    sender_membership = create_membership(user=sender, establishment=establishment)
    receiver_membership = create_membership(user=receiver, establishment=establishment)
    token_sender = login(api_client, user=sender)

    dm_response = api_client.post(
        chat_url(establishment.id, "conversations/dm/"),
        {"membership_id": str(receiver_membership.id)},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token_sender}",
    )
    conversation_id = dm_response.json()["conversation"]["id"]
    conversation = ChatConversation.objects.get(id=conversation_id)

    message = ChatMessage.objects.create(
        conversation=conversation,
        author_membership=sender_membership,
        body="hello",
        client_message_id=uuid.uuid4(),
    )
    conversation.last_message_at = message.created_at
    conversation.save(update_fields=["last_message_at", "updated_at"])

    token_receiver = login(api_client, user=receiver)
    list_response = api_client.get(
        chat_url(establishment.id, "conversations/"),
        HTTP_AUTHORIZATION=f"Bearer {token_receiver}",
    )
    assert list_response.json()["items"][0]["unread"] is True

    seen_response = api_client.post(
        chat_url(establishment.id, f"conversations/{conversation_id}/seen/"),
        HTTP_AUTHORIZATION=f"Bearer {token_receiver}",
    )
    assert seen_response.status_code == 204

    participant = ChatParticipant.objects.get(
        conversation_id=conversation_id,
        membership=receiver_membership,
    )
    assert participant.last_seen_message_id == message.id
    assert participant.last_seen_message_created_at == message.created_at

    message.delete()
    list_response_after_purge = api_client.get(
        chat_url(establishment.id, "conversations/"),
        HTTP_AUTHORIZATION=f"Bearer {token_receiver}",
    )
    assert list_response_after_purge.json()["items"][0]["unread"] is False


def test_mark_seen_without_messages_is_noop(api_client):
    establishment = create_establishment()
    user = create_user(username="chat_seen_noop")
    other = create_user(username="chat_seen_other")
    create_membership(user=user, establishment=establishment)
    other_membership = create_membership(user=other, establishment=establishment)
    token = login(api_client, user=user)

    dm_response = api_client.post(
        chat_url(establishment.id, "conversations/dm/"),
        {"membership_id": str(other_membership.id)},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    conversation_id = dm_response.json()["conversation"]["id"]

    seen_response = api_client.post(
        chat_url(establishment.id, f"conversations/{conversation_id}/seen/"),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert seen_response.status_code == 204


def test_owner_can_toggle_chat_enabled(api_client):
    establishment = create_establishment(chat_enabled=True)
    owner = create_user(username="chat_owner_toggle")
    create_membership(
        user=owner,
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    token = login(api_client, user=owner)

    response = api_client.patch(
        chat_url(establishment.id, "settings/"),
        {"chat_enabled": False},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 200
    assert response.json()["chat_enabled"] is False
    establishment.refresh_from_db()
    assert establishment.chat_enabled is False


def test_owner_can_re_enable_chat_after_disable(api_client):
    establishment = create_establishment(chat_enabled=False)
    owner = create_user(username="chat_owner_reenable")
    create_membership(
        user=owner,
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    token = login(api_client, user=owner)

    response = api_client.patch(
        chat_url(establishment.id, "settings/"),
        {"chat_enabled": True},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 200
    assert response.json()["chat_enabled"] is True
    establishment.refresh_from_db()
    assert establishment.chat_enabled is True


def test_director_can_re_enable_chat_after_disable(api_client):
    establishment = create_establishment(chat_enabled=False)
    director = create_user(username="chat_director_reenable")
    create_membership(
        user=director,
        establishment=establishment,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    token = login(api_client, user=director)

    response = api_client.patch(
        chat_url(establishment.id, "settings/"),
        {"chat_enabled": True},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 200
    assert response.json()["chat_enabled"] is True
