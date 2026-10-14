"""Assign every captured source once, and pack those groups under one call ceiling.

A section that does not fit is subdivided. A single element that still does not fit refuses
the analysis. Nothing is truncated.
"""

from __future__ import annotations

from dataclasses import dataclass

from houston.brain.collection import (
    CATEGORY_DOCUMENT,
    CATEGORY_EXECUTION,
    CATEGORY_PLAN,
    CATEGORY_SIGNAL,
    CATEGORY_TASK,
    document_stable_key,
)
from houston.brain.configuration import canonical_json, digest, estimate_tokens, useful_input_tokens
from houston.brain.contract import ENGINE_RULES, SCHEMA_VERSION
from houston.brain.errors import BrainWorkError

_ROW_FIELDS = ("value_kind", "period", "scope", "definition", "ambiguities")
_LINKED = {CATEGORY_SIGNAL, CATEGORY_EXECUTION, CATEGORY_TASK, CATEGORY_PLAN}


@dataclass(frozen=True)
class PlannedLot:
    stable_key: str
    payload: dict
    input_hash: str
    reserved_input_tokens: int


@dataclass(frozen=True)
class _PieceCost:
    """UTF-8 length of the three variable JSON arrays in one reading envelope."""

    sections_bytes: int
    section_count: int
    items_bytes: int
    item_count: int
    piece_bytes: int
    piece_count: int

    def concat(self, other: _PieceCost) -> _PieceCost:
        return _PieceCost(
            sections_bytes=_concat_array_bytes(
                self.sections_bytes,
                self.section_count,
                other.sections_bytes,
                other.section_count,
            ),
            section_count=self.section_count + other.section_count,
            items_bytes=_concat_array_bytes(
                self.items_bytes,
                self.item_count,
                other.items_bytes,
                other.item_count,
            ),
            item_count=self.item_count + other.item_count,
            piece_bytes=_concat_array_bytes(
                self.piece_bytes,
                self.piece_count,
                other.piece_bytes,
                other.piece_count,
            ),
            piece_count=self.piece_count + other.piece_count,
        )


_EMPTY_COST = _PieceCost(2, 0, 2, 0, 2, 0)
_ENVELOPE_KEYS = (
    "items",
    "knowledge",
    "required_piece_ids",
    "role",
    "rules",
    "schema_version",
    "searches",
    "sections",
)


def _canonical_bytes(value: object) -> int:
    return len(canonical_json(value).encode("utf-8"))


def _array_bytes(element_bytes: list[int]) -> int:
    """Byte length of a canonical JSON array. An empty array is `[]`."""
    count = len(element_bytes)
    if count == 0:
        return 2
    return 2 + sum(element_bytes) + count - 1


def _concat_array_bytes(left: int, left_count: int, right: int, right_count: int) -> int:
    """Length of a JSON array formed by appending two canonical arrays.

    Both sides are `[]` (2 bytes) when empty. Joining two non-empty arrays drops one
    bracket pair and adds the comma between them, which is one byte less than the sum.
    """
    if left_count == 0:
        return right
    if right_count == 0:
        return left
    return left + right - 1


class _ReadingMeter:
    """Token count of a reading envelope, identical to estimate_tokens(reading_envelope(...)).

    Stable objects are serialized once. Section and item objects are serialized once.
    Merging groups adds those byte lengths and the JSON commas; it does not dump again.
    """

    def __init__(self, knowledge: dict | None, searches: list[str]):
        self._knowledge_bytes = None if knowledge is None else _canonical_bytes(knowledge)
        self._searches_bytes = _canonical_bytes(list(searches))
        self._rules_bytes = _canonical_bytes(list(ENGINE_RULES))
        self._role_bytes = _canonical_bytes("analysis")
        self._schema_bytes = _canonical_bytes(SCHEMA_VERSION)
        self._key_bytes = {key: _canonical_bytes(key) for key in _ENVELOPE_KEYS}
        self._objects: dict[int, int] = {}

    def section_group(self, section: dict) -> _Group:
        piece_ids = [str(section["piece_id"])] if section.get("piece_id") else []
        return _Group(
            [section],
            [],
            _PieceCost(
                sections_bytes=_array_bytes([self._object_bytes(section)]),
                section_count=1,
                items_bytes=2,
                item_count=0,
                piece_bytes=_array_bytes([_canonical_bytes(piece_id) for piece_id in piece_ids]),
                piece_count=len(piece_ids),
            ),
        )

    def item_group(self, items: list[dict]) -> _Group:
        return _Group(
            [],
            list(items),
            _PieceCost(
                sections_bytes=2,
                section_count=0,
                items_bytes=_array_bytes([self._object_bytes(item) for item in items]),
                item_count=len(items),
                piece_bytes=2,
                piece_count=0,
            ),
        )

    def payload_bytes(self, cost: _PieceCost) -> int:
        values = {
            "required_piece_ids": cost.piece_bytes,
            "role": self._role_bytes,
            "rules": self._rules_bytes,
            "schema_version": self._schema_bytes,
            "searches": self._searches_bytes,
            "sections": cost.sections_bytes,
        }
        if cost.item_count:
            values["items"] = cost.items_bytes
        if self._knowledge_bytes is not None:
            values["knowledge"] = self._knowledge_bytes
        total = 2
        for index, key in enumerate(sorted(values)):
            if index:
                total += 1
            total += self._key_bytes[key] + 1 + values[key]
        return total

    def tokens(self, cost: _PieceCost) -> int:
        return max(1, (self.payload_bytes(cost) + 3) // 4)

    def _object_bytes(self, value: dict) -> int:
        key = id(value)
        cached = self._objects.get(key)
        if cached is None:
            cached = _canonical_bytes(value)
            self._objects[key] = cached
        return cached


@dataclass
class _Group:
    sections: list[dict]
    items: list[dict]
    cost: _PieceCost


def _empty_group() -> _Group:
    return _Group([], [], _EMPTY_COST)


def plan_lots(
    sections: list[dict],
    *,
    per_call_input_tokens: int,
    total_input_tokens: int,
    max_calls: int,
    knowledge: dict | None = None,
    searches: list[str] | None = None,
    items=None,
) -> list[PlannedLot]:
    if per_call_input_tokens <= 0 or total_input_tokens <= 0 or max_calls <= 0:
        raise BrainWorkError(
            code="configuration_unusable",
            message="La configuration figée de l'analyse est inutilisable.",
        )
    useful = useful_input_tokens(per_call_input_tokens)
    if useful <= 0:
        raise BrainWorkError(
            code="budget_exceeded",
            message="La réservation des lots dépasse le budget de l'analyse.",
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
    if items is not None:
        _bind_document_items(numbered, items)
    codes = list(searches or [])
    meter = _ReadingMeter(knowledge, codes)
    groups: list[_Group] = []
    for section in numbered:
        groups.extend(_section_groups(section, useful, meter))
    if items is not None:
        groups.extend(_item_groups(items, useful, meter))
    packed = _pack(groups, useful, meter)
    planned = [
        _lot(index, group, knowledge, codes) for index, group in enumerate(packed, start=1)
    ]
    _require_unique_pieces(planned)
    if items is not None:
        _require_complete(planned, items)
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
    for index, block in enumerate(payload.get("qualitative") or []):
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
                "item_ids": [document_stable_key("qualitative", index)],
            }
        )
    groups: list[dict] = []
    measure_index = 0
    for measure in payload.get("measures") or []:
        if not isinstance(measure, dict):
            continue
        item_key = document_stable_key("measure", measure_index)
        measure_index += 1
        locator = measure.get("locator") if isinstance(measure.get("locator"), dict) else {}
        header = locator.get("header")
        unit = measure.get("unit")
        identity = (locator.get("sheet") or locator.get("page"), header, unit)
        row = _measure_row(measure, item_key, locator)
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
        item_ids = [str(row["stable_key"]) for row in group["rows"]]
        if group["kind"] == "table" and group["header"]:
            sections.append(
                {
                    "kind": "table",
                    "header": group["header"],
                    "unit": group["unit"],
                    "locator": group["locator"],
                    "rows": group["rows"],
                    "item_ids": item_ids,
                }
            )
            continue
        row = group["rows"][0]
        paragraph = {
            "kind": "paragraph",
            "text": row["text"],
            "locator": row["locator"],
            "item_ids": item_ids,
            "item_id": row["item_id"],
            "stable_key": row["stable_key"],
        }
        for key in _ROW_FIELDS:
            if key in row:
                paragraph[key] = row[key]
        sections.append(paragraph)
    for index, section in enumerate(sections):
        section["piece_id"] = f"s{index:04d}"
    return sections


def reading_envelope(
    sections: list[dict],
    knowledge: dict | None,
    *,
    searches: list[str] | None = None,
    items: list[dict] | None = None,
) -> dict:
    """The object a reading call estimates, hashes, and sends.

    Rules, Knowledge, and search codes are inside this object. The public catalogue is not.
    """
    pieces = [str(section["piece_id"]) for section in sections if section.get("piece_id")]
    payload = {
        "role": "analysis",
        "schema_version": SCHEMA_VERSION,
        "rules": list(ENGINE_RULES),
        "required_piece_ids": pieces,
        "sections": sections,
        "searches": list(searches or []),
    }
    if items:
        payload["items"] = items
    if knowledge is not None:
        payload["knowledge"] = knowledge
    return payload


def _lot(index: int, group: _Group, knowledge: dict | None, searches: list[str]) -> PlannedLot:
    envelope = reading_envelope(
        group.sections,
        knowledge,
        searches=searches,
        items=group.items,
    )
    return PlannedLot(
        stable_key=f"lot-{index:04d}",
        payload=envelope,
        input_hash=digest(envelope),
        reserved_input_tokens=estimate_tokens(envelope),
    )


def _section_groups(section: dict, budget: int, meter: _ReadingMeter) -> list[_Group]:
    piece = _section_payload(section)
    whole = meter.section_group(piece)
    if _fits(_empty_group(), whole, budget, meter):
        return [whole]
    return [meter.section_group(part) for part in _subdivide(section, budget, meter)]


def _fits(current: _Group, incoming: _Group, budget: int, meter: _ReadingMeter) -> bool:
    merged = _merge(current, incoming)
    if not merged.sections and not merged.items:
        return True
    return meter.tokens(merged.cost) <= budget


def _merge(current: _Group, incoming: _Group) -> _Group:
    return _Group(
        sections=[*current.sections, *incoming.sections],
        items=[*current.items, *incoming.items],
        cost=current.cost.concat(incoming.cost),
    )


def _pack(groups: list[_Group], budget: int, meter: _ReadingMeter) -> list[_Group]:
    packed: list[_Group] = []
    current = _empty_group()
    for group in groups:
        if current.sections or current.items:
            if _fits(current, group, budget, meter):
                current = _merge(current, group)
                continue
            packed.append(current)
            current = _empty_group()
        if not _fits(current, group, budget, meter):
            raise _unsplittable()
        current = group
    if current.sections or current.items:
        packed.append(current)
    return packed


def _subdivide(section: dict, budget: int, meter: _ReadingMeter) -> list[dict]:
    if section.get("kind") == "table":
        return _table_rows(section, budget, meter)
    paragraphs = [part for part in str(section.get("text") or "").split("\n\n") if part.strip()]
    if len(paragraphs) <= 1:
        raise _unsplittable()
    parent = str(section.get("piece_id") or "piece")
    pieces = []
    for index, paragraph in enumerate(paragraphs):
        child = _paragraph_from_parent(section, paragraph, keep_item=index == 0)
        child["piece_id"] = f"{parent}-p{index:04d}"
        if not _fits(_empty_group(), meter.section_group(child), budget, meter):
            raise _unsplittable()
        pieces.append(child)
    return pieces


def _table_rows(section: dict, budget: int, meter: _ReadingMeter) -> list[dict]:
    rows = section.get("rows") or []
    if not rows:
        raise _unsplittable()
    parent = str(section.get("piece_id") or "piece")
    pieces = []
    for index, row in enumerate(rows):
        child = dict(section)
        child["piece_id"] = f"{parent}-p{index:04d}"
        child["rows"] = [row]
        child["item_ids"] = [str(row.get("stable_key") or row.get("item_id"))]
        piece = _table_payload(child, [row])
        if not _fits(_empty_group(), meter.section_group(piece), budget, meter):
            raise _unsplittable()
        pieces.append(piece)
    return pieces


def _paragraph_from_parent(section: dict, text: str, *, keep_item: bool) -> dict:
    payload = {
        "kind": "paragraph",
        "text": text,
        "locator": section.get("locator") or {},
        "item_ids": list(section.get("item_ids") or []) if keep_item else [],
    }
    if section.get("piece_id"):
        payload["piece_id"] = section["piece_id"]
    if keep_item and section.get("item_id"):
        payload["item_id"] = section["item_id"]
    if keep_item and section.get("stable_key"):
        payload["stable_key"] = section["stable_key"]
    if keep_item:
        for key in _ROW_FIELDS:
            if key in section:
                payload[key] = section[key]
    if section.get("header"):
        payload["header"] = section["header"]
    if section.get("unit"):
        payload["unit"] = section["unit"]
    return payload


def _section_payload(section: dict) -> dict:
    if section.get("kind") == "table":
        return _table_payload(section, section.get("rows") or [])
    return _paragraph_from_parent(section, section.get("text") or "", keep_item=True)


def _table_payload(section: dict, rows: list[dict]) -> dict:
    payload = {
        "kind": "table",
        "header": section.get("header"),
        "unit": section.get("unit"),
        "locator": section.get("locator") or {},
        "rows": rows,
    }
    item_ids = [
        str(row.get("stable_key") or row.get("item_id"))
        for row in rows
        if row.get("stable_key") or row.get("item_id")
    ]
    if item_ids:
        payload["item_ids"] = item_ids
    if section.get("piece_id"):
        payload["piece_id"] = section["piece_id"]
    return payload


def _measure_row(measure: dict, item_key: str, locator: dict) -> dict:
    row = {
        "text": _measure_text(measure),
        "locator": locator,
        "item_id": item_key,
        "stable_key": item_key,
    }
    for key in _ROW_FIELDS:
        if key not in measure or measure[key] is None:
            continue
        row[key] = measure[key]
    return row


def _measure_text(measure: dict) -> str:
    parts = [
        measure.get("label"),
        measure.get("value"),
        measure.get("unit"),
        measure.get("raw"),
    ]
    return " ".join(str(part) for part in parts if part not in (None, ""))


def _bind_document_items(sections: list[dict], items) -> None:
    by_key = {
        item.stable_key: item
        for item in items
        if getattr(item, "category", None) == CATEGORY_DOCUMENT
    }
    for section in sections:
        rows = section.get("rows") or []
        if rows:
            for row in rows:
                key = str(row.get("stable_key") or row.get("item_id") or "")
                item = by_key.get(key)
                if item is None:
                    continue
                row["stable_key"] = item.stable_key
                row["item_id"] = str(item.id)
            continue
        keys = [str(key) for key in section.get("item_ids") or []]
        if len(keys) == 1 and keys[0] in by_key:
            section["item_id"] = str(by_key[keys[0]].id)


def _item_groups(items, budget: int, meter: _ReadingMeter) -> list[_Group]:
    groups = []
    for cluster in _clusters(items):
        whole = meter.item_group(cluster)
        if _fits(_empty_group(), whole, budget, meter):
            groups.append(whole)
            continue
        for bundle in _split_cluster(cluster):
            group = meter.item_group(bundle)
            if not _fits(_empty_group(), group, budget, meter):
                raise _unsplittable()
            groups.append(group)
    return groups


def _clusters(items) -> list[list[dict]]:
    pending = [_item_view(item) for item in items if item.category != CATEGORY_DOCUMENT]
    by_key = {item["stable_key"]: item for item in pending}
    taken: set[str] = set()

    def take(view: dict | None) -> dict | None:
        if view is None or view["stable_key"] in taken:
            return None
        taken.add(view["stable_key"])
        return view

    signals = sorted(
        (item for item in pending if item["category"] == CATEGORY_SIGNAL),
        key=lambda item: item["stable_key"],
    )
    executions = [item for item in pending if item["category"] == CATEGORY_EXECUTION]
    tasks = [item for item in pending if item["category"] == CATEGORY_TASK]
    plans = [item for item in pending if item["category"] == CATEGORY_PLAN]
    clusters: list[list[dict]] = []
    for signal in signals:
        members = [taken_item for taken_item in (take(signal),) if taken_item]
        source = _payload_text(signal, "source_id")
        related = sorted(
            (
                item
                for item in executions
                if _payload_text(item, "source_signal_id") == source and source
            ),
            key=lambda item: item["stable_key"],
        )
        execution_ids = set()
        for execution in related:
            chosen = take(execution)
            if chosen is None:
                continue
            members.append(chosen)
            execution_id = _payload_text(execution, "source_id")
            if execution_id:
                execution_ids.add(execution_id)
            for task in sorted(
                (item for item in tasks if _payload_text(item, "execution_id") == execution_id),
                key=lambda item: item["stable_key"],
            ):
                chosen_task = take(task)
                if chosen_task is not None:
                    members.append(chosen_task)
        for plan in sorted(plans, key=lambda item: item["stable_key"]):
            if not _plan_links(plan, source, execution_ids):
                continue
            chosen_plan = take(plan)
            if chosen_plan is not None:
                members.append(chosen_plan)
        if members:
            clusters.append(members)
    for execution in sorted(executions, key=lambda item: item["stable_key"]):
        chosen = take(execution)
        if chosen is None:
            continue
        members = [chosen]
        execution_id = _payload_text(execution, "source_id")
        for task in sorted(
            (item for item in tasks if _payload_text(item, "execution_id") == execution_id),
            key=lambda item: item["stable_key"],
        ):
            chosen_task = take(task)
            if chosen_task is not None:
                members.append(chosen_task)
        for plan in sorted(plans, key=lambda item: item["stable_key"]):
            if execution_id and execution_id in _payload_list(plan, "execution_ids"):
                chosen_plan = take(plan)
                if chosen_plan is not None:
                    members.append(chosen_plan)
        clusters.append(members)
    for task in sorted(tasks, key=lambda item: item["stable_key"]):
        chosen = take(task)
        if chosen is not None:
            clusters.append([chosen])
    for plan in sorted(plans, key=lambda item: item["stable_key"]):
        chosen = take(plan)
        if chosen is not None:
            clusters.append([chosen])
    others = sorted(
        (
            item
            for item in pending
            if item["category"] not in _LINKED and item["stable_key"] in by_key
        ),
        key=lambda item: (item["category"], item["stable_key"]),
    )
    for item in others:
        chosen = take(item)
        if chosen is not None:
            clusters.append([chosen])
    return clusters


def _split_cluster(members: list[dict]) -> list[list[dict]]:
    """Separate on signal, execution, task, and plan. Each payload keeps its foreign keys."""
    signals = [item for item in members if item["category"] == CATEGORY_SIGNAL]
    executions = [item for item in members if item["category"] == CATEGORY_EXECUTION]
    tasks = [item for item in members if item["category"] == CATEGORY_TASK]
    plans = [item for item in members if item["category"] == CATEGORY_PLAN]
    others = [item for item in members if item["category"] not in _LINKED]
    bundles: list[list[dict]] = []
    tasks_by_execution: dict[str, list[dict]] = {}
    for task in tasks:
        tasks_by_execution.setdefault(_payload_text(task, "execution_id"), []).append(task)
    consumed: set[str] = set()
    for execution in executions:
        execution_id = _payload_text(execution, "source_id")
        attached = tasks_by_execution.get(execution_id, [])
        for task in attached:
            consumed.add(task["stable_key"])
        bundles.append([execution])
        for task in attached:
            bundles.append([task])
    for task in tasks:
        if task["stable_key"] not in consumed:
            bundles.append([task])
    bundles.extend([signal] for signal in signals)
    bundles.extend([plan] for plan in plans)
    bundles.extend([item] for item in others)
    return bundles


def _item_view(item) -> dict:
    payload = item.payload if isinstance(item.payload, dict) else {}
    return {
        "item_id": str(item.id),
        "stable_key": item.stable_key,
        "category": item.category,
        "role": item.role,
        "payload": payload,
    }


def _plan_links(plan: dict, source: str, execution_ids: set[str]) -> bool:
    if source and source in _payload_list(plan, "source_signal_ids"):
        return True
    return bool(execution_ids.intersection(_payload_list(plan, "execution_ids")))


def _payload_text(item: dict, key: str) -> str:
    value = item["payload"].get(key) if isinstance(item.get("payload"), dict) else None
    if value in (None, ""):
        return ""
    return str(value)


def _payload_list(item: dict, key: str) -> set[str]:
    value = item["payload"].get(key) if isinstance(item.get("payload"), dict) else None
    if not isinstance(value, list):
        return set()
    return {str(entry) for entry in value if entry not in (None, "")}


def _require_unique_pieces(planned: list[PlannedLot]) -> None:
    found = []
    for lot in planned:
        found.extend(lot.payload.get("required_piece_ids") or [])
    if len(found) != len(set(found)):
        raise _incomplete()


def _require_complete(planned: list[PlannedLot], items) -> None:
    assigned = _assigned_keys(planned)
    expected = [item.stable_key for item in items]
    if len(assigned) != len(set(assigned)) or set(assigned) != set(expected):
        raise _incomplete()


def _assigned_keys(planned: list[PlannedLot]) -> list[str]:
    found = []
    for lot in planned:
        for section in lot.payload.get("sections") or []:
            found.extend(str(key) for key in section.get("item_ids") or [])
        for item in lot.payload.get("items") or []:
            if item.get("stable_key"):
                found.append(str(item["stable_key"]))
    return found


def _unsplittable() -> BrainWorkError:
    return BrainWorkError(
        code="budget_exceeded",
        message="Un morceau de section dépasse le plafond d'un appel.",
    )


def _incomplete() -> BrainWorkError:
    return BrainWorkError(
        code="partition_incomplete",
        message="La répartition du dossier est incomplète.",
    )
