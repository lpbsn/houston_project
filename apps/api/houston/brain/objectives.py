"""Objective revisions copied into a dossier.

Evaluations and the current bilan stay in a later lot.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date

from django.db import transaction

from houston.brain.errors import BrainWorkError
from houston.brain.models import BrainObjective, BrainObjectiveRevision


def revision_content_hash(
    *,
    indicator: str,
    unit: str,
    scope: str,
    reference: str,
    target: str,
    due_on: date | None,
    measurement_period_start: date | None,
    measurement_period_end: date | None,
    method: str,
) -> str:
    payload = {
        "due_on": due_on.isoformat() if due_on else None,
        "indicator": indicator,
        "measurement_period_end": (
            measurement_period_end.isoformat() if measurement_period_end else None
        ),
        "measurement_period_start": (
            measurement_period_start.isoformat() if measurement_period_start else None
        ),
        "method": method,
        "reference": reference,
        "scope": scope,
        "target": target,
        "unit": unit,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def record_objective_revision(
    *,
    establishment,
    objective: BrainObjective | None = None,
    indicator: str,
    unit: str = "",
    scope: str = "",
    reference: str = "",
    target: str = "",
    due_on: date | None = None,
    measurement_period_start: date | None = None,
    measurement_period_end: date | None = None,
    method: str = "",
) -> BrainObjectiveRevision:
    """Append the current revision. Does not evaluate it and does not publish a bilan."""
    if objective is not None and objective.establishment_id != establishment.id:
        raise BrainWorkError(
            code="objective_establishment_mismatch",
            message="L'objectif n'appartient pas à cet établissement.",
        )
    bounds = (measurement_period_start, measurement_period_end)
    if (bounds[0] is None) != (bounds[1] is None):
        raise BrainWorkError(
            code="objective_measurement_period_incomplete",
            message="La période de mesure doit avoir un début et une fin.",
        )
    if bounds[0] is not None and bounds[1] is not None and bounds[1] <= bounds[0]:
        raise BrainWorkError(
            code="objective_measurement_period_order",
            message="La fin de la période de mesure doit être postérieure au début.",
        )
    content_hash = revision_content_hash(
        indicator=indicator,
        unit=unit,
        scope=scope,
        reference=reference,
        target=target,
        due_on=due_on,
        measurement_period_start=measurement_period_start,
        measurement_period_end=measurement_period_end,
        method=method,
    )
    with transaction.atomic():
        if objective is None:
            objective = BrainObjective.objects.create(establishment=establishment)
        revision = BrainObjectiveRevision.objects.create(
            objective=objective,
            establishment=establishment,
            indicator=indicator,
            unit=unit,
            scope=scope,
            reference=reference,
            target=target,
            due_on=due_on,
            measurement_period_start=measurement_period_start,
            measurement_period_end=measurement_period_end,
            method=method,
            content_hash=content_hash,
        )
        objective.current_revision = revision
        objective.save(update_fields=["current_revision", "updated_at"])
    return revision


def revision_overlaps_period(
    revision: BrainObjectiveRevision,
    *,
    period_start: date,
    period_end: date,
) -> bool:
    if revision.due_on is not None and period_start <= revision.due_on < period_end:
        return True
    start = revision.measurement_period_start
    end = revision.measurement_period_end
    if start is not None and end is not None and start < period_end and end > period_start:
        return True
    return False
