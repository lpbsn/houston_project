from __future__ import annotations

import csv
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path

from django.conf import settings

from houston.establishments.taxonomy_normalization import slugify_label

POLE_COLUMN = "Pole d'activité"
SUBJECT_COLUMN = "Sujets"

TRANSVERSAL_BUSINESS_UNIT_KEYS = frozenset(
    {
        "maintenance",
        "communication",
        "rh",
        "evenements_privatisations",
        # Legacy v1 module keys still used by taxonomy backfill heuristics.
        "rh_planning",
        "event",
        "evenements",
        "administration",
        "administration_back_office",
    }
)

QUASI_DUPLICATE_RATIO = 0.85


@dataclass(frozen=True)
class CatalogBusinessUnitRow:
    key: str
    label: str
    default_unit_type: str
    description: str
    sort_order: int = 0


@dataclass(frozen=True)
class CatalogActivitySubjectRow:
    key: str
    label: str
    catalog_business_unit_key: str
    description: str
    sort_order: int = 0


@dataclass
class CatalogValidationReport:
    business_unit_count: int = 0
    activity_subject_count: int = 0
    trimmed_labels: list[str] = field(default_factory=list)
    deduplicated_pairs: list[str] = field(default_factory=list)
    quasi_duplicates: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def has_warnings(self) -> bool:
        return bool(self.warnings or self.quasi_duplicates)


@dataclass(frozen=True)
class NormalizedCatalog:
    business_units: tuple[CatalogBusinessUnitRow, ...]
    activity_subjects: tuple[CatalogActivitySubjectRow, ...]
    report: CatalogValidationReport


def catalogue_dir() -> Path:
    repo_root = Path(settings.BASE_DIR).parent.parent
    return repo_root / "docs" / "catalogue"


def suggestion_source_csv_path() -> Path:
    return catalogue_dir() / "suggestion_source.csv"


def business_units_csv_path() -> Path:
    return catalogue_dir() / "business_units.csv"


def activity_subjects_csv_path() -> Path:
    return catalogue_dir() / "activity_subjects.csv"


def default_unit_type_for_business_unit_key(key: str) -> str:
    if key in TRANSVERSAL_BUSINESS_UNIT_KEYS:
        return "transversal"
    return "dedicated"


def _trim_report(report: CatalogValidationReport, *, raw: str, trimmed: str, context: str) -> str:
    if raw != trimmed:
        report.trimmed_labels.append(f"{context}: {raw!r} -> {trimmed!r}")
    return trimmed


def parse_suggestion_source_rows(*, path: Path | None = None) -> list[tuple[int, str, str]]:
    source_path = path or suggestion_source_csv_path()
    rows: list[tuple[int, str, str]] = []
    with source_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        for line_number, raw in enumerate(reader, start=2):
            pole = raw.get(POLE_COLUMN) or ""
            subject = raw.get(SUBJECT_COLUMN) or ""
            rows.append((line_number, pole, subject))
    return rows


def normalize_catalog_from_source(*, path: Path | None = None) -> NormalizedCatalog:
    report = CatalogValidationReport()
    seen_pairs: set[tuple[str, str]] = set()
    bu_order: list[str] = []
    bu_labels: dict[str, str] = {}
    subject_rows: list[CatalogActivitySubjectRow] = []
    subject_sort = 10

    for line_number, raw_pole, raw_subject in parse_suggestion_source_rows(path=path):
        pole = _trim_report(
            report,
            raw=raw_pole,
            trimmed=raw_pole.strip(),
            context=f"line {line_number} pole",
        )
        subject = _trim_report(
            report,
            raw=raw_subject,
            trimmed=raw_subject.strip(),
            context=f"line {line_number} subject",
        )

        if not pole and not subject:
            continue
        if not pole:
            report.warnings.append(f"line {line_number}: empty pole with subject {subject!r}")
            continue
        if not subject:
            report.warnings.append(f"line {line_number}: empty subject for pole {pole!r}")
            continue

        pair = (pole, subject)
        if pair in seen_pairs:
            report.deduplicated_pairs.append(f"line {line_number}: {pole!r} / {subject!r}")
            continue
        seen_pairs.add(pair)

        bu_key = slugify_label(pole)
        if bu_key not in bu_labels:
            bu_labels[bu_key] = pole
            bu_order.append(bu_key)

        subject_key = f"{bu_key}__{slugify_label(subject)}"
        subject_rows.append(
            CatalogActivitySubjectRow(
                key=subject_key,
                label=subject,
                catalog_business_unit_key=bu_key,
                description="",
                sort_order=subject_sort,
            )
        )
        subject_sort += 10

    business_units = tuple(
        CatalogBusinessUnitRow(
            key=bu_key,
            label=bu_labels[bu_key],
            default_unit_type=default_unit_type_for_business_unit_key(bu_key),
            description="",
            sort_order=(index + 1) * 10,
        )
        for index, bu_key in enumerate(bu_order)
    )

    _detect_quasi_duplicates(
        report=report,
        subject_rows=subject_rows,
    )

    report.business_unit_count = len(business_units)
    report.activity_subject_count = len(subject_rows)
    return NormalizedCatalog(
        business_units=business_units,
        activity_subjects=tuple(subject_rows),
        report=report,
    )


def _detect_quasi_duplicates(
    *,
    report: CatalogValidationReport,
    subject_rows: list[CatalogActivitySubjectRow],
) -> None:
    by_bu: dict[str, list[CatalogActivitySubjectRow]] = {}
    for row in subject_rows:
        by_bu.setdefault(row.catalog_business_unit_key, []).append(row)

    for bu_key, rows in by_bu.items():
        for left_index, left in enumerate(rows):
            left_slug = slugify_label(left.label)
            for right in rows[left_index + 1 :]:
                right_slug = slugify_label(right.label)
                if left_slug == right_slug:
                    continue
                ratio = SequenceMatcher(None, left_slug, right_slug).ratio()
                if ratio >= QUASI_DUPLICATE_RATIO:
                    message = (
                        f"{bu_key}: quasi-duplicate labels "
                        f"{left.label!r} vs {right.label!r} (ratio={ratio:.2f})"
                    )
                    report.quasi_duplicates.append(message)
                    report.warnings.append(message)


def load_normalized_business_unit_rows(
    *, path: Path | None = None
) -> tuple[CatalogBusinessUnitRow, ...]:
    csv_path = path or business_units_csv_path()
    rows: list[CatalogBusinessUnitRow] = []
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            rows.append(
                CatalogBusinessUnitRow(
                    key=raw["key"],
                    label=raw["label"],
                    default_unit_type=raw.get("default_unit_type") or "dedicated",
                    description=raw.get("description") or "",
                    sort_order=int(raw.get("sort_order") or 0),
                )
            )
    return tuple(rows)


def load_normalized_activity_subject_rows(
    *, path: Path | None = None
) -> tuple[CatalogActivitySubjectRow, ...]:
    csv_path = path or activity_subjects_csv_path()
    rows: list[CatalogActivitySubjectRow] = []
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            rows.append(
                CatalogActivitySubjectRow(
                    key=raw["key"],
                    label=raw["label"],
                    catalog_business_unit_key=raw["business_unit_key"],
                    description=raw.get("description") or "",
                    sort_order=int(raw.get("sort_order") or 0),
                )
            )
    return tuple(rows)


def write_normalized_catalog_csvs(*, catalog: NormalizedCatalog) -> None:
    catalogue_dir().mkdir(parents=True, exist_ok=True)

    bu_path = business_units_csv_path()
    with bu_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["key", "label", "default_unit_type", "description", "sort_order"],
        )
        writer.writeheader()
        for row in catalog.business_units:
            writer.writerow(
                {
                    "key": row.key,
                    "label": row.label,
                    "default_unit_type": row.default_unit_type,
                    "description": row.description,
                    "sort_order": row.sort_order,
                }
            )

    as_path = activity_subjects_csv_path()
    with as_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["key", "label", "business_unit_key", "description", "sort_order"],
        )
        writer.writeheader()
        for row in catalog.activity_subjects:
            writer.writerow(
                {
                    "key": row.key,
                    "label": row.label,
                    "business_unit_key": row.catalog_business_unit_key,
                    "description": row.description,
                    "sort_order": row.sort_order,
                }
            )
