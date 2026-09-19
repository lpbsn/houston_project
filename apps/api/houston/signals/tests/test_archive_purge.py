from __future__ import annotations

import uuid

from houston.signals.migrations._archive_purge import json_mentions_any_uuid, strip_uuids_from_json


def test_json_helpers_strip_and_detect_archived_uuids():
    archived = str(uuid.uuid4())
    kept = str(uuid.uuid4())
    uuids = frozenset({archived})
    payload = {
        "surviving_signal_id": kept,
        "merged_signal_id": archived,
        archived: "as-key",
        "qualification_events": [
            {"source_signal_id": archived, "kept": kept},
            archived,
        ],
    }

    assert json_mentions_any_uuid(payload, uuids) is True
    cleaned = strip_uuids_from_json(payload, uuids)
    assert json_mentions_any_uuid(cleaned, uuids) is False
    assert cleaned["surviving_signal_id"] == kept
    assert "merged_signal_id" not in cleaned
    assert archived not in cleaned
    assert cleaned["qualification_events"] == [{"kept": kept}]
