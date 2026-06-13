from __future__ import annotations

import uuid

from houston.core.observability import build_observation_pipeline_candidate_apply_log_context


def test_build_observation_pipeline_candidate_apply_log_context_includes_eval_fields():
    observation_id = uuid.uuid4()
    establishment_id = uuid.uuid4()

    context = build_observation_pipeline_candidate_apply_log_context(
        observation_id=observation_id,
        establishment_id=establishment_id,
        event="observation_pipeline_candidate_applied",
        aggregation_key="agg-key",
        taxonomy_bucket_key="bucket-key",
        issue_focus="sirop mojito",
        active_taxonomy_peer_count=2,
        hint_used=False,
        hint_rejected_reason="hint_issue_focus_mismatch",
        candidate_outcome="created_signal",
    )

    assert context["issue_focus"] == "sirop mojito"
    assert context["taxonomy_bucket_key"] == "bucket-key"
    assert context["active_taxonomy_peer_count"] == 2
    assert context["hint_rejected_reason"] == "hint_issue_focus_mismatch"
    assert "structured_summary" not in str(context).lower()
