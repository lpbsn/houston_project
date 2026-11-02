from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import patch

import pytest
from django.test import override_settings
from houston.ai.transcription import transcribe_audio_file
from houston.establishments.models import Establishment
from houston.organizations.models import Organization

pytestmark = pytest.mark.django_db


def _establishment() -> Establishment:
    organization = Organization.objects.create(
        name=f"Org {uuid.uuid4().hex[:6]}",
        status=Organization.Status.ACTIVE,
    )
    return Establishment.objects.create(
        name="Transcription Hotel",
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )


@override_settings(OPENAI_API_KEY="test-key")
def test_transcription_returns_text_longer_than_the_legacy_1000_character_cut(tmp_path: Path):
    full_text = "phrase complète. " * 80
    assert len(full_text) > 1000
    audio_path = tmp_path / "dictee.webm"
    audio_path.write_bytes(b"audio")

    with patch(
        "houston.ai.transcription._call_openai_transcription",
        return_value=(full_text, "fr"),
    ):
        result = transcribe_audio_file(
            establishment=_establishment(),
            audio_path=audio_path,
            declared_content_type="audio/webm",
        )

    assert result.text == full_text
