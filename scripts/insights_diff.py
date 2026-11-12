"""Compare Insight result structure and availability without exposing row values.

Usage: python scripts/insights_diff.py BASELINE_JSON CURRENT_JSON
The current input can be either a full pipeline response or a projected snapshot.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def project(payload: dict[str, Any]) -> dict[str, Any]:
    """Keep only stable shape and status fields; discard values and chart points."""
    summary = payload.get("executive_summary") or {}
    if not isinstance(summary, dict):
        summary = {}

    def items(key: str, fields: tuple[str, ...]) -> list[dict[str, Any]]:
        projected = []
        for item in payload.get(key) or []:
            if isinstance(item, dict):
                projected.append({field: item.get(field) for field in fields})
        return sorted(projected, key=lambda item: str(item.get("id") or ""))

    return {
        "schema": 1,
        "success": payload.get("success"),
        "db_type": payload.get("db_type"),
        "summary_source": summary.get("source"),
        "metrics": items("key_metrics", ("id", "status", "reason", "format")),
        "charts": items("charts", ("id", "status", "reason", "type")),
    }


def compare(expected: dict[str, Any], actual: dict[str, Any]) -> list[str]:
    """Report only projected paths, including status and shape changes."""
    changes = []

    def visit(path: str, left: Any, right: Any) -> None:
        if isinstance(left, dict) and isinstance(right, dict):
            for key in sorted(set(left) | set(right)):
                visit(f"{path}.{key}" if path else key, left.get(key), right.get(key))
        elif isinstance(left, list) and isinstance(right, list):
            if len(left) != len(right):
                changes.append(f"{path}: count {len(left)} -> {len(right)}")
            for index, (a, b) in enumerate(zip(left, right)):
                visit(f"{path}[{index}]", a, b)
        elif left != right:
            changes.append(f"{path}: {left!r} -> {right!r}")

    visit("", expected, actual)
    return changes


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("Usage: python scripts/insights_diff.py BASELINE_JSON CURRENT_JSON")
        return 2
    baseline = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    current = json.loads(Path(argv[2]).read_text(encoding="utf-8"))
    if not isinstance(baseline, dict) or not isinstance(current, dict):
        print("Both inputs must contain JSON objects")
        return 2
    if "key_metrics" in baseline:
        baseline = project(baseline)
    if "key_metrics" in current:
        current = project(current)
    differences = compare(baseline, current)
    for difference in differences:
        print(difference)
    if differences:
        return 1
    print("Insight structure/status matches baseline")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
