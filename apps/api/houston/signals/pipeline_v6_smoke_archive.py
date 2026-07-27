"""Archive helpers for Lot 4 technical and Lot 10 business OpenAI smokes."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from houston.signals.constants import (
    AI_OBSERVATION_PIPELINE_PROMPT_VERSION,
    AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
SMOKE_ARCHIVE_DIR = REPO_ROOT / ".artifacts" / "pipeline-v6-smoke"
EVAL_ARCHIVE_DIR = REPO_ROOT / ".artifacts" / "pipeline-v6-eval"


def _utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def write_smoke_archive(
    *,
    kind: str,
    payload: dict[str, Any],
    archive_dir: Path | None = None,
) -> Path:
    """Write JSON + Markdown summary under .artifacts/pipeline-v6-smoke/."""
    target_dir = archive_dir or SMOKE_ARCHIVE_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = _utc_stamp()
    base = f"{kind}-{stamp}"
    body = {
        "kind": kind,
        "archived_at": stamp,
        "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        "prompt_version": AI_OBSERVATION_PIPELINE_PROMPT_VERSION,
        **payload,
    }
    json_path = target_dir / f"{base}.json"
    md_path = target_dir / f"{base}.md"
    json_path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    passed = body.get("passed")
    lines = [
        f"# Pipeline V6 smoke — {kind}",
        "",
        f"- archived_at: `{stamp}`",
        f"- schema: `{AI_OBSERVATION_PIPELINE_SCHEMA_VERSION}`",
        f"- prompt: `{AI_OBSERVATION_PIPELINE_PROMPT_VERSION}`",
        f"- passed: `{passed}`",
        "",
    ]
    if body.get("summary"):
        lines.append(str(body["summary"]))
        lines.append("")
    if body.get("errors"):
        lines.append("## Errors")
        for err in body["errors"]:
            lines.append(f"- {err}")
        lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path


def write_eval_archive(
    *,
    report: dict[str, Any],
    archive_dir: Path | None = None,
) -> Path:
    """Persist a V6 corpus eval report under .artifacts/pipeline-v6-eval/."""
    target_dir = archive_dir or EVAL_ARCHIVE_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = _utc_stamp()
    path = target_dir / f"eval-{stamp}.json"
    body = {
        "archived_at": stamp,
        "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        "prompt_version": AI_OBSERVATION_PIPELINE_PROMPT_VERSION,
        **report,
    }
    path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def latest_smoke_archive(*, kind: str, archive_dir: Path | None = None) -> Path | None:
    target_dir = archive_dir or SMOKE_ARCHIVE_DIR
    if not target_dir.exists():
        return None
    matches = sorted(target_dir.glob(f"{kind}-*.json"))
    return matches[-1] if matches else None
