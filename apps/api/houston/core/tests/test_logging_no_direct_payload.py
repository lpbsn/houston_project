from __future__ import annotations

import ast
from pathlib import Path

HOUSTON_ROOT = Path(__file__).resolve().parents[2]
SKIP_DIR_NAMES = frozenset({"tests", "migrations", "__pycache__"})
LOG_METHODS = frozenset({"debug", "info", "warning", "error", "exception", "critical"})


def _is_target_logger_call(node: ast.Call) -> bool:
    if not isinstance(node.func, ast.Attribute):
        return False
    if node.func.attr not in LOG_METHODS:
        return False
    return isinstance(node.func.value, ast.Name) and node.func.value.id == "logger"


def _check_logger_call(node: ast.Call) -> str | None:
    if not _is_target_logger_call(node):
        return None
    if len(node.args) > 1:
        return "logger call uses positional formatting arguments"
    if not node.args:
        return None
    message = node.args[0]
    if isinstance(message, ast.JoinedStr):
        return "logger message is an f-string"
    if (
        isinstance(message, ast.Constant)
        and isinstance(message.value, str)
        and "%" in message.value
        and len(node.args) > 1
    ):
        return "logger message uses % formatting with positional arguments"
    return None


def _iter_houston_sources() -> list[Path]:
    sources: list[Path] = []
    for path in sorted(HOUSTON_ROOT.rglob("*.py")):
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        sources.append(path)
    return sources


def _collect_logger_violations(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        reason = _check_logger_call(node)
        if reason is not None:
            violations.append(f"{path}:{node.lineno}: {reason}")
    return violations


def test_houston_logger_calls_avoid_direct_payload_interpolation():
    violations: list[str] = []
    for path in _iter_houston_sources():
        violations.extend(_collect_logger_violations(path))
    assert not violations, "Direct logger payload interpolation found:\n" + "\n".join(violations)
