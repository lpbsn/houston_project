from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

_FOLD = str.maketrans("éèêëàâäîïôöùûüç", "eeeeaaaiioouuuc")
_EXCEL_ERRORS = frozenset(
    {
        "#DIV/0!",
        "#N/A",
        "#VALUE!",
        "#REF!",
        "#NAME?",
        "#NUM!",
        "#NULL!",
        "#GETTING_DATA",
        "#SPILL!",
        "#CALC!",
        "#BUSY!",
        "#CONNECT!",
        "#BLOCKED!",
    }
)
_MONTHS = (
    "janvier",
    "fevrier",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "aout",
    "septembre",
    "octobre",
    "novembre",
    "decembre",
)
_AMBIGUITY_ORDER = (
    "decimal_separator",
    "ht_ttc",
    "euro_scale",
    "percent_points",
    "month_cumulative",
    "detail_total",
)
_UNIT_PATTERN = re.compile(
    r"(?i)(?:k€|keur|k\s*eur|€|eur|euros?|%|points?|pts?)"
)
_DEFINITION = re.compile(r"^(?P<label>.+?)\s*\((?P<definition>[^)]+)\)\s*$")
_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{2}/\d{2}/\d{4}\b")


def fold(text: str) -> str:
    return text.casefold().translate(_FOLD)


def decimal_text(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in {"", "-", "-0"}:
        return "0"
    return text


@dataclass(frozen=True)
class ParsedCell:
    kind: str
    value: Decimal | None
    unit: str | None
    ambiguities: tuple[str, ...]
    raw: str


@dataclass(frozen=True)
class LabelInfo:
    label: str
    unit: str | None
    definition: str | None
    period: str | None
    ambiguities: tuple[str, ...]


def parse_cell(raw: str | None) -> ParsedCell:
    text = "" if raw is None else str(raw).strip()
    if text == "":
        return ParsedCell("empty", None, None, (), text)
    if text.upper() in _EXCEL_ERRORS:
        return ParsedCell("error", None, None, (), text)
    if text.startswith("="):
        return ParsedCell("formula", None, None, (), text)
    body, unit, flags = _strip_unit(text)
    parsed = _parse_numeric_body(body)
    if parsed is None:
        return ParsedCell("text", None, None, (), text)
    if parsed == "ambiguous":
        return ParsedCell("uninterpretable", None, None, ("decimal_separator",), text)
    value = parsed
    kind = "zero" if value == 0 else "number"
    return ParsedCell(kind, value, unit, flags, text)


def interpret_label(header: str) -> LabelInfo:
    original = header.strip()
    definition = None
    label = original
    match = _DEFINITION.match(original)
    if match and _is_definition(match.group("definition")):
        label = match.group("label").strip()
        definition = match.group("definition").strip()
    unit, flags = _label_unit_and_flags(original)
    period = _period_text(original)
    return LabelInfo(label, unit, definition, period, flags)


def merge_ambiguities(*groups: tuple[str, ...]) -> tuple[str, ...]:
    present = {flag for group in groups for flag in group}
    return tuple(flag for flag in _AMBIGUITY_ORDER if flag in present)


def _strip_unit(text: str) -> tuple[str, str | None, tuple[str, ...]]:
    if _UNIT_PATTERN.search(text) is None:
        return text, None, ()
    unit, flags = _unit_from_fragment(text)
    body = _UNIT_PATTERN.sub(" ", text)
    body = re.sub(r"[\s/]+", " ", body).strip()
    return body, unit, flags


def _label_unit_and_flags(text: str) -> tuple[str | None, tuple[str, ...]]:
    folded = fold(text)
    flags: list[str] = []
    has_ht = bool(re.search(r"(?<![a-z])ht(?![a-z])", folded) or "hors taxe" in folded)
    has_ttc = "ttc" in folded or "toutes taxes" in folded
    if has_ht and has_ttc:
        flags.append("ht_ttc")
    unit, unit_flags = _unit_from_fragment(text)
    flags.extend(unit_flags)
    if ("mois" in folded or "mensuel" in folded) and (
        "cumul" in folded or "ytd" in folded
    ):
        flags.append("month_cumulative")
    if "detail" in folded and "total" in folded:
        flags.append("detail_total")
    return unit, merge_ambiguities(tuple(flags))


def _unit_from_fragment(context: str) -> tuple[str | None, tuple[str, ...]]:
    folded = fold(context)
    without_kilo = re.sub(r"k€|keur|k\s*eur", " ", folded)
    has_kilo = without_kilo != folded
    has_euro = bool(re.search(r"€|(?<![a-z])euros?(?![a-z])", without_kilo))
    has_percent = "%" in context or "pourcent" in folded
    has_points = bool(re.search(r"(?<![a-z])(points?|pts?)(?![a-z])", folded))
    flags: list[str] = []
    unit = None
    if has_kilo and has_euro:
        flags.append("euro_scale")
    elif has_kilo:
        unit = "kEUR"
    elif has_euro:
        unit = "EUR"
    if has_percent and has_points:
        flags.append("percent_points")
        unit = None
    elif has_percent and unit is None:
        unit = "percent"
    elif has_points and unit is None:
        unit = "points"
    return unit, merge_ambiguities(tuple(flags))


def _period_text(text: str) -> str | None:
    folded = fold(text)
    if any(month in folded for month in _MONTHS):
        return text.strip()
    if _DATE.search(text):
        return text.strip()
    if re.search(r"(?<![a-z])(mois|cumul|ytd|n-1)(?![a-z0-9])", folded):
        return text.strip()
    return None


def _is_definition(text: str) -> bool:
    residual = _UNIT_PATTERN.sub("", text)
    residual = re.sub(r"[\s/]+", "", residual)
    if not residual:
        return False
    folded = fold(text.strip())
    if folded in {"ht", "ttc", "hors taxes", "hors taxe"}:
        return False
    return " " in folded or len(folded) > 12


def _parse_numeric_body(body: str) -> Decimal | str | None:
    text = body.strip().replace("\u00a0", " ").replace("\u202f", " ")
    if not text:
        return None
    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1].strip()
    if text.startswith("+"):
        text = text[1:].strip()
    elif text.startswith("-"):
        negative = not negative
        text = text[1:].strip()
    if not text:
        return None
    if " " in text:
        spaced = _parse_spaced(text)
        if spaced is None:
            return None
        return _signed(spaced, negative)
    if "," in text and "." in text:
        mixed = _parse_mixed(text)
        if mixed is None:
            return "ambiguous"
        return _signed(mixed, negative)
    if "," in text or "." in text:
        single = _parse_single_separator(text)
        if single is None:
            return None
        if single == "ambiguous":
            return "ambiguous"
        return _signed(single, negative)
    if re.fullmatch(r"\d+", text):
        return _signed(Decimal(text), negative)
    return None


def _parse_spaced(text: str) -> Decimal | None:
    if re.fullmatch(r"\d{1,3}(?: \d{3})+(?:,\d+)?", text):
        return Decimal(text.replace(" ", "").replace(",", "."))
    if re.fullmatch(r"\d{1,3}(?: \d{3})+(?:\.\d+)?", text):
        return Decimal(text.replace(" ", ""))
    return None


def _parse_mixed(text: str) -> Decimal | None:
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+,\d+", text):
        return Decimal(text.replace(".", "").replace(",", "."))
    if re.fullmatch(r"\d{1,3}(?:,\d{3})+\.\d+", text):
        return Decimal(text.replace(",", ""))
    return None


def _parse_single_separator(text: str) -> Decimal | str | None:
    separator = "," if "," in text else "."
    decimal_match = re.fullmatch(rf"\d+{re.escape(separator)}\d+", text)
    thousands_match = re.fullmatch(rf"\d{{1,3}}(?:{re.escape(separator)}\d{{3}})+", text)
    decimal_value = Decimal(text.replace(separator, ".")) if decimal_match else None
    thousands_value = Decimal(text.replace(separator, "")) if thousands_match else None
    if (
        decimal_value is not None
        and thousands_value is not None
        and decimal_value != thousands_value
    ):
        return "ambiguous"
    if decimal_value is not None:
        return decimal_value
    if thousands_value is not None:
        return thousands_value
    return None


def _signed(value: Decimal, negative: bool) -> Decimal:
    if negative and value != 0:
        return -value
    return value
