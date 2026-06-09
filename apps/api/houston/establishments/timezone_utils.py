from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from django.utils import timezone

from houston.establishments.models import DEFAULT_ESTABLISHMENT_TIMEZONE, Establishment


def establishment_timezone(establishment: Establishment) -> ZoneInfo:
    timezone_name = establishment.timezone or DEFAULT_ESTABLISHMENT_TIMEZONE
    return ZoneInfo(timezone_name)


def establishment_local_date(
    *,
    establishment: Establishment,
    at: datetime | None = None,
) -> date:
    moment = at or timezone.now()
    return moment.astimezone(establishment_timezone(establishment)).date()
