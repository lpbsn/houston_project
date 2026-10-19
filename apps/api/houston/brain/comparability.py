"""KPI comparability for the investigation engine.

A comparison is accepted only when its kind and its conditions are explicit.
Nothing is normalized. A missing component is a gap, not a breakdown.
The published figure is recomposed from its operands.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from houston.brain.numbers import decimal_text, fold

COMPARISON_TEMPORAL = "temporal"
COMPARISON_ACTUAL_VS_REFERENCE = "actual_vs_reference"

NATURE_ACTUAL = "actual"
NATURE_BUDGET = "budget"
NATURE_FORECAST = "forecast"
_NATURES = frozenset({NATURE_ACTUAL, NATURE_BUDGET, NATURE_FORECAST})
_REFERENCE_NATURES = frozenset({NATURE_BUDGET, NATURE_FORECAST})

TAX_HT = "ht"
TAX_TTC = "ttc"
TAX_UNSPECIFIED = "unspecified"
_TAX_TREATMENTS = frozenset({TAX_HT, TAX_TTC, TAX_UNSPECIFIED})

_RATE_UNITS = frozenset({"%", "percent", "point", "points", "pt", "pts"})


@dataclass(frozen=True)
class KpiMeasure:
    """One measure whose comparison conditions are already explicit.

    ``period_end`` is exclusive, as on a confirmed reporting.
    ``duration_days`` and ``opening_days`` are written bases. They are never derived
    to rescale a value. Absent opening days stay absent.
    """

    value: Decimal
    unit: str
    definition: str
    scope: str
    nature: str
    tax_treatment: str
    period_start: date
    period_end: date
    duration_days: int | None = None
    opening_days: int | None = None
    ambiguities: tuple[str, ...] = ()
    method: str | None = None


@dataclass(frozen=True)
class ComparisonVerdict:
    accepted: bool
    code: str
    reserve: str | None = None
    duration_bases: tuple[int, int] | None = None
    opening_days: tuple[int | None, int | None] = (None, None)


@dataclass(frozen=True)
class ArithmeticVerdict:
    accepted: bool
    code: str
    value: Decimal | None
    unit: str | None = None
    reserve: str | None = None
    duration_bases: tuple[int, int] | None = None


@dataclass(frozen=True)
class IdentityVerdict:
    accepted: bool
    code: str
    value: Decimal | None


@dataclass(frozen=True)
class VariationBreakdown:
    accepted: bool
    code: str
    volume_effect: Decimal | None = None
    price_effect: Decimal | None = None
    amount_difference: Decimal | None = None


def compare_measures(left: KpiMeasure, right: KpiMeasure, kind: str) -> ComparisonVerdict:
    """Accept a temporal evolution or an actual-versus-reference comparison."""
    opening = (left.opening_days, right.opening_days)
    if kind not in {COMPARISON_TEMPORAL, COMPARISON_ACTUAL_VS_REFERENCE}:
        return _refused("comparison_kind_invalid", opening)
    code = _shared_code(left, right)
    if code:
        return _refused(code, opening)
    if kind == COMPARISON_TEMPORAL:
        code = _temporal_code(left, right)
    else:
        code = _reference_code(left, right)
    if code:
        return _refused(code, opening)
    duration_code, bases = _duration_status(left, right)
    if duration_code in {"duration_base_missing", "duration_base_conflict"}:
        return _refused(duration_code, opening)
    return ComparisonVerdict(
        True,
        "accepted",
        reserve=duration_code,
        duration_bases=bases,
        opening_days=opening,
    )


def measured_difference(
    left: KpiMeasure,
    right: KpiMeasure,
    *,
    kind: str,
) -> ArithmeticVerdict:
    """Subtract two comparable measures. The result keeps their unit and is not rescaled."""
    verdict = compare_measures(left, right, kind)
    if not verdict.accepted:
        return _arithmetic(verdict.code)
    return ArithmeticVerdict(
        True,
        "accepted",
        left.value - right.value,
        unit=str(left.unit).strip(),
        reserve=verdict.reserve,
        duration_bases=verdict.duration_bases,
    )


def measured_variation(base: KpiMeasure, current: KpiMeasure) -> ArithmeticVerdict:
    """Relative change of two temporal measures. A rate is not varied like an amount."""
    verdict = compare_measures(base, current, COMPARISON_TEMPORAL)
    if not verdict.accepted:
        return _arithmetic(verdict.code)
    if _is_rate(base.unit) or _is_rate(current.unit):
        return _arithmetic("rate_variation")
    if base.value == 0:
        return _arithmetic("invalid_calculation")
    change = (current.value - base.value) / base.value
    return ArithmeticVerdict(
        True,
        "accepted",
        change,
        reserve=verdict.reserve,
        duration_bases=verdict.duration_bases,
    )


def sum_values(
    values: tuple[Decimal | None, ...],
    units: tuple[str | None, ...],
) -> ArithmeticVerdict:
    """Sum amounts of one unit. A missing term or a rate produces no partial total."""
    if len(values) < 2 or len(values) != len(units):
        return _arithmetic("invalid_calculation")
    present: list[Decimal] = []
    for value in values:
        if value is None:
            return _arithmetic("component_missing")
        present.append(value)
    folded = [_unit_key(unit) for unit in units]
    if any(not unit for unit in folded):
        return _arithmetic("unit_missing")
    if any(_is_rate(unit) for unit in folded):
        return _arithmetic("rate_not_summable")
    if len(set(folded)) != 1:
        return _arithmetic("unit_mismatch")
    return ArithmeticVerdict(
        True,
        "accepted",
        sum(present, Decimal(0)),
        unit=str(units[0]).strip(),
    )


def recompose_amount(
    *,
    volume: Decimal | None,
    unit_price: Decimal | None,
    published: Decimal | None,
) -> IdentityVerdict:
    """Accept ``amount = volume × unit price`` only when the product matches."""
    if volume is None or unit_price is None or published is None:
        return IdentityVerdict(False, "component_missing", None)
    product = volume * unit_price
    if decimal_text(product) != decimal_text(published):
        return IdentityVerdict(False, "not_recomputed", None)
    return IdentityVerdict(True, "accepted", product)


def recompose_unit_price(
    *,
    amount: Decimal | None,
    volume: Decimal | None,
) -> IdentityVerdict:
    """Recover a unit price from the two operands that exist."""
    if amount is None or volume is None:
        return IdentityVerdict(False, "component_missing", None)
    if volume == 0:
        return IdentityVerdict(False, "invalid_calculation", None)
    return IdentityVerdict(True, "accepted", amount / volume)


def recompose_volume(
    *,
    amount: Decimal | None,
    unit_price: Decimal | None,
) -> IdentityVerdict:
    """Recover a volume from the two operands that exist."""
    if amount is None or unit_price is None:
        return IdentityVerdict(False, "component_missing", None)
    if unit_price == 0:
        return IdentityVerdict(False, "invalid_calculation", None)
    return IdentityVerdict(True, "accepted", amount / unit_price)


def decompose_variation(
    *,
    volume_before: Decimal | None,
    volume_after: Decimal | None,
    price_before: Decimal | None,
    price_after: Decimal | None,
    amount_before: Decimal | None,
    amount_after: Decimal | None,
) -> VariationBreakdown:
    """Split a variation into volume and price effects when every operand exists.

    A missing component returns no effect. The effects are published only when each
    period's amount identity holds and the two effects recompose the amount change.
    """
    components = (
        volume_before,
        volume_after,
        price_before,
        price_after,
        amount_before,
        amount_after,
    )
    if any(component is None for component in components):
        return VariationBreakdown(False, "component_missing")
    assert volume_before is not None
    assert volume_after is not None
    assert price_before is not None
    assert price_after is not None
    assert amount_before is not None
    assert amount_after is not None
    if decimal_text(volume_before * price_before) != decimal_text(amount_before):
        return VariationBreakdown(False, "not_recomputed")
    if decimal_text(volume_after * price_after) != decimal_text(amount_after):
        return VariationBreakdown(False, "not_recomputed")
    volume_effect = (volume_after - volume_before) * price_before
    price_effect = volume_after * (price_after - price_before)
    amount_difference = amount_after - amount_before
    if decimal_text(volume_effect + price_effect) != decimal_text(amount_difference):
        return VariationBreakdown(False, "not_recomputed")
    return VariationBreakdown(
        True,
        "accepted",
        volume_effect=volume_effect,
        price_effect=price_effect,
        amount_difference=amount_difference,
    )


def _shared_code(left: KpiMeasure, right: KpiMeasure) -> str | None:
    if _span_days(left) is None or _span_days(right) is None:
        return "period_invalid"
    if left.ambiguities or right.ambiguities:
        return "ambiguous"
    if left.nature not in _NATURES or right.nature not in _NATURES:
        return "nature_invalid"
    if left.tax_treatment not in _TAX_TREATMENTS or right.tax_treatment not in _TAX_TREATMENTS:
        return "tax_invalid"
    if left.tax_treatment != right.tax_treatment:
        return "tax_mismatch"
    left_unit = _unit_key(left.unit)
    right_unit = _unit_key(right.unit)
    if not left_unit or not right_unit:
        return "unit_missing"
    if left_unit != right_unit:
        return "unit_mismatch"
    if not _text(left.definition) or not _text(right.definition):
        return "definition_missing"
    if _text(left.definition) != _text(right.definition):
        return "definition_mismatch"
    if not _text(left.scope) or not _text(right.scope):
        return "scope_missing"
    if _text(left.scope) != _text(right.scope):
        return "scope_mismatch"
    if _text(left.method) != _text(right.method):
        return "method_changed"
    return None


def _temporal_code(left: KpiMeasure, right: KpiMeasure) -> str | None:
    if left.nature != right.nature:
        return "nature_mixed"
    if (left.period_start, left.period_end) == (right.period_start, right.period_end):
        return "period_not_distinct"
    return None


def _reference_code(left: KpiMeasure, right: KpiMeasure) -> str | None:
    natures = {left.nature, right.nature}
    if NATURE_ACTUAL not in natures or not natures <= {NATURE_ACTUAL, *_REFERENCE_NATURES}:
        return "nature_not_reference"
    if len(natures) != 2:
        return "nature_not_reference"
    if (left.period_start, left.period_end) != (right.period_start, right.period_end):
        return "period_mismatch"
    return None


def _duration_status(
    left: KpiMeasure,
    right: KpiMeasure,
) -> tuple[str | None, tuple[int, int] | None]:
    left_span = _span_days(left)
    right_span = _span_days(right)
    if left_span is None or right_span is None:
        return "period_invalid", None
    if _base_conflicts(left, left_span) or _base_conflicts(right, right_span):
        return "duration_base_conflict", None
    if left_span == right_span:
        return None, None
    if left.duration_days is None or right.duration_days is None:
        return "duration_base_missing", None
    return "unequal_duration_bases", (left.duration_days, right.duration_days)


def _base_conflicts(measure: KpiMeasure, span: int) -> bool:
    if measure.duration_days is None:
        return False
    return measure.duration_days != span


def _span_days(measure: KpiMeasure) -> int | None:
    span = (measure.period_end - measure.period_start).days
    if span <= 0:
        return None
    return span


def _text(value: str | None) -> str:
    return fold(str(value or "")).strip()


def _unit_key(unit: str | None) -> str:
    return _text(unit)


def _is_rate(unit: str | None) -> bool:
    return _unit_key(unit) in _RATE_UNITS


def _refused(
    code: str,
    opening: tuple[int | None, int | None],
) -> ComparisonVerdict:
    return ComparisonVerdict(False, code, opening_days=opening)


def _arithmetic(code: str) -> ArithmeticVerdict:
    return ArithmeticVerdict(False, code, None)
