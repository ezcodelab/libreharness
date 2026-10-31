#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Summarize benchmark runs.csv data without inventing missing numbers.

With no runs.csv, prints a clear no-results message and exits 0. The local B1-B8
scaffold computes counts, pass rates, and medians. The coding runner also gets a
paired per-task difference and a task-clustered bootstrap confidence interval.
"""

from __future__ import annotations

import argparse
import csv
import random
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
    parser.add_argument("--baseline", default="plain", help="baseline arm for a paired coding report")
    parser.add_argument("--candidate", default="current", help="candidate arm for a paired coding report")
    parser.add_argument("--bootstrap", type=int, default=1000, help="bootstrap iterations")
    parser.add_argument("--seed", type=int, default=0, help="bootstrap seed")
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
            columns = reader.fieldnames or []
            if "task" in columns and "reward" in columns:
                rows.extend(dict(row) for row in reader)
                continue
            missing = [name for name in REQUIRED if name not in columns]
            if missing:
                raise SystemExit(f"{display(path)}: missing columns: {', '.join(missing)}")
            for index, row in enumerate(reader, start=2):
                where = f"{display(path)}:{index}"
                row["task_pass"] = flag(row.get("task_pass"), where)
                row["hidden_pass"] = flag(row.get("hidden_pass"), where)
                rows.append(row)
    return rows


def coding_solved(row: dict) -> int:
    value = number(row.get("reward"))
    return 1 if value is not None and value >= 1.0 else 0


def paired_diffs(
    rows: list[dict], baseline: str, candidate: str
) -> list[tuple[str, float, float, float]]:
    by_task: dict[str, dict[str, list[float]]] = {}
    for row in rows:
        arm = row.get("arm", "")
        task = row.get("task", "")
        reward = number(row.get("reward"))
        if not arm or not task or reward is None:
            continue
        by_task.setdefault(task, {}).setdefault(arm, []).append(reward)
    diffs = []
    for task, arms in sorted(by_task.items()):
        if baseline not in arms or candidate not in arms:
            continue
        first = statistics.mean(arms[baseline])
        second = statistics.mean(arms[candidate])
        diffs.append((task, first, second, second - first))
    return diffs


def bootstrap_ci(values: list[float], iterations: int, seed: int) -> tuple[float, float] | None:
    if not values:
        return None
    generator = random.Random(seed)
    means = []
    for _ in range(max(1, iterations)):
        sample = [values[generator.randrange(len(values))] for _ in values]
        means.append(statistics.mean(sample))
    means.sort()
    lower = means[max(0, int(0.025 * len(means)) - 1)]
    upper = means[min(len(means) - 1, int(0.975 * len(means)))]
    return lower, upper


def coding_report(
    rows: list[dict], baseline: str, candidate: str, iterations: int, seed: int
) -> int:
    print("Coding benchmark summary")
    print()
    print("| Arm | Trials | Solved | Rate | Exceptions | Cost USD | Tokens | Mean wall s | Test-first |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for arm in sorted({row.get("arm", "") for row in rows}):
        items = [row for row in rows if row.get("arm") == arm]
        solved = sum(coding_solved(row) for row in items)
        first = [row for row in items if row.get("test_first") in {"0", "1"}]
        first_rate = (
            f"{sum(row.get('test_first') == '1' for row in first) / len(first):.0%}"
            if first
            else "n/a"
        )
        tokens = sum(
            (number(row.get("input_tokens")) or 0)
            + (number(row.get("output_tokens")) or 0)
            for row in items
        )
        print(
            f"| {arm} | {len(items)} | {solved} | {solved / len(items):.0%} | "
            f"{sum(bool(row.get('exception')) for row in items)} | "
            f"${sum(number(row.get('cost_usd')) or 0 for row in items):.4f} | "
            f"{tokens:.0f} | "
            f"{statistics.mean(number(row.get('wall_seconds')) or 0 for row in items):.1f} | "
            f"{first_rate} |"
        )

    diffs = paired_diffs(rows, baseline, candidate)
    print()
    print(f"Paired by task: {candidate} - {baseline}")
    if not diffs:
        print("No task has both arms with a numeric reward.")
        return 0
    print("| Task | Baseline | Candidate | Difference |")
    print("|---|---:|---:|---:|")
    for task, first, second, difference in diffs:
        print(f"| {task} | {first:.0%} | {second:.0%} | {difference:+.0%} |")
    values = [difference for _task, _first, _second, difference in diffs]
    mean_diff = statistics.mean(values)
    interval = bootstrap_ci(values, iterations, seed)
    improved = sum(value > 0 for value in values)
    regressed = sum(value < 0 for value in values)
    tied = len(values) - improved - regressed
    print()
    print(
        f"tasks: {len(values)} | mean difference: {mean_diff * 100:+.1f} pp | "
        f"95% bootstrap CI: [{interval[0] * 100:+.1f}, {interval[1] * 100:+.1f}] pp | "
        f"improved/regressed/tied: {improved}/{regressed}/{tied}"
    )
    print(
        "This is a task-clustered bootstrap. It is inconclusive if the interval "
        "crosses zero or if the task count is too small to estimate variance."
    )
    return 0


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
    if "task" in rows[0] and "reward" in rows[0]:
        return coding_report(
            rows, args.baseline, args.candidate, args.bootstrap, args.seed
        )

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
