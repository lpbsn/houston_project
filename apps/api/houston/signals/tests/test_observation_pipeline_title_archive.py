"""Deterministic guards for the title-wording comparison archive.

These tests do not call OpenAI. They lock two delivery rules: a v6_3 reference
snapshot is not judged by v6_4 writing criteria, and before/after archives stay
as separate files through the existing smoke archive writer.
"""

from __future__ import annotations

from houston.signals.pipeline_v6_smoke_archive import latest_smoke_archive, write_smoke_archive
from houston.signals.tests.test_openai_observation_pipeline_v6_4_title_smoke import (
    title_archive_kind,
    title_writing_criteria_apply,
)


def test_v6_3_reference_does_not_apply_v6_4_writing_criteria():
    assert title_writing_criteria_apply("ai_observation_pipeline_v6_3") is False
    assert title_writing_criteria_apply("ai_observation_pipeline_v6_4") is True


def test_before_and_after_title_archives_stay_distinct(tmp_path):
    before_kind = title_archive_kind("ai_observation_pipeline_v6_3")
    after_kind = title_archive_kind("ai_observation_pipeline_v6_4")
    assert before_kind != after_kind

    before = write_smoke_archive(
        kind=before_kind,
        payload={"passed": True, "summary": "reference v6_3"},
        archive_dir=tmp_path,
    )
    after = write_smoke_archive(
        kind=after_kind,
        payload={"passed": True, "summary": "after v6_4"},
        archive_dir=tmp_path,
    )

    assert before.exists()
    assert after.exists()
    assert before != after
    assert before.with_suffix(".md").exists()
    assert after.with_suffix(".md").exists()
    assert latest_smoke_archive(kind=before_kind, archive_dir=tmp_path) == before
    assert latest_smoke_archive(kind=after_kind, archive_dir=tmp_path) == after
    assert before.read_text(encoding="utf-8") != after.read_text(encoding="utf-8")
