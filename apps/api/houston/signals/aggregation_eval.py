from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from django.db.models import Count, QuerySet

from houston.signals.constants import ACTIVE_SIGNAL_STATUSES
from houston.signals.models import CandidateSignal, Signal


def _normalize_issue_focus(value: str | None) -> str:
    from houston.signals.services import normalize_issue_focus

    return normalize_issue_focus(value)


@dataclass(frozen=True)
class TaxonomyDuplicateGroup:
    establishment_id: uuid.UUID
    affected_business_unit_id: uuid.UUID
    responsible_business_unit_id: uuid.UUID
    activity_subject_id: uuid.UUID
    operational_unit_id: uuid.UUID | None
    signal_count: int
    distinct_issue_focus_count: int
    issue_focuses: tuple[str, ...]


@dataclass
class IssueFocusEvalMetrics:
    establishment_id: uuid.UUID | None
    active_signal_count: int = 0
    taxonomy_duplicate_group_count: int = 0
    taxonomy_duplicate_signal_count: int = 0
    taxonomy_duplicate_groups: list[TaxonomyDuplicateGroup] = field(default_factory=list)
    hint_provided_candidate_count: int = 0
    hint_rejected_created_count: int = 0
    hint_issue_focus_mismatch_count: int = 0
    lot4bis_trigger_indicators: dict[str, bool] = field(default_factory=dict)


def format_taxonomy_bucket_key(
    *,
    affected_business_unit_id: uuid.UUID,
    responsible_business_unit_id: uuid.UUID,
    activity_subject_id: uuid.UUID,
    operational_unit_id: uuid.UUID | None,
) -> str:
    unit_token = str(operational_unit_id) if operational_unit_id is not None else "null"
    return (
        f"{affected_business_unit_id}|{responsible_business_unit_id}|"
        f"{activity_subject_id}|{unit_token}"
    )


def count_active_taxonomy_peers_with_different_focus(
    *,
    establishment_id: uuid.UUID,
    affected_business_unit_id: uuid.UUID,
    responsible_business_unit_id: uuid.UUID,
    activity_subject_id: uuid.UUID,
    operational_unit_id: uuid.UUID | None,
    issue_focus: str,
) -> int:
    queryset = Signal.objects.filter(
        establishment_id=establishment_id,
        affected_business_unit_id=affected_business_unit_id,
        responsible_business_unit_id=responsible_business_unit_id,
        activity_subject_id=activity_subject_id,
        status__in=ACTIVE_SIGNAL_STATUSES,
    ).exclude(issue_focus=issue_focus)
    if operational_unit_id is None:
        queryset = queryset.filter(operational_unit__isnull=True)
    else:
        queryset = queryset.filter(operational_unit_id=operational_unit_id)
    return queryset.count()


def find_active_taxonomy_duplicate_groups(
    *,
    establishment_id: uuid.UUID | None = None,
    limit: int = 50,
) -> list[TaxonomyDuplicateGroup]:
    queryset = Signal.objects.filter(status__in=ACTIVE_SIGNAL_STATUSES)
    if establishment_id is not None:
        queryset = queryset.filter(establishment_id=establishment_id)

    grouped = (
        queryset.values(
            "establishment_id",
            "affected_business_unit_id",
            "responsible_business_unit_id",
            "activity_subject_id",
            "operational_unit_id",
        )
        .annotate(
            signal_count=Count("id"),
            distinct_issue_focus_count=Count("issue_focus", distinct=True),
        )
        .filter(signal_count__gt=1, distinct_issue_focus_count__gt=1)
        .order_by("-signal_count", "-distinct_issue_focus_count")[:limit]
    )

    groups: list[TaxonomyDuplicateGroup] = []
    for row in grouped:
        peer_queryset = queryset.filter(
            establishment_id=row["establishment_id"],
            affected_business_unit_id=row["affected_business_unit_id"],
            responsible_business_unit_id=row["responsible_business_unit_id"],
            activity_subject_id=row["activity_subject_id"],
        )
        if row["operational_unit_id"] is None:
            peer_queryset = peer_queryset.filter(operational_unit__isnull=True)
        else:
            peer_queryset = peer_queryset.filter(
                operational_unit_id=row["operational_unit_id"],
            )
        focuses = tuple(
            sorted(
                {
                    focus
                    for focus in peer_queryset.values_list("issue_focus", flat=True)
                    if focus
                }
            )
        )
        groups.append(
            TaxonomyDuplicateGroup(
                establishment_id=row["establishment_id"],
                affected_business_unit_id=row["affected_business_unit_id"],
                responsible_business_unit_id=row["responsible_business_unit_id"],
                activity_subject_id=row["activity_subject_id"],
                operational_unit_id=row["operational_unit_id"],
                signal_count=row["signal_count"],
                distinct_issue_focus_count=row["distinct_issue_focus_count"],
                issue_focuses=focuses,
            )
        )
    return groups


def _hint_rejection_queryset(
    *,
    establishment_id: uuid.UUID | None = None,
) -> QuerySet[CandidateSignal]:
    queryset = CandidateSignal.objects.filter(
        ai_aggregate_hint_signal_id__isnull=False,
        outcome=CandidateSignal.Outcome.CREATED_SIGNAL,
    )
    if establishment_id is not None:
        queryset = queryset.filter(establishment_id=establishment_id)
    return queryset


def count_hint_issue_focus_mismatches(
    *,
    establishment_id: uuid.UUID | None = None,
) -> tuple[int, int]:
    rejected_queryset = _hint_rejection_queryset(establishment_id=establishment_id)
    hint_provided_count = CandidateSignal.objects.filter(
        ai_aggregate_hint_signal_id__isnull=False,
    )
    if establishment_id is not None:
        hint_provided_count = hint_provided_count.filter(establishment_id=establishment_id)

    mismatch_count = 0
    for candidate in rejected_queryset.only(
        "issue_focus",
        "ai_aggregate_hint_signal_id",
    ):
        hint_signal = Signal.objects.filter(
            id=candidate.ai_aggregate_hint_signal_id,
        ).only("issue_focus").first()
        if hint_signal is None:
            continue
        if _normalize_issue_focus(candidate.issue_focus) != _normalize_issue_focus(
            hint_signal.issue_focus,
        ):
            mismatch_count += 1

    return hint_provided_count.count(), mismatch_count


def compute_lot4bis_trigger_indicators(
    *,
    metrics: IssueFocusEvalMetrics,
    min_duplicate_groups: int = 3,
    min_hint_mismatch_rate: float = 0.15,
    min_duplicate_signals: int = 6,
) -> dict[str, bool]:
    hint_rate = 0.0
    if metrics.hint_provided_candidate_count > 0:
        hint_rate = (
            metrics.hint_issue_focus_mismatch_count / metrics.hint_provided_candidate_count
        )

    return {
        "numerous_taxonomy_duplicate_groups": (
            metrics.taxonomy_duplicate_group_count >= min_duplicate_groups
        ),
        "frequent_reformulation_creates": (
            metrics.taxonomy_duplicate_signal_count >= min_duplicate_signals
        ),
        "elevated_hint_issue_focus_mismatch_rate": (
            metrics.hint_issue_focus_mismatch_count > 0
            and hint_rate >= min_hint_mismatch_rate
        ),
    }


def compute_issue_focus_eval_metrics(
    *,
    establishment_id: uuid.UUID | None = None,
    duplicate_group_limit: int = 50,
) -> IssueFocusEvalMetrics:
    active_signals = Signal.objects.filter(status__in=ACTIVE_SIGNAL_STATUSES)
    if establishment_id is not None:
        active_signals = active_signals.filter(establishment_id=establishment_id)

    duplicate_groups = find_active_taxonomy_duplicate_groups(
        establishment_id=establishment_id,
        limit=duplicate_group_limit,
    )
    hint_provided_count, hint_mismatch_count = count_hint_issue_focus_mismatches(
        establishment_id=establishment_id,
    )
    rejected_hint_count = _hint_rejection_queryset(
        establishment_id=establishment_id,
    ).count()

    metrics = IssueFocusEvalMetrics(
        establishment_id=establishment_id,
        active_signal_count=active_signals.count(),
        taxonomy_duplicate_group_count=len(duplicate_groups),
        taxonomy_duplicate_signal_count=sum(group.signal_count for group in duplicate_groups),
        taxonomy_duplicate_groups=duplicate_groups,
        hint_provided_candidate_count=hint_provided_count,
        hint_rejected_created_count=rejected_hint_count,
        hint_issue_focus_mismatch_count=hint_mismatch_count,
    )
    metrics.lot4bis_trigger_indicators = compute_lot4bis_trigger_indicators(
        metrics=metrics,
    )
    return metrics


def issue_focus_eval_metrics_to_dict(metrics: IssueFocusEvalMetrics) -> dict[str, Any]:
    return {
        "establishment_id": (
            str(metrics.establishment_id) if metrics.establishment_id is not None else None
        ),
        "active_signal_count": metrics.active_signal_count,
        "taxonomy_duplicate_group_count": metrics.taxonomy_duplicate_group_count,
        "taxonomy_duplicate_signal_count": metrics.taxonomy_duplicate_signal_count,
        "hint_provided_candidate_count": metrics.hint_provided_candidate_count,
        "hint_rejected_created_count": metrics.hint_rejected_created_count,
        "hint_issue_focus_mismatch_count": metrics.hint_issue_focus_mismatch_count,
        "lot4bis_trigger_indicators": metrics.lot4bis_trigger_indicators,
        "taxonomy_duplicate_groups": [
            {
                "establishment_id": str(group.establishment_id),
                "taxonomy_bucket_key": format_taxonomy_bucket_key(
                    affected_business_unit_id=group.affected_business_unit_id,
                    responsible_business_unit_id=group.responsible_business_unit_id,
                    activity_subject_id=group.activity_subject_id,
                    operational_unit_id=group.operational_unit_id,
                ),
                "signal_count": group.signal_count,
                "distinct_issue_focus_count": group.distinct_issue_focus_count,
                "issue_focuses": list(group.issue_focuses),
            }
            for group in metrics.taxonomy_duplicate_groups
        ],
    }
