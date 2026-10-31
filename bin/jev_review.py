# SPDX-License-Identifier: MIT
#!/usr/bin/env python3
"""Advisory Jev review for a diff.

Sends one state (task + diff) and typed questions to a System One endpoint.
Prints scores and a verdict; never prints the API key.

Exit: 0 = pass, 2 = send back, 3 = config/API/secret-shaped input,
4 = the requested (free) model is gone.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_URL = os.environ.get(
    "JEV_ENDPOINT", "https://opencode.ai/inference/systemone/v1/systemone"
)
DEFAULT_MODELS_URL = os.environ.get(
    "JEV_MODELS_URL", "https://opencode.ai/inference/v1/models"
)
DEFAULT_MODEL = os.environ.get("JEV_MODEL", "")
# Cloudflare (error 1010) blocks Python-urllib's default signature; curl is
# the client the API docs use.
USER_AGENT = "curl/8.0"

AXES = (
    "performance",
    "size",
    "maintainability",
    "simplicity",
    "reliability",
    "scalability",
    "security",
)

LEVELS = [
    "Poor: a defect that blocks the change.",
    "Weak: would need rework before merge.",
    "Adequate: acceptable with minor notes.",
    "Good: solid, no material notes.",
    "Excellent: no notes.",
]

SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
]

KEY_PATHS = (Path.home() / ".config/opencode/jev.key",)


def secret_shaped(text: str) -> bool:
    return any(pattern.search(text) for pattern in SECRET_PATTERNS)


def resolve_key(explicit: str | None) -> tuple[str | None, str | None]:
    if explicit:
        p = Path(explicit).expanduser()
        if p.is_file():
            return p.read_text().strip(), str(p)
        return explicit, "--key"
    for env in ("JEV_API_KEY", "OPENCODE_API_KEY", "TYPESAFE_API_KEY"):
        value = os.environ.get(env)
        if value:
            return value, env
    key_file = os.environ.get("JEV_KEY_FILE")
    if key_file:
        p = Path(key_file).expanduser()
        if p.is_file():
            value = p.read_text().strip()
            if value:
                return value, str(p)
    for path in KEY_PATHS:
        if path.is_file():
            value = path.read_text().strip()
            if value:
                return value, str(path)
    return None, None


def build_payload(task: str, diff: str, model: str) -> dict:
    questions: dict[str, dict] = {}
    for axis in AXES:
        questions[axis] = {
            "type": "score",
            "instructions": (
                f"Judge the {axis} of this change on the five levels. "
                "Use the task and the diff; do not assume missing code."
            ),
            "criteria": LEVELS,
        }
    questions["ship"] = {
        "type": "noul",
        "instructions": (
            "Does this diff meet the definition of done without a material defect?"
        ),
    }
    questions["scope"] = {
        "type": "noul",
        "instructions": "Does the diff stay within the stated task and avoid scope creep?",
    }
    questions["tests"] = {
        "type": "noul",
        "instructions": (
            "Is there a test, a measured check, or a documented verification step "
            "for this change?"
        ),
    }
    questions["secret_leak"] = {
        "type": "noul",
        "instructions": (
            "Does the diff contain a secret, token, password, API key, private key, "
            "or PII in code, logs, or UI copy?"
        ),
    }
    state = (
        "TASK:\n"
        + task.strip()
        + "\n\nQUALITY AXES:\n"
        + "performance, size, maintainability, simplicity, reliability, "
        "scalability, security. A failure on any axis sends the change back.\n\n"
        + "DIFF:\n"
        + diff
    )
    return {"model": model, "state": state, "questions": questions}


def post(url: str, key: str, payload: dict, timeout: int) -> dict:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def get_json(url: str, key: str, timeout: int) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def model_ids(data) -> set[str]:
    """Tolerant parser for the models list: data/models/items or a mapping."""
    if isinstance(data, dict):
        for name in ("data", "models", "items"):
            items = data.get(name)
            if isinstance(items, list):
                return {
                    str(item.get("id") or item.get("name") or item)
                    for item in items
                    if isinstance(item, (dict, str))
                }
        return {str(key) for key in data if isinstance(data[key], (dict, str))}
    if isinstance(data, list):
        return {
            str(item.get("id") or item.get("name") or item)
            for item in data
            if isinstance(item, (dict, str))
        }
    return set()


def explain_403(body: str) -> str:
    if "1010" in body or "cloudflare" in body.lower():
        return (
            "HTTP 403 from Cloudflare (Error 1010): the client signature was "
            "blocked, not the key. The script sends curl/8.0; if this persists, "
            "try --key-file or check the network."
        )
    return "HTTP 403: the key is missing the permission this call needs."


def check_model(model: str, key: str, models_url: str, timeout: int) -> int:
    try:
        data = get_json(models_url, key, timeout)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:300]
        if exc.code in (401, 403):
            print(f"check: {explain_403(body)}", file=sys.stderr)
            if "1010" not in body:
                print(
                    "Grant Models: Read on the service-account key, or rely on "
                    "the review call's own error.",
                    file=sys.stderr,
                )
            return 3
        print(f"check: model list failed (HTTP {exc.code}): {body}", file=sys.stderr)
        return 3
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"check: model list unreachable: {exc}", file=sys.stderr)
        return 3

    ids = model_ids(data)
    if not ids:
        print("check: could not parse the model list", file=sys.stderr)
        return 3
    if model not in ids:
        print(
            f"FREE JEV GONE: '{model}' is not in the Console model list.\n"
            "Update DEFAULT_MODEL in bin/jev_review.py to jev-1.13 (paid), or\n"
            "pass the same --model to the check and the review. Reviews will\n"
            "fail until this changes.",
            file=sys.stderr,
        )
        return 4
    print(f"check: '{model}' is available")
    return 0


def mock_response(kind: str) -> dict:
    good = kind == "good"
    axes = {
        axis: {
            "type": "score",
            "score": 3.5 if good else 1.0,
            "confidence": 0.8,
            "legend": {str(i): level for i, level in enumerate(LEVELS)},
            "probabilities": {},
        }
        for axis in AXES
    }
    axes.update(
        {
            "ship": {"type": "noul", "noul": 0.92 if good else 0.2},
            "scope": {"type": "noul", "noul": 0.95 if good else 0.3},
            "tests": {"type": "noul", "noul": 0.9 if good else 0.2},
            "secret_leak": {"type": "noul", "noul": 0.02 if good else 0.1},
        }
    )
    return {"model": "mock", "answers": axes, "usage": {"input_tokens": 0, "output_tokens": 0}}


def verdict(data: dict) -> tuple[bool, list[str]]:
    answers = data.get("answers")
    if not isinstance(answers, dict):
        raise ValueError("response has no 'answers' object")

    problems: list[str] = []
    for axis in AXES:
        answer = answers.get(axis, {})
        score = answer.get("score")
        if score is None:
            problems.append(f"{axis}: missing score")
            continue
        if float(score) < 2.0:
            problems.append(f"{axis}: {float(score):.2f}/4 — send back")

    for name, threshold, compare in (
        ("ship", 0.5, "lt"),
        ("scope", 0.5, "lt"),
        ("tests", 0.5, "lt"),
    ):
        value = answers.get(name, {}).get("noul")
        if value is None:
            problems.append(f"{name}: missing answer")
        elif compare == "lt" and float(value) < threshold:
            problems.append(f"{name}: {float(value):.2f} — send back")

    leak = answers.get("secret_leak", {}).get("noul")
    if leak is not None and float(leak) > 0.5:
        problems.append(f"secret_leak: {float(leak):.2f} — send back")

    return not problems, problems


def print_report(data: dict, passed: bool, problems: list[str], as_json: bool) -> None:
    answers = data.get("answers", {})
    if as_json:
        print(json.dumps({"passed": passed, "problems": problems, "answers": answers}, indent=2))
        return
    print("Jev advisory review\n")
    print(f"{'axis':<16}{'score':>7}")
    for axis in AXES:
        value = answers.get(axis, {}).get("score")
        shown = f"{float(value):.2f}" if value is not None else "?"
        print(f"{axis:<16}{shown:>7}")
    for name in ("ship", "scope", "tests", "secret_leak"):
        value = answers.get(name, {}).get("noul")
        shown = f"{float(value):.2f}" if value is not None else "?"
        print(f"{name:<16}{shown:>7}")
    print()
    if passed:
        print("VERDICT: pass (advisory).")
    else:
        print("VERDICT: send back.")
        for problem in problems:
            print(f"- {problem}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diff", help="diff file, or - for stdin")
    parser.add_argument("--task", default="", help="the task the diff claims to do")
    parser.add_argument("--task-file", help="read the task state from this file")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--endpoint", default=DEFAULT_URL)
    parser.add_argument("--models-url", default=DEFAULT_MODELS_URL)
    parser.add_argument("--key-file")
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--max-chars", type=int, default=30000)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--check",
        action="store_true",
        help="only check that --model is still offered (exit 4 when gone)",
    )
    parser.add_argument(
        "--allow-secret-shaped",
        action="store_true",
        help="send even if the diff matches a secret-shaped pattern",
    )
    parser.add_argument(
        "--mock",
        choices=("good", "bad"),
        help="skip the network and return a canned verdict (tests only)",
    )
    args = parser.parse_args()

    if not args.model:
        print(
            "error: set JEV_MODEL or pass --model; the public client does not "
            "hardcode a rotating model",
            file=sys.stderr,
        )
        return 3

    if args.check:
        key, _source = resolve_key(args.key_file)
        if not key:
            print(
                "error: no Jev key. Set OPENCODE_API_KEY, pass --key-file, or "
                "create ~/.config/opencode/console.key (chmod 600).",
                file=sys.stderr,
            )
            return 3
        return check_model(args.model, key, args.models_url, args.timeout)

    if args.task_file:
        args.task = Path(args.task_file).read_text().strip()
    if not args.diff:
        parser.error("--diff is required (use - for stdin)")
    if args.diff == "-":
        diff = sys.stdin.read()
    else:
        diff = Path(args.diff).read_text()
    if not diff.strip():
        print("error: empty diff", file=sys.stderr)
        return 3

    truncated = len(diff) > args.max_chars
    if truncated:
        diff = diff[: args.max_chars] + "\n\n[... diff truncated ...]"
    if len(args.task) > args.max_chars:
        args.task = args.task[: args.max_chars] + "\n\n[... task truncated ...]"

    if not args.allow_secret_shaped:
        for label, text in (("diff", diff), ("task", args.task)):
            if secret_shaped(text):
                print(
                    f"error: the {label} looks like it contains a secret or PII; "
                    "redact it or pass --allow-secret-shaped",
                    file=sys.stderr,
                )
                return 3

    payload = build_payload(args.task, diff, args.model)
    if args.dry_run:
        print(json.dumps(payload, indent=2))
        return 0

    if args.mock:
        data = mock_response(args.mock)
    else:
        key, source = resolve_key(args.key_file)
        if not key:
            print(
                "error: no Jev key. Set OPENCODE_API_KEY, pass --key-file, or "
                "create ~/.config/opencode/console.key (chmod 600).",
                file=sys.stderr,
            )
            return 3
        try:
            data = post(args.endpoint, key, payload, args.timeout)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:300]
            if exc.code in (400, 404) and args.model.endswith("-free"):
                print(
                    f"FREE JEV GONE: '{args.model}' was rejected (HTTP "
                    f"{exc.code}). Update DEFAULT_MODEL in bin/jev_review.py to "
                    "jev-1.13 (paid) or pass the same --model to the check and "
                    "the review. No review was run.",
                    file=sys.stderr,
                )
                return 4
            if exc.code in (401, 403):
                print(
                    "error: Jev " + explain_403(detail) + " Detail: " + detail,
                    file=sys.stderr,
                )
                return 3
            print(f"error: Jev HTTP {exc.code}: {detail}", file=sys.stderr)
            return 3
        except (urllib.error.URLError, TimeoutError) as exc:
            print(f"error: Jev unreachable: {exc}", file=sys.stderr)
            return 3

    try:
        passed, problems = verdict(data)
    except ValueError as exc:
        print(f"error: unexpected Jev response: {exc}", file=sys.stderr)
        print(json.dumps(data, indent=2)[:1000], file=sys.stderr)
        return 3

    print_report(data, passed, problems, args.json)
    return 0 if passed else 2


if __name__ == "__main__":
    sys.exit(main())
