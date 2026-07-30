from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from houston.testing.factories import create_establishment, create_membership


@pytest.fixture
def paris_establishment(db):
    return create_establishment(name="Paris Hotel", timezone="Europe/Paris")


@pytest.fixture
def paris_membership(paris_establishment):
    return create_membership(establishment=paris_establishment)


@pytest.fixture
def utc_establishment(db):
    return create_establishment(name="UTC Hotel", timezone="UTC")


@pytest.fixture
def utc_membership(utc_establishment):
    return create_membership(establishment=utc_establishment)


def aware_local(
    tz_name: str,
    year: int,
    month: int,
    day: int,
    hour: int = 0,
    minute: int = 0,
) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=ZoneInfo(tz_name))
