#!/usr/bin/env python3
"""Lot 1 static inventory: cross-imports between test_*.py modules."""

from __future__ import annotations

import re
import sys
from pathlib import Path

PATTERN = re.compile(
    r"^\s*from\s+(houston\.[\w.]+\.tests\.test_[\w]+)\s+import\s+(.+)$",
    re.MULTILINE,
)


def scan(repo_root: Path) -> list[tuple[str, str, str]]:
    api_root = repo_root / "apps" / "api" / "houston"
    rows: list[tuple[str, str, str]] = []
    for path in sorted(api_root.rglob("test_*.py")):
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(repo_root / "apps" / "api").as_posix()
        for match in PATTERN.finditer(text):
            source = match.group(1)
            imports = match.group(2).strip()
            rows.append((rel, source, imports))
    return rows


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    rows = scan(repo_root)
    print(f"Cross-imports from test_*.py modules: {len(rows)}")
    print("importer\timported_module\timports")
    for importer, source, imports in rows:
        print(f"{importer}\t{source}\t{imports}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
