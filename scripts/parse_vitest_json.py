#!/usr/bin/env python3
"""Parse Vitest JSON reporter output and rank slowest files/tests (Lot 1 baseline)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _duration_ms(node: dict) -> float:
    duration = node.get("duration")
    if duration is not None:
        return float(duration)
    start = node.get("start") or node.get("startTime")
    end = node.get("end") or node.get("endTime")
    if start is not None and end is not None:
        return float(end) - float(start)
    return 0.0


def _collect_tests(suite: dict, file_path: str, out: list[dict]) -> None:
    for child in suite.get("assertionResults") or []:
        out.append(
            {
                "file": file_path,
                "name": child.get("fullName") or child.get("title") or child.get("name"),
                "duration_ms": _duration_ms(child),
                "status": child.get("status"),
            }
        )
    for child in suite.get("testResults") or []:
        child_file = child.get("name") or file_path
        _collect_tests(child, child_file, out)


def parse_vitest_json(data: dict) -> tuple[list[dict], list[dict]]:
    file_rows: list[dict] = []
    test_rows: list[dict] = []

    for result in data.get("testResults") or []:
        file_path = result.get("name") or "unknown"
        duration = _duration_ms(result)
        file_rows.append(
            {
                "file": file_path,
                "duration_ms": duration,
                "num_tests": len(result.get("assertionResults") or []),
                "status": result.get("status"),
            }
        )
        _collect_tests(result, file_path, test_rows)

    file_rows.sort(key=lambda r: r["duration_ms"], reverse=True)
    test_rows.sort(key=lambda r: r["duration_ms"], reverse=True)
    return file_rows, test_rows


def _format_table(rows: list[dict], columns: list[str], limit: int) -> str:
    lines = ["\t".join(columns)]
    for row in rows[:limit]:
        lines.append("\t".join(str(row.get(c, "")) for c in columns))
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("json_path", type=Path, help="Vitest JSON output file")
    parser.add_argument("--top-files", type=int, default=30)
    parser.add_argument("--top-tests", type=int, default=50)
    parser.add_argument("--out", type=Path, help="Optional summary text output")
    args = parser.parse_args()

    data = json.loads(args.json_path.read_text(encoding="utf-8"))
    file_rows, test_rows = parse_vitest_json(data)

    total_ms = sum(r["duration_ms"] for r in file_rows)
    summary_lines = [
        f"Vitest total (sum of file durations): {total_ms:.0f} ms ({total_ms / 1000:.1f}s)",
        f"Files: {len(file_rows)} | Tests parsed: {len(test_rows)}",
        "",
        f"=== Top {args.top_files} files by duration ===",
        _format_table(file_rows, ["file", "duration_ms", "num_tests", "status"], args.top_files),
        "",
        f"=== Top {args.top_tests} tests by duration ===",
        _format_table(test_rows, ["file", "name", "duration_ms", "status"], args.top_tests),
    ]
    summary = "\n".join(summary_lines)
    print(summary)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(summary, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
