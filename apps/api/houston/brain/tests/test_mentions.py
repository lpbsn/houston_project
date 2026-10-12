from __future__ import annotations

from datetime import date

from houston.brain.mentions import first_period_mention

_START = date(2026, 3, 1)
_END = date(2026, 4, 1)


def test_iso_numeric_and_nominative_dates_in_the_period_are_mentions():
    iso = first_period_mention(
        title="Incident",
        structured_summary="Vu le 2026-03-15 au matin.",
        period_start=_START,
        period_end=_END,
    )
    numeric = first_period_mention(
        title="15/03/2026",
        structured_summary="",
        period_start=_START,
        period_end=_END,
    )
    named = first_period_mention(
        title="",
        structured_summary="Constaté le 15 mars 2026.",
        period_start=_START,
        period_end=_END,
    )
    folded = first_period_mention(
        title="",
        structured_summary="Constaté le 15 fevrier 2026, puis le 2 mars 2026.",
        period_start=_START,
        period_end=_END,
    )
    assert iso is not None and iso.civil_date == date(2026, 3, 15)
    assert iso.field == "structured_summary"
    assert iso.provenance()["uncertainty"] == "text_mention"
    assert numeric is not None and numeric.field == "title"
    assert named is not None and named.civil_date == date(2026, 3, 15)
    assert folded is not None and folded.civil_date == date(2026, 3, 2)


def test_dates_outside_the_period_or_invalid_dates_are_not_period_mentions():
    outside = first_period_mention(
        title="Clos le 02/01/2026",
        structured_summary="Rien d'autre.",
        period_start=_START,
        period_end=_END,
    )
    invalid = first_period_mention(
        title="31/02/2026",
        structured_summary="2026-02-31",
        period_start=_START,
        period_end=_END,
    )
    boundary = first_period_mention(
        title="2026-04-01",
        structured_summary="",
        period_start=_START,
        period_end=_END,
    )
    assert outside is None
    assert invalid is None
    assert boundary is None
