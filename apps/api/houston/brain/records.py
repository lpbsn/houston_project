from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

EXTRACTOR_ID = "houston.brain.extract"
EXTRACTOR_VERSION = "1"

VALUE_NUMBER = "number"
VALUE_ZERO = "zero"
VALUE_EMPTY = "empty"
VALUE_ERROR = "error"
VALUE_UNINTERPRETABLE = "uninterpretable"
VALUE_ABSENT = "absent"

SOURCE_TEXT = "text"
SOURCE_EXCEL_NUMBER = "excel_number"
SOURCE_ABSENT = "absent"
SOURCE_ERROR = "error"
SOURCE_EMPTY = "empty"


@dataclass
class GridCell:
    raw: str | None = None
    source: str = SOURCE_TEXT
    number: Decimal | None = None
    row: int | None = None
    column: int | None = None
    coordinate: str | None = None

    def is_empty(self) -> bool:
        if self.source == SOURCE_EMPTY:
            return True
        if self.source == SOURCE_TEXT:
            return not (self.raw or "").strip()
        return False


@dataclass(frozen=True)
class Measure:
    label: str | None
    value: str | None
    value_kind: str
    unit: str | None
    period: str | None
    scope: str | None
    definition: str | None
    locator: dict
    ambiguities: tuple[str, ...]
    raw: str | None

    def as_dict(self) -> dict:
        return {
            "label": self.label,
            "value": self.value,
            "value_kind": self.value_kind,
            "unit": self.unit,
            "period": self.period,
            "scope": self.scope,
            "definition": self.definition,
            "locator": self.locator,
            "ambiguities": list(self.ambiguities),
            "raw": self.raw,
        }


@dataclass(frozen=True)
class QualitativeBlock:
    kind: str
    text: str
    locator: dict

    def as_dict(self) -> dict:
        return {"kind": self.kind, "text": self.text, "locator": self.locator}


@dataclass
class ExtractionResult:
    source_format: str
    measures: list[Measure]
    qualitative: list[QualitativeBlock]
    warnings: list[dict]

    def analyzable(self) -> bool:
        if any(block.text.strip() for block in self.qualitative):
            return True
        return any(measure.value_kind != VALUE_EMPTY for measure in self.measures)

    def as_payload(self) -> dict:
        return {
            "format": self.source_format,
            "measures": [measure.as_dict() for measure in self.measures],
            "qualitative": [block.as_dict() for block in self.qualitative],
            "warnings": self.warnings,
        }
