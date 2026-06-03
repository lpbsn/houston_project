from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from django.db.models import Q

from houston.establishments.models import (
    OperationalDomain,
    OperationalModule,
    OperationalSubject,
)
from houston.signals.constants import FEED_SIGNAL_STATUSES

FEED_FILTERABLE_STATUSES = frozenset(FEED_SIGNAL_STATUSES)

MAX_FILTER_STATUSES = 3
MAX_FILTER_MODULE_KEYS = 20
MAX_FILTER_DOMAIN_KEYS = 50
MAX_FILTER_SUBJECT_KEYS = 100


@dataclass(frozen=True)
class SignalFeedFilters:
    statuses: tuple[str, ...] = ()
    module_keys: tuple[str, ...] = ()
    domain_keys: tuple[str, ...] = ()
    subject_keys: tuple[str, ...] = ()

    def has_any(self) -> bool:
        return bool(self.statuses or self.module_keys or self.domain_keys or self.subject_keys)


class SignalFeedFilterValidationError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


def parse_signal_feed_filters(
    *,
    query_params: Any,
    establishment_id: uuid.UUID,
) -> SignalFeedFilters:
    statuses = _parse_statuses(query_params.get("statuses"))
    module_keys = _parse_taxonomy_keys(
        raw=query_params.get("module_keys"),
        max_count=MAX_FILTER_MODULE_KEYS,
        param_name="module_keys",
    )
    domain_keys = _parse_taxonomy_keys(
        raw=query_params.get("domain_keys"),
        max_count=MAX_FILTER_DOMAIN_KEYS,
        param_name="domain_keys",
    )
    subject_keys = _parse_taxonomy_keys(
        raw=query_params.get("subject_keys"),
        max_count=MAX_FILTER_SUBJECT_KEYS,
        param_name="subject_keys",
    )

    _validate_taxonomy_keys_exist(
        establishment_id=establishment_id,
        module_keys=module_keys,
        domain_keys=domain_keys,
        subject_keys=subject_keys,
    )

    return SignalFeedFilters(
        statuses=statuses,
        module_keys=module_keys,
        domain_keys=domain_keys,
        subject_keys=subject_keys,
    )


def build_applied_filters_payload(
    *,
    view_mode: str,
    filters: SignalFeedFilters | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"view_mode": view_mode}
    if filters is None:
        payload["statuses"] = []
        payload["module_keys"] = []
        payload["domain_keys"] = []
        payload["subject_keys"] = []
        return payload

    payload["statuses"] = list(filters.statuses)
    payload["module_keys"] = list(filters.module_keys)
    payload["domain_keys"] = list(filters.domain_keys)
    payload["subject_keys"] = list(filters.subject_keys)
    return payload


def apply_feed_filters(queryset, *, filters: SignalFeedFilters | None):
    if filters is None or not filters.has_any():
        return queryset

    if filters.statuses:
        queryset = queryset.filter(status__in=filters.statuses)

    category_q = Q()
    if filters.module_keys:
        category_q |= Q(operational_module__key__in=filters.module_keys)
    if filters.domain_keys:
        category_q |= Q(operational_domain__key__in=filters.domain_keys)
    if filters.subject_keys:
        category_q |= Q(operational_subject__key__in=filters.subject_keys)
    if category_q:
        queryset = queryset.filter(category_q)

    return queryset


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
            "statuses must only contain open, in_progress, or resolved.",
        )

    return normalized


def _parse_taxonomy_keys(*, raw: str | None, max_count: int, param_name: str) -> tuple[str, ...]:
    values = _parse_csv_values(raw=raw)
    if not values:
        return ()

    normalized = _dedupe_sorted(values)
    if len(normalized) > max_count:
        raise SignalFeedFilterValidationError(
            f"{param_name} accepts at most {max_count} values.",
        )

    return normalized


def _validate_taxonomy_keys_exist(
    *,
    establishment_id: uuid.UUID,
    module_keys: tuple[str, ...],
    domain_keys: tuple[str, ...],
    subject_keys: tuple[str, ...],
) -> None:
    if module_keys:
        found = set(
            OperationalModule.objects.filter(
                establishment_id=establishment_id,
                active=True,
                key__in=module_keys,
            ).values_list("key", flat=True),
        )
        unknown = [key for key in module_keys if key not in found]
        if unknown:
            raise SignalFeedFilterValidationError(
                f"Unknown or inactive module_keys: {', '.join(unknown)}.",
            )

    if domain_keys:
        found = set(
            OperationalDomain.objects.filter(
                establishment_id=establishment_id,
                active=True,
                key__in=domain_keys,
            ).values_list("key", flat=True),
        )
        unknown = [key for key in domain_keys if key not in found]
        if unknown:
            raise SignalFeedFilterValidationError(
                f"Unknown or inactive domain_keys: {', '.join(unknown)}.",
            )

    if subject_keys:
        found = set(
            OperationalSubject.objects.filter(
                establishment_id=establishment_id,
                active=True,
                key__in=subject_keys,
            ).values_list("key", flat=True),
        )
        unknown = [key for key in subject_keys if key not in found]
        if unknown:
            raise SignalFeedFilterValidationError(
                f"Unknown or inactive subject_keys: {', '.join(unknown)}.",
            )
