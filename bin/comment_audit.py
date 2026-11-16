#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Flag low-value code comments without banning comments.

Reported rules:
- phase-narration: "Phase 1", "Step 2", or a numbered step comment.
- todo: TODO, FIXME, or XXX.
- commented-out-code: a comment body that still looks like code.
- workaround-justification: a workaround or do-not-remove/change comment with
  no checkable external reference (URL, issue, CVE, or fixed-in version).

Comments that explain a non-obvious why, module and function docstrings, and
SPDX headers are left alone. Scan the named files, or stdin when no file is
named. Exit 0 when clean, 1 on findings, 2 when an input cannot be read.

An inline ``comment-discipline: allow <reason>`` suppresses findings on that
comment line. ``--allow RULE`` suppresses one rule for the whole run.
"""

from __future__ import annotations

import argparse
import io
import re
import sys
import tokenize
from pathlib import Path
from typing import Iterator, NamedTuple

RULES = (
    "phase-narration",
    "todo",
    "commented-out-code",
    "workaround-justification",
)

HASH_STYLES = {
    ".bash",
    ".cfg",
    ".conf",
    ".ini",
    ".pl",
    ".ps1",
    ".r",
    ".rb",
    ".sh",
    ".toml",
    ".yaml",
    ".yml",
    ".zsh",
}
SLASH_STYLES = {
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".css",
    ".go",
    ".h",
    ".hpp",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".kts",
    ".less",
    ".mjs",
    ".php",
    ".rs",
    ".scala",
    ".scss",
    ".swift",
    ".ts",
    ".tsx",
}
HASH_NAMES = {"Dockerfile", "Gemfile", "Makefile", "Rakefile"}

ALLOW = re.compile(r"comment-discipline:\s*allow\s+\S", re.IGNORECASE)
SPDX = re.compile(r"^SPDX-License-Identifier:")
CODING = re.compile(r"^-\*-.*-\*-$")
PHASE = re.compile(r"^(?:phase|step)\s+\d+\b", re.IGNORECASE)
NUMBERED_STEP = re.compile(r"^\d+[.)]\s+\S")
TODO = re.compile(r"\b(?:TODO|FIXME|XXX)\b")
WORKAROUND = re.compile(r"\b(?:workaround|work[ -]?around)\b", re.IGNORECASE)
CONSTRAINT = re.compile(
    r"\b(?:do not|don't)\s+"
    r"(?:remove|delete|change|edit|modify|rename|reorder|touch)\b",
    re.IGNORECASE,
)
# Only a reference a reviewer can check counts; "it breaks" is not a reason.
EXTERNAL_REASON = re.compile(
    r"https?://\S+"
    r"|\b(?:issue|bug|ticket|pr|pull request)\s*#?\d+\b"
    r"|\bCVE-\d{4}-\d{4,}\b"
    r"|\b[A-Z][A-Z0-9]+-\d+\b"
    r"|\bfixed in\s+v?\d+(?:\.\d+)+\b",
    re.IGNORECASE,
)

CODE_PATTERNS = (
    re.compile(r"^(?:def|class)\s+[A-Za-z_]\w*\s*[\(:]"),
    re.compile(r"^(?:import|from)\s+[A-Za-z_][\w.]*"),
    re.compile(
        r"^(?:return|raise|yield|throw)\s+(?:"
        r"[\(\[\{'\"]|"
        r"[-+]?\d|"
        r"(?:None|True|False|null|nil|undefined)\b|"
        r"new\b|"
        r"[A-Za-z_]\w*(?:\(|\.)"
        r")"
    ),
    re.compile(r"^(?:print|console\.log|console\.error|throw new)\s*\("),
    re.compile(r"^(?:const|let|var)\s+[A-Za-z_$]\w*\s*="),
    re.compile(r"^(?:function|func|fn)\s+[A-Za-z_$]\w*\s*\("),
    re.compile(r"^[A-Za-z_$][\w.$]*\s*\([^)]*\)\s*;?\s*$"),
    re.compile(
        r"^[A-Za-z_$][\w.$\[\]'\"]*\s*(?:=|\+=|-=|\*=)\s*(?:"
        r"[\(\[\{'\"]|"
        r"new\b|"
        r"(?:None|True|False|null|nil|undefined)\b|"
        r"[A-Za-z_]\w*\s*\("
        r")"
    ),
)


class Finding(NamedTuple):
    line: int
    rule: str
    text: str


def style_for(name: str) -> str | None:
    path = Path(name)
    if path.suffix.lower() == ".py":
        return "python"
    if path.name in HASH_NAMES or path.suffix.lower() in HASH_STYLES:
        return "hash"
    if path.suffix.lower() in SLASH_STYLES:
        return "slash"
    return None


def clean_comment(body: str, block: bool = False) -> str:
    body = body.strip()
    if block:
        body = re.sub(r"^\*\s+", "", body).strip()
        if body == "*":
            body = ""
    return " ".join(body.split())


def python_comments(text: str) -> list[tuple[int, str]]:
    comments: list[tuple[int, str]] = []
    try:
        stream = io.StringIO(text)
        for token in tokenize.generate_tokens(stream.readline):
            if token.type == tokenize.COMMENT:
                comments.append((token.start[0], clean_comment(token.string.lstrip("#"))))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        # Keep the comments tokenized before the error; a generic rescan would
        # mistake docstrings for comments.
        pass
    return comments


def generic_comments(
    text: str, hash_style: bool, slash_style: bool
) -> Iterator[tuple[int, str]]:
    quote: str | None = None
    in_block = False
    for line_no, line in enumerate(text.splitlines(), 1):
        index = 0
        while index < len(line):
            if in_block:
                end = line.find("*/", index)
                if end == -1:
                    yield line_no, clean_comment(line[index:], block=True)
                    break
                yield line_no, clean_comment(line[index:end], block=True)
                in_block = False
                index = end + 2
                continue
            char = line[index]
            if quote:
                if char == "\\":
                    index += 2
                    continue
                if char == quote:
                    quote = None
                index += 1
                continue
            if char in "'\"`":
                quote = char
                index += 1
                continue
            if hash_style and char == "#" and (index == 0 or line[index - 1].isspace()):
                yield line_no, clean_comment(line[index + 1 :])
                break
            if (
                slash_style
                and line.startswith("//", index)
                and (index == 0 or line[index - 1].isspace())
                and not (index > 0 and line[index - 1] == ":")
            ):
                yield line_no, clean_comment(line[index + 2 :])
                break
            if slash_style and line.startswith("/*", index):
                in_block = True
                index += 2
                continue
            index += 1
        else:
            if quote in {"'", '"'}:
                quote = None


def looks_like_code(text: str) -> bool:
    return any(pattern.search(text) for pattern in CODE_PATTERNS)


def rules_for(text: str, context: str | None = None) -> list[str]:
    rules: list[str] = []
    if not text or SPDX.search(text) or text.startswith("!") or CODING.search(text):
        return rules
    if ALLOW.search(text):
        return rules
    if PHASE.search(text) or NUMBERED_STEP.search(text):
        rules.append("phase-narration")
    if TODO.search(text):
        rules.append("todo")
    if looks_like_code(text):
        rules.append("commented-out-code")
    if (WORKAROUND.search(text) or CONSTRAINT.search(text)) and not EXTERNAL_REASON.search(
        context or text
    ):
        rules.append("workaround-justification")
    return rules


def scan(
    name: str, text: str, allowed: set[str], style: str | None = None
) -> list[Finding]:
    style = style or style_for(name)
    if style == "python":
        comments: Iterator[tuple[int, str]] = iter(python_comments(text))
    elif style == "hash":
        comments = generic_comments(text, hash_style=True, slash_style=False)
    elif style == "slash":
        comments = generic_comments(text, hash_style=False, slash_style=True)
    else:
        print(f"comment_audit: skip {name}: unsupported comment style", file=sys.stderr)
        return []
    items = list(comments)
    findings = []
    start = 0
    while start < len(items):
        end = start + 1
        while end < len(items) and items[end][0] <= items[end - 1][0] + 1:
            end += 1
        context = " ".join(body for _, body in items[start:end])
        for line_no, body in items[start:end]:
            for rule in rules_for(body, context):
                if rule not in allowed:
                    findings.append(Finding(line_no, rule, body))
        start = end
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Flag low-value comments in source files.",
        epilog="Inline escape: comment-discipline: allow <reason>",
    )
    parser.add_argument(
        "files",
        nargs="*",
        metavar="FILE",
        help="file to scan; '-' reads stdin (default when no file is given)",
    )
    parser.add_argument(
        "--allow",
        action="append",
        choices=RULES,
        default=[],
        metavar="RULE",
        help="skip one rule for the whole run (repeatable)",
    )
    parser.add_argument(
        "--stdin-name",
        default="<stdin>",
        help="name used for stdin output and style detection (default: %(default)s)",
    )
    args = parser.parse_args()
    allowed = set(args.allow)
    inputs: list[tuple[str, str, str | None]] = []
    errors = 0

    names = args.files or ["-"]
    if "-" in names and sys.stdin.isatty():
        parser.error("no piped input and no file to scan")
    for name in names:
        if name == "-":
            inputs.append(
                (args.stdin_name, sys.stdin.read(), style_for(args.stdin_name) or "hash")
            )
            continue
        path = Path(name)
        if not path.is_file():
            print(f"comment_audit: {name}: not a file", file=sys.stderr)
            errors += 1
            continue
        try:
            inputs.append(
                (name, path.read_text(encoding="utf-8", errors="replace"), None)
            )
        except OSError as error:
            print(f"comment_audit: {name}: {error}", file=sys.stderr)
            errors += 1

    count = 0
    for name, text, style in inputs:
        for finding in scan(name, text, allowed, style):
            print(f"{name}:{finding.line}: {finding.rule}: {finding.text}")
            count += 1

    if errors:
        return 2
    return 1 if count else 0


if __name__ == "__main__":
    sys.exit(main())
