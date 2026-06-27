from __future__ import annotations

import pytest
from houston.realtime.operational_invalidation_events import (
    NOTIFICATION_BULK_UPDATED_REASON,
    NOTIFICATION_CREATED_REASON,
    NOTIFICATION_INVALIDATION_SUBJECT_TYPE,
    NOTIFICATION_UPDATED_REASON,
    REASON_GATED_SUBJECT_TYPES,
    event_pairs,
    load_operational_invalidation_contract,
    notification_reasons,
    operational_invalidation_events,
)


def test_contract_has_expected_version_and_event_count():
    payload = load_operational_invalidation_contract()
    assert payload["version"] == 1
    assert len(payload["events"]) == 15
    assert len(operational_invalidation_events()) == 15


def test_contract_events_have_valid_dispatch():
    for event in operational_invalidation_events():
        assert event.dispatch in {"by_subject_type", "by_reason"}


def test_reason_gated_subject_types_match_contract():
    expected = frozenset(
        event.subject_type
        for event in operational_invalidation_events()
        if event.dispatch == "by_reason"
    )
    assert REASON_GATED_SUBJECT_TYPES == expected
    assert REASON_GATED_SUBJECT_TYPES == frozenset({"comment", "notification"})


def test_notification_constants_match_contract():
    contract_notification_reasons = notification_reasons()
    assert NOTIFICATION_INVALIDATION_SUBJECT_TYPE == "notification"
    assert NOTIFICATION_CREATED_REASON in contract_notification_reasons
    assert NOTIFICATION_UPDATED_REASON in contract_notification_reasons
    assert NOTIFICATION_BULK_UPDATED_REASON in contract_notification_reasons
    assert contract_notification_reasons == frozenset(
        {
            NOTIFICATION_CREATED_REASON,
            NOTIFICATION_UPDATED_REASON,
            NOTIFICATION_BULK_UPDATED_REASON,
        }
    )


@pytest.mark.parametrize(
    ("subject_type", "reason"),
    sorted(event_pairs()),
)
def test_contract_event_pair_is_unique(subject_type: str, reason: str):
    matches = [
        event
        for event in operational_invalidation_events()
        if event.subject_type == subject_type and event.reason == reason
    ]
    assert len(matches) == 1
