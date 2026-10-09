from __future__ import annotations

from decimal import Decimal

from houston.brain.numbers import interpret_label, parse_cell


def test_decimal_readings_that_disagree_stay_unresolved():
    parsed = parse_cell("1.234")
    assert parsed.kind == "uninterpretable"
    assert parsed.value is None
    assert parsed.ambiguities == ("decimal_separator",)


def test_single_convention_decimals_are_exact():
    assert parse_cell("12,5").value == Decimal("12.5")
    assert parse_cell("1.234,56").value == Decimal("1234.56")
    assert parse_cell("1,234.56").value == Decimal("1234.56")
    assert parse_cell("1 200 €").value == Decimal("1200")
    assert parse_cell("1 200 €").unit == "EUR"
    assert parse_cell("0").kind == "zero"
    assert parse_cell("").kind == "empty"
    assert parse_cell("#N/A").kind == "error"
    assert parse_cell("=1+1").kind == "formula"


def test_explicit_units_are_not_flagged_as_conflicts():
    kilo = interpret_label("CA k€")
    assert kilo.unit == "kEUR"
    assert "euro_scale" not in kilo.ambiguities
    euros = interpret_label("CA €")
    assert euros.unit == "EUR"
    assert "euro_scale" not in euros.ambiguities
    both = interpret_label("Montant (€ / k€)")
    assert both.unit is None
    assert "euro_scale" in both.ambiguities
    tax = interpret_label("CA HT")
    assert "ht_ttc" not in tax.ambiguities
    mixed = interpret_label("CA HT/TTC")
    assert "ht_ttc" in mixed.ambiguities
