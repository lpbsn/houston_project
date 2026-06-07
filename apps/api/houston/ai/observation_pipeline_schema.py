from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from houston.signals.constants import AI_LOCATION_TEXT_MAX_LENGTH, MAX_CANDIDATES_PER_OBSERVATION


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PipelineCandidateOutput(_StrictModel):
    title: str = Field(min_length=1, max_length=200)
    structured_summary: str = Field(min_length=1, max_length=2000)
    operational_module_key: str | None = Field(default=None, max_length=100)
    operational_domain_key: str | None = Field(default=None, max_length=150)
    operational_subject_key: str | None = Field(default=None, max_length=200)
    affected_business_unit_key: str | None = Field(default=None, max_length=100)
    responsible_business_unit_key: str | None = Field(default=None, max_length=100)
    activity_subject_key: str | None = Field(default=None, max_length=200)
    operational_unit_key: str | None = None
    location_text: str | None = Field(default=None, max_length=AI_LOCATION_TEXT_MAX_LENGTH)
    aggregate_into_signal_id: str | None = None

    def uses_v3_classification(self) -> bool:
        return bool(
            self.affected_business_unit_key
            and self.responsible_business_unit_key
            and self.activity_subject_key
        )

    def uses_legacy_classification(self) -> bool:
        return bool(
            self.operational_module_key
            and self.operational_domain_key
            and self.operational_subject_key
        )


class ObservationPipelineOutput(_StrictModel):
    schema_version: str
    candidates: list[PipelineCandidateOutput] = Field(
        default_factory=list,
        max_length=MAX_CANDIDATES_PER_OBSERVATION,
    )
