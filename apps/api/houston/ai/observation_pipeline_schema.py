from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from houston.signals.constants import (
    AI_ISSUE_FOCUS_MAX_LENGTH,
    AI_LOCATION_TEXT_MAX_LENGTH,
    AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
    MAX_CANDIDATES_PER_OBSERVATION,
)


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PipelineCandidateOutput(_StrictModel):
    title: str = Field(min_length=1, max_length=200)
    structured_summary: str = Field(min_length=1, max_length=2000)
    issue_focus: str = Field(min_length=1, max_length=AI_ISSUE_FOCUS_MAX_LENGTH)
    affected_business_unit_key: str = Field(min_length=1, max_length=100)
    responsible_business_unit_key: str = Field(min_length=1, max_length=100)
    activity_subject_key: str = Field(min_length=1, max_length=200)
    operational_unit_key: str | None = None
    location_text: str | None = Field(default=None, max_length=AI_LOCATION_TEXT_MAX_LENGTH)
    aggregate_into_signal_id: str | None = None


class ObservationPipelineOutput(_StrictModel):
    schema_version: str
    candidates: list[PipelineCandidateOutput] = Field(
        default_factory=list,
        max_length=MAX_CANDIDATES_PER_OBSERVATION,
    )

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, value: str) -> str:
        if value != AI_OBSERVATION_PIPELINE_SCHEMA_VERSION:
            raise ValueError(
                f"schema_version must be {AI_OBSERVATION_PIPELINE_SCHEMA_VERSION!r}, "
                f"got {value!r}"
            )
        return value
