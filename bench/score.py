#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compute LibreHarness pass@1 at the fixed benchmark budget.

The headline metric is one number: pass@1 = tasks whose first repetition passes
all hidden tests / tasks in the suite. Cost and wall time are reported beside
it, never blended into a composite score.
"""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
from pathlib import Path

TRUE = {"1", "true", "yes", "pass", "passed"}


def find_runs(path: Path) -> Path | None:
    if path.is_file():
        return path
    candidate = path / "runs.csv"
    return candidate if candidate.is_file() else None


def number(value: str | None) -> float | None:
    if value is None or value.strip() == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def first_rows(rows: list[dict[str, str]], arm: str) -> dict[str, dict[str, str]]:
    chosen: dict[str, dict[str, str]] = {}
    for row in rows:
        if row.get("arm", "").strip() != arm:
            continue
        task = row.get("task_id", "").strip()
        if not task:
            continue
        repetition = number(row.get("repetition")) or 1
        current = chosen.get(task)
        if current is None or repetition < (number(current.get("repetition")) or 1):
            chosen[task] = row
    return chosen


def score(rows: list[dict[str, str]], arm: str) -> dict:
    chosen = first_rows(rows, arm)
    if not chosen:
        return {"arm": arm, "tasks": 0, "pass_at_1": None, "costs": [], "times": []}
    passed = 0
    costs = []
    times = []
    for row in chosen.values():
        value = row.get("hidden_pass", "").strip().lower()
        if value in TRUE:
            passed += 1
        cost = number(row.get("cost_usd"))
        if cost is not None:
            costs.append(cost)
        wall = number(row.get("wall_seconds"))
        if wall is not None:
            times.append(wall)
    return {
        "arm": arm,
        "tasks": len(chosen),
        "pass_at_1": 100.0 * passed / len(chosen),
        "costs": costs,
        "times": times,
    }


def show(result: dict) -> None:
    if result["tasks"] == 0:
        print(f"{result['arm']}: no tasks")
        return
    score_value = result["pass_at_1"]
    cost = statistics.median(result["costs"]) if result["costs"] else None
    wall = statistics.median(result["times"]) if result["times"] else None
    cost_text = f"${cost:.2f}" if cost is not None else "n/a"
    wall_text = f"{wall:.0f}s" if wall is not None else "n/a"
    print(
        f"{result['arm']}: pass@1 {score_value:.1f}% "
        f"({result['tasks']} tasks; median cost {cost_text}; median wall {wall_text})"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("bench/results"),
                        help="results directory or runs.csv")
    parser.add_argument("--arm", default="harness",
                        help="arm to score (default: harness)")
    parser.add_argument("--baseline", help="optional baseline arm, e.g. plain")
    parser.add_argument("--candidate", help="optional candidate arm, e.g. harness")
    args = parser.parse_args()

    runs = find_runs(args.input)
    if runs is None:
        print("No benchmark results found at", args.input)
        print("Status: protocol and scaffold only. No run data, no score, no claim.")
        print("Run the plain baseline first, then the harness arm, then rerun this script.")
        return 0

    with runs.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    if args.baseline or args.candidate:
        baseline = args.baseline or "plain"
        candidate = args.candidate or "harness"
        first = score(rows, baseline)
        second = score(rows, candidate)
        show(first)
        show(second)
        if first["pass_at_1"] is not None and second["pass_at_1"] is not None:
            print(f"delta: {second['pass_at_1'] - first['pass_at_1']:+.1f} percentage points")
    else:
        show(score(rows, args.arm))

    print("Headline metric: pass@1 at the fixed benchmark budget. Cost and wall time are secondary.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
