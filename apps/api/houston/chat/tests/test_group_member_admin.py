from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from config.asgi import application
from django.db import close_old_connections
from houston.chat.models import ChatParticipant
from houston.chat.services import (
    add_group_participant,
    leave_group_conversation,
    promote_group_participant,
    remove_group_participant,
)
from houston.chat.tests.conftest import (
    create_establishment,
    create_membership,
    create_user,
    default_ws_headers,
    get_ws_ticket,
    login,
)
from houston.chat.tests.helpers import chat_url, create_group
from houston.establishments.models import EstablishmentMembership
from houston.establishments.services import deactivate_membership_for_management


async def _connect_authenticated(*, ticket: str, establishment):
    communicator = WebsocketCommunicator(
        application,
        f"/ws/v1/establishments/{establishment.id}/chat/",
        headers=default_ws_headers(),
    )
    connected, _ = await communicator.connect()
    assert connected
    await communicator.send_json_to({"type": "auth", "ticket": ticket})
    auth_event = await communicator.receive_json_from()
    assert auth_event["type"] == "auth.ok"
    return communicator


@pytest.mark.django_db
def test_member_cannot_manage_group_participants(api_client):
    establishment = create_establishment()
    manager = create_user(username="chat_lot2_admin")
    staff = create_user(username="chat_lot2_member")
    peer = create_user(username="chat_lot2_peer")
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
    peer_membership = create_membership(
        user=peer,
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

    token_staff = login(api_client, user=staff)
    add_response = api_client.post(
        chat_url(establishment.id, f"conversations/{conversation_id}/participants/"),
        {"membership_id": str(peer_membership.id)},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token_staff}",
    )
    assert add_response.status_code == 403

    promote_response = api_client.post(
        chat_url(
            establishment.id,
            f"conversations/{conversation_id}/participants/{staff_membership.id}/promote/",
        ),
        HTTP_AUTHORIZATION=f"Bearer {token_staff}",
    )
    assert promote_response.status_code == 403

    remove_response = api_client.delete(
        chat_url(
            establishment.id,
            f"conversations/{conversation_id}/participants/{peer_membership.id}/",
        ),
        HTTP_AUTHORIZATION=f"Bearer {token_staff}",
    )
    assert remove_response.status_code == 403


@pytest.mark.django_db
def test_admin_cannot_self_remove_via_participants_endpoint(api_client):
    establishment = create_establishment()
    manager = create_user(username="chat_lot2_self_admin")
    staff = create_user(username="chat_lot2_self_staff")
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
    token = login(api_client, user=manager)
    group_response = create_group(
        api_client,
        token=token,
        establishment_id=establishment.id,
        title="Ops",
        membership_ids=[staff_membership.id],
    )
    conversation_id = group_response.json()["conversation"]["id"]

    response = api_client.delete(
        chat_url(
            establishment.id,
            f"conversations/{conversation_id}/participants/{manager_membership.id}/",
        ),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"


@pytest.mark.django_db
def test_reintegrate_former_participant_resets_role_and_pin(api_client):
    establishment = create_establishment()
    manager = create_user(username="chat_lot2_rejoin_admin")
    staff = create_user(username="chat_lot2_rejoin_staff")
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
        title="Ops",
        membership_ids=[staff_membership.id],
    )
    conversation_id = uuid.UUID(group_response.json()["conversation"]["id"])

    participant = ChatParticipant.objects.get(
        conversation_id=conversation_id,
        membership=staff_membership,
    )
    participant.pinned_at = participant.joined_at
    participant.role = ChatParticipant.Role.ADMIN
    participant.save(update_fields=["pinned_at", "role", "updated_at"])

    remove_response = api_client.delete(
        chat_url(
            establishment.id,
            f"conversations/{conversation_id}/participants/{staff_membership.id}/",
        ),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert remove_response.status_code == 204

    add_response = api_client.post(
        chat_url(establishment.id, f"conversations/{conversation_id}/participants/"),
        {"membership_id": str(staff_membership.id)},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert add_response.status_code == 201

    rejoined = ChatParticipant.objects.get(
        conversation_id=conversation_id,
        membership=staff_membership,
    )
    assert rejoined.left_at is None
    assert rejoined.role == ChatParticipant.Role.MEMBER
    assert rejoined.pinned_at is None


@pytest.mark.django_db
def test_eligible_memberships_exclude_active_participants_before_limit(api_client):
    establishment = create_establishment()
    actor = create_user(username="zzz_eligible_actor")
    actor.first_name = "Zzz"
    actor.last_name = "Actor"
    actor.save(update_fields=["first_name", "last_name"])
    actor_membership = create_membership(
        user=actor,
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
    )
    active_memberships = []
    for index in range(5):
        user = create_user(username=f"aaa_active_{index:03d}")
        user.first_name = "Aaa"
        user.last_name = f"Active{index:03d}"
        user.save(update_fields=["first_name", "last_name"])
        active_memberships.append(
            create_membership(
                user=user,
                establishment=establishment,
                role=EstablishmentMembership.Role.STAFF,
            )
        )
    candidate_memberships = []
    for index in range(100):
        user = create_user(username=f"bbb_candidate_{index:03d}")
        user.first_name = "Bbb"
        user.last_name = f"Candidate{index:03d}"
        user.save(update_fields=["first_name", "last_name"])
        candidate_memberships.append(
            create_membership(
                user=user,
                establishment=establishment,
                role=EstablishmentMembership.Role.STAFF,
            )
        )

    token = login(api_client, user=actor)
    group_response = create_group(
        api_client,
        token=token,
        establishment_id=establishment.id,
        title="Crowded",
        membership_ids=[item.id for item in active_memberships],
    )
    conversation_id = group_response.json()["conversation"]["id"]

    unscoped = api_client.get(
        chat_url(establishment.id, "eligible-memberships/"),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert unscoped.status_code == 200
    unscoped_ids = {item["membership_id"] for item in unscoped.json()["items"]}
    assert any(str(item.id) in unscoped_ids for item in active_memberships)

    scoped = api_client.get(
        chat_url(establishment.id, f"eligible-memberships/?conversation_id={conversation_id}"),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert scoped.status_code == 200
    scoped_items = scoped.json()["items"]
    assert len(scoped_items) == 100
    scoped_ids = {item["membership_id"] for item in scoped_items}
    for membership in active_memberships:
        assert str(membership.id) not in scoped_ids
    assert str(actor_membership.id) not in scoped_ids
    assert scoped_ids == {str(item.id) for item in candidate_memberships}


@pytest.mark.django_db
def test_last_admin_leave_promotes_remaining_member(api_client):
    establishment = create_establishment()
    manager = create_user(username="chat_lot2_leave_admin")
    staff = create_user(username="chat_lot2_leave_staff")
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


@pytest.mark.django_db
def test_last_admin_deactivation_promotes_remaining_member(api_client):
    establishment = create_establishment()
    owner = create_user(username="chat_lot2_deact_owner")
    manager = create_user(username="chat_lot2_deact_admin")
    staff = create_user(username="chat_lot2_deact_staff")
    owner_membership = create_membership(
        user=owner,
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
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
    token = login(api_client, user=manager)
    group_response = create_group(
        api_client,
        token=token,
        establishment_id=establishment.id,
        title="Shift",
        membership_ids=[staff_membership.id],
    )
    conversation_id = group_response.json()["conversation"]["id"]

    deactivate_membership_for_management(
        current_membership=owner_membership,
        establishment_id=establishment.id,
        membership_id=manager_membership.id,
    )

    staff_participant = ChatParticipant.objects.get(
        conversation_id=conversation_id,
        membership=staff_membership,
    )
    assert staff_participant.left_at is None
    assert staff_participant.role == ChatParticipant.Role.ADMIN


@pytest.mark.django_db(transaction=True)
def test_concurrent_admin_leaves_keep_at_least_one_admin():
    establishment = create_establishment()
    admin_a_user = create_user(username="chat_lot2_concurrent_a")
    admin_b_user = create_user(username="chat_lot2_concurrent_b")
    member_user = create_user(username="chat_lot2_concurrent_member")
    admin_a = create_membership(
        user=admin_a_user,
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
    )
    admin_b = create_membership(
        user=admin_b_user,
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
    )
    member = create_membership(
        user=member_user,
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )

    conversation = None

    def setup() -> None:
        nonlocal conversation
        from houston.chat.services import create_group_conversation

        conversation = create_group_conversation(
            actor_membership=admin_a,
            title="Concurrent",
            membership_ids=[admin_a.id, admin_b.id, member.id],
        )
        promote_group_participant(
            actor_membership=admin_a,
            conversation_id=conversation.id,
            target_membership_id=admin_b.id,
        )

    setup()
    assert conversation is not None

    def leave_a(_: int) -> None:
        close_old_connections()
        try:
            leave_group_conversation(
                actor_membership=admin_a,
                conversation_id=conversation.id,
            )
        finally:
            close_old_connections()

    def leave_b(_: int) -> None:
        close_old_connections()
        try:
            leave_group_conversation(
                actor_membership=admin_b,
                conversation_id=conversation.id,
            )
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(leave_a, 0),
            executor.submit(leave_b, 0),
        ]
        for future in futures:
            future.result()

    active = list(
        ChatParticipant.objects.filter(
            conversation_id=conversation.id,
            left_at__isnull=True,
        )
    )
    assert active
    assert any(item.role == ChatParticipant.Role.ADMIN for item in active)


@pytest.mark.django_db(transaction=True)
def test_ws_emits_conversation_updated_on_add_and_promote(api_client):
    establishment = create_establishment()
    admin = create_user(username="chat_lot2_ws_admin")
    member = create_user(username="chat_lot2_ws_member")
    target = create_user(username="chat_lot2_ws_target")
    admin_membership = create_membership(
        user=admin,
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
    )
    member_membership = create_membership(
        user=member,
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    target_membership = create_membership(
        user=target,
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    token = login(api_client, user=admin)
    group_response = create_group(
        api_client,
        token=token,
        establishment_id=establishment.id,
        title="Live",
        membership_ids=[member_membership.id],
    )
    conversation_id = uuid.UUID(group_response.json()["conversation"]["id"])
    target_ticket = get_ws_ticket(api_client, user=target, establishment=establishment)
    member_ticket = get_ws_ticket(api_client, user=member, establishment=establishment)

    async def run_add():
        target_comm = await _connect_authenticated(
            ticket=target_ticket,
            establishment=establishment,
        )
        await database_sync_to_async(add_group_participant)(
            actor_membership=admin_membership,
            conversation_id=conversation_id,
            target_membership_id=target_membership.id,
        )
        event = await target_comm.receive_json_from()
        await target_comm.disconnect()
        return event

    add_event = async_to_sync(run_add)()
    close_old_connections()
    assert add_event["type"] == "conversation.updated"
    assert add_event["conversation_id"] == str(conversation_id)

    async def run_promote():
        member_comm = await _connect_authenticated(
            ticket=member_ticket,
            establishment=establishment,
        )
        await database_sync_to_async(promote_group_participant)(
            actor_membership=admin_membership,
            conversation_id=conversation_id,
            target_membership_id=member_membership.id,
        )
        event = await member_comm.receive_json_from()
        await member_comm.disconnect()
        return event

    promote_event = async_to_sync(run_promote)()
    close_old_connections()
    assert promote_event["type"] == "conversation.updated"
    assert promote_event["conversation_id"] == str(conversation_id)


@pytest.mark.django_db(transaction=True)
def test_ws_remove_revokes_target_and_updates_remaining_actives(api_client):
    establishment = create_establishment()
    admin = create_user(username="chat_lot2_ws_remove_admin")
    remaining = create_user(username="chat_lot2_ws_remove_remaining")
    target = create_user(username="chat_lot2_ws_remove_target")
    admin_membership = create_membership(
        user=admin,
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
    )
    remaining_membership = create_membership(
        user=remaining,
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    target_membership = create_membership(
        user=target,
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    token = login(api_client, user=admin)
    group_response = create_group(
        api_client,
        token=token,
        establishment_id=establishment.id,
        title="Remove live",
        membership_ids=[remaining_membership.id, target_membership.id],
    )
    conversation_id = uuid.UUID(group_response.json()["conversation"]["id"])
    remaining_ticket = get_ws_ticket(api_client, user=remaining, establishment=establishment)
    target_ticket = get_ws_ticket(api_client, user=target, establishment=establishment)

    async def run():
        remaining_comm = await _connect_authenticated(
            ticket=remaining_ticket,
            establishment=establishment,
        )
        target_comm = await _connect_authenticated(
            ticket=target_ticket,
            establishment=establishment,
        )
        await database_sync_to_async(remove_group_participant)(
            actor_membership=admin_membership,
            conversation_id=conversation_id,
            target_membership_id=target_membership.id,
        )
        remaining_event = await remaining_comm.receive_json_from()
        target_event = await target_comm.receive_json_from()
        await remaining_comm.disconnect()
        await target_comm.disconnect()
        return remaining_event, target_event

    remaining_event, target_event = async_to_sync(run)()
    close_old_connections()

    assert remaining_event["type"] == "conversation.updated"
    assert remaining_event["conversation_id"] == str(conversation_id)
    assert set(remaining_event.keys()) == {"type", "conversation_id"}

    assert target_event["type"] == "conversation.access_revoked"
    assert target_event["conversation_id"] == str(conversation_id)
    assert target_event["reason"] == "participant_removed"


@pytest.mark.django_db(transaction=True)
def test_ws_leave_revokes_leaver_and_updates_remaining_with_auto_promote(api_client):
    establishment = create_establishment()
    admin = create_user(username="chat_lot2_ws_leave_admin")
    remaining = create_user(username="chat_lot2_ws_leave_remaining")
    admin_membership = create_membership(
        user=admin,
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
    )
    remaining_membership = create_membership(
        user=remaining,
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    token_admin = login(api_client, user=admin)
    group_response = create_group(
        api_client,
        token=token_admin,
        establishment_id=establishment.id,
        title="Leave live",
        membership_ids=[remaining_membership.id],
    )
    conversation_id = uuid.UUID(group_response.json()["conversation"]["id"])
    remaining_ticket = get_ws_ticket(api_client, user=remaining, establishment=establishment)
    admin_ticket = get_ws_ticket(api_client, user=admin, establishment=establishment)

    async def run():
        remaining_comm = await _connect_authenticated(
            ticket=remaining_ticket,
            establishment=establishment,
        )
        admin_comm = await _connect_authenticated(
            ticket=admin_ticket,
            establishment=establishment,
        )
        await database_sync_to_async(leave_group_conversation)(
            actor_membership=admin_membership,
            conversation_id=conversation_id,
        )
        remaining_event = await remaining_comm.receive_json_from()
        admin_event = await admin_comm.receive_json_from()
        await remaining_comm.disconnect()
        await admin_comm.disconnect()
        return remaining_event, admin_event

    remaining_event, admin_event = async_to_sync(run)()
    close_old_connections()

    assert remaining_event["type"] == "conversation.updated"
    assert remaining_event["conversation_id"] == str(conversation_id)
    assert set(remaining_event.keys()) == {"type", "conversation_id"}

    assert admin_event["type"] == "conversation.access_revoked"
    assert admin_event["conversation_id"] == str(conversation_id)
    assert admin_event["reason"] == "participant_left"

    remaining_participant = ChatParticipant.objects.get(
        conversation_id=conversation_id,
        membership=remaining_membership,
    )
    assert remaining_participant.role == ChatParticipant.Role.ADMIN

    token_remaining = login(api_client, user=remaining)
    detail_response = api_client.get(
        chat_url(establishment.id, f"conversations/{conversation_id}/"),
        HTTP_AUTHORIZATION=f"Bearer {token_remaining}",
    )
    assert detail_response.status_code == 200
    body = detail_response.json()
    assert body["can_manage"] is True
    assert body["can_delete"] is True
    remaining_summary = next(
        item
        for item in body["participants"]
        if item["membership_id"] == str(remaining_membership.id)
    )
    assert remaining_summary["participant_role"] == "admin"


@pytest.mark.django_db
def test_remove_admin_keeps_group_with_admin(api_client):
    establishment = create_establishment()
    manager = create_user(username="chat_lot2_remove_admin_a")
    other_admin = create_user(username="chat_lot2_remove_admin_b")
    staff = create_user(username="chat_lot2_remove_staff")
    create_membership(
        user=manager,
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
    )
    other_admin_membership = create_membership(
        user=other_admin,
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
        title="Ops",
        membership_ids=[other_admin_membership.id, staff_membership.id],
    )
    conversation_id = group_response.json()["conversation"]["id"]
    promote_response = api_client.post(
        chat_url(
            establishment.id,
            f"conversations/{conversation_id}/participants/{other_admin_membership.id}/promote/",
        ),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert promote_response.status_code == 204

    remove_response = api_client.delete(
        chat_url(
            establishment.id,
            f"conversations/{conversation_id}/participants/{other_admin_membership.id}/",
        ),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert remove_response.status_code == 204

    active_admins = ChatParticipant.objects.filter(
        conversation_id=conversation_id,
        left_at__isnull=True,
        role=ChatParticipant.Role.ADMIN,
    )
    assert active_admins.exists()


@pytest.mark.django_db
def test_cross_establishment_participant_add_rejected(api_client):
    establishment_a = create_establishment()
    establishment_b = create_establishment()
    manager = create_user(username="chat_lot2_tenant_admin")
    staff = create_user(username="chat_lot2_tenant_staff")
    foreign = create_user(username="chat_lot2_tenant_foreign")
    create_membership(
        user=manager,
        establishment=establishment_a,
        role=EstablishmentMembership.Role.MANAGER,
    )
    staff_membership = create_membership(
        user=staff,
        establishment=establishment_a,
        role=EstablishmentMembership.Role.STAFF,
    )
    foreign_membership = create_membership(
        user=foreign,
        establishment=establishment_b,
        role=EstablishmentMembership.Role.STAFF,
    )
    token = login(api_client, user=manager)
    group_response = create_group(
        api_client,
        token=token,
        establishment_id=establishment_a.id,
        title="Ops",
        membership_ids=[staff_membership.id],
    )
    conversation_id = group_response.json()["conversation"]["id"]

    response = api_client.post(
        chat_url(establishment_a.id, f"conversations/{conversation_id}/participants/"),
        {"membership_id": str(foreign_membership.id)},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"
