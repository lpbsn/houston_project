"""Explicit dates read from Signal title and structured summary.

A mention is a civil date with its place in the text. It is never a recording timestamp.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date

_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_NUMERIC = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")
_MONTH = re.compile(
    r"\b(\d{1,2})\s+([A-Za-zÀ-ÿ]{3,9})\s+(\d{4})\b",
    re.IGNORECASE,
)

_FRENCH_MONTHS = {
    "janvier": 1,
    "fevrier": 2,
    "mars": 3,
    "avril": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
    "aout": 8,
    "septembre": 9,
    "octobre": 10,
    "novembre": 11,
    "decembre": 12,
}
_ENGLISH_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


@dataclass(frozen=True)
class DateMention:
    civil_date: date
    start: int
    end: int
    field: str

    def provenance(self) -> dict:
        return {
            "field": self.field,
            "start": self.start,
            "end": self.end,
            "uncertainty": "text_mention",
        }


def _fold_month(token: str) -> str:
    decomposed = unicodedata.normalize("NFD", token.casefold())
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")


def _civil(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _collect(text: str, field: str) -> list[DateMention]:
    found: list[DateMention] = []
    for match in _ISO.finditer(text):
        parsed = _civil(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        if parsed is not None:
            found.append(DateMention(parsed, match.start(), match.end(), field))
    for match in _NUMERIC.finditer(text):
        parsed = _civil(int(match.group(3)), int(match.group(2)), int(match.group(1)))
        if parsed is not None:
            found.append(DateMention(parsed, match.start(), match.end(), field))
    for match in _MONTH.finditer(text):
        month = _FRENCH_MONTHS.get(_fold_month(match.group(2)))
        if month is None:
            month = _ENGLISH_MONTHS.get(match.group(2).casefold())
        if month is None:
            continue
        parsed = _civil(int(match.group(3)), month, int(match.group(1)))
        if parsed is not None:
            found.append(DateMention(parsed, match.start(), match.end(), field))
    found.sort(key=lambda item: (item.start, item.end))
    return found


def first_period_mention(
    *,
    title: str,
    structured_summary: str,
    period_start: date,
    period_end: date,
) -> DateMention | None:
    """First explicit date that falls in [period_start, period_end), title then summary."""
    for field, text in (("title", title or ""), ("structured_summary", structured_summary or "")):
        for mention in _collect(text, field):
            if period_start <= mention.civil_date < period_end:
                return mention
    return None
