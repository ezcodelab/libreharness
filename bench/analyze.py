#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Summarize benchmark runs.csv data without inventing missing numbers.

With no runs.csv, prints a clear no-results message and exits 0. The scaffold
computes counts, pass rates, and medians per task and arm. Paired tests and
confidence intervals described in bench/protocol.md are not automated yet.
"""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = ROOT / "results"
REQUIRED = ("run_id", "comparison", "arm", "task_id", "task_pass", "hidden_pass")
# shortcut: medians only, add paired tests and price-table cost before a release claim.


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="runs.csv file or directory containing results (default: bench/results)",
    )
    return parser.parse_args(argv)


def find_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if path.is_dir():
        return sorted(path.rglob("runs.csv"))
    return []


def number(value: str | None) -> float | None:
    if value is None or not str(value).strip():
        return None
    try:
        return float(value)
    except ValueError:
        return None


def flag(value: str | None, where: str) -> int:
    text = "" if value is None else str(value).strip().lower()
    if text in {"1", "true", "yes"}:
        return 1
    if text in {"0", "false", "no"}:
        return 0
    raise SystemExit(f"{where}: expected 0 or 1, got {value!r}")


def median(values: list[float]) -> str:
    return f"{statistics.median(values):.2f}" if values else "n/a"


def display(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.name


def load_rows(files: list[Path]) -> list[dict]:
    rows: list[dict] = []
    for path in files:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            missing = [name for name in REQUIRED if name not in (reader.fieldnames or [])]
            if missing:
                raise SystemExit(f"{display(path)}: missing columns: {', '.join(missing)}")
            for index, row in enumerate(reader, start=2):
                where = f"{display(path)}:{index}"
                row["task_pass"] = flag(row.get("task_pass"), where)
                row["hidden_pass"] = flag(row.get("hidden_pass"), where)
                rows.append(row)
    return rows


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    path = args.input if args.input is not None else DEFAULT_INPUT
    files = find_files(path)
    if not files:
        print(f"No benchmark results found at {display(path)}.")
        print("Status: protocol and scaffold only. No run data, no summary, no claim.")
        print("Run a live repetition with bench/runner.py --live, score it with the evaluator, then rerun this script.")
        return 0

    rows = load_rows(files)
    if not rows:
        print(f"No benchmark rows found in {', '.join(display(file) for file in files)}.")
        print("Status: no results, no claim.")
        return 0

    groups: dict[tuple[str, str, str], list[dict]] = {}
    for row in rows:
        key = (row["comparison"], row["task_id"], row["arm"])
        groups.setdefault(key, []).append(row)

    print("Benchmark summary from " + ", ".join(display(file) for file in files))
    print()
    print("| Comparison | Task | Arm | n | task_pass | hidden_pass | median wall s | median tokens | median cost USD |")
    print("|---|---|---|---|---|---|---|---|---|")
    for (comparison, task, arm), items in sorted(groups.items()):
        count = len(items)
        task_pass = sum(item["task_pass"] for item in items)
        hidden_pass = sum(item["hidden_pass"] for item in items)
        walls = [value for item in items if (value := number(item.get("wall_seconds"))) is not None]
        tokens = []
        for item in items:
            prompt = number(item.get("input_tokens"))
            completion = number(item.get("output_tokens"))
            if prompt is not None and completion is not None:
                tokens.append(prompt + completion)
        costs = [value for item in items if (value := number(item.get("cost_usd"))) is not None]
        print(
            f"| {comparison} | {task} | {arm} | {count} | {task_pass}/{count} | "
            f"{hidden_pass}/{count} | {median(walls)} | {median(tokens)} | {median(costs)} |"
        )
    print()
    print("Medians only. Paired tests, confidence intervals, and sensitivity analysis are not automated here.")
    print("See bench/protocol.md before making a claim.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
