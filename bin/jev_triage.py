# SPDX-License-Identifier: MIT
#!/usr/bin/env python3
"""Jev triage for /close: is there a durable lesson, and what kind?

Exit: 0 = durable, 2 = no durable lesson, 3 = config/API error,
4 = the free model is gone.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from jev_review import (  # noqa: E402
    DEFAULT_MODEL,
    DEFAULT_URL,
    explain_403,
    post,
    resolve_key,
)

KINDS = {
    "none": "No durable lesson; the task is routine.",
    "task": "A fact or step specific to this task.",
    "process": "A rule about how to work: review, testing, evidence, scope.",
    "design": "A UI or design preference.",
    "skill": "A repeatable procedure that should become a skill.",
}


def build_payload(state: str, model: str) -> dict:
    return {
        "model": model,
        "state": state,
        "questions": {
            "durable": {
                "type": "noul",
                "instructions": (
                    "Does this state contain a lesson that would change a future "
                    "decision or prevent a repeated mistake?"
                ),
            },
            "kind": {
                "type": "choice",
                "instructions": "What kind of lesson is it?",
                "criteria": KINDS,
            },
            "scope": {
                "type": "choice",
                "instructions": "Where should the lesson apply?",
                "criteria": {
                    "project": "Only this repository or project.",
                    "global": "Across projects.",
                },
            },
            "confidence": {
                "type": "score",
                "instructions": "How confident are you that this lesson is durable?",
                "criteria": ["Low", "Medium", "High"],
            },
        },
    }


def parse(data: dict) -> dict:
    answers = data.get("answers")
    if not isinstance(answers, dict):
        raise ValueError("response has no 'answers' object")
    durable = answers.get("durable", {}).get("noul")
    kind = answers.get("kind", {}).get("choice", "none")
    scope = answers.get("scope", {}).get("choice", "project")
    confidence = answers.get("confidence", {}).get("score")
    if durable is None:
        raise ValueError("response has no durable answer")
    return {
        "durable": float(durable) >= 0.6 and kind != "none",
        "probability": float(durable),
        "kind": kind,
        "scope": scope,
        "confidence": confidence,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True, help="file containing the compact task state")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--endpoint", default=DEFAULT_URL)
    parser.add_argument("--key-file")
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not args.model:
        print(
            "error: set JEV_MODEL or pass --model; the public client does not "
            "hardcode a rotating model",
            file=sys.stderr,
        )
        return 3

    state = Path(args.state).read_text().strip()
    if not state:
        print("error: empty state", file=sys.stderr)
        return 3
    if len(state) > 12000:
        state = state[:12000] + "\n\n[... state truncated ...]"

    key, _source = resolve_key(args.key_file)
    if not key:
        print(
            "error: no Jev key. Set OPENCODE_API_KEY, pass --key-file, or create "
            "~/.config/opencode/console.key (chmod 600).",
            file=sys.stderr,
        )
        return 3

    try:
        data = post(args.endpoint, key, build_payload(state, args.model), args.timeout)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:300]
        if exc.code in (400, 404) and args.model.endswith("-free"):
            print(
                f"FREE JEV GONE: '{args.model}' was rejected (HTTP {exc.code}). "
                "Update DEFAULT_MODEL in bin/jev_review.py to jev-1.13 (paid).",
                file=sys.stderr,
            )
            return 4
        if exc.code in (401, 403):
            print("error: " + explain_403(detail) + " Detail: " + detail, file=sys.stderr)
            return 3
        print(f"error: Jev HTTP {exc.code}: {detail}", file=sys.stderr)
        return 3
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"error: Jev unreachable: {exc}", file=sys.stderr)
        return 3

    try:
        result = parse(data)
    except ValueError as exc:
        print(f"error: unexpected Jev response: {exc}", file=sys.stderr)
        return 3

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"durable: {'yes' if result['durable'] else 'no'} ({result['probability']:.2f})")
        print(f"kind: {result['kind']}")
        print(f"scope: {result['scope']}")
        if result["confidence"] is not None:
            print(f"confidence: {float(result['confidence']):.2f}/2")
    return 0 if result["durable"] else 2


if __name__ == "__main__":
    sys.exit(main())
