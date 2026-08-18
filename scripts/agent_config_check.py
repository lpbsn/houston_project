#!/usr/bin/env python3
"""Structural invariants for Houston/Spore Cursor agent configuration.

`.cursor` is canonical. `.agents` is a generated mirror of commands, rules, and
skills. Run with `--sync` to copy `.cursor` → `.agents`.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

MIRRORED_TREES = ("commands", "rules", "skills")

EXPECTED_COMMANDS = frozenset(
    {
        "create-plan.md",
        "implement-changes.md",
        "review-changes.md",
        "hygiene-pass.md",
        "test-review.md",
        "docs-review.md",
    }
)

EXPECTED_RULES = frozenset(
    {
        "api-contract.mdc",
        "responsive-surfaces.mdc",
    }
)

EXPECTED_SKILLS = frozenset({"native-runtime-debug"})

FORBIDDEN_COMMANDS = frozenset(
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


def relative_files(directory: Path) -> dict[str, Path]:
    files: dict[str, Path] = {}
    if not directory.is_dir():
        return files
    for path in sorted(directory.rglob("*")):
        if path.is_file():
            files[path.relative_to(directory).as_posix()] = path
    return files


def sync_agents() -> None:
    agents_root = ROOT / ".agents"
    agents_root.mkdir(exist_ok=True)
    expected_dirs = set(MIRRORED_TREES)
    for child in list(agents_root.iterdir()):
        if child.name not in expected_dirs:
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    for tree in MIRRORED_TREES:
        src = ROOT / ".cursor" / tree
        dst = agents_root / tree
        if dst.exists():
            shutil.rmtree(dst)
        if src.exists():
            shutil.copytree(src, dst)


def check_plans_not_tracked(errors: list[str]) -> None:
    for path in git_ls_files(".cursor/plans/**"):
        errors.append(f"Cursor plan still tracked by git: {path}")


def check_commands(errors: list[str]) -> None:
    commands_dir = ROOT / ".cursor/commands"
    if not commands_dir.is_dir():
        errors.append("Missing .cursor/commands/")
        return
    present = {path.name for path in commands_dir.glob("*.md")}
    extra = present - EXPECTED_COMMANDS
    missing = EXPECTED_COMMANDS - present
    for name in sorted(extra):
        errors.append(f"Unexpected command file: .cursor/commands/{name}")
    for name in sorted(missing):
        errors.append(f"Missing required command file: .cursor/commands/{name}")
    for name in sorted(FORBIDDEN_COMMANDS & present):
        errors.append(f"Forbidden leftover command: .cursor/commands/{name}")


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
    skills_dir = ROOT / ".cursor/skills"
    if not skills_dir.is_dir():
        errors.append("Missing .cursor/skills/")
        return
    present = {child.name for child in skills_dir.iterdir() if child.is_dir()}
    extra = present - EXPECTED_SKILLS
    missing = EXPECTED_SKILLS - present
    for name in sorted(extra):
        errors.append(f"Unexpected skill directory: .cursor/skills/{name}/")
    for name in sorted(missing):
        errors.append(f"Missing required skill directory: .cursor/skills/{name}/")
    for child in skills_dir.iterdir():
        if child.is_dir() and not (child / "SKILL.md").exists():
            errors.append(f".cursor/skills/{child.name}/ missing SKILL.md")
        elif child.is_file():
            errors.append(f"Unexpected file in .cursor/skills/: {child.name}")


def check_agents_parity(errors: list[str]) -> None:
    settings_mirror = ROOT / ".agents/settings.json"
    if settings_mirror.exists():
        errors.append(".agents/settings.json must not exist; settings are .cursor-only")

    agents_root = ROOT / ".agents"
    if agents_root.is_dir():
        extra_top = [
            child.name
            for child in agents_root.iterdir()
            if child.name not in MIRRORED_TREES
        ]
        for name in sorted(extra_top):
            errors.append(f"Unexpected .agents entry (not a mirrored tree): {name}")

    for tree in MIRRORED_TREES:
        src = ROOT / ".cursor" / tree
        dst = ROOT / ".agents" / tree
        src_files = relative_files(src)
        dst_files = relative_files(dst)
        if not src.exists() and not dst.exists():
            continue
        if src.exists() and not dst.exists():
            errors.append(f"Missing mirrored tree: .agents/{tree}/")
            continue
        if dst.exists() and not src.exists():
            errors.append(f".agents/{tree}/ exists without canonical .cursor/{tree}/")
            continue
        extra = set(dst_files) - set(src_files)
        missing = set(src_files) - set(dst_files)
        for name in sorted(extra):
            errors.append(f".agents/{tree}/{name} has no canonical .cursor counterpart")
        for name in sorted(missing):
            errors.append(f".agents/{tree}/{name} is missing (run --sync)")
        for name in sorted(set(src_files) & set(dst_files)):
            if src_files[name].read_bytes() != dst_files[name].read_bytes():
                errors.append(f".agents/{tree}/{name} differs from .cursor/{tree}/{name}")


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
    check_commands(errors)
    check_rules(errors)
    check_skills(errors)
    check_agents_parity(errors)
    check_pytest_args_usage(errors)
    check_indexing_uploads(errors)
    check_env_example_access(errors)
    check_settings_json(errors)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Copy .cursor/{commands,rules,skills} to .agents, then check.",
    )
    args = parser.parse_args(argv)

    if args.sync:
        sync_agents()

    errors: list[str] = []
    check(errors)

    if errors:
        print("agent_config_check.py FAILED:\n", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    suffix = " (synced)" if args.sync else ""
    print(f"agent_config_check.py OK{suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
