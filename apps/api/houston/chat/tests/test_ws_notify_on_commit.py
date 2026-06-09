from __future__ import annotations

from unittest.mock import patch

import pytest
from django.db import transaction
from houston.chat.services import remove_group_participant
from houston.chat.tests.conftest import (
    create_establishment,
    create_membership,
    create_user,
)


@pytest.mark.django_db(transaction=True)
def test_access_revoked_not_emitted_on_transaction_rollback():
    establishment = create_establishment()
    admin = create_user(username="chat_on_commit_admin")
    target = create_user(username="chat_on_commit_target")
    admin_membership = create_membership(
        user=admin,
        establishment=establishment,
        role="manager",
    )
    target_membership = create_membership(user=target, establishment=establishment)

    from houston.chat.services import create_group_conversation

    conversation = create_group_conversation(
        actor_membership=admin_membership,
        title="On commit rollback",
        membership_ids=[target_membership.id],
    )

    with patch("houston.chat.ws_notify.notify_conversation_access_revoked") as mock_notify:
        with pytest.raises(RuntimeError, match="force rollback"):
            with transaction.atomic():
                remove_group_participant(
                    actor_membership=admin_membership,
                    conversation_id=conversation.id,
                    target_membership_id=target_membership.id,
                )
                raise RuntimeError("force rollback")

        mock_notify.assert_not_called()


@pytest.mark.django_db(transaction=True)
def test_access_revoked_emitted_after_transaction_commit():
    establishment = create_establishment()
    admin = create_user(username="chat_on_commit_success_admin")
    target = create_user(username="chat_on_commit_success_target")
    admin_membership = create_membership(
        user=admin,
        establishment=establishment,
        role="manager",
    )
    target_membership = create_membership(user=target, establishment=establishment)

    from houston.chat.services import create_group_conversation

    conversation = create_group_conversation(
        actor_membership=admin_membership,
        title="On commit success",
        membership_ids=[target_membership.id],
    )

    with patch("houston.chat.ws_notify.notify_conversation_access_revoked") as mock_notify:
        remove_group_participant(
            actor_membership=admin_membership,
            conversation_id=conversation.id,
            target_membership_id=target_membership.id,
        )

        mock_notify.assert_called_once_with(
            establishment_id=establishment.id,
            membership_id=target_membership.id,
            conversation_id=conversation.id,
            reason="participant_removed",
        )
