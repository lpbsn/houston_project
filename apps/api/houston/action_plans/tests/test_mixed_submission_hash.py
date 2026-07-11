from __future__ import annotations

import uuid
from datetime import date, datetime, time, timezone

from houston.action_plans.mixed_submission_hash import compute_mixed_request_hash


def test_request_hash_is_stable_for_equivalent_payloads():
    membership_id = uuid.uuid4()
    business_unit_id = uuid.uuid4()
    schedule_body = {
        "end_date": date(2026, 7, 25),
        "start_at": time(9, 0),
        "end_at": time(10, 0),
        "recurrence_days": ["monday", "tuesday"],
        "assignees": [
            {
                "membership_id": membership_id,
                "business_unit_id": business_unit_id,
            }
        ],
        "use_shared_chronology": False,
    }
    reordered = {
        **schedule_body,
        "assignees": list(reversed(schedule_body["assignees"])),
        "recurrence_days": ["tuesday", "monday"],
    }
    use_body = {
        "use_shared_chronology": False,
        "assignees": [],
    }

    first = compute_mixed_request_hash(schedule_body=schedule_body, use_body=use_body)
    second = compute_mixed_request_hash(schedule_body=reordered, use_body=use_body)

    assert first == second


def test_request_hash_changes_when_use_body_changes():
    schedule_body = {
        "end_date": date(2026, 7, 25),
        "start_at": time(9, 0),
        "end_at": time(10, 0),
        "recurrence_days": ["monday"],
        "assignees": [],
        "use_shared_chronology": False,
    }
    first = compute_mixed_request_hash(
        schedule_body=schedule_body,
        use_body={"use_shared_chronology": False, "assignees": []},
    )
    second = compute_mixed_request_hash(
        schedule_body=schedule_body,
        use_body={"use_shared_chronology": True, "assignees": []},
    )

    assert first != second


def test_request_hash_handles_assignee_datetime_fields():
    membership_id = uuid.uuid4()
    business_unit_id = uuid.uuid4()
    start_at = datetime(2026, 7, 12, 10, 0, tzinfo=timezone.utc)
    end_at = datetime(2026, 7, 12, 12, 0, tzinfo=timezone.utc)
    schedule_body = {
        "end_date": date(2026, 7, 25),
        "start_at": time(9, 0),
        "end_at": time(10, 0),
        "recurrence_days": ["monday"],
        "assignees": [],
        "use_shared_chronology": False,
    }
    use_body = {
        "use_shared_chronology": False,
        "assignees": [
            {
                "membership_id": membership_id,
                "business_unit_id": business_unit_id,
                "start_at": start_at,
                "end_at": end_at,
            }
        ],
    }

    assert compute_mixed_request_hash(schedule_body=schedule_body, use_body=use_body)
