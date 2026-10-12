"""Group consecutive extracted sections, and subdivide only a section that does not fit one call."""

from __future__ import annotations

from dataclasses import dataclass

from houston.brain.configuration import digest, estimate_tokens
from houston.brain.errors import BrainWorkError


@dataclass(frozen=True)
class PlannedLot:
    stable_key: str
    payload: dict
    input_hash: str
    reserved_input_tokens: int


def plan_lots(
    sections: list[dict],
    *,
    per_call_input_tokens: int,
    total_input_tokens: int,
    max_calls: int,
    knowledge: dict | None = None,
) -> list[PlannedLot]:
    if per_call_input_tokens <= 0 or total_input_tokens <= 0 or max_calls <= 0:
        raise BrainWorkError(
            code="configuration_unusable",
            message="La configuration figée de l'analyse est inutilisable.",
        )
    if not sections:
        raise BrainWorkError(
            code="empty_document",
            message="Le fichier ne contient pas de contenu analysable.",
        )
    numbered = []
    for index, section in enumerate(sections):
        item = dict(section)
        item.setdefault("piece_id", f"s{index:04d}")
        numbered.append(item)
    sections = numbered
    groups: list[list[dict]] = []
    current: list[dict] = []
    for section in sections:
        piece = _section_payload(section)
        if _fits(current, piece, per_call_input_tokens, knowledge):
            current.append(piece)
            continue
        if _fits([], piece, per_call_input_tokens, knowledge):
            if current:
                groups.append(current)
            current = [piece]
            continue
        if current:
            groups.append(current)
            current = []
        for part in _subdivide(section, per_call_input_tokens, knowledge):
            if _fits(current, part, per_call_input_tokens, knowledge):
                current.append(part)
                continue
            if current:
                groups.append(current)
            if not _fits([], part, per_call_input_tokens, knowledge):
                raise _unsplittable()
            current = [part]
    if current:
        groups.append(current)
    planned = [
        _lot(index, parts, knowledge) for index, parts in enumerate(groups, start=1)
    ]
    reserved = sum(lot.reserved_input_tokens for lot in planned)
    if len(planned) > max_calls or reserved > total_input_tokens:
        raise BrainWorkError(
            code="budget_exceeded",
            message="La réservation des lots dépasse le budget de l'analyse.",
        )
    return planned


def sections_from_payload(payload: dict) -> list[dict]:
    """Document order: qualitative blocks, then measure tables that share a header."""
    sections: list[dict] = []
    for block in payload.get("qualitative") or []:
        if not isinstance(block, dict):
            continue
        text = str(block.get("text") or "")
        if not text.strip():
            continue
        sections.append(
            {
                "kind": "paragraph",
                "text": text,
                "locator": block.get("locator") if isinstance(block.get("locator"), dict) else {},
            }
        )
    groups: list[dict] = []
    for measure in payload.get("measures") or []:
        if not isinstance(measure, dict):
            continue
        locator = measure.get("locator") if isinstance(measure.get("locator"), dict) else {}
        header = locator.get("header")
        unit = measure.get("unit")
        identity = (locator.get("sheet") or locator.get("page"), header, unit)
        row = {
            "text": _measure_text(measure),
            "locator": locator,
        }
        if groups and groups[-1]["identity"] == identity and header:
            groups[-1]["rows"].append(row)
            continue
        groups.append(
            {
                "identity": identity,
                "kind": "table" if header else "paragraph",
                "header": header,
                "unit": unit,
                "locator": {key: value for key, value in locator.items() if key != "header"},
                "rows": [row],
                "text": row["text"],
            }
        )
    for group in groups:
        if group["kind"] == "table" and len(group["rows"]) >= 1 and group["header"]:
            sections.append(
                {
                    "kind": "table",
                    "header": group["header"],
                    "unit": group["unit"],
                    "locator": group["locator"],
                    "rows": group["rows"],
                }
            )
        else:
            sections.append(
                {
                    "kind": "paragraph",
                    "text": group["text"],
                    "locator": group["rows"][0]["locator"],
                }
            )
    for index, section in enumerate(sections):
        section["piece_id"] = f"s{index:04d}"
    return sections


def _lot(index: int, parts: list[dict], knowledge: dict | None) -> PlannedLot:
    payload = {"sections": parts}
    hashed = _costed(parts, knowledge)
    return PlannedLot(
        stable_key=f"lot-{index:04d}",
        payload=payload,
        input_hash=digest(hashed),
        reserved_input_tokens=estimate_tokens(hashed),
    )


def _costed(parts: list[dict], knowledge: dict | None) -> dict:
    payload = {"sections": parts}
    if knowledge is not None:
        payload["knowledge"] = knowledge
    return payload


def _fits(
    current: list[dict],
    piece: dict,
    per_call_input_tokens: int,
    knowledge: dict | None,
) -> bool:
    if not current and estimate_tokens(_costed([piece], knowledge)) <= per_call_input_tokens:
        return True
    if not current:
        return False
    return estimate_tokens(_costed([*current, piece], knowledge)) <= per_call_input_tokens


def _subdivide(section: dict, per_call_input_tokens: int, knowledge: dict | None) -> list[dict]:
    kind = section.get("kind")
    if kind == "table":
        return _table_rows(section, per_call_input_tokens, knowledge)
    paragraphs = [part for part in str(section.get("text") or "").split("\n\n") if part.strip()]
    if len(paragraphs) <= 1:
        raise _unsplittable()
    parent = str(section.get("piece_id") or "piece")
    pieces = []
    for index, paragraph in enumerate(paragraphs):
        child = dict(section)
        child["piece_id"] = f"{parent}-p{index:04d}"
        piece = _paragraph_payload(paragraph, section.get("locator") or {}, child)
        if estimate_tokens(_costed([piece], knowledge)) > per_call_input_tokens:
            raise _unsplittable()
        pieces.append(piece)
    return pieces


def _table_rows(section: dict, per_call_input_tokens: int, knowledge: dict | None) -> list[dict]:
    rows = section.get("rows") or []
    if not rows:
        raise _unsplittable()
    parent = str(section.get("piece_id") or "piece")
    pieces = []
    for index, row in enumerate(rows):
        child = dict(section)
        child["piece_id"] = f"{parent}-p{index:04d}"
        piece = _table_payload(child, [row])
        if estimate_tokens(_costed([piece], knowledge)) > per_call_input_tokens:
            raise _unsplittable()
        pieces.append(piece)
    return pieces


def _section_payload(section: dict) -> dict:
    if section.get("kind") == "table":
        return _table_payload(section, section.get("rows") or [])
    return _paragraph_payload(section.get("text") or "", section.get("locator") or {}, section)


def _paragraph_payload(text: str, locator: dict, section: dict) -> dict:
    payload = {"kind": "paragraph", "text": text, "locator": locator}
    if section.get("piece_id"):
        payload["piece_id"] = section["piece_id"]
    if section.get("header"):
        payload["header"] = section["header"]
    if section.get("unit"):
        payload["unit"] = section["unit"]
    return payload


def _table_payload(section: dict, rows: list[dict]) -> dict:
    payload = {
        "kind": "table",
        "header": section.get("header"),
        "unit": section.get("unit"),
        "locator": section.get("locator") or {},
        "rows": rows,
    }
    if section.get("piece_id"):
        payload["piece_id"] = section["piece_id"]
    return payload


def _measure_text(measure: dict) -> str:
    parts = [
        measure.get("label"),
        measure.get("value"),
        measure.get("unit"),
        measure.get("raw"),
    ]
    return " ".join(str(part) for part in parts if part not in (None, ""))


def _unsplittable() -> BrainWorkError:
    return BrainWorkError(
        code="budget_exceeded",
        message="Un morceau de section dépasse le plafond d'un appel.",
    )
