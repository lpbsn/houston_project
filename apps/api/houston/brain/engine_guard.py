"""Structural checks on a model restitution. Prose is not interpreted.

A finding whose citation is not an examined sealed copy is removed.
A figure that does not resolve is omitted. A neighboring finding stays.
"""

from __future__ import annotations

from houston.brain.engine_tools import SealedView

SCHEMA_VERSION = "brain_engine_v1"
_ESTABLISHED = frozenset({"constat", "explication_etayee"})
_STATUSES = _ESTABLISHED | frozenset(
    {"hypothese", "hypothese_fragilisee", "absence_explication"}
)
_DISPOSITIONS = frozenset({"attached", "not_significant"})


def qualify_restitution(
    restitution: dict,
    view: SealedView,
    trace: list,
    examined: set[str],
) -> dict:
    """Publish the findings that hold and name the ones that were removed."""
    body = restitution if isinstance(restitution, dict) else {}
    compares = _compares(trace)
    published = []
    limits = _model_limits(body.get("limits"))
    significant_open = False
    for index, raw in enumerate(body.get("subjects") or []):
        if not isinstance(raw, dict):
            limits.append({"code": "finding_removed", "subject_key": f"subject:{index}"})
            continue
        key = str(raw.get("key") or f"subject:{index}")
        decision = _subject_decision(raw, key, view, examined, compares)
        if decision["remove"]:
            limits.append(decision["limit"])
            if raw.get("significant") is True:
                significant_open = True
            continue
        published.append(decision["subject"])
        if (
            decision["subject"].get("significant") is True
            and decision["subject"].get("examined") is not True
        ):
            significant_open = True
    anchors, missing = _anchors(body.get("anchors"), view)
    for anchor_id in missing:
        limits.append({"code": "anchor_undisposed", "anchor_id": anchor_id})
    contribution = any(subject.get("contribution") is True for subject in published)
    if missing or significant_open:
        qualification = "partial" if contribution else "not_publishable"
    elif contribution:
        qualification = "complete"
    else:
        qualification = "not_publishable"
    proposals = body.get("proposals") if isinstance(body.get("proposals"), dict) else {}
    return {
        "schema_version": SCHEMA_VERSION,
        "qualification": qualification,
        "subjects": published,
        "anchors": anchors,
        "limits": limits,
        "proposals": proposals,
    }


def _subject_decision(raw, key, view, examined, compares) -> dict:
    status = str(raw.get("epistemic_status") or "")
    evidence_ids = _strings(raw.get("evidence_ids"))
    if status not in _STATUSES or any(item_id not in examined for item_id in evidence_ids):
        return {"remove": True, "limit": {"code": "finding_removed", "subject_key": key}}
    established = status in _ESTABLISHED
    if established and raw.get("decisive_contradiction_unexamined") is True:
        return {
            "remove": True,
            "limit": {"code": "contradiction_unexamined", "subject_key": key},
        }
    figures = _figures(raw.get("figures"), view, examined, compares)
    retained = _contribution_retained(raw, evidence_ids, view, compares)
    return {
        "remove": False,
        "subject": {
            "key": key,
            "significant": raw.get("significant") is True,
            "examined": raw.get("examined") is True,
            "contribution": retained,
            "epistemic_status": status,
            "statement": str(raw.get("statement") or ""),
            "evidence_ids": evidence_ids,
            "compare_ids": _strings(raw.get("compare_ids")),
            "decisive_contradiction_unexamined": raw.get("decisive_contradiction_unexamined")
            is True,
            "figures": figures,
        },
    }


def _contribution_retained(raw, evidence_ids, view, compares) -> bool:
    if raw.get("contribution") is not True or not evidence_ids:
        return False
    items = [view.by_id[item_id] for item_id in evidence_ids if item_id in view.by_id]
    if not items:
        return False
    if any(item.category != "document" for item in items):
        return True
    return _cites_accepted_compare(raw, compares)


def _cites_accepted_compare(raw, compares) -> bool:
    for compare_id in _strings(raw.get("compare_ids")):
        compare = compares.get(compare_id)
        if not isinstance(compare, dict) or compare.get("accepted") is not True:
            continue
        left = str(compare.get("left_item_id") or "")
        right = str(compare.get("right_item_id") or "")
        if left and right and left != right:
            return True
    return False


def _figures(raw, view, examined, compares) -> list:
    if not isinstance(raw, list):
        return []
    resolved = []
    for figure in raw:
        if not isinstance(figure, dict):
            continue
        source = figure.get("source")
        if source == "measure":
            item = view.by_id.get(str(figure.get("item_id") or ""))
            if item is None or str(item.id) not in examined:
                continue
            payload = item.payload if isinstance(item.payload, dict) else {}
            if "value" not in payload:
                continue
            resolved.append(
                {
                    "source": "measure",
                    "item_id": str(item.id),
                    "label": payload.get("label"),
                    "value": payload.get("value"),
                    "unit": payload.get("unit"),
                }
            )
        elif source == "compare":
            compare = compares.get(str(figure.get("compare_id") or ""))
            if not isinstance(compare, dict):
                continue
            resolved.append(
                {
                    "source": "compare",
                    "compare_id": compare.get("compare_id"),
                    "accepted": compare.get("accepted"),
                    "code": compare.get("code"),
                    "difference": compare.get("difference"),
                    "variation": compare.get("variation"),
                }
            )
    return resolved


def _anchors(raw, view: SealedView) -> tuple[list, list]:
    expected = [str(item.id) for item in view.of("document")]
    supplied = {}
    if isinstance(raw, list):
        for anchor in raw:
            if not isinstance(anchor, dict):
                continue
            anchor_id = str(anchor.get("anchor_id") or "")
            disposition = str(anchor.get("disposition") or "")
            if anchor_id and disposition in _DISPOSITIONS:
                supplied[anchor_id] = {
                    "anchor_id": anchor_id,
                    "disposition": disposition,
                    "subject_key": str(anchor.get("subject_key") or ""),
                }
    published = [supplied[anchor_id] for anchor_id in expected if anchor_id in supplied]
    missing = [anchor_id for anchor_id in expected if anchor_id not in supplied]
    return published, missing


def _compares(trace: list) -> dict:
    found = {}
    for entry in trace:
        if entry.get("kind") != "tool" or entry.get("tool") != "compare":
            continue
        compare = (entry.get("envelope") or {}).get("compare")
        if isinstance(compare, dict) and compare.get("compare_id"):
            found[str(compare["compare_id"])] = compare
    return found


def _model_limits(raw) -> list:
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, (str, dict))]


def _strings(raw) -> list[str]:
    if not isinstance(raw, list):
        return []
    return [str(item) for item in raw if item]
