from __future__ import annotations

import ast
from pathlib import Path

ACTION_PLANS_ROOT = Path(__file__).resolve().parents[1]


def _module_imports(module_path: Path) -> set[str]:
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def test_action_plans_materialization_does_not_import_selectors():
    imports = _module_imports(ACTION_PLANS_ROOT / "materialization.py")
    assert "houston.action_plans.selectors" not in imports


def test_action_plans_schedule_services_does_not_import_selectors():
    imports = _module_imports(ACTION_PLANS_ROOT / "schedule_services.py")
    assert "houston.action_plans.selectors" not in imports
