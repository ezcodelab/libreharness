# SPDX-License-Identifier: MIT
#!/usr/bin/env python3
"""Offline Jev shadow routing for fixed playbook and model-tier choices."""

from __future__ import annotations

import argparse
import json
import os
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
    secret_shaped,
)

TIERS = {
    "hold": "Keep the current session model.",
    "workhorse": "Routine implementation or exploration on the cheap workhorse.",
    "planner": "Architecture, ambiguous scope, or hard judgment on the planner.",
    "challenger": "An explicit second opinion from the strong challenger.",
}


def playbook_ids() -> tuple[str, ...]:
    home = Path(
        os.environ.get("HARNESS_HOME", Path.home() / ".config/opencode")
    ).expanduser()
    directory = home / "skills/engineering-loop/references/playbooks"
    try:
        names = tuple(
            sorted(path.stem for path in directory.glob("*.md") if path.is_file())
        )
    except OSError:
        return ()
    return names


def fallback(playbook: str, tier: str, reason: str) -> dict:
    return {
        "source": "deterministic",
        "playbook": playbook,
        "tier": tier,
        "confidence": 0.0,
        "fallback_reason": reason,
    }


def parse(data: dict, playbooks: tuple[str, ...], minimum: float) -> dict:
    answers = data.get("answers")
    if not isinstance(answers, dict):
        raise ValueError("response has no answers")
    playbook = answers.get("playbook", {})
    tier = answers.get("tier", {})
    if not isinstance(playbook, dict) or not isinstance(tier, dict):
        raise ValueError("response choices are malformed")
    selected_playbook = playbook.get("choice")
    selected_tier = tier.get("choice")
    if selected_playbook not in playbooks:
        raise ValueError("playbook choice is not in the fixed option set")
    if selected_tier not in TIERS:
        raise ValueError("tier choice is not in the fixed option set")
    confidences = [
        float(playbook.get("confidence") or 0),
        float(tier.get("confidence") or 0),
    ]
    confidence = min(confidences)
    if confidence < minimum:
        raise ValueError("choice confidence is below the threshold")
    return {
        "source": "jev",
        "playbook": selected_playbook,
        "tier": selected_tier,
        "confidence": round(confidence, 6),
    }


def build_payload(state: str, model: str, playbooks: tuple[str, ...]) -> dict:
    return {
        "model": model,
        "state": state,
        "questions": {
            "playbook": {
                "type": "choice",
                "instructions": "Which engineering playbook best fits this task?",
                "criteria": {name: name for name in playbooks},
            },
            "tier": {
                "type": "choice",
                "instructions": (
                    "Which model tier is sufficient? Choose hold when the task "
                    "needs the current model or the evidence is uncertain."
                ),
                "criteria": TIERS,
            },
        },
    }


def mock_answers(mode: str, playbooks: tuple[str, ...]) -> dict:
    if mode == "bad":
        return {
            "answers": {
                "playbook": {"choice": "invented", "confidence": 0.99},
                "tier": {"choice": "max", "confidence": 0.99},
            }
        }
    playbook = "bug-fix" if "bug-fix" in playbooks else playbooks[0]
    return {
        "answers": {
            "playbook": {"choice": playbook, "confidence": 0.91},
            "tier": {"choice": "workhorse", "confidence": 0.82},
        }
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True)
    parser.add_argument("--fallback-playbook", required=True)
    parser.add_argument("--fallback-tier", choices=tuple(TIERS), default="hold")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--endpoint", default=DEFAULT_URL)
    parser.add_argument("--key-file")
    parser.add_argument("--timeout", type=int, default=10)
    parser.add_argument("--min-confidence", type=float, default=0.7)
    parser.add_argument("--mock", choices=("good", "bad", "timeout"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    playbooks = playbook_ids()
    if args.fallback_playbook not in playbooks:
        print("error: fallback playbook is not in the registered set", file=sys.stderr)
        return 3
    try:
        state = Path(args.state).read_text().strip()
    except OSError as exc:
        print(json.dumps(fallback(args.fallback_playbook, args.fallback_tier, str(exc))))
        return 0
    if not state:
        print(json.dumps(fallback(args.fallback_playbook, args.fallback_tier, "empty state")))
        return 0
    if len(state) > 12000:
        state = state[:12000]
    if secret_shaped(state):
        print(
            json.dumps(
                fallback(
                    args.fallback_playbook,
                    args.fallback_tier,
                    "secret-shaped state",
                )
            )
        )
        return 0

    if not args.mock and not args.model:
        print(
            json.dumps(
                fallback(args.fallback_playbook, args.fallback_tier, "no model")
            )
        )
        return 0
    payload = build_payload(state, args.model or "mock", playbooks)
    if args.dry_run:
        print(json.dumps(payload, indent=2))
        return 0
    if args.mock == "timeout":
        print(
            json.dumps(
                fallback(
                    args.fallback_playbook,
                    args.fallback_tier,
                    "mock timeout",
                )
            )
        )
        return 0
    if args.mock:
        data = mock_answers(args.mock, playbooks)
    else:
        key, _source = resolve_key(args.key_file)
        if not key:
            print(
                json.dumps(
                    fallback(args.fallback_playbook, args.fallback_tier, "no key")
                )
            )
            return 0
        try:
            data = post(args.endpoint, key, payload, args.timeout)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:200]
            reason = explain_403(detail) if exc.code in (401, 403) else f"HTTP {exc.code}"
            print(
                json.dumps(
                    fallback(args.fallback_playbook, args.fallback_tier, reason)
                )
            )
            return 0
        except (urllib.error.URLError, TimeoutError) as exc:
            print(
                json.dumps(
                    fallback(args.fallback_playbook, args.fallback_tier, str(exc))
                )
            )
            return 0
    try:
        print(json.dumps(parse(data, playbooks, args.min_confidence)))
    except (TypeError, ValueError) as exc:
        print(
            json.dumps(
                fallback(args.fallback_playbook, args.fallback_tier, str(exc))
            )
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
