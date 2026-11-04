# SPDX-License-Identifier: MIT
#!/usr/bin/env python3
"""Advisory Jev critique of a goal decomposition.

Reads a goal task and its child tasks from the work queue, asks whether the
plan is complete/testable, and prints a recommendation. It never edits the
plan and never blocks execution; the operator or agent decides.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tasks  # noqa: E402
from jev_review import (  # noqa: E402
    DEFAULT_MODEL,
    DEFAULT_URL,
    explain_403,
    post,
    resolve_key,
    secret_shaped,
)

CHOICES = {
    "none": "No material gap.",
    "acceptance": "One or more children have no testable acceptance.",
    "dependency": "A dependency or ordering is missing or wrong.",
    "risk": "A one-way door, security boundary, or rollback gap is missing.",
    "scope": "A child is too large or two children overlap.",
    "ambiguous": "The goal itself is not clear enough to verify.",
}


def build_state(goal: dict, children: list[dict], max_chars: int = 12000) -> str:
    lines = [
        f"GOAL: {goal['meta'].get('id')} — {goal['meta'].get('title')}",
        f"SCOPE: {' '.join(goal['sections'].get('Scope', '').split())}",
        f"ACCEPTANCE: {' '.join(goal['sections'].get('Acceptance', '').split())}",
        "",
        "CHILDREN:",
    ]
    for child in children:
        meta = child["meta"]
        lines += [
            f"- {meta.get('id')} [{meta.get('status')}] {meta.get('title')}",
            f"  scope: {' '.join(child['sections'].get('Scope', '').split())}",
            f"  acceptance: {' '.join(child['sections'].get('Acceptance', '').split())}",
            f"  depends_on: {meta.get('depends_on', '') or 'none'}",
        ]
    state = "\n".join(lines).strip()
    if len(state) > max_chars:
        state = state[:max_chars] + "\n\n[... plan truncated ...]"
    return state


def build_payload(state: str, model: str) -> dict:
    return {
        "model": model,
        "state": state,
        "questions": {
            "complete": {
                "type": "noul",
                "instructions": (
                    "Does this child-task plan cover the stated goal and its "
                    "acceptance without a material omission?"
                ),
            },
            "testable": {
                "type": "noul",
                "instructions": (
                    "Does every child have an observable acceptance check, or a "
                    "documented [T] with a plan?"
                ),
            },
            "gap": {
                "type": "choice",
                "instructions": "What is the largest gap, if any?",
                "criteria": CHOICES,
            },
            "risk": {
                "type": "score",
                "instructions": "How risky is this plan to execute without a person?",
                "criteria": ["Low", "Medium", "High", "Unacceptable"],
            },
            "recommendation": {
                "type": "choice",
                "instructions": "What should happen before execution?",
                "criteria": {
                    "proceed": "Execute as written.",
                    "revise": "Fix the named gap first.",
                    "stop": "A person must decide or provide a missing fact.",
                },
            },
        },
    }


def number(value, default: float = 0.0) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def answer(answers: dict, name: str) -> dict:
    value = answers.get(name)
    return value if isinstance(value, dict) else {}


def parse(data: dict) -> dict:
    answers = data.get("answers")
    if not isinstance(answers, dict):
        raise ValueError("response has no 'answers' object")
    complete = number(answer(answers, "complete").get("noul"))
    testable = number(answer(answers, "testable").get("noul"))
    risk = number(answer(answers, "risk").get("score"))
    gap = answer(answers, "gap").get("choice", "none")
    recommendation = answer(answers, "recommendation").get("choice", "revise")
    if complete < 0.5 or testable < 0.5 or gap not in ("none",):
        recommendation = "stop" if recommendation == "stop" else "revise"
    if risk >= 3:
        recommendation = "stop"
    return {
        "complete": complete,
        "testable": testable,
        "risk": risk,
        "gap": gap,
        "recommendation": recommendation,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--goal", required=True, help="goal task id")
    parser.add_argument("--root", default=str(tasks.ROOT))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--endpoint", default=DEFAULT_URL)
    parser.add_argument("--key-file")
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--mock", choices=("good", "bad"))
    args = parser.parse_args()

    if not args.model:
        print(
            "error: set JEV_MODEL or pass --model; the public client does not "
            "hardcode a rotating model",
            file=sys.stderr,
        )
        return 3

    root = Path(args.root).resolve()
    goal = tasks.find_task(root, args.goal)
    if goal["meta"].get("kind") != "goal":
        print(f"error: {goal['meta'].get('id')} is not a goal", file=sys.stderr)
        return 3
    children = tasks.children_of(root, goal["meta"]["id"])
    if not children:
        print("error: goal has no child tasks", file=sys.stderr)
        return 3
    state = build_state(goal, children)
    if secret_shaped(state):
        print("error: plan state looks like it contains a secret or PII", file=sys.stderr)
        return 3

    payload = build_payload(state, args.model)
    if args.dry_run:
        print(json.dumps(payload, indent=2))
        return 0

    if args.mock:
        answers = {
            "complete": {"type": "noul", "noul": 0.9 if args.mock == "good" else 0.3},
            "testable": {"type": "noul", "noul": 0.9 if args.mock == "good" else 0.4},
            "gap": {"type": "choice", "choice": "none" if args.mock == "good" else "acceptance"},
            "risk": {"type": "score", "score": 1.0 if args.mock == "good" else 3.0},
            "recommendation": {
                "type": "choice",
                "choice": "proceed" if args.mock == "good" else "stop",
            },
        }
        data = {"answers": answers}
    else:
        key, _source = resolve_key(args.key_file)
        if not key:
            print(
                "error: no Jev key. Set OPENCODE_API_KEY, pass --key-file, or "
                "create ~/.config/opencode/jev.key (chmod 600).",
                file=sys.stderr,
            )
            return 3
        try:
            data = post(args.endpoint, key, payload, args.timeout)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:300]
            if exc.code in (400, 404) and args.model.endswith("-free"):
                print(
                    f"FREE JEV GONE: '{args.model}' was rejected (HTTP {exc.code}). "
                    "Update DEFAULT_MODEL in bin/jev_review.py to jev-1.13 (paid).",
                    file=sys.stderr,
                )
                return 4
            print(f"error: Jev {explain_403(detail)} Detail: {detail}", file=sys.stderr)
            return 3
        except (urllib.error.URLError, TimeoutError) as exc:
            print(f"error: Jev unavailable: {exc}", file=sys.stderr)
            return 3

    try:
        result = parse(data)
    except ValueError as exc:
        print(f"error: unexpected Jev response: {exc}", file=sys.stderr)
        return 3
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"complete: {result['complete']:.2f}")
        print(f"testable: {result['testable']:.2f}")
        print(f"risk: {result['risk']:.2f}")
        print(f"gap: {result['gap']}")
        print(f"recommendation: {result['recommendation']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
