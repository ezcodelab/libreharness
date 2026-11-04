#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Plan, and optionally run, one benchmark task repetition.

The default is a dry run. It prints the planned headless command and writes a
sample manifest, but it does not call a model, contact a provider, or touch a
fixture. A live run requires --live, --model, and --workspace, and prints a
cost warning first.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shlex
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TASKS = tuple(f"B{i}" for i in range(1, 9))
C_TASKS = ("B1", "B4", "B7", "B8")
TIME_LIMIT_MINUTES = 30
DEFAULT_MODEL = "provider/model"
PROMPT_MARKER = "## Prompt"
ARMS = {
    "plain": "A",
    "harness": "A",
    "pre-refactor": "B",
    "rc": "B",
    "harness-no-jev": "C",
    "harness-jev": "C",
}
JEV_ENABLED = {
    "plain": False,
    "harness": False,
    "pre-refactor": True,
    "rc": True,
    "harness-no-jev": False,
    "harness-jev": True,
}


def task_prompt(task_id: str) -> str:
    """Return the fenced prompt block from a task file."""
    path = ROOT / "tasks" / f"{task_id}.md"
    if not path.is_file():
        raise SystemExit(f"missing task file: bench/tasks/{task_id}.md")
    lines = path.read_text(encoding="utf-8").splitlines()
    marker = next((i for i, line in enumerate(lines) if line.strip() == PROMPT_MARKER), None)
    if marker is None:
        raise SystemExit(f"bench/tasks/{task_id}.md: missing {PROMPT_MARKER}")
    start = next((i for i in range(marker + 1, len(lines)) if lines[i].startswith("```")), None)
    if start is None:
        raise SystemExit(f"bench/tasks/{task_id}.md: missing fenced prompt")
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("```")), None)
    if end is None:
        raise SystemExit(f"bench/tasks/{task_id}.md: unterminated prompt fence")
    return "\n".join(lines[start + 1 : end]).strip() + "\n"


def manifest(args: argparse.Namespace, run_id: str) -> dict:
    comparison = ARMS[args.arm]
    jev = JEV_ENABLED[args.arm]
    return {
        "schema": 1,
        "status": "live" if args.live else ("dry-run" if args.dry_run else "plan"),
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "protocol": "bench/protocol.md",
        "environment": {
            "harness_commit": "fill before live run",
            "pre_refactor_commit": None if comparison != "B" else "fill before live run",
            "opencode_version": "fill before live run",
            "model_id": args.model,
            "provider": "fill before live run",
            "price_snapshot": {
                "currency": "USD",
                "input_per_million": None,
                "output_per_million": None,
                "cache_read_per_million": None,
                "cache_write_per_million": None,
            },
            "container_image_digest": "fill before live run",
            "seed": args.seed,
            "operator": "fill before live run",
            "token_cap": "fill before live run",
        },
        "jev": {
            "enabled": jev,
            "endpoint": None,
            "model": None,
            "prompt_hash": None,
            "threshold_profile": None,
            "transport": None,
        },
        "planned_run": {
            "run_id": run_id,
            "comparison": comparison,
            "arm": args.arm,
            "task_id": args.task,
            "repetition": args.repetition,
            "time_limit_minutes": TIME_LIMIT_MINUTES,
            "prompt_file": f"bench/tasks/{args.task}.md",
        },
        "deviations": [],
    }


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def as_text(value: str | bytes | None) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return value or ""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--task", choices=TASKS, default="B1", help="task id (default: B1)")
    parser.add_argument(
        "--arm", choices=sorted(ARMS), default="harness", help="benchmark arm (default: harness)"
    )
    parser.add_argument(
        "--repetition", type=int, choices=(1, 2, 3), default=1, help="repetition 1 to 3 (default: 1)"
    )
    parser.add_argument("--seed", type=int, default=0, help="randomization seed recorded in the manifest")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("bench/results/dry-run"),
        help="relative output directory (default: bench/results/dry-run)",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="provider/model for a live run")
    parser.add_argument("--workspace", type=Path, default=None, help="fresh fixture checkout for a live run")
    parser.add_argument("--dry-run", action="store_true", help="plan only, write a sample manifest, call no model")
    parser.add_argument(
        "--live", action="store_true", help="invoke OpenCode against a paid model provider (cost warning)"
    )
    args = parser.parse_args(argv)
    if args.dry_run and args.live:
        parser.error("--dry-run and --live are mutually exclusive")
    if args.out.is_absolute():
        parser.error("--out must be a relative path")
    if ARMS[args.arm] == "C" and args.task not in C_TASKS:
        parser.error(f"comparison C uses only {', '.join(C_TASKS)}")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    run_id = f"{args.task}-{args.arm}-r{args.repetition}"
    prompt = task_prompt(args.task)
    data = manifest(args, run_id)
    out = args.out
    if not args.live:
        data["planned_command"] = shlex.join(
            [
                "opencode",
                "run",
                "--format",
                "json",
                "--model",
                args.model,
                "--title",
                run_id,
                f"<prompt from bench/tasks/{args.task}.md>",
            ]
        )
        write_json(out / "manifest.json", data)
        print(f"status: {'dry run' if args.dry_run else 'plan only'}, no model called")
        print(f"run: {run_id} (comparison {data['planned_run']['comparison']}, repetition {args.repetition})")
        print("planned command:")
        print(f"  {data['planned_command']}")
        print(f"manifest sample: {out / 'manifest.json'}")
        print("live execution: add --live --model provider/model --workspace <fresh fixture checkout>")
        return 0

    if args.model == DEFAULT_MODEL:
        raise SystemExit("--live needs an explicit --model, not the placeholder")
    if args.workspace is None:
        raise SystemExit("--live needs --workspace pointing at a fresh fixture checkout")
    workspace = args.workspace.resolve()
    if not workspace.is_dir():
        raise SystemExit(f"workspace is not a directory: {args.workspace}")

    run_dir = out / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
    command = [
        "opencode",
        "run",
        "--format",
        "json",
        "--model",
        args.model,
        "--title",
        run_id,
        prompt,
    ]
    print(
        "WARNING: --live calls a paid model provider. This run is billed and may take "
        f"up to {TIME_LIMIT_MINUTES} minutes. Do not point it at a production checkout.",
        file=sys.stderr,
    )
    data["planned_run"]["command"] = shlex.join(command[:-1]) + " <prompt>"
    data["workspace"] = "external checkout"
    started = dt.datetime.now(dt.timezone.utc)
    clock = time.monotonic()
    timed_out = False
    try:
        result = subprocess.run(
            command,
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=TIME_LIMIT_MINUTES * 60 + 120,
            check=False,
        )
        stdout, stderr, returncode = result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired as error:
        timed_out = True
        stdout = as_text(error.stdout)
        stderr = as_text(error.stderr)
        returncode = None
    wall_seconds = round(time.monotonic() - clock, 3)
    (run_dir / "session.json").write_text(stdout, encoding="utf-8")
    (run_dir / "stderr.txt").write_text(stderr, encoding="utf-8")
    diff = subprocess.run(
        ["git", "-C", str(workspace), "diff", "--no-ext-diff"],
        capture_output=True,
        text=True,
        check=False,
    )
    (run_dir / "diff.patch").write_text(diff.stdout, encoding="utf-8")
    write_json(
        run_dir / "timing.json",
        {
            "started_at": started.isoformat(timespec="seconds"),
            "wall_seconds": wall_seconds,
            "timeout": timed_out,
            "returncode": returncode,
        },
    )
    data["result"] = {
        "run_id": run_id,
        "returncode": returncode,
        "timed_out": timed_out,
        "wall_seconds": wall_seconds,
        "run_dir": run_dir.as_posix(),
    }
    write_json(out / "manifest.json", data)
    print(f"run directory: {run_dir}")
    if timed_out:
        print("result: timeout, recorded as a failure")
        return 1
    print(f"result: exit code {returncode}")
    return 0 if returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
