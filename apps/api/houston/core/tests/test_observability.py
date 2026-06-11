from __future__ import annotations

import uuid

from houston.core.observability import (
    build_api_request_log_context,
    build_observation_processing_log_context,
    build_refresh_token_reuse_log_context,
    build_temporary_upload_image_type_log_context,
    build_ws_auth_failure_log_context,
    sanitize_log_context,
)
from houston.observations.models import ObservationProcessing


def test_build_observation_processing_log_context_omits_sensitive_fields():
    processing = ObservationProcessing(
        observation_id=uuid.uuid4(),
        status=ObservationProcessing.Status.FAILED,
        attempt_count=2,
        last_error_code="provider_timeout",
        outcome="",
    )

    context = build_observation_processing_log_context(
        processing=processing,
        establishment_id=uuid.uuid4(),
        event="observation_pipeline_failed",
    )

    assert context["processing_status"] == ObservationProcessing.Status.FAILED
    assert context["ux_status"] == "analysis_failed"
    assert context["last_error_code"] == "provider_timeout"
    assert "raw_text" not in context
    assert "ticket" not in str(context).lower()


def test_sanitize_log_context_drops_unknown_and_sensitive_keys():
    observation_id = str(uuid.uuid4())
    context = sanitize_log_context(
        {
            "observation_id": observation_id,
            "raw_text": "secret observation body",
            "unexpected": "value",
        },
        allowed_keys=frozenset({"observation_id", "raw_text"}),
    )

    assert context == {"observation_id": observation_id}
    assert "raw_text" not in context


def test_build_ws_auth_failure_log_context_is_safe():
    establishment_id = uuid.uuid4()
    context = build_ws_auth_failure_log_context(
        establishment_id=establishment_id,
        reason="invalid_ticket",
        close_code=4001,
    )

    assert context["establishment_id"] == str(establishment_id)
    assert context["ws_auth_failure_reason"] == "invalid_ticket"
    assert context["ws_close_code"] == 4001
    assert "ticket" not in context


def test_build_api_request_log_context_is_safe():
    context = build_api_request_log_context(
        request_path="/api/v1/observations/",
        request_method="post",
    )

    assert context["request_path"] == "/api/v1/observations/"
    assert context["request_method"] == "POST"


def test_build_refresh_token_reuse_log_context_is_safe():
    session_id = uuid.uuid4()
    refresh_family_id = uuid.uuid4()
    refresh_record_id = uuid.uuid4()
    user_id = uuid.uuid4()

    context = build_refresh_token_reuse_log_context(
        session_id=session_id,
        refresh_family_id=refresh_family_id,
        refresh_record_id=refresh_record_id,
        user_id=user_id,
    )

    assert context == {
        "session_id": str(session_id),
        "refresh_family_id": str(refresh_family_id),
        "refresh_record_id": str(refresh_record_id),
        "user_id": str(user_id),
    }
    assert "event" not in context
    assert "token" not in context
    assert "refresh_token_id" not in context


def test_build_temporary_upload_image_type_log_context_is_safe():
    context = build_temporary_upload_image_type_log_context(
        declared_content_type="image/gif",
        size_bytes=128,
        pillow_image_format="GIF",
        pillow_image_mode="P",
        pillow_image_size=(8, 8),
        heif_plugin_loaded=False,
        error_raised_at="_canonical_from_detected_format",
    )

    assert context["declared_content_type"] == "image/gif"
    assert context["size_bytes"] == 128
    assert context["pillow_image_format"] == "GIF"
    assert context["pillow_image_mode"] == "P"
    assert context["pillow_image_size"] == "8x8"
    assert context["heif_plugin_loaded"] is False
    assert context["error_raised_at"] == "_canonical_from_detected_format"
    assert "event" not in context
    assert "uploaded_filename" not in context
    assert "name" not in context
