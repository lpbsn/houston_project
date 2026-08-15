"""Frozen Architecture A token-overlap shortlist.

Runtime remains classifier v2.1 -> exact semantic alias -> token_overlap_v1 ->
duplicate guard v2 -> backend authority, with gpt-5-mini as the product model.

Keep the four projections distinct:
- classifier LLM: ``signature.build_signal_pattern_payload``
- signature/claim: ``signature.build_signal_pattern_identity_payload``
- guard LLM: ``pattern_guard._duplicate_guard_signal_payload``
- token_overlap_v1: ``_duplicate_guard_source_tokens``

Do not unify these projections or change shortlist scoring/ranking here.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

from django.conf import settings

from houston.analytics.labels import normalize_pattern_label
from houston.analytics.models import OperationalPattern
from houston.signals.models import Signal

DUPLICATE_GUARD_SHORTLIST_STRATEGY = "token_overlap_v1"


@dataclass(frozen=True)
class PatternDuplicateGuardCandidate:
    id: uuid.UUID
    label: str
    normalized_label: str
    semantic_label: str
    normalized_semantic_label: str
    score: float


class PatternDuplicateGuardShortlist(list[PatternDuplicateGuardCandidate]):
    def __init__(
        self,
        candidates=(),
        *,
        patterns_scanned: int,
        shortlist_elapsed_ms: int,
    ):
        super().__init__(candidates)
        self.patterns_scanned = patterns_scanned
        self.shortlist_size = len(self)
        self.shortlist_elapsed_ms = shortlist_elapsed_ms

    @property
    def metrics(self) -> dict[str, int]:
        return {
            "patterns_scanned": self.patterns_scanned,
            "shortlist_size": self.shortlist_size,
            "shortlist_elapsed_ms": self.shortlist_elapsed_ms,
        }


def _duplicate_guard_shortlist(
    *,
    signal: Signal,
    canonical_label: str,
) -> list[PatternDuplicateGuardCandidate]:
    started_at = time.monotonic()
    min_score = settings.HOUSTON_ANALYTICS_PATTERN_DUPLICATE_GUARD_MIN_SCORE
    max_candidates = settings.HOUSTON_ANALYTICS_PATTERN_DUPLICATE_GUARD_MAX_CANDIDATES
    if max_candidates <= 0:
        return PatternDuplicateGuardShortlist(
            patterns_scanned=0,
            shortlist_elapsed_ms=_elapsed_ms(started_at),
        )

    source_tokens = _duplicate_guard_source_tokens(
        signal=signal,
        canonical_label=canonical_label,
    )
    if not source_tokens:
        return PatternDuplicateGuardShortlist(
            patterns_scanned=0,
            shortlist_elapsed_ms=_elapsed_ms(started_at),
        )

    patterns_scanned = 0
    candidates: list[PatternDuplicateGuardCandidate] = []
    for pattern in OperationalPattern.objects.filter(
        organization=signal.establishment.organization,
        status=OperationalPattern.Status.ACTIVE,
    ):
        patterns_scanned += 1
        candidate_tokens = _normalized_tokens(pattern.semantic_label)
        if not candidate_tokens:
            continue
        score = len(source_tokens & candidate_tokens) / len(candidate_tokens)
        if score >= min_score:
            candidates.append(
                PatternDuplicateGuardCandidate(
                    id=pattern.id,
                    label=pattern.label,
                    normalized_label=pattern.normalized_label,
                    semantic_label=pattern.semantic_label,
                    normalized_semantic_label=pattern.normalized_semantic_label,
                    score=score,
                )
            )

    candidates.sort(
        key=lambda candidate: (
            -candidate.score,
            candidate.normalized_semantic_label,
            candidate.semantic_label,
            candidate.id,
        )
    )
    return PatternDuplicateGuardShortlist(
        candidates[:max_candidates],
        patterns_scanned=patterns_scanned,
        shortlist_elapsed_ms=_elapsed_ms(started_at),
    )


def _duplicate_guard_source_tokens(
    *,
    signal: Signal,
    canonical_label: str,
) -> set[str]:
    activity_subject = signal.activity_subject.label if signal.activity_subject_id else ""
    operational_unit = signal.operational_unit.label if signal.operational_unit_id else ""
    return _normalized_tokens(
        " ".join(
            [
                canonical_label,
                signal.title,
                signal.structured_summary,
                signal.issue_focus,
                activity_subject,
                operational_unit,
            ]
        )
    )


def _normalized_tokens(value: str) -> set[str]:
    return {token for token in normalize_pattern_label(value).split() if len(token) >= 3}


def _elapsed_ms(started_at: float) -> int:
    return int((time.monotonic() - started_at) * 1000)
