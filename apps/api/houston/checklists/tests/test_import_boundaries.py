from __future__ import annotations

import ast
from pathlib import Path

CHECKLISTS_ROOT = Path(__file__).resolve().parents[1]


def _module_imports(module_path: Path) -> set[str]:
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def test_checklists_selectors_does_not_import_services_or_materialization():
    imports = _module_imports(CHECKLISTS_ROOT / "selectors.py")
    assert "houston.checklists.services" not in imports
    assert "houston.checklists.materialization" not in imports


def test_checklists_selectors_source_does_not_reference_ensure_visible():
    source = (CHECKLISTS_ROOT / "selectors.py").read_text(encoding="utf-8")
    assert "ensure_visible_executions_materialized" not in source


def test_checklists_materialization_does_not_import_selectors_or_services():
    imports = _module_imports(CHECKLISTS_ROOT / "materialization.py")
    assert "houston.checklists.selectors" not in imports
    assert "houston.checklists.services" not in imports
