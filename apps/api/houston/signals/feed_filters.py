from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from django.db.models import Q

from houston.establishments.models import ActivitySubject, BusinessUnit
from houston.signals.constants import ACTIVE_SIGNAL_STATUSES, FEED_SIGNAL_STATUSES
from houston.signals.models import Signal

FEED_FILTERABLE_STATUSES = frozenset(FEED_SIGNAL_STATUSES)

MAX_FILTER_STATUSES = 4
MAX_FILTER_BUSINESS_UNIT_IDS = 20
MAX_FILTER_ACTIVITY_SUBJECT_IDS = 50

LEGACY_BUSINESS_UNIT_KEYS_PARAM_DETAIL = (
    "business_unit_keys is no longer supported; use business_unit_ids."
)


@dataclass(frozen=True)
class SignalFeedFilters:
    statuses: tuple[str, ...] = ()
    business_unit_ids: tuple[uuid.UUID, ...] = ()
    activity_subject_ids: tuple[uuid.UUID, ...] = ()
    needs_qualification: bool = False

    def has_any(self) -> bool:
        return bool(
            self.statuses
            or self.business_unit_ids
            or self.activity_subject_ids
            or self.needs_qualification
        )


class SignalFeedFilterValidationError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


def parse_signal_feed_filters(
    *,
    query_params: Any,
    establishment_id: uuid.UUID,
) -> SignalFeedFilters:
    if "business_unit_keys" in query_params:
        raise SignalFeedFilterValidationError(LEGACY_BUSINESS_UNIT_KEYS_PARAM_DETAIL)

    statuses = _parse_statuses(query_params.get("statuses"))
    business_unit_ids = _parse_business_unit_ids(
        raw=query_params.get("business_unit_ids"),
    )
    activity_subject_ids = _parse_activity_subject_ids(
        raw=query_params.get("activity_subject_ids"),
    )
    needs_qualification = _parse_needs_qualification(
        query_params.get("needs_qualification"),
    )

    _validate_business_unit_ids_exist(
        establishment_id=establishment_id,
        business_unit_ids=business_unit_ids,
    )
    _validate_activity_subject_ids_exist(
        establishment_id=establishment_id,
        activity_subject_ids=activity_subject_ids,
    )

    return SignalFeedFilters(
        statuses=statuses,
        business_unit_ids=business_unit_ids,
        activity_subject_ids=activity_subject_ids,
        needs_qualification=needs_qualification,
    )


def build_applied_filters_payload(
    *,
    view_mode: str,
    filters: SignalFeedFilters | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"view_mode": view_mode}
    if filters is None:
        payload["statuses"] = []
        payload["business_unit_ids"] = []
        payload["activity_subject_ids"] = []
        payload["needs_qualification"] = False
        return payload

    payload["statuses"] = list(filters.statuses)
    payload["business_unit_ids"] = [str(value) for value in filters.business_unit_ids]
    payload["activity_subject_ids"] = [str(value) for value in filters.activity_subject_ids]
    payload["needs_qualification"] = filters.needs_qualification
    return payload


def apply_feed_filters(queryset, *, filters: SignalFeedFilters | None):
    if filters is None or not filters.has_any():
        return queryset

    if filters.statuses:
        queryset = queryset.filter(status__in=filters.statuses)

    if filters.business_unit_ids:
        queryset = queryset.filter(
            Q(affected_business_unit_id__in=filters.business_unit_ids)
            | Q(responsible_business_unit_id__in=filters.business_unit_ids)
        )

    if filters.activity_subject_ids:
        queryset = queryset.filter(activity_subject_id__in=filters.activity_subject_ids)

    if filters.needs_qualification:
        # "Non classifié": missing responsible among active lifecycle.
        # Affected and activity_subject are ignored (same predicate as the UI badge).
        # Distinct from routing_status=unassigned and from visibility "total unclassified".
        queryset = queryset.filter(
            responsible_business_unit__isnull=True,
            status__in=ACTIVE_SIGNAL_STATUSES,
        )

    return queryset


def _parse_needs_qualification(raw: Any) -> bool:
    if raw is None or raw == "":
        return False
    if isinstance(raw, bool):
        return raw
    value = str(raw).strip().lower()
    if value in {"true", "1", "yes"}:
        return True
    if value in {"false", "0", "no"}:
        return False
    raise SignalFeedFilterValidationError(
        "needs_qualification must be true or false.",
    )


def _parse_csv_values(*, raw: str | None) -> list[str]:
    if raw is None or not str(raw).strip():
        return []
    return [segment.strip() for segment in str(raw).split(",") if segment.strip()]


def _dedupe_sorted(values: list[str]) -> tuple[str, ...]:
    return tuple(sorted(set(values)))


def _parse_statuses(raw: str | None) -> tuple[str, ...]:
    values = _parse_csv_values(raw=raw)
    if not values:
        return ()

    normalized = _dedupe_sorted(values)
    if len(normalized) > MAX_FILTER_STATUSES:
        raise SignalFeedFilterValidationError(
            f"statuses accepts at most {MAX_FILTER_STATUSES} values.",
        )

    invalid = [value for value in normalized if value not in FEED_FILTERABLE_STATUSES]
    if invalid:
        raise SignalFeedFilterValidationError(
            "statuses must only contain open, in_progress, resolved, or canceled.",
        )

    return normalized


def _parse_uuid_list(*, raw: str | None, max_count: int, param_name: str) -> tuple[uuid.UUID, ...]:
    values = _parse_csv_values(raw=raw)
    if not values:
        return ()

    normalized = _dedupe_sorted(values)
    if len(normalized) > max_count:
        raise SignalFeedFilterValidationError(
            f"{param_name} accepts at most {max_count} values.",
        )

    parsed: list[uuid.UUID] = []
    invalid: list[str] = []
    for value in normalized:
        try:
            parsed.append(uuid.UUID(value))
        except ValueError:
            invalid.append(value)

    if invalid:
        raise SignalFeedFilterValidationError(
            f"Invalid {param_name}: {', '.join(invalid)}.",
        )

    return tuple(parsed)


def _parse_business_unit_ids(*, raw: str | None) -> tuple[uuid.UUID, ...]:
    return _parse_uuid_list(
        raw=raw,
        max_count=MAX_FILTER_BUSINESS_UNIT_IDS,
        param_name="business_unit_ids",
    )


def _parse_activity_subject_ids(*, raw: str | None) -> tuple[uuid.UUID, ...]:
    return _parse_uuid_list(
        raw=raw,
        max_count=MAX_FILTER_ACTIVITY_SUBJECT_IDS,
        param_name="activity_subject_ids",
    )


def _validate_business_unit_ids_exist(
    *,
    establishment_id: uuid.UUID,
    business_unit_ids: tuple[uuid.UUID, ...],
) -> None:
    if not business_unit_ids:
        return

    found = set(
        BusinessUnit.objects.filter(
            establishment_id=establishment_id,
            active=True,
            id__in=business_unit_ids,
        ).values_list("id", flat=True),
    )
    unknown = [str(value) for value in business_unit_ids if value not in found]
    if unknown:
        raise SignalFeedFilterValidationError(
            f"Unknown or inactive business_unit_ids: {', '.join(unknown)}.",
        )


def _validate_activity_subject_ids_exist(
    *,
    establishment_id: uuid.UUID,
    activity_subject_ids: tuple[uuid.UUID, ...],
) -> None:
    if not activity_subject_ids:
        return

    found = set(
        ActivitySubject.objects.filter(
            establishment_id=establishment_id,
            active=True,
            id__in=activity_subject_ids,
        ).values_list("id", flat=True),
    )
    unknown = [str(value) for value in activity_subject_ids if value not in found]
    if unknown:
        raise SignalFeedFilterValidationError(
            f"Unknown or inactive activity_subject_ids: {', '.join(unknown)}.",
        )
