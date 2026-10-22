"""One REPEATABLE READ capture. The commit closes the dossier; a failure leaves it unclosed.

The budget is a monotonic deadline checked before each SQL statement, including the
closing writes, and once more immediately before COMMIT. Python between those checks
is not interrupted: it can run past the deadline, and the next check then rolls the
transaction back without closing the dossier. Each statement receives, as its
statement_timeout, only the time still left when it starts. COMMIT receives the time
still left after the closing write, not another copy of the original budget.
"""

from __future__ import annotations

import logging
import time

from django.db import connection, transaction
from django.db.utils import OperationalError

from houston.analytics.journal import get_history_reliable_from
from houston.brain.collection import REQUIRED_SEARCHES, collect_capture
from houston.brain.corpus import assemble_investigation_corpus
from houston.brain.dossier import assemble_period_snapshot, persist_period_contents
from houston.brain.errors import BrainWorkError, CaptureTimeout
from houston.brain.models import (
    BrainAnalysis,
    BrainDossier,
    BrainDossierItem,
    BrainExtraction,
    BrainSearchRun,
)

logger = logging.getLogger(__name__)

_OPEN_STATUSES = (BrainAnalysis.Status.QUEUED, BrainAnalysis.Status.RUNNING)


class _Budget:
    """Deadline checked at each statement. Python between checks is not preempted."""

    def __init__(self, started: float, timeout_seconds: int):
        self.deadline = started + timeout_seconds

    def remaining(self) -> float:
        return self.deadline - time.monotonic()

    def arm(self) -> None:
        remaining = self.remaining()
        if remaining <= 0:
            raise CaptureTimeout()
        millis = max(1, int(remaining * 1000))
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT set_config('statement_timeout', %s, true)",
                [str(millis)],
            )

    def run(self, fn):
        self.arm()
        try:
            return fn()
        except OperationalError as exc:
            if _is_statement_timeout(exc):
                raise CaptureTimeout() from exc
            raise

    def pause(self, seconds: float) -> None:
        def sleep():
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_sleep(%s)", [seconds])

        self.run(sleep)


def capture_dossier(
    analysis_id,
    *,
    _pauses: tuple[float, ...] = (),
    _pauses_before_close: tuple[float, ...] = (),
    _fail_before_close: bool = False,
    _before_close=None,
    _before_commit=None,
) -> BrainDossier:
    """Copy the establishment view and close the dossier in one transaction.

    Injected pauses and hooks exist so tests can prove the deadline and the snapshot.
    Production callers leave them empty. A Python pause is not cut at the deadline;
    the following statement check refuses the close.
    """
    if connection.in_atomic_block:
        raise BrainWorkError(
            code="capture_nested_transaction",
            message="La capture doit ouvrir sa propre transaction.",
        )
    started = time.monotonic()
    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            analysis = _load_analysis(analysis_id)
            timeout_seconds, ceiling = _ceilings(analysis)
            budget = _Budget(started, timeout_seconds)
            for delay in _pauses:
                budget.pause(delay)
            capture_at = budget.run(_transaction_timestamp)
            dossier = _capture_in_snapshot(
                analysis,
                capture_at=capture_at,
                ceiling=ceiling,
                budget=budget,
                fail_before_close=_fail_before_close,
                before_close=_before_close,
                pauses_before_close=_pauses_before_close,
                before_commit=_before_commit,
            )
            budget.arm()
    except CaptureTimeout:
        logger.info(
            "brain_capture_timeout",
            extra={"event": "brain_capture_timeout", "analysis_id": str(analysis_id)},
        )
        raise
    except OperationalError as exc:
        if _is_statement_timeout(exc):
            logger.info(
                "brain_capture_timeout",
                extra={"event": "brain_capture_timeout", "analysis_id": str(analysis_id)},
            )
            raise CaptureTimeout() from exc
        raise
    logger.info(
        "brain_dossier_closed",
        extra={
            "event": "brain_dossier_closed",
            "analysis_id": str(analysis.id),
            "dossier_id": str(dossier.id),
        },
    )
    return dossier


def capture_period_dossier(
    analysis_id,
    *,
    _pauses: tuple[float, ...] = (),
    _fail_before_close: bool = False,
    _before_close=None,
    _before_commit=None,
) -> BrainDossier:
    """Copy one period and close that dossier. Only the V3 executor calls this.

    The transaction matches ``capture_dossier``: REPEATABLE READ, one timestamp,
    commit closes the dossier. Observations are not read. No provider call is made.
    """
    if connection.in_atomic_block:
        raise BrainWorkError(
            code="capture_nested_transaction",
            message="La capture doit ouvrir sa propre transaction.",
        )
    started = time.monotonic()
    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            analysis = _load_analysis(analysis_id)
            timeout_seconds, ceiling = _ceilings(analysis)
            budget = _Budget(started, timeout_seconds)
            for delay in _pauses:
                budget.pause(delay)
            capture_at = budget.run(_transaction_timestamp)
            dossier = _capture_period_in_snapshot(
                analysis,
                capture_at=capture_at,
                ceiling=ceiling,
                budget=budget,
                fail_before_close=_fail_before_close,
                before_close=_before_close,
                before_commit=_before_commit,
            )
            budget.arm()
    except CaptureTimeout:
        logger.info(
            "brain_capture_timeout",
            extra={"event": "brain_capture_timeout", "analysis_id": str(analysis_id)},
        )
        raise
    except OperationalError as exc:
        if _is_statement_timeout(exc):
            logger.info(
                "brain_capture_timeout",
                extra={"event": "brain_capture_timeout", "analysis_id": str(analysis_id)},
            )
            raise CaptureTimeout() from exc
        raise
    logger.info(
        "brain_period_dossier_closed",
        extra={
            "event": "brain_period_dossier_closed",
            "analysis_id": str(analysis.id),
            "dossier_id": str(dossier.id),
        },
    )
    return dossier


def capture_investigation_dossier(
    analysis_id,
    *,
    _pauses: tuple[float, ...] = (),
    _fail_before_close: bool = False,
    _before_close=None,
    _before_commit=None,
) -> BrainDossier:
    """Copy the searchable corpus and close the dossier before any tool runs.

    Same transaction as the other captures: REPEATABLE READ, one timestamp,
    commit closes the dossier. Observations are not read. No provider call is made.
    """
    if connection.in_atomic_block:
        raise BrainWorkError(
            code="capture_nested_transaction",
            message="La capture doit ouvrir sa propre transaction.",
        )
    started = time.monotonic()
    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            analysis = _load_analysis(analysis_id)
            timeout_seconds, ceiling = _ceilings(analysis)
            budget = _Budget(started, timeout_seconds)
            for delay in _pauses:
                budget.pause(delay)
            capture_at = budget.run(_transaction_timestamp)
            dossier = _capture_investigation_in_snapshot(
                analysis,
                capture_at=capture_at,
                ceiling=ceiling,
                budget=budget,
                fail_before_close=_fail_before_close,
                before_close=_before_close,
                before_commit=_before_commit,
            )
            budget.arm()
    except CaptureTimeout:
        logger.info(
            "brain_capture_timeout",
            extra={"event": "brain_capture_timeout", "analysis_id": str(analysis_id)},
        )
        raise
    except OperationalError as exc:
        if _is_statement_timeout(exc):
            logger.info(
                "brain_capture_timeout",
                extra={"event": "brain_capture_timeout", "analysis_id": str(analysis_id)},
            )
            raise CaptureTimeout() from exc
        raise
    logger.info(
        "brain_investigation_dossier_closed",
        extra={
            "event": "brain_investigation_dossier_closed",
            "analysis_id": str(analysis.id),
            "dossier_id": str(dossier.id),
        },
    )
    return dossier


def _capture_investigation_in_snapshot(
    analysis: BrainAnalysis,
    *,
    capture_at,
    ceiling: int,
    budget: _Budget,
    fail_before_close: bool,
    before_close,
    before_commit,
) -> BrainDossier:
    if analysis.status not in _OPEN_STATUSES:
        raise BrainWorkError(
            code="analysis_not_open",
            message="Cette analyse n'accepte plus de capture.",
        )
    reporting = analysis.reporting
    if (
        reporting.period_start is None
        or reporting.period_end is None
        or reporting.establishment_id != analysis.establishment_id
    ):
        raise BrainWorkError(
            code="reporting_period_missing",
            message="La période confirmée du reporting est absente.",
        )
    closed = budget.run(
        lambda: BrainDossier.objects.filter(
            analysis_id=analysis.id,
            closed_at__isnull=False,
        ).exists()
    )
    if closed:
        raise BrainWorkError(
            code="dossier_already_closed",
            message="Le dossier est déjà fermé.",
        )
    extraction = _locked_extraction(budget, analysis)
    reliable_from = budget.run(get_history_reliable_from)
    rows = assemble_investigation_corpus(
        analysis=analysis,
        extraction_payload=extraction.payload,
        capture_at=capture_at,
        reliable_from=reliable_from,
        ceiling=ceiling,
        run=budget.run,
    )
    if before_close is not None:
        budget.arm()
        before_close()
    if fail_before_close:
        raise BrainWorkError(
            code="capture_incomplete",
            message="La capture n'a pas été fermée.",
        )
    establishment = analysis.establishment
    dossier = budget.run(
        lambda: BrainDossier.objects.create(
            analysis=analysis,
            establishment=establishment,
            timezone=establishment.timezone,
            period_start=reporting.period_start,
            period_end=reporting.period_end,
            capture_started_at=capture_at,
        )
    )
    budget.run(
        lambda: BrainDossierItem.objects.bulk_create(
            [
                BrainDossierItem(
                    dossier=dossier,
                    category=row.category,
                    stable_key=row.stable_key,
                    role=row.role,
                    payload=row.payload,
                    reason=row.reason,
                )
                for row in rows
            ]
        )
    )
    dossier.closed_at = budget.run(_transaction_timestamp)
    budget.run(lambda: dossier.save(update_fields=["closed_at", "updated_at"]))
    if before_commit is not None:
        before_commit(budget)
    return dossier


def _capture_period_in_snapshot(
    analysis: BrainAnalysis,
    *,
    capture_at,
    ceiling: int,
    budget: _Budget,
    fail_before_close: bool,
    before_close,
    before_commit,
) -> BrainDossier:
    if analysis.status not in _OPEN_STATUSES:
        raise BrainWorkError(
            code="analysis_not_open",
            message="Cette analyse n'accepte plus de capture.",
        )
    reporting = analysis.reporting
    if (
        reporting.period_start is None
        or reporting.period_end is None
        or reporting.establishment_id != analysis.establishment_id
    ):
        raise BrainWorkError(
            code="reporting_period_missing",
            message="La période confirmée du reporting est absente.",
        )
    closed = budget.run(
        lambda: BrainDossier.objects.filter(
            analysis_id=analysis.id,
            closed_at__isnull=False,
        ).exists()
    )
    if closed:
        raise BrainWorkError(
            code="dossier_already_closed",
            message="Le dossier est déjà fermé.",
        )
    extraction = _locked_extraction(budget, analysis)
    reliable_from = budget.run(get_history_reliable_from)
    assembled = assemble_period_snapshot(
        establishment=analysis.establishment,
        reporting=reporting,
        extraction_payload=extraction.payload,
        capture_at=capture_at,
        reliable_from=reliable_from,
        ceiling=ceiling,
        run=budget.run,
    )
    if before_close is not None:
        budget.arm()
        before_close()
    if fail_before_close:
        raise BrainWorkError(
            code="capture_incomplete",
            message="La capture n'a pas été fermée.",
        )
    establishment = analysis.establishment
    dossier = budget.run(
        lambda: BrainDossier.objects.create(
            analysis=analysis,
            establishment=establishment,
            timezone=establishment.timezone,
            period_start=reporting.period_start,
            period_end=reporting.period_end,
            capture_started_at=capture_at,
        )
    )
    budget.run(lambda: persist_period_contents(dossier, assembled))
    dossier.closed_at = budget.run(_transaction_timestamp)
    budget.run(lambda: dossier.save(update_fields=["closed_at", "updated_at"]))
    if before_commit is not None:
        before_commit(budget)
    return dossier


def _capture_in_snapshot(
    analysis: BrainAnalysis,
    *,
    capture_at,
    ceiling: int,
    budget: _Budget,
    fail_before_close: bool,
    before_close,
    pauses_before_close: tuple[float, ...],
    before_commit,
) -> BrainDossier:
    if analysis.status not in _OPEN_STATUSES:
        raise BrainWorkError(
            code="analysis_not_open",
            message="Cette analyse n'accepte plus de capture.",
        )
    reporting = analysis.reporting
    if (
        reporting.period_start is None
        or reporting.period_end is None
        or reporting.establishment_id != analysis.establishment_id
    ):
        raise BrainWorkError(
            code="reporting_period_missing",
            message="La période confirmée du reporting est absente.",
        )
    closed = budget.run(
        lambda: BrainDossier.objects.filter(
            analysis_id=analysis.id,
            closed_at__isnull=False,
        ).exists()
    )
    if closed:
        raise BrainWorkError(
            code="dossier_already_closed",
            message="Le dossier est déjà fermé.",
        )
    extraction = _locked_extraction(budget, analysis)
    reliable_from = budget.run(get_history_reliable_from)
    establishment = analysis.establishment
    rows, searches = collect_capture(
        establishment=establishment,
        reporting=reporting,
        extraction_payload=extraction.payload,
        capture_at=capture_at,
        reliable_from=reliable_from,
        ceiling=ceiling,
        run=budget.run,
    )
    if {search.code for search in searches} != set(REQUIRED_SEARCHES):
        raise BrainWorkError(
            code="capture_searches_incomplete",
            message="Une recherche minimale n'a pas été exécutée.",
        )
    if before_close is not None:
        budget.arm()
        before_close()
    dossier = budget.run(
        lambda: BrainDossier.objects.create(
            analysis=analysis,
            establishment=establishment,
            timezone=establishment.timezone,
            period_start=reporting.period_start,
            period_end=reporting.period_end,
            capture_started_at=capture_at,
        )
    )
    budget.run(
        lambda: BrainDossierItem.objects.bulk_create(
            [
                BrainDossierItem(
                    dossier=dossier,
                    category=row.category,
                    stable_key=row.stable_key,
                    role=row.role,
                    payload=row.payload,
                    reason=row.reason,
                )
                for row in rows
            ]
        )
    )
    budget.run(
        lambda: BrainSearchRun.objects.bulk_create(
            [
                BrainSearchRun(
                    dossier=dossier,
                    code=search.code,
                    criteria=search.as_criteria(),
                    examined_count=search.examined_count,
                    retained_count=search.retained_count,
                )
                for search in searches
            ]
        )
    )
    if fail_before_close:
        raise BrainWorkError(
            code="capture_incomplete",
            message="La capture n'a pas été fermée.",
        )
    for delay in pauses_before_close:
        budget.pause(delay)
    dossier.closed_at = budget.run(_transaction_timestamp)
    budget.run(lambda: dossier.save(update_fields=["closed_at", "updated_at"]))
    if before_commit is not None:
        before_commit(budget)
    return dossier


def _load_analysis(analysis_id) -> BrainAnalysis:
    analysis = (
        BrainAnalysis.objects.select_related("reporting", "establishment")
        .filter(pk=analysis_id)
        .first()
    )
    if analysis is None:
        raise BrainWorkError(
            code="analysis_not_found",
            message="L'analyse est introuvable.",
        )
    return analysis


def _locked_extraction(budget: _Budget, analysis: BrainAnalysis) -> BrainExtraction:
    config = analysis.configuration if isinstance(analysis.configuration, dict) else {}
    try:
        extractor_id = config["extractor_id"]
        extractor_version = config["extractor_version"]
        source_sha256 = config["source_sha256"]
    except (KeyError, TypeError) as exc:
        raise BrainWorkError(
            code="configuration_unusable",
            message="La configuration figée de l'analyse est inutilisable.",
        ) from exc
    extraction = budget.run(
        lambda: BrainExtraction.objects.filter(
            reporting_id=analysis.reporting_id,
            extractor_id=extractor_id,
            extractor_version=extractor_version,
            source_sha256=source_sha256,
        ).first()
    )
    if extraction is None or not isinstance(extraction.payload, dict):
        raise BrainWorkError(
            code="configuration_unusable",
            message="La configuration figée de l'analyse est inutilisable.",
        )
    return extraction


def _ceilings(analysis: BrainAnalysis) -> tuple[int, int]:
    config = analysis.configuration if isinstance(analysis.configuration, dict) else {}
    ceilings = config.get("ceilings")
    if not isinstance(ceilings, dict):
        raise BrainWorkError(
            code="configuration_unusable",
            message="La configuration figée de l'analyse est inutilisable.",
        )
    try:
        timeout_seconds = int(ceilings["capture_timeout_seconds"])
        ceiling = int(ceilings["max_candidates_per_category"])
    except (KeyError, TypeError, ValueError) as exc:
        raise BrainWorkError(
            code="configuration_unusable",
            message="La configuration figée de l'analyse est inutilisable.",
        ) from exc
    if timeout_seconds <= 0 or ceiling <= 0:
        raise BrainWorkError(
            code="configuration_unusable",
            message="La configuration figée de l'analyse est inutilisable.",
        )
    return timeout_seconds, ceiling


def _transaction_timestamp():
    with connection.cursor() as cursor:
        cursor.execute("SELECT transaction_timestamp()")
        return cursor.fetchone()[0]


def _is_statement_timeout(exc: BaseException) -> bool:
    seen: BaseException | None = exc
    while seen is not None:
        sqlstate = getattr(seen, "sqlstate", None) or getattr(seen, "pgcode", None)
        if sqlstate == "57014" or "statement timeout" in str(seen).lower():
            return True
        seen = seen.__cause__
    return False
