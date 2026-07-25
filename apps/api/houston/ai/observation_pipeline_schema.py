from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from houston.signals.constants import (
    AI_CANONICAL_OBJECT_MAX_LENGTH,
    AI_EXPECTED_ACTION_VALUES,
    AI_INFORMATION_TYPE_MAX_LENGTH,
    AI_ISSUE_FOCUS_MAX_LENGTH,
    AI_LOCATION_TEXT_MAX_LENGTH,
    AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
    AI_SIGNAL_KIND_VALUES,
    MAX_CANDIDATES_PER_OBSERVATION,
)

SignalKindLiteral = Literal["actionable", "informational"]
ExpectedActionLiteral = Literal[
    "clean_secure",
    "repair",
    "replenish",
    "inspect",
    "coordinate",
    "assist",
    "inform",
    "monitor",
    "safety_response",
]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PipelineCandidateOutput(_StrictModel):
    title: str = Field(min_length=1, max_length=200)
    structured_summary: str = Field(min_length=1, max_length=2000)
    issue_focus: str = Field(min_length=1, max_length=AI_ISSUE_FOCUS_MAX_LENGTH)
    canonical_object: str = Field(min_length=1, max_length=AI_CANONICAL_OBJECT_MAX_LENGTH)
    signal_kind: SignalKindLiteral
    expected_action: ExpectedActionLiteral | None
    information_type: str | None = Field(max_length=AI_INFORMATION_TYPE_MAX_LENGTH)
    affected_business_unit_routing_key: str | None = Field(max_length=180)
    responsible_business_unit_routing_key: str | None = Field(max_length=180)
    activity_subject_routing_key: str | None = Field(max_length=150)
    operational_unit_key: str | None
    location_text: str | None = Field(max_length=AI_LOCATION_TEXT_MAX_LENGTH)

    @field_validator("signal_kind")
    @classmethod
    def validate_signal_kind(cls, value: str) -> str:
        if value not in AI_SIGNAL_KIND_VALUES:
            raise ValueError(f"signal_kind must be one of {AI_SIGNAL_KIND_VALUES}")
        return value

    @field_validator("expected_action")
    @classmethod
    def validate_expected_action(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if value not in AI_EXPECTED_ACTION_VALUES:
            raise ValueError(f"expected_action must be one of {AI_EXPECTED_ACTION_VALUES}")
        return value

    @model_validator(mode="after")
    def validate_information_type_for_signal_kind(self) -> PipelineCandidateOutput:
        if self.signal_kind == "actionable":
            if self.information_type is not None:
                raise ValueError("information_type must be null when signal_kind is actionable")
            return self
        if self.information_type is None:
            raise ValueError(
                "information_type must be a non-empty string when signal_kind is informational"
            )
        if not self.information_type.strip():
            raise ValueError(
                "information_type must be non-empty after strip when signal_kind is informational"
            )
        # No silent normalization: keep original string; only reject whitespace-only / oversize.
        if len(self.information_type) > AI_INFORMATION_TYPE_MAX_LENGTH:
            raise ValueError(
                f"information_type must be at most {AI_INFORMATION_TYPE_MAX_LENGTH} characters"
            )
        return self


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
                f"schema_version must be {AI_OBSERVATION_PIPELINE_SCHEMA_VERSION!r}, got {value!r}"
            )
        return value
