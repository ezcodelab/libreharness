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
import random
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
ARM_NAME = re.compile(r"^[a-z0-9][a-z0-9-]*$")


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
    except OSError as error:
        raise SystemExit(f"cannot read {path}: {error}") from error
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


def parse_arm(value: str) -> tuple[str, Path]:
    name, separator, path = value.partition("=")
    name = name.strip()
    path = path.strip()
    if not separator or not name or not path:
        raise SystemExit(f"invalid --arm {value!r}; expected NAME=FEATURE_JSON")
    if not ARM_NAME.fullmatch(name):
        raise SystemExit(
            f"invalid arm name {name!r}; use lowercase letters, digits, and hyphens"
        )
    return name, Path(path)


def load_arms(args: argparse.Namespace) -> list[tuple[str, Path, dict]]:
    if args.arm:
        arms: list[tuple[str, Path, dict]] = []
        seen: set[str] = set()
        for value in args.arm:
            name, path = parse_arm(value)
            if name in seen:
                raise SystemExit(f"duplicate arm name: {name}")
            seen.add(name)
            arms.append((name, path, load_feature(path)))
        return arms
    return [
        ("baseline", args.baseline, load_feature(args.baseline)),
        ("candidate", args.candidate, load_feature(args.candidate)),
    ]


def load_defects(path: Path) -> list[dict]:
    data = load_json(path)
    if not isinstance(data, list):
        raise SystemExit(f"{path}: defects must be a list")
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


def finding_severity(finding: dict) -> str:
    severity = str(finding.get("severity", "")).strip().lower()
    return severity if severity in {"blocker", "major", "nit"} else "unknown"


def score_findings(findings: list[dict], defects: list[dict]) -> dict:
    matched: list[str] = []
    false_positives = 0
    false_blockers = 0
    false_majors = 0
    false_nits = 0
    false_unknown = 0
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
            severity = finding_severity(finding)
            if severity == "blocker":
                false_blockers += 1
            elif severity == "major":
                false_majors += 1
            elif severity == "nit":
                false_nits += 1
            else:
                false_unknown += 1
        elif hit in matched:
            duplicates += 1
        else:
            matched.append(hit)

    defect_severity: dict[str, int] = {"blocker": 0, "major": 0, "nit": 0}
    matched_severity: dict[str, int] = {"blocker": 0, "major": 0, "nit": 0}
    for defect in defects:
        severity = str(defect.get("severity", "")).strip().lower()
        if severity not in defect_severity:
            continue
        defect_severity[severity] += 1
        if defect["id"] in matched:
            matched_severity[severity] += 1

    true_positives = len(matched)
    denominator = true_positives + false_positives
    clean = not defects
    return {
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_blockers": false_blockers,
        "false_majors": false_majors,
        "false_nits": false_nits,
        "false_unknown": false_unknown,
        "duplicates": duplicates,
        "clean": clean,
        "recall": true_positives / len(defects) if defects else 0.0,
        "precision": (1.0 if false_positives == 0 else 0.0)
        if clean
        else (true_positives / denominator if denominator else 0.0),
        "recall_by_severity": {
            severity: matched_severity[severity] / total if total else None
            for severity, total in defect_severity.items()
        },
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


def assistant_text(text: str) -> str:
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
    return "\n".join(chunks) if chunks else text


def has_json_answer(text: str) -> bool:
    text = assistant_text(text)
    for block in re.findall(r"```(?:json)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE):
        try:
            parsed = json.loads(block.strip())
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, (list, dict)):
            return True
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end > start:
        try:
            parsed = json.loads(text[start : end + 1])
            return isinstance(parsed, (list, dict))
        except json.JSONDecodeError:
            pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            parsed = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return False
        return isinstance(parsed, dict) and "findings" in parsed
    return False


def extract_findings(text: str) -> list[dict]:
    text = assistant_text(text)
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
    start = text.find("{")
    end = text.rfind("}")
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


def planned_order(
    arms: list[tuple[str, Path, dict]], repetitions: int, seed: int
) -> list[tuple[str, int]]:
    order = [
        (name, repetition)
        for name, _path, _feature in arms
        for repetition in range(1, repetitions + 1)
    ]
    random.Random(seed).shuffle(order)
    return order


def manifest(
    *,
    status: str,
    model: str,
    fixture: Path,
    defects: Path,
    arms: list[tuple[str, Path, dict]],
    repetitions: int,
    timeout: int,
    seed: int,
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
        "seed": seed,
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


def _rate(value: float | None) -> str:
    return f"{value:.3f}" if value is not None else ""


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
        "false_blockers": scored["false_blockers"],
        "false_majors": scored["false_majors"],
        "false_nits": scored["false_nits"],
        "duplicates": scored["duplicates"],
        "clean": scored["clean"],
        "recall": f"{scored['recall']:.3f}",
        "precision": f"{scored['precision']:.3f}",
        "recall_blockers": _rate(scored["recall_by_severity"]["blocker"]),
        "recall_majors": _rate(scored["recall_by_severity"]["major"]),
        "recall_nits": _rate(scored["recall_by_severity"]["nit"]),
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
        "--standalone",
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
            # Keep the host's OpenCode auth store, but not its plugins, global
            # AGENTS.md, agents, commands, or skills. Without this, the host
            # auto-intake plugin turns the review prompt into a LibreHarness
            # task and the benchmark measures the harness instead of the prompt.
            config_home = Path(workspace) / "config"
            state_home = Path(workspace) / "state"
            config_home.mkdir()
            state_home.mkdir()
            environment["XDG_CONFIG_HOME"] = str(config_home)
            environment["XDG_STATE_HOME"] = str(state_home)
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
    if not error and not findings and not has_json_answer(stdout):
        error = "no JSON findings"
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


def rescore_directory(out: Path, defects: list[dict]) -> int:
    runs_path = out / "runs.csv"
    if not runs_path.is_file():
        raise SystemExit(f"no runs.csv in {out}")
    with runs_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise SystemExit(f"no rows in {runs_path}")
    for row in rows:
        run_dir = out / "runs" / f"{row['arm']}-r{row['repetition']}"
        findings_path = run_dir / "findings.json"
        if not findings_path.is_file():
            raise SystemExit(f"missing {findings_path}")
        findings = load_json(findings_path)
        if not isinstance(findings, list):
            raise SystemExit(f"{findings_path}: expected a findings list")
        scored = score_findings(findings, defects)
        row["findings"] = len(findings)
        row["true_positives"] = scored["true_positives"]
        row["false_positives"] = scored["false_positives"]
        row["false_blockers"] = scored["false_blockers"]
        row["false_majors"] = scored["false_majors"]
        row["false_nits"] = scored["false_nits"]
        row["duplicates"] = scored["duplicates"]
        row["recall"] = f"{scored['recall']:.3f}"
        row["precision"] = f"{scored['precision']:.3f}"
        row["recall_blockers"] = _rate(scored["recall_by_severity"]["blocker"])
        row["recall_majors"] = _rate(scored["recall_by_severity"]["major"])
        row["recall_nits"] = _rate(scored["recall_by_severity"]["nit"])
    output = out / "runs-rescored.csv"
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print_summary(rows)
    print(f"rescored: {output}")
    return 0


def print_summary(rows: list[dict]) -> None:
    if not rows:
        print("no rows")
        return
    print("| Arm | Feature | n | Errors | Recall | Precision | False blockers | Tokens (total) | Cost USD (total) | Wall s (mean) |")
    print("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    arms = sorted({row["arm"] for row in rows})
    for arm in arms:
        items = [row for row in rows if row["arm"] == arm]
        errors = sum(1 for row in items if row["error"])
        scored = [row for row in items if not row["error"]]
        if scored:
            clean = all(row.get("clean", False) for row in scored)
            recall = (
                "n/a"
                if clean
                else f"{statistics.mean(float(row['recall']) for row in scored):.0%}"
            )
            precision = f"{statistics.mean(float(row['precision']) for row in scored):.0%}"
            false_blockers = f"{statistics.mean(int(row['false_blockers']) for row in scored):.2f}"
            tokens = str(sum(int(row["input_tokens"]) + int(row["output_tokens"]) for row in scored))
            cost = f"${sum(float(row['cost_usd']) for row in scored):.4f}"
            wall = f"{statistics.mean(float(row['wall_seconds']) for row in scored):.1f}"
        else:
            recall = precision = false_blockers = tokens = cost = wall = "n/a"
        print(
            f"| {arm} | {items[0]['label']} | {len(items)} | {errors} | {recall} | "
            f"{precision} | {false_blockers} | {tokens} | {cost} | {wall} |"
        )

    print("\nPer-run results:")
    print("| Arm | Rep | Order | Recall | Precision | False blockers | Tokens | Cost USD | Wall s | Error |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|---|")
    for row in sorted(rows, key=lambda item: (item["arm"], int(item["repetition"]))):
        tokens = int(row["input_tokens"]) + int(row["output_tokens"])
        recall = "n/a" if row.get("clean") else f"{float(row['recall']):.0%}"
        print(
            f"| {row['arm']} | {row['repetition']} | {row.get('sequence', '')} | "
            f"{recall} | {float(row['precision']):.0%} | "
            f"{row['false_blockers']} | {tokens} | ${float(row['cost_usd']):.4f} | "
            f"{float(row['wall_seconds']):.1f} | {row['error']} |"
        )

    print("\nSpread (min-max):")
    print("| Arm | Recall | Precision | Wall s |")
    print("|---|---|---|---|")
    for arm in arms:
        items = [row for row in rows if row["arm"] == arm and not row["error"]]
        if not items:
            print(f"| {arm} | n/a | n/a | n/a |")
            continue
        recalls = [float(row["recall"]) for row in items]
        precisions = [float(row["precision"]) for row in items]
        walls = [float(row["wall_seconds"]) for row in items]
        recall_text = (
            "n/a"
            if all(row.get("clean", False) for row in items)
            else f"{min(recalls):.0%}-{max(recalls):.0%}"
        )
        print(
            f"| {arm} | {recall_text} | "
            f"{min(precisions):.0%}-{max(precisions):.0%} | "
            f"{min(walls):.1f}-{max(walls):.1f} |"
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="plan only; call no model")
    mode.add_argument("--self-check", action="store_true", help="score the sample findings; call no model")
    mode.add_argument("--rescore", action="store_true", help="rescore a saved run directory; call no model")
    mode.add_argument("--live", action="store_true", help="invoke OpenCode against a paid provider")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="provider/model for a live run")
    parser.add_argument(
        "--arm",
        action="append",
        metavar="NAME=FEATURE_JSON",
        help="repeatable named arm; overrides --baseline and --candidate",
    )
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE, help="baseline feature JSON")
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE, help="candidate feature JSON")
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE, help="seeded design spec")
    parser.add_argument("--defects", type=Path, default=DEFAULT_DEFECTS, help="seeded defect list")
    parser.add_argument("--findings", type=Path, default=DEFAULT_FINDINGS, help="sample findings for --self-check")
    parser.add_argument("--repetitions", type=int, choices=(1, 2, 3), default=1)
    parser.add_argument("--seed", type=int, default=0, help="randomize arm order with this seed")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="per-run timeout in seconds")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("bench/results/ablation-dry-run"),
        help="relative output directory (default: bench/results/ablation-dry-run)",
    )
    args = parser.parse_args(argv)
    if args.out.is_absolute() and not args.rescore:
        parser.error("--out must be a relative path")
    if not (args.dry_run or args.self_check or args.rescore or args.live):
        args.dry_run = True
    if args.live and args.model == DEFAULT_MODEL:
        parser.error("--live needs an explicit --model, not the placeholder")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    defects = load_defects(args.defects)

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
        print(f"false_blockers: {scored['false_blockers']}")
        print(f"false_majors: {scored['false_majors']}")
        print(f"false_nits: {scored['false_nits']}")
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

    if args.rescore:
        return rescore_directory(args.out, defects)

    try:
        spec = args.fixture.read_text(encoding="utf-8")
    except OSError as error:
        raise SystemExit(f"cannot read {args.fixture}: {error}") from error
    arms = load_arms(args)
    order = planned_order(arms, args.repetitions, args.seed)
    data = manifest(
        status="live" if args.live else "dry-run",
        model=args.model,
        fixture=args.fixture,
        defects=args.defects,
        arms=arms,
        repetitions=args.repetitions,
        timeout=args.timeout,
        seed=args.seed,
    )
    data["run_order"] = [f"{name}-r{repetition}" for name, repetition in order]
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
    features = {name: feature for name, _path, feature in arms}
    rows: list[dict] = []
    for sequence, (name, repetition) in enumerate(order, start=1):
        print(
            f"WARNING: --live calls a paid model provider. "
            f"Running {name} repetition {repetition} (order {sequence}).",
            file=sys.stderr,
        )
        row = run_arm(
            arm=name,
            feature=features[name],
            spec=spec,
            defects=defects,
            model=args.model,
            repetition=repetition,
            timeout=args.timeout,
            out=out,
        )
        row["sequence"] = sequence
        rows.append(row)
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
