from __future__ import annotations

import pytest
from django.test import override_settings
from houston.chat.rate_limits import ChatMessageRateLimitExceeded, check_message_send_rate_limit
from houston.chat.tests.conftest import create_establishment, create_membership, create_user


@pytest.mark.django_db
def test_message_send_rate_limit_blocks_after_threshold():
    establishment = create_establishment()
    user = create_user(username="chat_rate_limit_user")
    membership = create_membership(user=user, establishment=establishment)

    with override_settings(
        HOUSTON_CHAT_RATE_LIMIT_ENABLED=True,
        HOUSTON_CHAT_MESSAGE_SEND_RATE_LIMIT_PER_MINUTE=2,
    ):
        check_message_send_rate_limit(
            establishment_id=establishment.id,
            membership_id=membership.id,
        )
        check_message_send_rate_limit(
            establishment_id=establishment.id,
            membership_id=membership.id,
        )
        with pytest.raises(ChatMessageRateLimitExceeded):
            check_message_send_rate_limit(
                establishment_id=establishment.id,
                membership_id=membership.id,
            )


@pytest.mark.django_db
def test_message_send_rate_limit_can_be_disabled():
    establishment = create_establishment()
    membership = create_membership(
        user=create_user(username="chat_rate_limit_disabled"),
        establishment=establishment,
    )

    with override_settings(
        HOUSTON_CHAT_RATE_LIMIT_ENABLED=False,
        HOUSTON_CHAT_MESSAGE_SEND_RATE_LIMIT_PER_MINUTE=1,
    ):
        for _ in range(5):
            check_message_send_rate_limit(
                establishment_id=establishment.id,
                membership_id=membership.id,
            )
