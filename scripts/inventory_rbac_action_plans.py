#!/usr/bin/env python3
"""Lot 1: static RBAC overlap matrix for action_plans (permissions vs hints vs API 403)."""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
API = REPO / "apps" / "api" / "houston" / "action_plans"

PERM_FILE = API / "tests" / "test_permissions.py"
HINTS_FILE = API / "tests" / "test_action_plan_permission_hints_api.py"
API_FILES = sorted((API / "tests").glob("test_*api*.py"))

RULES = [
    ("can_create_action_plan / catalog", r"can_create|cannot_create|create.*403|staff_create"),
    ("can_use catalog", r"can_use|use.*403|inactive_catalog"),
    ("can_manage catalog", r"can_manage|manage_catalog|can_update|can_deactivate|can_activate"),
    ("can_mark_done execution", r"can_mark_done|mark_done.*403|pilot_assignee_can_mark"),
    ("can_validate execution", r"can_validate|validate.*403"),
    ("can_cancel execution", r"can_cancel|cancel.*403"),
    ("can_execute task", r"can_execute|execute.*403"),
    ("can_schedule", r"can_schedule|schedule.*403"),
    ("cross_pole / linked plan", r"cross_pole|linked_action|define_cross"),
    ("visibility / readable", r"visible|readable|out_of_scope"),
]


def count_matches(path: Path, pattern: str) -> int:
    if not path.exists():
        return 0
    text = path.read_text(encoding="utf-8")
    return len(re.findall(pattern, text, re.IGNORECASE))


def main() -> None:
    api_blob = "\n".join(p.read_text(encoding="utf-8") for p in API_FILES)
    print("rule\tpermissions_unit\thints_api\tapi_403_or_hints\toverlap_layers")
    for label, pattern in RULES:
        p = count_matches(PERM_FILE, pattern)
        h = count_matches(HINTS_FILE, pattern)
        a = len(re.findall(pattern, api_blob, re.IGNORECASE))
        layers = sum(1 for n in (p, h, a) if n > 0)
        print(f"{label}\t{p}\t{h}\t{a}\t{layers}")


if __name__ == "__main__":
    main()
