from __future__ import annotations

import ast
from pathlib import Path

from houston.realtime.operational_invalidation_events import (
    NOTIFICATION_BULK_UPDATED_REASON,
    NOTIFICATION_CREATED_REASON,
    NOTIFICATION_UPDATED_REASON,
    event_pairs,
)

API_ROOT = Path(__file__).resolve().parents[3]

EMITTER_SCAN_FILES: tuple[Path, ...] = (
    API_ROOT / "houston/signals/services.py",
    API_ROOT / "houston/actions/services.py",
    API_ROOT / "houston/checklists/services.py",
    API_ROOT / "houston/checklists/materialization.py",
    API_ROOT / "houston/comments/services.py",
    API_ROOT / "houston/notifications/services.py",
)

SCHEDULE_INVALIDATION_FUNCTIONS = frozenset(
    {
        "schedule_establishment_invalidation",
        "schedule_membership_invalidation",
    }
)

WRAPPER_SUBJECT_TYPES = {
    "_schedule_signal_invalidation": "signal",
    "_schedule_action_invalidation": "action",
    "_schedule_checklist_invalidation": "checklist",
    "_schedule_execution_invalidation": "execution",
    "_schedule_comment_invalidation": "comment",
    "_schedule_notification_invalidation": "notification",
}

KNOWN_REASON_CONSTANTS = {
    "NOTIFICATION_CREATED_REASON": NOTIFICATION_CREATED_REASON,
    "NOTIFICATION_UPDATED_REASON": NOTIFICATION_UPDATED_REASON,
    "NOTIFICATION_BULK_UPDATED_REASON": NOTIFICATION_BULK_UPDATED_REASON,
}


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _string_value(node: ast.expr | None) -> str | None:
    if node is None:
        return None
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return KNOWN_REASON_CONSTANTS.get(node.id)
    return None


def _keyword_value(call: ast.Call, name: str) -> ast.expr | None:
    for keyword in call.keywords:
        if keyword.arg == name:
            return keyword.value
    return None


def _extract_event_from_call(call: ast.Call) -> tuple[str, str] | None:
    function_name = _call_name(call)
    if function_name is None:
        return None

    if function_name in SCHEDULE_INVALIDATION_FUNCTIONS:
        subject_type = _string_value(_keyword_value(call, "subject_type"))
        reason = _string_value(_keyword_value(call, "reason"))
        if subject_type is None or reason is None:
            return None
        return subject_type, reason

    subject_type = WRAPPER_SUBJECT_TYPES.get(function_name)
    if subject_type is None:
        return None

    reason = _string_value(_keyword_value(call, "reason"))
    if reason is None:
        return None
    return subject_type, reason


def scan_emitted_operational_invalidation_events(paths: tuple[Path, ...]) -> set[tuple[str, str]]:
    emitted: set[tuple[str, str]] = set()
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            event = _extract_event_from_call(node)
            if event is not None:
                emitted.add(event)
    return emitted


def test_emitted_operational_reasons_are_in_contract():
    emitted = scan_emitted_operational_invalidation_events(EMITTER_SCAN_FILES)
    contract = event_pairs()
    orphan_emissions = emitted - contract
    assert orphan_emissions == set(), (
        f"Emitted operational invalidation events missing from contract: {orphan_emissions}"
    )


def test_contract_operational_reasons_are_emitted():
    emitted = scan_emitted_operational_invalidation_events(EMITTER_SCAN_FILES)
    contract = event_pairs()
    stale_contract_entries = contract - emitted
    assert stale_contract_entries == set(), (
        f"Contract documents operational events not emitted in scan scope: {stale_contract_entries}"
    )
