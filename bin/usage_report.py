# SPDX-License-Identifier: MIT
#!/usr/bin/env python3
"""Aggregate model usage into cost per successfully verified task."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import datetime
from pathlib import Path

import tasks


def jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text().splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def timestamp(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def reviewed_tasks(root: Path) -> dict[str, dict]:
    result = {}
    for task in tasks.all_tasks(root):
        if task["meta"].get("status") != "done":
            continue
        if task["meta"].get("kind", "task") != "task":
            continue
        path = tasks.review_path(root, task["meta"]["id"])
        try:
            artifact = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if artifact.get("verdict") == "PASS" and artifact.get("task") == task["meta"]["id"]:
            result[task["meta"]["id"]] = artifact
    return result


def report_data(root: Path) -> dict:
    verified = reviewed_tasks(root)
    usage = jsonl(root / "metrics/usage-log.jsonl")
    mappings = jsonl(root / "metrics/session-tasks.jsonl")
    by_session: dict[str, list[dict]] = {}
    for item in mappings:
        if isinstance(item.get("session"), str) and isinstance(item.get("task"), str):
            by_session.setdefault(item["session"], []).append(item)
    for items in by_session.values():
        items.sort(key=lambda item: str(item.get("observed_at", "")))

    token_keys = ("input", "output", "reasoning", "cache_read", "cache_write")
    totals = {key: 0.0 for key in token_keys}
    cost = 0.0
    attributed_cost = 0.0
    calls = 0
    retries = 0
    verified_sessions: dict[str, str] = {}
    for row in usage:
        row_cost = float(row.get("cost") or 0)
        cost += row_cost
        for key in token_keys:
            totals[key] += float(row.get(key) or 0)
        calls += int(row.get("calls") or 0)
        retries += int(row.get("retries") or 0)
        session = row.get("session")
        observed = timestamp(row.get("observed_at", ""))
        candidates = [
            item
            for item in by_session.get(session, [])
            if observed is None
            or timestamp(item.get("observed_at", "")) is None
            or timestamp(item.get("observed_at", "")) <= observed
        ]
        task_id = candidates[-1]["task"] if candidates else ""
        if task_id in verified:
            attributed_cost += row_cost
            verified_sessions.setdefault(task_id, session)

    durations = []
    for task_id, session in verified_sessions.items():
        starts = [
            timestamp(item.get("observed_at", ""))
            for item in by_session.get(session, [])
            if item.get("task") == task_id
        ]
        start = next((value for value in starts if value is not None), None)
        end = timestamp(verified[task_id].get("recorded_at", ""))
        if start and end and end >= start:
            durations.append((end - start).total_seconds() / 60)
    return {
        "tasks_verified": len(verified),
        "tasks_measured": len(verified_sessions),
        "model_cost": round(cost, 6),
        "attributed_cost": round(attributed_cost, 6),
        "unattributed_cost": round(cost - attributed_cost, 6),
        "cost_per_verified_task": round(cost / len(verified), 6) if verified else None,
        "tokens": {key: int(value) for key, value in totals.items()},
        "model_calls": calls,
        "retries": retries,
        "median_minutes_to_verify": round(statistics.median(durations), 2)
        if durations
        else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(tasks.ROOT))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    data = report_data(root)
    if args.json:
        print(json.dumps(data, indent=2))
        return 0
    print(f"verified tasks: {data['tasks_verified']}")
    print(f"measured tasks: {data['tasks_measured']}")
    print(f"model cost: ${data['model_cost']:.6f}")
    cost = data["cost_per_verified_task"]
    print(f"cost per verified task: {'unavailable' if cost is None else f'${cost:.6f}'}")
    print(
        "tokens: "
        + ", ".join(f"{key}={value}" for key, value in data["tokens"].items())
    )
    print(f"model calls: {data['model_calls']}")
    print(f"retries: {data['retries']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
