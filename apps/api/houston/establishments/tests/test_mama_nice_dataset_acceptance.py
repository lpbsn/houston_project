import uuid
from datetime import datetime, timedelta

import pytest

from houston.chat.models import ChatConversation, ChatMessage
from houston.establishments.mama_nice_dataset_acceptance import (
    TOTAL_EXECUTION_COUNT,
    authored_calendar_specs,
    runtime_calendar_elapsed_specs,
    runtime_calendar_remaining_specs,
    validate_mama_nice_dataset,
)
from houston.establishments.mama_nice_dataset_constants import (
    FUTURE_BY_MONTH,
    FUTURE_EXECUTION_COUNT,
    HISTORICAL_EXECUTION_COUNT,
    PARIS_TZ,
    SNAPSHOT,
)
from houston.testing.factories import build_membership


def test_canonical_calendar_specs_are_independent_of_reference_clock():
    specs = authored_calendar_specs()
    assert len(specs) == FUTURE_EXECUTION_COUNT
    assert HISTORICAL_EXECUTION_COUNT + len(specs) == TOTAL_EXECUTION_COUNT
    months = {
        (item.start_at.astimezone(PARIS_TZ).year, item.start_at.astimezone(PARIS_TZ).month)
        for item in specs
    }
    assert {(year, month) for year, month in FUTURE_BY_MONTH} <= months
    assert len(runtime_calendar_elapsed_specs(reference_at=SNAPSHOT)) == 0
    assert len(runtime_calendar_remaining_specs(reference_at=SNAPSHOT)) == FUTURE_EXECUTION_COUNT


def test_runtime_projection_moves_elapsed_calendar_rows_without_calling_them_futures():
    reference_at = datetime(2026, 9, 23, 15, 30, tzinfo=SNAPSHOT.tzinfo)
    elapsed = runtime_calendar_elapsed_specs(reference_at=reference_at)
    remaining = runtime_calendar_remaining_specs(reference_at=reference_at)
    assert elapsed
    assert all(SNAPSHOT < item.start_at <= reference_at for item in elapsed)
    assert all(item.start_at > reference_at for item in remaining)
    assert len(elapsed) + len(remaining) == FUTURE_EXECUTION_COUNT
    assert {authored_id(item) for item in elapsed}.isdisjoint(
        {authored_id(item) for item in remaining}
    )
    expected_elapsed = HISTORICAL_EXECUTION_COUNT + len(elapsed)
    expected_remaining = len(remaining)
    assert expected_elapsed + expected_remaining == TOTAL_EXECUTION_COUNT
    assert expected_elapsed != HISTORICAL_EXECUTION_COUNT
    assert expected_remaining != FUTURE_EXECUTION_COUNT


def authored_id(item) -> str:
    from houston.establishments.mama_nice_dataset_acceptance import authored_calendar_identity

    return authored_calendar_identity(item)


def test_later_reference_does_not_change_canonical_180():
    later = SNAPSHOT + timedelta(hours=16)
    assert len(authored_calendar_specs()) == FUTURE_EXECUTION_COUNT
    assert len(runtime_calendar_remaining_specs(reference_at=later)) < FUTURE_EXECUTION_COUNT


@pytest.mark.django_db
def test_seeded_chat_rows_fail_acceptance():
    membership = build_membership()
    conversation = ChatConversation.objects.create(
        establishment=membership.establishment,
        type=ChatConversation.Type.GROUP,
        title="Hors corpus",
        created_by_membership=membership,
    )
    ChatMessage.objects.create(
        conversation=conversation,
        author_membership=membership,
        body="hors corpus",
        client_message_id=uuid.uuid4(),
    )
    errors = validate_mama_nice_dataset(establishment=membership.establishment)
    assert "chat rows were seeded: 1 conversations, 1 messages" in errors
