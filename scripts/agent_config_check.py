#!/usr/bin/env python3
"""Structural invariants for Houston/Spore agent configuration.

Reusable workflows are canonical Agent Skills under `.agents/skills`. Cursor
keeps only its editor-specific rules and settings under `.cursor`.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

EXPECTED_SKILLS = frozenset(
    {
        "create-plan",
        "docs-review",
        "hygien-pass",
        "implement-changes",
        "native-runtime-debug",
        "review-changes",
        "test-review",
    }
)

EXPECTED_RULES = frozenset(
    {
        "api-contract.mdc",
        "responsive-surfaces.mdc",
    }
)

FORBIDDEN_RULES = frozenset(
    {
        "00-agent-behavior.mdc",
        "20-mobile-pwa-shell.mdc",
        "30-local-infra.mdc",
        "40-testing.mdc",
        "80-security-data-integrity.mdc",
        "90-rule-authoring.mdc",
    }
)

SCAN_PYTEST_PATHS = [
    ROOT / "AGENTS.md",
    ROOT / "apps/api/AGENTS.md",
    ROOT / "apps/web/AGENTS.md",
    ROOT / ".agents",
    ROOT / ".cursor",
    ROOT / "docs",
]

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
        stripped = line.strip()
        if not stripped or stripped.startswith("-") or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        meta[key.strip()] = value.strip()
    return meta, body


def check_plans_not_tracked(errors: list[str]) -> None:
    for path in git_ls_files(".cursor/plans/**"):
        errors.append(f"Cursor plan still tracked by git: {path}")


def check_rules(errors: list[str]) -> None:
    rules_dir = ROOT / ".cursor/rules"
    if not rules_dir.is_dir():
        errors.append("Missing .cursor/rules/")
        return
    present = {path.name for path in rules_dir.glob("*.mdc")}
    extra = present - EXPECTED_RULES
    missing = EXPECTED_RULES - present
    for name in sorted(extra):
        errors.append(f"Unexpected rule file: .cursor/rules/{name}")
    for name in sorted(missing):
        errors.append(f"Missing required rule file: .cursor/rules/{name}")
    for name in sorted(FORBIDDEN_RULES & present):
        errors.append(f"Forbidden leftover rule: .cursor/rules/{name}")

    for file in sorted(rules_dir.glob("*.mdc")):
        text = file.read_text(encoding="utf-8")
        meta, _body = parse_frontmatter(text)
        rel = file.relative_to(ROOT)
        if not meta:
            errors.append(f"{rel}: missing YAML frontmatter")
            continue
        if "description" not in meta:
            errors.append(f"{rel}: missing frontmatter description")
        always = meta.get("alwaysApply", "")
        if always == "true":
            errors.append(f"{rel}: alwaysApply must not be true")
        elif always != "false":
            errors.append(f"{rel}: alwaysApply must be false")


def check_skills(errors: list[str]) -> None:
    skills_dir = ROOT / ".agents/skills"
    if not skills_dir.is_dir():
        errors.append("Missing .agents/skills/")
        return
    present = {child.name for child in skills_dir.iterdir() if child.is_dir()}
    extra = present - EXPECTED_SKILLS
    missing = EXPECTED_SKILLS - present
    for name in sorted(extra):
        errors.append(f"Unexpected skill directory: .agents/skills/{name}/")
    for name in sorted(missing):
        errors.append(f"Missing required skill directory: .agents/skills/{name}/")
    for child in skills_dir.iterdir():
        if child.is_dir() and not (child / "SKILL.md").exists():
            errors.append(f".agents/skills/{child.name}/ missing SKILL.md")
        elif child.is_file():
            errors.append(f"Unexpected file in .agents/skills/: {child.name}")


def check_agents_layout(errors: list[str]) -> None:
    agents_root = ROOT / ".agents"
    if not agents_root.is_dir():
        errors.append("Missing .agents/")
        return
    for child in sorted(agents_root.iterdir()):
        if child.name != "skills":
            errors.append(f"Unexpected .agents entry: {child.name}")


def check_pytest_args_usage(errors: list[str]) -> None:
    for base in SCAN_PYTEST_PATHS:
        files: list[Path]
        if base.is_file():
            files = [base]
        elif base.is_dir():
            files = sorted(path for path in base.rglob("*") if path.suffix in {".md", ".mdc"})
        else:
            continue
        for file in files:
            text = file.read_text(encoding="utf-8")
            for match in PYTEST_ARGS_PATTERN.finditer(text):
                errors.append(
                    f"{file.relative_to(ROOT)}: unsafe pytest invocation `{match.group(0)}`"
                )


def check_indexing_uploads(errors: list[str]) -> None:
    indexing = ROOT / ".cursorindexingignore"
    if not indexing.exists():
        return
    for line in indexing.read_text(encoding="utf-8").splitlines():
        if line.strip() == "uploads/":
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
        return
    try:
        json.loads(settings.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f".cursor/settings.json: invalid JSON ({exc})")


def check(errors: list[str]) -> None:
    check_plans_not_tracked(errors)
    check_rules(errors)
    check_skills(errors)
    check_agents_layout(errors)
    check_pytest_args_usage(errors)
    check_indexing_uploads(errors)
    check_env_example_access(errors)
    check_settings_json(errors)


def main() -> int:
    errors: list[str] = []
    check(errors)

    if errors:
        print("agent_config_check.py FAILED:\n", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print("agent_config_check.py OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
