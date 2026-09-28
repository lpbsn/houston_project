from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from houston.core.civil_time import PARIS, history_civil_window

UTC = ZoneInfo("UTC")


def _paris(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=PARIS)


def test_seven_days_include_today_and_exclude_the_day_before_the_window():
    window = history_civil_window(period="7", now=_paris(2026, 3, 29, 12))
    assert window is not None
    assert window.start == _paris(2026, 3, 23)
    assert window.end == _paris(2026, 3, 30)
    assert window.start <= _paris(2026, 3, 29, 0, 30) < window.end
    assert window.start <= _paris(2026, 3, 29, 23, 30) < window.end
    assert _paris(2026, 3, 22, 23, 30) < window.start
    assert _paris(2026, 3, 30, 0, 0) >= window.end


def test_spring_forward_midnight_stays_on_the_paris_civil_day():
    window = history_civil_window(period="7", now=_paris(2026, 3, 29, 12))
    assert window is not None
    # 00:30 Paris on the spring-forward day is still the previous UTC date.
    before_jump = datetime(2026, 3, 28, 23, 30, tzinfo=UTC)
    assert before_jump.astimezone(PARIS).date().isoformat() == "2026-03-29"
    assert window.start <= before_jump < window.end
    day_before_window = datetime(2026, 3, 22, 22, 30, tzinfo=UTC)
    assert day_before_window.astimezone(PARIS).date().isoformat() == "2026-03-22"
    assert day_before_window < window.start


def test_fall_back_overlap_stays_inside_the_paris_civil_day():
    window = history_civil_window(period="7", now=_paris(2026, 10, 25, 12))
    assert window is not None
    first = datetime(2026, 10, 25, 2, 30, tzinfo=PARIS, fold=0)
    second = datetime(2026, 10, 25, 2, 30, tzinfo=PARIS, fold=1)
    assert window.start <= first < window.end
    assert window.start <= second < window.end
    assert _paris(2026, 10, 26) >= window.end


def test_custom_period_is_half_open_on_paris_midnights():
    window = history_civil_window(
        period="custom",
        now=_paris(2026, 1, 1),
        custom_from=_paris(2026, 3, 28).date(),
        custom_to=_paris(2026, 3, 29).date(),
    )
    assert window is not None
    assert window.start == _paris(2026, 3, 28)
    assert window.end == _paris(2026, 3, 30)
    assert _paris(2026, 3, 29, 23, 30) < window.end


def test_all_period_is_unbounded():
    assert history_civil_window(period="all", now=_paris(2026, 6, 1)) is None


def test_custom_period_rejects_an_inverted_range():
    with pytest.raises(ValueError):
        history_civil_window(
            period="custom",
            now=_paris(2026, 6, 1),
            custom_from=_paris(2026, 6, 2).date(),
            custom_to=_paris(2026, 6, 1).date(),
        )
