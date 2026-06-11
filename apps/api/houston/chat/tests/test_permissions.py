from __future__ import annotations

import pytest
from houston.accounts.models import User
from houston.chat.models import ChatConversation, ChatParticipant
from houston.chat.permissions import (
    can_access_chat,
    can_create_dm,
    can_create_group,
    can_manage_establishment_chat_settings,
    can_send_message,
    can_view_conversation,
)
from houston.establishments.models import Establishment, EstablishmentMembership
from houston.organizations.models import Organization
from houston.testing.factories import build_membership, create_membership, create_user

pytestmark = pytest.mark.django_db


def _build_conversation(*, membership: EstablishmentMembership) -> ChatConversation:
    conversation = ChatConversation.objects.create(
        establishment=membership.establishment,
        type=ChatConversation.Type.GROUP,
        title="Ops",
        created_by_membership=membership,
    )
    ChatParticipant.objects.create(
        conversation=conversation,
        membership=membership,
        role=ChatParticipant.Role.ADMIN,
    )
    return conversation


def test_deactivated_membership_denies_chat_permissions():
    membership = build_membership(membership_status=EstablishmentMembership.Status.DEACTIVATED)

    assert not can_access_chat(membership)
    assert not can_create_dm(membership)
    assert not can_create_group(membership)
    assert not can_manage_establishment_chat_settings(membership)


@pytest.mark.parametrize(
    "establishment_status",
    [
        Establishment.Status.DRAFT,
        Establishment.Status.DEACTIVATED,
    ],
)
def test_non_active_establishment_denies_chat_permissions(establishment_status):
    membership = build_membership(establishment_status=establishment_status)

    assert not can_access_chat(membership)
    assert not can_manage_establishment_chat_settings(membership)


@pytest.mark.parametrize(
    "organization_status",
    [
        Organization.Status.SUSPENDED,
        Organization.Status.ARCHIVED,
    ],
)
def test_non_active_organization_denies_chat_permissions(organization_status):
    membership = build_membership(organization_status=organization_status)

    assert not can_access_chat(membership)
    assert not can_create_group(membership)


@pytest.mark.parametrize(
    "user_status",
    [
        User.Status.PENDING,
        User.Status.SUSPENDED,
        User.Status.ANONYMIZED,
    ],
)
def test_non_active_user_denies_chat_permissions(user_status):
    membership = build_membership(user_status=user_status)

    assert not can_access_chat(membership)
    assert not can_create_dm(membership)


def test_chat_access_requires_chat_enabled():
    membership = build_membership()
    membership.establishment.chat_enabled = False
    membership.establishment.save(update_fields=["chat_enabled"])

    assert not can_access_chat(membership)


def test_group_creation_requires_action_role():
    membership = build_membership(role=EstablishmentMembership.Role.STAFF)
    membership.establishment.chat_enabled = True
    membership.establishment.save(update_fields=["chat_enabled"])

    assert can_access_chat(membership)
    assert not can_create_group(membership)


def test_chat_settings_management_requires_admin_role():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    owner.establishment.chat_enabled = True
    owner.establishment.save(update_fields=["chat_enabled"])
    staff = create_membership(
        establishment=owner.establishment,
        user=create_user(username="chat_perm_staff"),
        role=EstablishmentMembership.Role.STAFF,
    )

    assert can_manage_establishment_chat_settings(owner)
    assert not can_manage_establishment_chat_settings(staff)


def test_conversation_visibility_requires_active_participation():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    owner.establishment.chat_enabled = True
    owner.establishment.save(update_fields=["chat_enabled"])
    outsider = create_membership(
        establishment=owner.establishment,
        user=create_user(username="chat_perm_outsider"),
        role=EstablishmentMembership.Role.MANAGER,
    )
    conversation = _build_conversation(membership=owner)

    assert can_view_conversation(owner, conversation)
    assert not can_view_conversation(outsider, conversation)
    assert not can_send_message(outsider, conversation)
