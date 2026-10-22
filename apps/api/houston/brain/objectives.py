"""Objective revisions and the evaluations attached to a captured revision.

A human decision appends a revision. An evaluation does not rewrite one.
The current bilan moves only when the captured revision is still current
and the measured period does not precede the bilan already displayed.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from decimal import Decimal, InvalidOperation

from django.db import transaction

from houston.brain.errors import BrainAccessDenied, BrainWorkError
from houston.brain.models import (
    BrainDossier,
    BrainDossierItem,
    BrainObjective,
    BrainObjectiveEvaluation,
    BrainObjectiveRevision,
)
from houston.establishments.permissions import resolve_establishment_admin_actor

DECISION_RECORDED = "recorded"
DECISION_ACCEPTED = "accepted"
DECISION_MODIFIED = "modified"
DECISION_REFUSED = "refused"
_HUMAN_DECISIONS = frozenset({DECISION_ACCEPTED, DECISION_MODIFIED, DECISION_REFUSED})
_ACCEPTED_DECISIONS = frozenset({DECISION_ACCEPTED, DECISION_MODIFIED})
_NUMERIC_CONDITIONS = frozenset({"eq", "gt", "gte", "lt", "lte"})
_CONDITIONS = frozenset({"", "qualitative", *_NUMERIC_CONDITIONS})
OUTCOME_REACHED = BrainObjectiveEvaluation.Outcome.REACHED
OUTCOME_NOT_REACHED = BrainObjectiveEvaluation.Outcome.NOT_REACHED
OUTCOME_NON_EVALUABLE = BrainObjectiveEvaluation.Outcome.NON_EVALUABLE
OUTCOME_QUALITATIVE = BrainObjectiveEvaluation.Outcome.QUALITATIVE


def revision_content_hash(
    *,
    indicator: str,
    unit: str,
    scope: str,
    reference: str,
    target: str,
    success_condition: str,
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
        "success_condition": success_condition,
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
    success_condition: str = "",
    due_on: date | None = None,
    measurement_period_start: date | None = None,
    measurement_period_end: date | None = None,
    method: str = "",
    decision: str = DECISION_RECORDED,
    justification: str = "",
    decided_by=None,
) -> BrainObjectiveRevision:
    """Append the current revision. Does not evaluate it and does not move the bilan."""
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
    condition = success_condition.strip()
    if condition not in _CONDITIONS:
        raise BrainWorkError(
            code="objective_condition_invalid",
            message="La condition de réussite n'est pas une condition prise en charge.",
        )
    content_hash = revision_content_hash(
        indicator=indicator,
        unit=unit,
        scope=scope,
        reference=reference,
        target=target,
        success_condition=condition,
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
            success_condition=condition,
            due_on=due_on,
            measurement_period_start=measurement_period_start,
            measurement_period_end=measurement_period_end,
            method=method,
            content_hash=content_hash,
            decision=decision,
            justification=justification,
            decided_by=decided_by,
        )
        objective.current_revision = revision
        objective.save(update_fields=["current_revision", "updated_at"])
    return revision


def decide_objective(
    *,
    user,
    objective_id,
    expected_revision_id,
    decision: str,
    indicator: str | None = None,
    unit: str | None = None,
    scope: str | None = None,
    reference: str | None = None,
    target: str | None = None,
    success_condition: str | None = None,
    due_on: date | None = None,
    measurement_period_start: date | None = None,
    measurement_period_end: date | None = None,
    method: str | None = None,
    justification: str = "",
) -> BrainObjectiveRevision:
    """Append a human decision. A stale revision leaves the newer decision in place."""
    if decision not in _HUMAN_DECISIONS:
        raise BrainWorkError(
            code="objective_decision_invalid",
            message="La décision d'objectif n'est pas reconnue.",
        )
    with transaction.atomic():
        objective = (
            BrainObjective.objects.select_for_update(of=("self",))
            .select_related("current_revision", "establishment")
            .filter(pk=objective_id)
            .first()
        )
        if objective is None or objective.current_revision_id is None:
            raise BrainWorkError(
                code="objective_not_found",
                message="L'objectif est introuvable.",
            )
        if resolve_establishment_admin_actor(user, objective.establishment_id) is None:
            raise BrainAccessDenied()
        current = objective.current_revision
        if current.id != expected_revision_id:
            raise BrainWorkError(
                code="objective_revision_conflict",
                message="Une décision plus récente existe déjà sur cet objectif.",
            )
        fields = {
            "indicator": current.indicator if indicator is None else indicator,
            "unit": current.unit if unit is None else unit,
            "scope": current.scope if scope is None else scope,
            "reference": current.reference if reference is None else reference,
            "target": current.target if target is None else target,
            "success_condition": (
                current.success_condition if success_condition is None else success_condition
            ),
            "due_on": current.due_on if due_on is None else due_on,
            "measurement_period_start": (
                current.measurement_period_start
                if measurement_period_start is None
                else measurement_period_start
            ),
            "measurement_period_end": (
                current.measurement_period_end
                if measurement_period_end is None
                else measurement_period_end
            ),
            "method": current.method if method is None else method,
        }
        if decision != DECISION_MODIFIED:
            fields = {
                "indicator": current.indicator,
                "unit": current.unit,
                "scope": current.scope,
                "reference": current.reference,
                "target": current.target,
                "success_condition": current.success_condition,
                "due_on": current.due_on,
                "measurement_period_start": current.measurement_period_start,
                "measurement_period_end": current.measurement_period_end,
                "method": current.method,
            }
        new_target = fields["target"].strip()
        target_changed = new_target != current.target.strip()
        if new_target and target_changed and not justification.strip():
            raise BrainWorkError(
                code="objective_target_unjustified",
                message="Une cible nouvelle exige une justification humaine.",
            )
        return record_objective_revision(
            establishment=objective.establishment,
            objective=objective,
            decision=decision,
            justification=justification.strip(),
            decided_by=user,
            **fields,
        )


def publish_objective_evaluations(analysis) -> None:
    """Write one evaluation per copied revision. Move the bilan only when both guards hold."""
    dossier = (
        BrainDossier.objects.filter(analysis_id=analysis.id, closed_at__isnull=False)
        .only("id", "period_start", "period_end", "establishment_id")
        .first()
    )
    if dossier is None or dossier.establishment_id != analysis.establishment_id:
        return
    items = list(
        BrainDossierItem.objects.filter(dossier_id=dossier.id, category="objective").only(
            "id",
            "payload",
        )
    )
    if not items:
        return
    measures = list(
        BrainDossierItem.objects.filter(
            dossier_id=dossier.id,
            category="document",
            role="mesure",
        ).only("id", "payload")
    )
    for item in items:
        payload = item.payload if isinstance(item.payload, dict) else {}
        revision_id = payload.get("revision_id")
        objective_id = payload.get("source_id")
        if not revision_id or not objective_id:
            raise BrainWorkError(
                code="evaluation_source_incomplete",
                message="La copie d'objectif ne porte pas sa révision.",
            )
        revision = (
            BrainObjectiveRevision.objects.filter(
                pk=revision_id,
                objective_id=objective_id,
                establishment_id=analysis.establishment_id,
            )
            .only(
                "id",
                "objective_id",
                "establishment_id",
                "indicator",
                "unit",
                "target",
                "decision",
                "success_condition",
            )
            .first()
        )
        if revision is None:
            raise BrainWorkError(
                code="evaluation_revision_missing",
                message="La révision copiée n'appartient pas à cet établissement.",
            )
        captured_decision = payload.get("decision")
        captured_condition = payload.get("success_condition")
        if captured_decision is None or captured_condition is None:
            raise BrainWorkError(
                code="evaluation_source_incomplete",
                message="La copie d'objectif ne porte pas sa décision ni sa condition.",
            )
        if (
            captured_decision != revision.decision
            or captured_condition != revision.success_condition
        ):
            raise BrainWorkError(
                code="evaluation_source_incomplete",
                message="La copie d'objectif ne correspond pas à la révision capturée.",
            )
        reading = _reading(revision, item, measures)
        evaluation, _created = BrainObjectiveEvaluation.objects.get_or_create(
            analysis=analysis,
            revision_id=revision.id,
            defaults={
                "objective_id": revision.objective_id,
                "establishment_id": analysis.establishment_id,
                "measured_period_start": dossier.period_start,
                "measured_period_end": dossier.period_end,
                "outcome": reading["outcome"],
                "reason": reading["reason"],
                "source_item_ids": reading["source_item_ids"],
                "measure": reading["measure"],
            },
        )
        _maybe_advance_bilan(evaluation)


def _maybe_advance_bilan(evaluation: BrainObjectiveEvaluation) -> None:
    objective = BrainObjective.objects.select_for_update().get(pk=evaluation.objective_id)
    if objective.current_revision_id != evaluation.revision_id:
        return
    if objective.current_bilan_id:
        current_end = (
            BrainObjectiveEvaluation.objects.filter(pk=objective.current_bilan_id)
            .values_list("measured_period_end", flat=True)
            .first()
        )
        if current_end is not None and evaluation.measured_period_end < current_end:
            return
    if objective.current_bilan_id == evaluation.id:
        return
    objective.current_bilan = evaluation
    objective.save(update_fields=["current_bilan", "updated_at"])


def _reading(revision: BrainObjectiveRevision, item, measures) -> dict:
    sources = [str(item.id)]
    pending = _decision_block(revision)
    if pending is not None:
        return {**pending, "source_item_ids": sources, "measure": None}
    if revision.success_condition == "qualitative":
        return {
            "outcome": OUTCOME_QUALITATIVE,
            "reason": "qualitative_appreciation",
            "source_item_ids": sources,
            "measure": None,
        }
    if revision.success_condition not in _NUMERIC_CONDITIONS:
        return {
            "outcome": OUTCOME_NON_EVALUABLE,
            "reason": "condition_missing",
            "source_item_ids": sources,
            "measure": None,
        }
    matched = _matching_measures(revision, measures)
    if not matched:
        return {
            "outcome": OUTCOME_NON_EVALUABLE,
            "reason": "measure_missing",
            "source_item_ids": sources,
            "measure": None,
        }
    if len(matched) > 1:
        return {
            "outcome": OUTCOME_NON_EVALUABLE,
            "reason": "ambiguous_measure",
            "source_item_ids": sources,
            "measure": None,
        }
    measure_item, measure = matched[0]
    sources.append(str(measure_item.id))
    stored = {
        "item_id": str(measure_item.id),
        "value": measure.get("value"),
        "unit": measure.get("unit"),
    }
    if measure.get("ambiguities"):
        reason = "ambiguous_measure"
    elif not _same_unit(revision.unit, measure.get("unit")):
        reason = "unit_mismatch"
    elif _decimal(revision.target) is None:
        reason = "target_not_numeric"
    elif _decimal(measure.get("value")) is None:
        reason = "comparison_not_verifiable"
    else:
        reached = _satisfies(
            revision.success_condition,
            _decimal(revision.target),
            _decimal(measure.get("value")),
        )
        return {
            "outcome": OUTCOME_REACHED if reached else OUTCOME_NOT_REACHED,
            "reason": "numeric_comparison",
            "source_item_ids": sources,
            "measure": stored,
        }
    return {
        "outcome": OUTCOME_NON_EVALUABLE,
        "reason": reason,
        "source_item_ids": sources,
        "measure": stored,
    }


def _decision_block(revision: BrainObjectiveRevision) -> dict | None:
    if revision.decision in _ACCEPTED_DECISIONS:
        return None
    reason = "decision_refused" if revision.decision == DECISION_REFUSED else "decision_pending"
    return {"outcome": OUTCOME_NON_EVALUABLE, "reason": reason}


def _matching_measures(revision: BrainObjectiveRevision, measures) -> list:
    indicator = revision.indicator.strip().casefold()
    if not indicator:
        return []
    found = []
    for item in measures:
        payload = item.payload if isinstance(item.payload, dict) else {}
        label = str(payload.get("label") or "").strip().casefold()
        if label == indicator:
            found.append((item, payload))
    return found


def _satisfies(operator: str, target: Decimal, value: Decimal) -> bool:
    if operator == "eq":
        return value == target
    if operator == "gt":
        return value > target
    if operator == "gte":
        return value >= target
    if operator == "lt":
        return value < target
    return value <= target


def _same_unit(left, right) -> bool:
    return str(left or "").strip().casefold() == str(right or "").strip().casefold() and bool(
        str(left or "").strip()
    )


def _decimal(value):
    if value is None or str(value).strip() == "":
        return None
    try:
        return Decimal(str(value).strip().replace(",", "."))
    except (InvalidOperation, ValueError):
        return None


def single_sealed_measure_reading(
    objective_payload: dict,
    measure_items: list[tuple[str, dict]],
) -> dict | None:
    """Outcome when exactly one sealed reporting measure matches the indicator.

    ``None`` means the count is not one. This does not read a live revision.
    """
    if objective_payload.get("decision") not in _ACCEPTED_DECISIONS:
        return None
    indicator = str(objective_payload.get("indicator") or "").strip().casefold()
    if not indicator:
        return None
    matched = [
        (item_id, payload)
        for item_id, payload in measure_items
        if str(payload.get("label") or "").strip().casefold() == indicator
    ]
    if len(matched) != 1:
        return None
    item_id, measure = matched[0]
    stored = {
        "item_id": item_id,
        "value": measure.get("value"),
        "unit": measure.get("unit"),
    }
    condition = str(objective_payload.get("success_condition") or "")
    if condition == "qualitative":
        return {
            "outcome": OUTCOME_QUALITATIVE,
            "reason": "qualitative_appreciation",
            "measure": None,
        }
    if condition not in _NUMERIC_CONDITIONS:
        return {
            "outcome": OUTCOME_NON_EVALUABLE,
            "reason": "condition_missing",
            "measure": None,
        }
    if measure.get("ambiguities"):
        reason = "ambiguous_measure"
    elif not _same_unit(objective_payload.get("unit"), measure.get("unit")):
        reason = "unit_mismatch"
    elif _decimal(objective_payload.get("target")) is None:
        reason = "target_not_numeric"
    elif _decimal(measure.get("value")) is None:
        reason = "comparison_not_verifiable"
    else:
        reached = _satisfies(
            condition,
            _decimal(objective_payload.get("target")),
            _decimal(measure.get("value")),
        )
        return {
            "outcome": OUTCOME_REACHED if reached else OUTCOME_NOT_REACHED,
            "reason": "numeric_comparison",
            "measure": stored,
        }
    return {
        "outcome": OUTCOME_NON_EVALUABLE,
        "reason": reason,
        "measure": stored,
    }


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
