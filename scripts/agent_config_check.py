#!/usr/bin/env python3
"""Deterministic guardrails for Houston Cursor agent configuration."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ALLOWED_COMMANDS = frozenset(
    {
        "scope.md",
        "implement-change.md",
        "audit.md",
        "review.md",
        "api-contract-change.md",
        "mobile-pwa-debug.md",
        "test-audit.md",
    }
)

DEPRECATED_COMMANDS = frozenset(
    {
        "need-scope.md",
        "ticket-scope.md",
        "backend-fix.md",
        "frontend-fix.md",
        "domain-lifecycle-change.md",
        "rbac-scope-change.md",
        "event-driven.md",
        "realtime-ws-change.md",
        "implementation-mode.md",
        "mobile-pwa-ui-change.md",
        "review-before-commit.md",
        "review-diff.md",
        "audit-mode.md",
    }
)

DEPRECATED_RULES = frozenset(
    {
        "000-project-contract.mdc",
        "01-agent-guardrails.mdc",
        "10-backend-django-drf.mdc",
        "20-frontend-react-vite-ts.mdc",
        "21-mobile-first-pwa.mdc",
        "30-docker-orbstack.mdc",
    }
)

SCAN_PYTEST_PATHS = [
    ROOT / "AGENTS.md",
    ROOT / "apps/api/AGENTS.md",
    ROOT / "apps/web/AGENTS.md",
    ROOT / ".cursor",
    ROOT / "docs",
]

ALWAYS_APPLY_MAX_LINES = 35
IMPLEMENT_CHANGE_MAX_LINES = 80

PYTEST_ARGS_PATTERN = re.compile(r"make\s+backend-test\s+PYTEST_ARGS\s*=")


def git_ls_files(pattern: str) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "ls-files", pattern],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return []
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


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


def iter_markdown_for_make(pattern: re.Pattern[str], paths: list[Path]) -> list[tuple[Path, str]]:
    hits: list[tuple[Path, str]] = []
    for base in paths:
        files: list[Path]
        if base.is_file():
            files = [base]
        elif base.is_dir():
            files = sorted(base.rglob("*"))
        else:
            continue
        for file in files:
            if file.suffix not in {".md", ".mdc"}:
                continue
            text = file.read_text(encoding="utf-8")
            for match in pattern.finditer(text):
                hits.append((file, match.group(0)))
    return hits


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    frontmatter = parts[1]
    body = parts[2]
    meta: dict[str, str] = {}
    for line in frontmatter.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip()
    return meta, body


def check_plans_not_tracked(errors: list[str]) -> None:
    tracked = git_ls_files(".cursor/plans/**")
    for path in tracked:
        errors.append(f"Cursor plan still tracked by git: {path}")


def check_commands_whitelist(errors: list[str]) -> None:
    commands_dir = ROOT / ".cursor/commands"
    if not commands_dir.is_dir():
        errors.append("Missing .cursor/commands/")
        return
    present = {path.name for path in commands_dir.glob("*.md")}
    extra = present - ALLOWED_COMMANDS
    missing = ALLOWED_COMMANDS - present
    for name in sorted(extra):
        errors.append(f"Unexpected command file: .cursor/commands/{name}")
    for name in sorted(missing):
        errors.append(f"Missing required command file: .cursor/commands/{name}")
    for name in sorted(DEPRECATED_COMMANDS & present):
        errors.append(f"Deprecated command still present: .cursor/commands/{name}")


def check_deprecated_rules(errors: list[str]) -> None:
    rules_dir = ROOT / ".cursor/rules"
    if not rules_dir.is_dir():
        return
    for name in DEPRECATED_RULES:
        if (rules_dir / name).exists():
            errors.append(f"Deprecated rule still present: .cursor/rules/{name}")


def check_pytest_args_usage(errors: list[str]) -> None:
    for file, match in iter_markdown_for_make(PYTEST_ARGS_PATTERN, SCAN_PYTEST_PATHS):
        errors.append(f"{file.relative_to(ROOT)}: unsafe pytest invocation `{match}`")


def check_indexing_uploads(errors: list[str]) -> None:
    indexing = ROOT / ".cursorindexingignore"
    if not indexing.exists():
        return
    for line in indexing.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped == "uploads/":
            errors.append(".cursorindexingignore: use `/uploads/` not `uploads/`")


def check_env_example_access(errors: list[str]) -> None:
    ignore = ROOT / ".cursorignore"
    if not ignore.exists():
        return
    text = ignore.read_text(encoding="utf-8")
    if ".env.*" in text and "!.env.example" not in text:
        errors.append(".cursorignore: .env.* without !.env.example exception")


def check_settings_json(errors: list[str]) -> None:
    settings = ROOT / ".cursor/settings.json"
    if not settings.exists():
        errors.append(".cursor/settings.json is missing")
        return
    try:
        parsed = json.loads(settings.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f".cursor/settings.json: invalid JSON ({exc})")
        return
    if parsed != {}:
        errors.append(".cursor/settings.json must be exactly {}")


def check_always_apply_rules(errors: list[str]) -> None:
    rules_dir = ROOT / ".cursor/rules"
    if not rules_dir.is_dir():
        return
    always_apply_files: list[Path] = []
    total_lines = 0
    for file in sorted(rules_dir.glob("*.mdc")):
        text = file.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(text)
        if meta.get("alwaysApply") != "true":
            continue
        always_apply_files.append(file)
        total_lines += len(body.strip().splitlines())
    if len(always_apply_files) > 1:
        names = ", ".join(path.name for path in always_apply_files)
        errors.append(f"More than one alwaysApply rule: {names}")
    if total_lines > ALWAYS_APPLY_MAX_LINES:
        errors.append(
            f"alwaysApply rules exceed {ALWAYS_APPLY_MAX_LINES} body lines (got {total_lines})"
        )


def check_implement_change_size(errors: list[str]) -> None:
    path = ROOT / ".cursor/commands/implement-change.md"
    if not path.exists():
        return
    line_count = len(path.read_text(encoding="utf-8").splitlines())
    if line_count > IMPLEMENT_CHANGE_MAX_LINES:
        errors.append(
            f"implement-change.md exceeds {IMPLEMENT_CHANGE_MAX_LINES} lines (got {line_count})"
        )


def check_skills_orphans(errors: list[str]) -> None:
    skills_dir = ROOT / ".cursor/skills"
    if not skills_dir.is_dir():
        return
    for child in skills_dir.iterdir():
        if child.is_dir() and not (child / "SKILL.md").exists():
            errors.append(f".cursor/skills/{child.name}/ missing SKILL.md")


def check_make_targets(errors: list[str]) -> None:
    make_pattern = re.compile(r"`make ([a-zA-Z0-9_-]+)`")
    targets = load_makefile_targets()
    scan_roots = [
        ROOT / "AGENTS.md",
        ROOT / "apps/api/AGENTS.md",
        ROOT / "apps/web/AGENTS.md",
        ROOT / ".cursor/rules",
        ROOT / ".cursor/commands",
    ]
    for file, target in iter_markdown_for_make(make_pattern, scan_roots):
        match = re.match(r"`make ([a-zA-Z0-9_-]+)`", target)
        if not match:
            continue
        name = match.group(1)
        if name not in targets:
            errors.append(f"{file.relative_to(ROOT)}: unknown make target `{name}`")


def main() -> int:
    errors: list[str] = []
    check_plans_not_tracked(errors)
    check_commands_whitelist(errors)
    check_deprecated_rules(errors)
    check_pytest_args_usage(errors)
    check_indexing_uploads(errors)
    check_env_example_access(errors)
    check_settings_json(errors)
    check_always_apply_rules(errors)
    check_implement_change_size(errors)
    check_skills_orphans(errors)
    check_make_targets(errors)

    if errors:
        print("agent_config_check.py FAILED:\n", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print("agent_config_check.py OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
