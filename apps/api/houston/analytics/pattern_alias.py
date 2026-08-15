from __future__ import annotations

import uuid
from dataclasses import dataclass

from django.db.models import Q

from houston.analytics.classifier import PatternClassifierInvalidOutputError
from houston.analytics.models import OperationalPattern
from houston.signals.models import Signal


@dataclass(frozen=True)
class PatternExactAliasResolution:
    status: str
    pattern: OperationalPattern | None = None


def _resolve_exact_pattern_alias(
    *,
    signal: Signal,
    normalized_alias: str,
) -> PatternExactAliasResolution:
    active_patterns = list(
        OperationalPattern.objects.filter(
            Q(normalized_semantic_label=normalized_alias)
            | Q(normalized_label=normalized_alias),
            organization=signal.establishment.organization,
            status=OperationalPattern.Status.ACTIVE,
        ).order_by("id")[:2]
    )
    if len(active_patterns) == 1:
        return PatternExactAliasResolution(status="resolved", pattern=active_patterns[0])
    if len(active_patterns) > 1:
        return PatternExactAliasResolution(status="ambiguous")

    merged_patterns = list(
        OperationalPattern.objects.filter(
            organization=signal.establishment.organization,
            normalized_semantic_label=normalized_alias,
            status=OperationalPattern.Status.MERGED,
        ).order_by("id")
    )
    if not merged_patterns:
        return PatternExactAliasResolution(status="none")

    targets: dict[uuid.UUID, OperationalPattern] = {}
    unresolved = False
    for pattern in merged_patterns:
        target = _resolve_merged_pattern_chain(signal=signal, pattern=pattern)
        if target is None:
            unresolved = True
            continue
        targets[target.id] = target
    if len(targets) == 1 and not unresolved:
        return PatternExactAliasResolution(
            status="resolved",
            pattern=next(iter(targets.values())),
        )
    return PatternExactAliasResolution(status="ambiguous")


def _resolve_active_pattern_target(
    *,
    signal: Signal,
    pattern: OperationalPattern,
) -> OperationalPattern:
    if (
        pattern.organization_id == signal.establishment.organization_id
        and pattern.status == OperationalPattern.Status.ACTIVE
    ):
        return pattern

    if pattern.status == OperationalPattern.Status.MERGED:
        target = _resolve_merged_pattern_chain(signal=signal, pattern=pattern)
        if target is not None:
            return target

    active = (
        OperationalPattern.objects.select_for_update()
        .filter(
            organization=signal.establishment.organization,
            normalized_semantic_label=pattern.normalized_semantic_label,
            status=OperationalPattern.Status.ACTIVE,
        )
        .first()
    )
    if active is not None:
        return active

    raise PatternClassifierInvalidOutputError(
        "No active target pattern could be resolved.",
        validation_branch="no_active_target_pattern",
    )


def _resolve_merged_pattern_chain(
    *,
    signal: Signal,
    pattern: OperationalPattern,
) -> OperationalPattern | None:
    seen = {pattern.id}
    current = pattern
    for _ in range(5):
        if current.merged_into_id is None:
            return None
        target = OperationalPattern.objects.select_for_update().get(pk=current.merged_into_id)
        if target.id in seen:
            return None
        seen.add(target.id)
        if target.organization_id != signal.establishment.organization_id:
            return None
        if target.status == OperationalPattern.Status.ACTIVE:
            return target
        if target.status != OperationalPattern.Status.MERGED:
            return None
        current = target
    return None
