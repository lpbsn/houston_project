#!/usr/bin/env python3
"""Documentation drift checks for Houston active docs and agent instructions."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SCAN_ROOTS = [
    ROOT / "README.md",
    ROOT / "INSTALL_MAC.md",
    ROOT / "AGENTS.md",
    ROOT / "apps/api/AGENTS.md",
    ROOT / "apps/web/AGENTS.md",
    ROOT / "docs",
    ROOT / ".cursor/rules",
    ROOT / ".cursor/commands",
    ROOT / "infra/railway/README.md",
]

FORBIDDEN_DIRS = [
    ROOT / "docs/archive",
    ROOT / "docs/audits",
    ROOT / "docs/evolution_action",
    ROOT / "docs/product/build_plan_mvp",
    ROOT / "docs/qa",
    ROOT / "docs/design",
]

FORBIDDEN_PATH_FRAGMENTS = [
    "docs/archive/",
    "docs/audits/",
    "docs/evolution_action/",
    "docs/product/build_plan_mvp/",
    "docs/qa/",
    "docs/design/",
]

LEGACY_ACTIVE_PATTERNS = [
    re.compile(r"houston/actions"),
    re.compile(r"houston/checklists"),
    re.compile(r"execution-feed/"),
    re.compile(r"\bChecklist domain\b"),
    re.compile(r"\bAction domain\b"),
]

LINK_PATTERN = re.compile(r"\]\(([^)]+)\)")
MAKE_PATTERN = re.compile(r"`make ([a-zA-Z0-9_-]+)`")


def iter_markdown_files() -> list[Path]:
    files: list[Path] = []
    for root in SCAN_ROOTS:
        if root.is_file():
            files.append(root)
        elif root.is_dir():
            for path in root.rglob("*"):
                if path.suffix in {".md", ".mdc"}:
                    files.append(path)
    return sorted(set(files))


def load_makefile_targets() -> set[str]:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    targets: set[str] = set()
    for line in makefile.splitlines():
        if line.startswith(".PHONY:"):
            chunk = line.split(":", 1)[1]
            targets.update(part.strip() for part in chunk.split() if part.strip())
        match = re.match(r"^([a-zA-Z0-9_.-]+):", line)
        if match:
            targets.add(match.group(1))
    return targets


def resolve_link(source: Path, target: str) -> Path | None:
    target = target.strip()
    if not target or target.startswith(("http://", "https://", "mailto:", "#")):
        return None
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    target = target.split("#", 1)[0].split("?", 1)[0]
    if not target:
        return None
    path = (source.parent / target).resolve()
    try:
        path.relative_to(ROOT)
    except ValueError:
        return None
    return path


def check_forbidden_dirs(errors: list[str]) -> None:
    for directory in FORBIDDEN_DIRS:
        if directory.exists():
            errors.append(f"Forbidden directory still exists: {directory.relative_to(ROOT)}")


def check_forbidden_references(files: list[Path], errors: list[str]) -> None:
    link_or_code = re.compile(
        r"(?:\]\(([^)]+)\)|`([^`]+)`)",
    )
    for file in files:
        text = file.read_text(encoding="utf-8")
        for match in link_or_code.finditer(text):
            candidate = match.group(1) or match.group(2) or ""
            for fragment in FORBIDDEN_PATH_FRAGMENTS:
                if fragment in candidate:
                    errors.append(
                        f"{file.relative_to(ROOT)}: references forbidden path `{candidate}`"
                    )


def check_links(files: list[Path], errors: list[str]) -> None:
    for file in files:
        text = file.read_text(encoding="utf-8")
        for match in LINK_PATTERN.finditer(text):
            resolved = resolve_link(file, match.group(1))
            if resolved is None:
                continue
            if not resolved.exists():
                errors.append(
                    f"{file.relative_to(ROOT)}: broken link `{match.group(1)}` → {resolved.relative_to(ROOT)}"
                )


def check_make_targets(files: list[Path], targets: set[str], errors: list[str]) -> None:
    for file in files:
        text = file.read_text(encoding="utf-8")
        for match in MAKE_PATTERN.finditer(text):
            target = match.group(1)
            if target not in targets:
                errors.append(
                    f"{file.relative_to(ROOT)}: unknown make target `{target}`"
                )


def check_legacy_terms(files: list[Path], errors: list[str]) -> None:
    for file in files:
        text = file.read_text(encoding="utf-8")
        for pattern in LEGACY_ACTIVE_PATTERNS:
            if pattern.search(text):
                # Allow explicit historical context in decisions doc
                if file.name == "action_plan.md" and "legacy" in text.lower():
                    continue
                if "removed" in text.lower() or "historical" in text.lower():
                    continue
                errors.append(
                    f"{file.relative_to(ROOT)}: legacy term matched `{pattern.pattern}`"
                )


def check_domain_headers(errors: list[str]) -> None:
    domains_dir = ROOT / "docs/product/domains"
    if not domains_dir.exists():
        return
    for file in sorted(domains_dir.glob("*.md")):
        text = file.read_text(encoding="utf-8")
        if not re.search(r"^Status:\s*.+", text, re.MULTILINE):
            errors.append(f"{file.relative_to(ROOT)}: missing `Status:` header")
        if not re.search(r"^Implementation status:\s*.+", text, re.MULTILINE):
            errors.append(
                f"{file.relative_to(ROOT)}: missing `Implementation status:` header"
            )


def check_readme_entrypoint(errors: list[str]) -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    if "docs/product/current_state.md" not in readme:
        errors.append("README.md must link to docs/product/current_state.md")
    if "docs/engineering/local_development.md" not in readme:
        errors.append("README.md must link to docs/engineering/local_development.md")
    if re.search(r"^## What Is Not Implemented Yet", readme, re.MULTILINE):
        errors.append(
            "README.md must not contain exhaustive `## What Is Not Implemented Yet` section"
        )


def main() -> int:
    errors: list[str] = []
    files = iter_markdown_files()
    makefile_targets = load_makefile_targets()

    check_forbidden_dirs(errors)
    check_forbidden_references(files, errors)
    check_links(files, errors)
    check_make_targets(files, makefile_targets, errors)
    check_legacy_terms(files, errors)
    check_domain_headers(errors)
    check_readme_entrypoint(errors)

    if errors:
        print("docs_check.py FAILED:\n", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(f"docs_check.py OK ({len(files)} markdown files scanned)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
