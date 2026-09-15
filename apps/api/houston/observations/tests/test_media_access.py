from __future__ import annotations

import time
import uuid
from unittest.mock import patch

from houston.observations.media_access import (
    sign_observation_media_preview,
    unsign_observation_media_preview,
)


def test_sign_reuses_token_inside_bucket_window_and_changes_after_window():
    establishment_id = uuid.uuid4()
    media_id = uuid.uuid4()
    bucket_start = 1_700_000_040.0
    with patch("houston.observations.media_access.time.time", return_value=bucket_start):
        first = sign_observation_media_preview(
            establishment_id=establishment_id,
            media_id=media_id,
        )
    with patch("houston.observations.media_access.time.time", return_value=bucket_start + 59):
        same_bucket = sign_observation_media_preview(
            establishment_id=establishment_id,
            media_id=media_id,
        )
    with patch("houston.observations.media_access.time.time", return_value=bucket_start + 60):
        next_bucket = sign_observation_media_preview(
            establishment_id=establishment_id,
            media_id=media_id,
        )

    assert first == same_bucket
    assert next_bucket != first


def test_unsign_accepts_bucketed_token_within_ttl():
    establishment_id = uuid.uuid4()
    media_id = uuid.uuid4()
    now = time.time()
    with patch("houston.observations.media_access.time.time", return_value=now):
        token = sign_observation_media_preview(
            establishment_id=establishment_id,
            media_id=media_id,
        )
    parsed_establishment_id, parsed_media_id = unsign_observation_media_preview(token=token)
    assert parsed_establishment_id == establishment_id
    assert parsed_media_id == media_id
