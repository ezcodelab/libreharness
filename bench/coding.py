#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run a fixed Terminal-Bench coding suite across harness arms.

The default is a dry run. A live run invokes Harbor once per arm and records
per-trial reward, exception, tokens, cost, wall time, and a test-first heuristic
from the agent log. This is a coding benchmark pilot, not a public claim.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import random
import re
import statistics
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_SUITE = ROOT / "coding-suite.json"
DEFAULT_OUT = Path("bench/results/coding-pilot")
DEFAULT_MODEL = "provider/model"
DEFAULT_TIMEOUT = 3600
TEST_PATH = re.compile(r"(^|/)(tests?|specs?)(/|$)|(_test|\.test|\.spec)\.", re.IGNORECASE)
SOURCE_SUFFIXES = {
    ".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".go", ".rs",
    ".c", ".h", ".cc", ".cpp", ".java", ".rb", ".sh",
}


def load_suite(path: Path) -> dict:
    try:
        suite = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise SystemExit(f"cannot read {path}: {error}") from error
    except json.JSONDecodeError as error:
        raise SystemExit(f"invalid JSON in {path}: {error}") from error
    for key in ("dataset", "tasks", "arms", "model"):
        if key not in suite:
            raise SystemExit(f"{path}: missing {key}")
    if not isinstance(suite["tasks"], list) or not suite["tasks"]:
        raise SystemExit(f"{path}: tasks must be a non-empty list")
    if not isinstance(suite["arms"], list) or not suite["arms"]:
        raise SystemExit(f"{path}: arms must be a non-empty list")
    names = set()
    for arm in suite["arms"]:
        if not isinstance(arm, dict) or not arm.get("name") or not arm.get("agent"):
            raise SystemExit(f"{path}: each arm needs name and agent")
        if arm["name"] in names:
            raise SystemExit(f"{path}: duplicate arm {arm['name']}")
        names.add(arm["name"])
    return suite


def planned_order(arms: list[dict], repetitions: int, seed: int) -> list[tuple[str, int]]:
    order = [
        (arm["name"], repetition)
        for arm in arms
        for repetition in range(1, repetitions + 1)
    ]
    random.Random(seed).shuffle(order)
    return order


def planned_command(
    suite: dict,
    arm: dict,
    model: str,
    run_out: Path,
    n_concurrent: int,
) -> list[str]:
    command = [
        "harbor",
        "run",
        "-d",
        suite["dataset"],
        "-a",
        arm["agent"],
        "-m",
        model,
        "--base-url",
        suite.get("base_url", ""),
        "--api-key-name",
        suite.get("api_key_name", "OLLAMA_API_KEY"),
        "--api-format",
        suite.get("api_format", "openai_chat_completions"),
        "--ak",
        f"version={suite.get('opencode_version', '1.19.5')}",
    ]
    if arm.get("profile"):
        command += ["--ak", f"profile={arm['profile']}"]
    for task in suite["tasks"]:
        command += ["-i", task]
    command += ["-k", "1", "-n", str(n_concurrent), "-o", str(run_out)]
    return command


def seconds_between(start: str | None, end: str | None) -> float:
    if not start or not end:
        return 0.0
    try:
        first = dt.datetime.fromisoformat(start.replace("Z", "+00:00"))
        last = dt.datetime.fromisoformat(end.replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    return max(0.0, (last - first).total_seconds())


def input_path(tool_input: dict) -> list[str]:
    for key in ("filePath", "path", "file", "filename"):
        value = tool_input.get(key)
        if isinstance(value, str) and value.strip():
            return [value.strip()]
    patch = tool_input.get("patchText") or tool_input.get("patch")
    if isinstance(patch, str):
        return [
            match.strip()
            for match in re.findall(
                r"^\*\*\* (?:Add|Update|Delete) File: (.+)$", patch, re.MULTILINE
            )
        ]
    return []


def writes_from_log(path: Path) -> list[str]:
    if not path.is_file():
        return []
    writes: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict) or event.get("type") != "tool_use":
            continue
        part = event.get("part") or {}
        if part.get("tool") not in {"write", "edit", "patch", "apply_patch"}:
            continue
        state = part.get("state") or {}
        tool_input = state.get("input") or {}
        if isinstance(tool_input, dict):
            writes.extend(input_path(tool_input))
    return writes


def test_first_from_log(path: Path) -> dict:
    writes = writes_from_log(path)
    test_paths: list[str] = []
    source_paths: list[str] = []
    for write in writes:
        normalized = write.replace("\\", "/")
        if TEST_PATH.search(normalized):
            test_paths.append(normalized)
        elif Path(normalized).suffix.lower() in SOURCE_SUFFIXES:
            source_paths.append(normalized)
    first_test = next(
        (index for index, path in enumerate(writes) if TEST_PATH.search(path.replace("\\", "/"))),
        None,
    )
    first_source = next(
        (
            index
            for index, path in enumerate(writes)
            if Path(path.replace("\\", "/")).suffix.lower() in SOURCE_SUFFIXES
            and not TEST_PATH.search(path.replace("\\", "/"))
        ),
        None,
    )
    if first_test is None and first_source is None:
        status = "unknown"
    elif first_test is not None and (first_source is None or first_test < first_source):
        status = "1"
    else:
        status = "0"
    return {
        "test_first": status,
        "test_files_changed": len(set(test_paths)),
        "source_files_changed": len(set(source_paths)),
    }


def read_trial_results(run_out: Path) -> list[tuple[Path, dict]]:
    trials: list[tuple[Path, dict]] = []
    for result_path in run_out.rglob("result.json"):
        try:
            data = json.loads(result_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict) and data.get("task_name"):
            trials.append((result_path, data))
    return trials


def trial_row(
    *,
    arm: dict,
    task: str,
    repetition: int,
    sequence: int,
    trial_dir: Path,
    data: dict,
) -> dict:
    verifier = data.get("verifier_result") or {}
    rewards = verifier.get("rewards") or {}
    reward = rewards.get("reward") if isinstance(rewards, dict) else rewards
    agent = data.get("agent_result") or {}
    execution = data.get("agent_execution") or {}
    exception = (data.get("exception_info") or {}).get("exception_type") or ""
    test_info = test_first_from_log(trial_dir / "agent" / "opencode.txt")
    return {
        "arm": arm["name"],
        "profile": arm.get("profile") or "",
        "task": task,
        "repetition": repetition,
        "sequence": sequence,
        "reward": "" if reward is None else reward,
        "exception": exception,
        "cost_usd": agent.get("cost_usd", 0.0) or 0.0,
        "input_tokens": agent.get("n_input_tokens", 0) or 0,
        "output_tokens": agent.get("n_output_tokens", 0) or 0,
        "cache_tokens": agent.get("n_cache_tokens", 0) or 0,
        "wall_seconds": round(
            seconds_between(execution.get("started_at"), execution.get("finished_at")), 1
        ),
        **test_info,
        "error": "",
    }


def run_arm(
    *,
    suite: dict,
    arm: dict,
    model: str,
    repetition: int,
    sequence: int,
    out: Path,
    timeout: int,
    n_concurrent: int,
) -> list[dict]:
    run_out = (out / f"{arm['name']}-r{repetition}").resolve()
    run_out.mkdir(parents=True, exist_ok=True)
    command = planned_command(suite, arm, model, run_out, n_concurrent)
    env = dict(os.environ)
    # Harbor imports a custom agent from the repository root, one level above
    # bench/. Pointing at bench/ makes every LibreHarness arm fail to import.
    env["PYTHONPATH"] = str(ROOT.parent) + (
        os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""
    )
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=env,
        )
        (run_out / "harbor.stdout.txt").write_text(result.stdout, encoding="utf-8")
        (run_out / "harbor.stderr.txt").write_text(result.stderr, encoding="utf-8")
        run_error = "" if result.returncode == 0 else f"harbor exit {result.returncode}"
    except subprocess.TimeoutExpired:
        run_error = "harbor timeout"
    except OSError as error:
        run_error = f"harbor failed: {error}"

    trials = read_trial_results(run_out)
    rows: list[dict] = []
    seen: set[str] = set()
    for result_path, data in trials:
        task = str(data["task_name"])
        seen.add(task)
        rows.append(
            trial_row(
                arm=arm,
                task=task,
                repetition=repetition,
                sequence=sequence,
                trial_dir=result_path.parent,
                data=data,
            )
        )
    for task in suite["tasks"]:
        if task not in seen:
            rows.append(
                {
                    "arm": arm["name"],
                    "profile": arm.get("profile") or "",
                    "task": task,
                    "repetition": repetition,
                    "sequence": sequence,
                    "reward": "",
                    "exception": "",
                    "cost_usd": 0.0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cache_tokens": 0,
                    "wall_seconds": 0.0,
                    "test_first": "unknown",
                    "test_files_changed": 0,
                    "source_files_changed": 0,
                    "error": run_error or "missing trial result",
                }
            )
    if run_error:
        for row in rows:
            row["error"] = row["error"] or run_error
    return rows


def solved(row: dict) -> int:
    try:
        return 1 if float(row["reward"]) >= 1.0 else 0
    except (TypeError, ValueError):
        return 0


def print_summary(rows: list[dict], tasks: list[str]) -> None:
    if not rows:
        print("no rows")
        return
    print("| Arm | Trials | Solved | Exceptions | Cost USD | Tokens | Wall s | Test-first | Test files |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for arm in sorted({row["arm"] for row in rows}):
        items = [row for row in rows if row["arm"] == arm]
        first = [row for row in items if row["test_first"] in {"0", "1"}]
        first_rate = (
            f"{sum(row['test_first'] == '1' for row in first) / len(first):.0%}"
            if first
            else "n/a"
        )
        print(
            f"| {arm} | {len(items)} | {sum(solved(row) for row in items)} | "
            f"{sum(bool(row['exception']) for row in items)} | "
            f"${sum(float(row['cost_usd']) for row in items):.4f} | "
            f"{sum(int(row['input_tokens']) + int(row['output_tokens']) for row in items)} | "
            f"{statistics.mean(float(row['wall_seconds']) for row in items):.1f} | "
            f"{first_rate} | "
            f"{sum(int(row['test_files_changed']) for row in items)} |"
        )
    print("\nPer-task:")
    print("| Arm | Task | Reward | Exception | Cost USD | Tokens | Wall s | Test-first | Test files | Error |")
    print("|---|---|---:|---|---:|---:|---:|---|---:|---|")
    for row in rows:
        print(
            f"| {row['arm']} | {row['task']} | {row['reward'] or 'n/a'} | "
            f"{row['exception'] or '-'} | ${float(row['cost_usd']):.4f} | "
            f"{int(row['input_tokens']) + int(row['output_tokens'])} | "
            f"{float(row['wall_seconds']):.1f} | {row['test_first']} | "
            f"{row['test_files_changed']} | {row['error']} |"
        )


def manifest(
    suite: dict,
    model: str,
    out: Path,
    seed: int,
    repetitions: int,
    order: list[tuple[str, int]],
    n_concurrent: int,
) -> dict:
    by_name = {arm["name"]: arm for arm in suite["arms"]}
    arms = []
    for arm in suite["arms"]:
        command = planned_command(
            suite,
            arm,
            model,
            (out / f"{arm['name']}-r1").resolve(),
            n_concurrent,
        )
        planned = " ".join(command).replace(str(out.resolve()), "<out>")
        arms.append(
            {
                "name": arm["name"],
                "label": arm.get("label", arm["name"]),
                "agent": arm["agent"],
                "profile": arm.get("profile"),
                "planned_command": planned,
            }
        )
    return {
        "schema": 1,
        "status": "dry-run",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "suite": suite.get("name", DEFAULT_SUITE.stem),
        "dataset": suite["dataset"],
        "tasks": suite["tasks"],
        "arms": arms,
        "model": model,
        "opencode_version": suite.get("opencode_version", "1.19.5"),
        "harbor_version": suite.get("harbor_version", "0.25.0"),
        "base_url": suite.get("base_url", ""),
        "api_format": suite.get("api_format", "openai_chat_completions"),
        "seed": seed,
        "repetitions": repetitions,
        "n_concurrent": n_concurrent,
        "run_order": [f"{name}-r{rep}" for name, rep in order],
        "planned_arms": [by_name[name]["name"] for name, _rep in order],
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="plan only; call no model")
    mode.add_argument("--live", action="store_true", help="run Harbor against a paid provider")
    parser.add_argument("--suite", type=Path, default=DEFAULT_SUITE, help="suite JSON")
    parser.add_argument("--model", default=None, help="provider/model; defaults to the suite")
    parser.add_argument("--repetitions", type=int, choices=(1, 2, 3), default=1)
    parser.add_argument("--seed", type=int, default=0, help="randomize arm order")
    parser.add_argument("--n-concurrent", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="per-arm timeout seconds")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="relative output directory")
    args = parser.parse_args(argv)
    if not args.dry_run and not args.live:
        args.dry_run = True
    if args.out.is_absolute():
        parser.error("--out must be a relative path")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    suite = load_suite(args.suite)
    model = args.model or suite["model"]
    if args.live and model == DEFAULT_MODEL:
        raise SystemExit("--live needs a concrete model, not the placeholder")
    order = planned_order(suite["arms"], args.repetitions, args.seed)
    data = manifest(suite, model, args.out, args.seed, args.repetitions, order, args.n_concurrent)
    if not args.live:
        data["status"] = "dry-run"
        (args.out / "manifest.json").parent.mkdir(parents=True, exist_ok=True)
        (args.out / "manifest.json").write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8"
        )
        print("status: dry run, no model called")
        print(f"suite: {data['suite']} ({len(data['tasks'])} tasks, {len(data['arms'])} arms)")
        print(f"tasks: {', '.join(data['tasks'])}")
        print(f"run order: {', '.join(data['run_order'])}")
        print(f"manifest: {args.out / 'manifest.json'}")
        print("live execution: add --live")
        return 0

    args.out.mkdir(parents=True, exist_ok=True)
    data["status"] = "live"
    (args.out / "manifest.json").write_text(
        json.dumps(data, indent=2) + "\n", encoding="utf-8"
    )
    by_name = {arm["name"]: arm for arm in suite["arms"]}
    rows: list[dict] = []
    for sequence, (name, repetition) in enumerate(order, start=1):
        print(
            f"WARNING: --live runs Harbor against a paid provider. "
            f"{name} repetition {repetition} (order {sequence}).",
            file=sys.stderr,
        )
        rows.extend(
            run_arm(
                suite=suite,
                arm=by_name[name],
                model=model,
                repetition=repetition,
                sequence=sequence,
                out=args.out,
                timeout=args.timeout,
                n_concurrent=args.n_concurrent,
            )
        )
    with (args.out / "runs.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print_summary(rows, suite["tasks"])
    print(f"results: {args.out}")
    noisy = [row for row in rows if row["exception"] and solved(row)]
    if noisy:
        print(
            f"note: {len(noisy)} solved trial(s) also recorded an agent exception; "
            "the verifier reward is kept and the exception is shown in the table.",
            file=sys.stderr,
        )
    failed = [
        row for row in rows if row["error"] or (row["exception"] and not solved(row))
    ]
    if failed:
        for row in failed[:10]:
            print(
                f"failed: {row['arm']} {row['task']} r{row['repetition']}: "
                f"{row['error'] or row['exception']}",
                file=sys.stderr,
            )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
