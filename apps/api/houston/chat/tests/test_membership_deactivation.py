from __future__ import annotations

import pytest
from houston.chat.models import ChatConversation, ChatParticipant
from houston.chat.tests.conftest import create_establishment, create_membership, create_user, login
from houston.chat.tests.helpers import chat_url, create_dm, create_group
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
