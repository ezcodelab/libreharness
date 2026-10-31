#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run a fast review-feature ablation against one seeded design spec.

The default is a dry run. It writes a manifest and calls no model. A live run
requires --live and an explicit --model. A self-check scores a sample findings
file against the seeded defects without calling a model.

This is a feature-level supplement to the Harbor/Terminal-Bench headline. It
answers one question quickly: does adding a review step find more seeded
defects without an unacceptable false-positive or token cost?
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import re
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_FIXTURE = ROOT / "fixtures/ablation/spec.md"
DEFAULT_DEFECTS = ROOT / "fixtures/ablation/defects.json"
DEFAULT_BASELINE = ROOT / "features/ablation/baseline.json"
DEFAULT_CANDIDATE = ROOT / "features/ablation/comprehension.json"
DEFAULT_FINDINGS = ROOT / "fixtures/ablation/sample-findings.json"
DEFAULT_MODEL = "provider/model"
DEFAULT_TIMEOUT = 300


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def display_path(path: Path) -> str:
    """Keep repo paths relative so a published manifest has no home path."""
    try:
        return path.resolve().relative_to(ROOT.parent.resolve()).as_posix()
    except ValueError:
        return path.name


def load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise SystemExit(f"missing file: {path}") from error
    except json.JSONDecodeError as error:
        raise SystemExit(f"invalid JSON in {path}: {error}") from error


def load_feature(path: Path) -> dict:
    data = load_json(path)
    if not isinstance(data, dict):
        raise SystemExit(f"{path}: feature must be a JSON object")
    for key in ("label", "prompt"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise SystemExit(f"{path}: missing non-empty {key}")
    return data


def load_defects(path: Path) -> list[dict]:
    data = load_json(path)
    if not isinstance(data, list) or not data:
        raise SystemExit(f"{path}: defects must be a non-empty list")
    for index, defect in enumerate(data):
        if not isinstance(defect, dict):
            raise SystemExit(f"{path}: defect {index} must be an object")
        for key in ("id", "match"):
            if not isinstance(defect.get(key), str) or not defect[key].strip():
                raise SystemExit(f"{path}: defect {index} missing {key}")
        try:
            re.compile(defect["match"], re.IGNORECASE)
        except re.error as error:
            raise SystemExit(f"{path}: defect {index} bad regex: {error}") from error
    return data


def finding_text(finding: dict) -> str:
    return " ".join(
        str(finding.get(key, ""))
        for key in ("title", "issue", "description", "location", "severity")
    )


def score_findings(findings: list[dict], defects: list[dict]) -> dict:
    matched: list[str] = []
    false_positives = 0
    duplicates = 0
    for finding in findings:
        text = finding_text(finding)
        hit = None
        for defect in defects:
            if re.search(defect["match"], text, re.IGNORECASE):
                hit = defect["id"]
                break
        if hit is None:
            false_positives += 1
        elif hit in matched:
            duplicates += 1
        else:
            matched.append(hit)
    true_positives = len(matched)
    denominator = true_positives + false_positives
    return {
        "true_positives": true_positives,
        "false_positives": false_positives,
        "duplicates": duplicates,
        "recall": true_positives / len(defects) if defects else 0.0,
        "precision": true_positives / denominator if denominator else 0.0,
        "matched": matched,
        "missed": [d["id"] for d in defects if d["id"] not in matched],
    }


def _normalise_findings(value: object) -> list[dict]:
    if isinstance(value, dict):
        value = value.get("findings", [])
    if not isinstance(value, list):
        return []
    findings: list[dict] = []
    for item in value:
        if isinstance(item, dict):
            findings.append(item)
        elif isinstance(item, str) and item.strip():
            findings.append({"issue": item.strip()})
    return findings


def extract_findings(text: str) -> list[dict]:
    # OpenCode --format=json emits JSONL. Read the assistant text parts, not
    # the raw event stream: brackets in tool calls or event metadata are not
    # findings.
    chunks: list[str] = []
    for line in text.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict) or event.get("type") != "text":
            continue
        part = event.get("part") or {}
        if isinstance(part.get("text"), str):
            chunks.append(part["text"])
    if chunks:
        text = "\n".join(chunks)

    blocks = re.findall(r"```(?:json)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    for block in reversed(blocks):
        try:
            parsed = json.loads(block.strip())
        except json.JSONDecodeError:
            continue
        findings = _normalise_findings(parsed)
        if findings:
            return findings
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end > start:
        try:
            return _normalise_findings(json.loads(text[start : end + 1]))
        except json.JSONDecodeError:
            pass
    return []


def extract_usage(stdout: str) -> dict:
    usage = {
        "input_tokens": 0,
        "output_tokens": 0,
        "reasoning_tokens": 0,
        "cache_read_tokens": 0,
        "cache_write_tokens": 0,
        "cost_usd": 0.0,
    }
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") != "step_finish":
            continue
        part = event.get("part") or {}
        tokens = part.get("tokens") or {}
        cache = tokens.get("cache") or {}
        usage["input_tokens"] += int(tokens.get("input") or 0)
        reasoning = int(tokens.get("reasoning") or 0)
        usage["output_tokens"] += int(tokens.get("output") or 0) + reasoning
        usage["reasoning_tokens"] += reasoning
        usage["cache_read_tokens"] += int(cache.get("read") or 0)
        usage["cache_write_tokens"] += int(cache.get("write") or 0)
        usage["cost_usd"] += float(part.get("cost") or 0.0)
    return usage


def build_instruction(feature: dict, spec: str) -> str:
    return f"{feature['prompt'].strip()}\n\n---\n\n{spec.strip()}\n"


def planned_command(arm_name: str, model: str) -> str:
    return (
        f"opencode run --format=json --model {model} "
        f"--title ablation-{arm_name} -- <instruction>"
    )


def manifest(
    *,
    status: str,
    model: str,
    fixture: Path,
    defects: Path,
    arms: list[tuple[str, Path, dict]],
    repetitions: int,
    timeout: int,
) -> dict:
    return {
        "schema": 1,
        "status": status,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "fixture": display_path(fixture),
        "fixture_sha256": sha256(fixture),
        "defects": display_path(defects),
        "defects_sha256": sha256(defects),
        "defect_count": len(load_defects(defects)),
        "model": model,
        "timeout_seconds": timeout,
        "repetitions": repetitions,
        "workspace": "fresh temporary directory per run; no project instructions",
        "arms": [
            {
                "name": name,
                "feature": feature.get("feature", name),
                "label": feature["label"],
                "feature_file": display_path(path),
                "prompt_sha256": hashlib.sha256(
                    feature["prompt"].encode("utf-8")
                ).hexdigest(),
                "planned_command": planned_command(name, model),
            }
            for name, path, feature in arms
        ],
    }


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def arm_row(
    *,
    arm: str,
    feature: dict,
    model: str,
    repetition: int,
    findings: list[dict],
    usage: dict,
    wall_seconds: float,
    defects: list[dict],
    error: str = "",
) -> dict:
    scored = score_findings(findings, defects)
    return {
        "arm": arm,
        "feature": feature.get("feature", arm),
        "label": feature["label"],
        "model": model,
        "repetition": repetition,
        "findings": len(findings),
        "true_positives": scored["true_positives"],
        "false_positives": scored["false_positives"],
        "duplicates": scored["duplicates"],
        "recall": f"{scored['recall']:.3f}",
        "precision": f"{scored['precision']:.3f}",
        "input_tokens": usage["input_tokens"],
        "output_tokens": usage["output_tokens"],
        "reasoning_tokens": usage["reasoning_tokens"],
        "cache_read_tokens": usage["cache_read_tokens"],
        "cost_usd": f"{usage['cost_usd']:.6f}",
        "wall_seconds": f"{wall_seconds:.1f}",
        "error": error,
    }


def run_arm(
    *,
    arm: str,
    feature: dict,
    spec: str,
    defects: list[dict],
    model: str,
    repetition: int,
    timeout: int,
    out: Path,
) -> dict:
    instruction = build_instruction(feature, spec)
    run_dir = out / "runs" / f"{arm}-r{repetition}"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "prompt.txt").write_text(instruction, encoding="utf-8")
    command = [
        "opencode",
        "run",
        "--format=json",
        "--model",
        model,
        "--title",
        f"ablation-{arm}-r{repetition}",
        "--",
        instruction,
    ]
    environment = dict(os.environ)
    environment.setdefault("OPENCODE_FAKE_VCS", "git")
    started = dt.datetime.now(dt.timezone.utc)
    clock = time.monotonic()
    error = ""
    stdout = ""
    stderr = ""
    try:
        with tempfile.TemporaryDirectory(prefix="libreharness-ablation-") as workspace:
            result = subprocess.run(
                command,
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
                env=environment,
            )
        stdout = result.stdout
        stderr = result.stderr
        if result.returncode != 0:
            error = f"exit {result.returncode}"
    except subprocess.TimeoutExpired as exc:
        error = "timeout"
        stdout = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
    wall_seconds = time.monotonic() - clock
    (run_dir / "stderr.txt").write_text(stderr, encoding="utf-8")
    (run_dir / "session.json").write_text(stdout, encoding="utf-8")
    # A failed or timed-out run is not a negative review result. Do not score
    # a partial stream as if it were a complete answer.
    findings = [] if error else extract_findings(stdout)
    usage = extract_usage(stdout)
    (run_dir / "findings.json").write_text(
        json.dumps(findings, indent=2) + "\n", encoding="utf-8"
    )
    row = arm_row(
        arm=arm,
        feature=feature,
        model=model,
        repetition=repetition,
        findings=findings,
        usage=usage,
        wall_seconds=wall_seconds,
        defects=defects,
        error=error,
    )
    row["started_at"] = started.isoformat(timespec="seconds")
    return row


def print_summary(rows: list[dict]) -> None:
    if not rows:
        print("no rows")
        return
    print("| Arm | Feature | n | Errors | Recall | Precision | Tokens | Cost USD | Wall s |")
    print("|---|---|---:|---:|---:|---:|---:|---:|---:|")
    arms = sorted({row["arm"] for row in rows})
    for arm in arms:
        items = [row for row in rows if row["arm"] == arm]
        errors = sum(1 for row in items if row["error"])
        recall = statistics.mean(float(row["recall"]) for row in items)
        precision = statistics.mean(float(row["precision"]) for row in items)
        tokens = sum(int(row["input_tokens"]) + int(row["output_tokens"]) for row in items)
        cost = sum(float(row["cost_usd"]) for row in items)
        wall = statistics.mean(float(row["wall_seconds"]) for row in items)
        print(
            f"| {arm} | {items[0]['label']} | {len(items)} | {errors} | {recall:.0%} | "
            f"{precision:.0%} | {tokens} | ${cost:.4f} | {wall:.1f} |"
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="plan only; call no model")
    mode.add_argument("--self-check", action="store_true", help="score the sample findings; call no model")
    mode.add_argument("--live", action="store_true", help="invoke OpenCode against a paid provider")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="provider/model for a live run")
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE, help="baseline feature JSON")
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE, help="candidate feature JSON")
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE, help="seeded design spec")
    parser.add_argument("--defects", type=Path, default=DEFAULT_DEFECTS, help="seeded defect list")
    parser.add_argument("--findings", type=Path, default=DEFAULT_FINDINGS, help="sample findings for --self-check")
    parser.add_argument("--repetitions", type=int, choices=(1, 2, 3), default=1)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="per-run timeout in seconds")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("bench/results/ablation-dry-run"),
        help="relative output directory (default: bench/results/ablation-dry-run)",
    )
    args = parser.parse_args(argv)
    if args.out.is_absolute():
        parser.error("--out must be a relative path")
    if not (args.dry_run or args.self_check or args.live):
        args.dry_run = True
    if args.live and args.model == DEFAULT_MODEL:
        parser.error("--live needs an explicit --model, not the placeholder")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    spec = args.fixture.read_text(encoding="utf-8")
    defects = load_defects(args.defects)
    baseline = load_feature(args.baseline)
    candidate = load_feature(args.candidate)
    arms = [
        ("baseline", args.baseline, baseline),
        ("candidate", args.candidate, candidate),
    ]

    if args.self_check:
        sample = load_json(args.findings)
        if not isinstance(sample, dict) or not isinstance(sample.get("findings"), list):
            raise SystemExit(f"{args.findings}: expected an object with a findings list")
        scored = score_findings(sample["findings"], defects)
        tokens = int(sample.get("input_tokens", 0)) + int(sample.get("output_tokens", 0))
        print(f"recall: {scored['recall']:.0%}")
        print(f"precision: {scored['precision']:.0%}")
        print(f"true_positives: {scored['true_positives']}")
        print(f"false_positives: {scored['false_positives']}")
        print(f"tokens: {tokens}")
        print(f"wall_seconds: {float(sample.get('wall_seconds', 0)):.1f}")
        expected = sample.get("expected")
        if isinstance(expected, dict):
            actual = {
                "recall": round(scored["recall"], 3),
                "precision": round(scored["precision"], 3),
                "true_positives": scored["true_positives"],
                "false_positives": scored["false_positives"],
            }
            for key, value in expected.items():
                if actual.get(key) != value:
                    print(f"self-check mismatch: {key} expected {value!r}, got {actual.get(key)!r}")
                    return 1
        return 0

    data = manifest(
        status="live" if args.live else "dry-run",
        model=args.model,
        fixture=args.fixture,
        defects=args.defects,
        arms=arms,
        repetitions=args.repetitions,
        timeout=args.timeout,
    )
    out = args.out
    if not args.live:
        write_json(out / "manifest.json", data)
        print("status: dry run, no model called")
        print(f"fixture: {args.fixture} ({data['fixture_sha256'][:12]})")
        print(f"defects: {data['defect_count']}")
        for name, _path, feature in arms:
            print(f"arm {name}: {feature['label']} ({feature.get('feature', name)})")
        print(f"manifest: {out / 'manifest.json'}")
        print("live execution: add --live --model provider/model --out bench/results/<name>")
        return 0

    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "manifest.json", data)
    rows: list[dict] = []
    for name, _path, feature in arms:
        for repetition in range(1, args.repetitions + 1):
            print(
                f"WARNING: --live calls a paid model provider. "
                f"Running {name} repetition {repetition}.",
                file=sys.stderr,
            )
            rows.append(
                run_arm(
                    arm=name,
                    feature=feature,
                    spec=spec,
                    defects=defects,
                    model=args.model,
                    repetition=repetition,
                    timeout=args.timeout,
                    out=out,
                )
            )
    fieldnames = list(rows[0].keys())
    with (out / "runs.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print_summary(rows)
    print(f"results: {out}")
    failed = [row for row in rows if row["error"]]
    if failed:
        for row in failed:
            print(
                f"failed: {row['arm']} repetition {row['repetition']}: {row['error']}",
                file=sys.stderr,
            )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
