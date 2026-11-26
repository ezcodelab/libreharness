#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
from __future__ import annotations

import argparse
import hashlib
import io
import os
import re
import sys
import tokenize
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

RULES = (
    "phase-narration",
    "todo",
    "commented-out-code",
    "workaround-justification",
    "suppression-debt",
    "comment-disallowed",
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
SKIP_DIRS = {
    ".git",
    ".mypy_cache",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "env",
    "node_modules",
    "vendor",
    "venv",
}

ALLOW = re.compile(r"comment-discipline:\s*allow\s+\S", re.IGNORECASE)
SPDX = re.compile(r"^SPDX-License-Identifier:")
CODING = re.compile(r"^-\*-.*-\*-$")
PHASE = re.compile(r"^(?:phase|step)\s+\d+\b", re.IGNORECASE)
TODO = re.compile(r"\b(?:TODO|FIXME|XXX)\b")
WORKAROUND = re.compile(r"\b(?:workaround|work[ -]?around)\b", re.IGNORECASE)
CONSTRAINT = re.compile(
    r"\b(?:do not|don't)\s+"
    r"(?:remove|delete|change|edit|modify|rename|reorder|touch)\b",
    re.IGNORECASE,
)
SUPPRESSION = re.compile(
    r"(?:eslint-disable(?:-next-line|-line)?\b"
    r"|@ts-(?:ignore|expect-error|nocheck)\b"
    r"|\btype:\s*ignore\b"
    r"|\bnoqa\b"
    r"|\bpylint:\s*disable\b"
    r"|\bpyright:\s*ignore\b"
    r"|\bmypy:\s*ignore-errors\b"
    r"|\bnosec\b"
    r"|\bshellcheck\s+disable\b"
    r"|\bnolint\b"
    r"|\b(?:istanbul|c8)\s+ignore\b"
    r"|\bpragma:\s*no\s*cover\b"
    r"|\b(?:rubocop|yamllint|bandit|golangci-lint):?\s*disable\b"
    r"|\bswiftlint:disable\b)",
    re.IGNORECASE,
)
LEGAL = re.compile(
    r"^(?:copyright\s+(?:\(c\)|\d{4})|licensed under\b|license:\s|spdx-)",
    re.IGNORECASE,
)
DOC_COMMENT = re.compile(r"^(?:/\*\*|///|//!|/\*!)")
VERSION = re.compile(r"^v?\d+(?:\.\d+)+$")
EXTERNAL_REASON = re.compile(
    r"https?://\S+"
    r"|\b(?:issue|bug|ticket|pr|pull request)\s*#?\d+\b"
    r"|#\d+\b"
    r"|\bCVE-\d{4}-\d{4,}\b"
    r"|\b[A-Z][A-Z0-9]+-\d+\b"
    r"|\bRFC\s?\d+\b"
    r"|\bfixed in\s+v?\d+(?:\.\d+)+\b",
    re.IGNORECASE,
)

CODE_PATTERNS = (
    re.compile(r"^(?:def|class)\s+[A-Za-z_]\w*\s*[\(:]"),
    re.compile(r"^(?:import\s+[A-Za-z_][\w.]*|from\s+[A-Za-z_][\w.]*\s+import\b)"),
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
    re.compile(r"^[A-Za-z_$][\w.$]*\s*\([^)]*\)\s*;$"),
    re.compile(
        r"^[A-Za-z_$][\w.$\[\]'\"]*\s*(?:=|\+=|-=|\*=)\s*(?:"
        r"[\(\[\{'\"]|"
        r"new\b|"
        r"(?:None|True|False|null|nil|undefined)\b|"
        r"[A-Za-z_]\w*\s*\("
        r")"
    ),
)

HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


@dataclass(frozen=True, order=True)
class Finding:
    path: str
    line: int
    rule: str
    text: str
    anchor: str


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
    if block and body.startswith("*"):
        body = body[1:].strip()
    return " ".join(body.split())


def python_comments(text: str) -> list[tuple[int, int, str]]:
    comments: list[tuple[int, int, str]] = []
    try:
        stream = io.StringIO(text)
        for token in tokenize.generate_tokens(stream.readline):
            if token.type == tokenize.COMMENT:
                comments.append(
                    (
                        token.start[0],
                        token.start[1],
                        clean_comment(token.string.lstrip("#")),
                    )
                )
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    return comments


def generic_comments(
    text: str, hash_style: bool, slash_style: bool
) -> Iterator[tuple[int, int, str]]:
    in_block = False
    for line_no, line in enumerate(text.splitlines(), 1):
        index = 0
        while index < len(line):
            if in_block:
                end = line.find("*/", index)
                if end < 0:
                    yield line_no, index, clean_comment(line[index:], block=True)
                    index = len(line)
                    break
                yield line_no, index, clean_comment(line[index:end], block=True)
                in_block = False
                index = end + 2
                continue
            if slash_style and line.startswith("/*", index):
                in_block = True
                index += 2
                continue
            if (
                hash_style
                and line[index] == "#"
                and (index == 0 or line[index - 1].isspace())
            ):
                yield line_no, index, clean_comment(line[index + 1 :])
                break
            if (
                slash_style
                and line.startswith("//", index)
                and (index == 0 or line[index - 1].isspace())
            ):
                yield line_no, index, clean_comment(line[index + 2 :])
                break
            if line[index] in "'\"`":
                quote = line[index]
                index += 1
                while index < len(line):
                    if line[index] == "\\":
                        index += 2
                        continue
                    if line[index] == quote:
                        index += 1
                        break
                    index += 1
                continue
            index += 1


def looks_like_code(text: str) -> bool:
    if " -> " in text:
        return False
    return any(pattern.search(text) for pattern in CODE_PATTERNS)


def anchor_for(
    lines: list[str], line_no: int, col: int, pure_comment_lines: set[int]
) -> str:
    before = lines[line_no - 1][:col].strip()
    context = before
    if not context:
        for offset in range(line_no, len(lines)):
            text = lines[offset].strip()
            if not text or (offset + 1) in pure_comment_lines:
                continue
            context = text
            break
    if not context:
        for offset in range(line_no - 2, -1, -1):
            text = lines[offset].strip()
            if not text or (offset + 1) in pure_comment_lines:
                continue
            context = text
            break
    normalized = " ".join(context.split())
    if not normalized:
        return ""
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]


def strict_keep(
    lines: list[str],
    line_no: int,
    col: int,
    text: str,
    context: str,
    block_doc: bool,
) -> bool:
    raw = lines[line_no - 1][col:]
    if SPDX.search(text) or text.startswith("!") or CODING.search(text):
        return True
    if LEGAL.search(text) or VERSION.fullmatch(text.strip()):
        return True
    if ALLOW.search(text) or ALLOW.search(context):
        return True
    if EXTERNAL_REASON.search(context):
        return True
    return block_doc or DOC_COMMENT.match(raw) is not None


def rules_for(text: str, context: str | None = None) -> list[str]:
    rules: list[str] = []
    if not text or SPDX.search(text) or text.startswith("!") or CODING.search(text):
        return rules
    if ALLOW.search(text):
        return rules
    if PHASE.search(text):
        rules.append("phase-narration")
    if TODO.search(text):
        rules.append("todo")
    if looks_like_code(text):
        rules.append("commented-out-code")
    if (WORKAROUND.search(text) or CONSTRAINT.search(text)) and not EXTERNAL_REASON.search(
        context or text
    ):
        rules.append("workaround-justification")
    if (
        SUPPRESSION.search(text)
        and not ALLOW.search(context or "")
        and not EXTERNAL_REASON.search(context or text)
    ):
        rules.append("suppression-debt")
    return rules


def scan(
    name: str,
    text: str,
    allowed: set[str],
    style: str | None = None,
    strict: bool = False,
) -> list[Finding]:
    style = style or style_for(name)
    if style == "python":
        comments: Iterator[tuple[int, int, str]] = iter(python_comments(text))
    elif style == "hash":
        comments = generic_comments(text, hash_style=True, slash_style=False)
    elif style == "slash":
        comments = generic_comments(text, hash_style=False, slash_style=True)
    else:
        return []
    items = list(comments)
    lines = text.splitlines()
    pure_comment_lines = {
        line for line, col, _ in items if not lines[line - 1][:col].strip()
    }
    doc_items: dict[tuple[int, int], bool] = {}
    doc = False
    for line_no, col, _ in items:
        raw = lines[line_no - 1][col:]
        stripped = lines[line_no - 1].lstrip()
        if (
            stripped.startswith("/**")
            or stripped.startswith("/*!")
            or raw.startswith("/**")
            or raw.startswith("/*!")
        ):
            doc = True
        keep_doc = doc or DOC_COMMENT.match(raw) is not None
        doc_items[(line_no, col)] = keep_doc
        if doc and "*/" in raw:
            doc = False
    findings: list[Finding] = []
    start = 0
    while start < len(items):
        end = start + 1
        while end < len(items) and items[end][0] <= items[end - 1][0] + 1:
            end += 1
        group = items[start:end]
        context = " ".join(body for _, _, body in group)
        for line_no, col, body in group:
            rules = rules_for(body, context)
            if strict and not rules and not strict_keep(
                lines, line_no, col, body, context, doc_items[(line_no, col)]
            ):
                rules = ["comment-disallowed"]
            anchor = anchor_for(lines, line_no, col, pure_comment_lines)
            for rule in rules:
                if rule not in allowed:
                    findings.append(Finding(name, line_no, rule, body, anchor))
        start = end
    return findings


def walk_files(root: Path) -> Iterator[Path]:
    if root.is_file():
        yield root
        return
    if not root.is_dir():
        return
    for directory, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(name for name in dirnames if name not in SKIP_DIRS)
        for filename in sorted(filenames):
            path = Path(directory) / filename
            if path.is_file():
                yield path


def display_path(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return str(path)


def scan_paths(
    paths: list[Path], allowed: set[str], base: Path, strict: bool = False
) -> tuple[list[Finding], int]:
    findings: list[Finding] = []
    errors = 0
    for root in paths:
        for path in walk_files(root):
            style = style_for(path.name)
            if style is None:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError as error:
                print(f"comment_audit: {path}: {error}", file=sys.stderr)
                errors += 1
                continue
            findings.extend(scan(display_path(path, base), text, allowed, style, strict))
    return findings, errors


def scan_stdin(name: str, allowed: set[str], strict: bool = False) -> list[Finding]:
    text = sys.stdin.read()
    return scan(name, text, allowed, style_for(name) or "hash", strict)


def parse_diff(text: str) -> dict[str, set[int]]:
    added: dict[str, set[int]] = defaultdict(set)
    path: str | None = None
    new_line = 0
    for line in text.splitlines():
        if line.startswith("+++ "):
            raw = line[4:].strip()
            if raw == "/dev/null":
                path = None
                continue
            raw = raw.split("\t", 1)[0].strip('"')
            if raw.startswith("b/"):
                raw = raw[2:]
            path = raw
            continue
        if line.startswith("@@ "):
            match = HUNK.match(line)
            new_line = int(match.group(1)) if match else 0
            continue
        if path is None:
            continue
        if line.startswith("+"):
            added[path].add(new_line)
            new_line += 1
        elif line.startswith(" "):
            new_line += 1
    return added


def scan_diff(
    text: str, allowed: set[str], base: Path, strict: bool = False
) -> tuple[list[Finding], int]:
    findings: list[Finding] = []
    errors = 0
    for name, lines in sorted(parse_diff(text).items()):
        path = (base / name).resolve()
        if not path.is_file():
            print(f"comment_audit: {name}: diff path is not a file", file=sys.stderr)
            errors += 1
            continue
        style = style_for(name)
        if style is None:
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        for finding in scan(name, content, allowed, style, strict):
            if finding.line in lines:
                findings.append(finding)
    return findings, errors


def read_baseline(path: Path) -> dict[tuple[str, str, str, str], int]:
    counts: dict[tuple[str, str, str, str], int] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        parts = line.split("\t", 4)
        if len(parts) == 4:
            raise ValueError(
                f"{path}:{number}: old four-column baseline; regenerate with --write-baseline"
            )
        if (
            len(parts) != 5
            or not parts[0].isdigit()
            or parts[2] not in RULES
            or (parts[4] and not re.fullmatch(r"[0-9a-f]{12}", parts[4]))
        ):
            raise ValueError(f"{path}:{number}: invalid baseline record")
        key = (parts[1], parts[2], parts[3], parts[4])
        counts[key] = counts.get(key, 0) + int(parts[0])
    return counts


def write_baseline(path: Path, findings: list[Finding]) -> int:
    counts = Counter(
        (finding.path, finding.rule, finding.text, finding.anchor)
        for finding in findings
    )
    lines = [
        f"{count}\t{key[0]}\t{key[1]}\t{key[2]}\t{key[3]}"
        for key, count in sorted(counts.items())
    ]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return sum(counts.values())


def filter_baseline(
    findings: list[Finding], baseline: dict[tuple[str, str, str, str], int]
) -> list[Finding]:
    remaining = dict(baseline)
    kept: list[Finding] = []
    for finding in findings:
        key = (finding.path, finding.rule, finding.text, finding.anchor)
        if remaining.get(key, 0) > 0:
            remaining[key] -= 1
        else:
            kept.append(finding)
    return kept


def report(findings: list[Finding]) -> None:
    for finding in sorted(findings):
        print(f"{finding.path}:{finding.line}: {finding.rule}: {finding.text}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail closed on comment debt in source and configuration files.",
        epilog="Inline escape: comment-discipline: allow <reason>",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        metavar="PATH",
        help="file or directory to scan; '-' reads stdin (default when no path is given)",
    )
    parser.add_argument(
        "--diff",
        metavar="PATCH",
        help="unified diff to scan; reports findings on added lines only ('-' reads stdin)",
    )
    parser.add_argument(
        "--baseline",
        metavar="FILE",
        help="suppress findings recorded in a baseline file",
    )
    parser.add_argument(
        "--write-baseline",
        metavar="FILE",
        help="write the current findings to a baseline file and exit clean",
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
    parser.add_argument(
        "--strict",
        action="store_true",
        help="flag every comment outside the keep list as comment-disallowed",
    )
    parser.add_argument("--list-rules", action="store_true", help="print the rule names and exit")
    args = parser.parse_args()

    if args.list_rules:
        for rule in RULES:
            print(rule)
        return 0
    if args.diff and args.paths:
        parser.error("--diff cannot be combined with paths")
    if args.write_baseline and args.diff:
        parser.error("--write-baseline cannot be combined with --diff")
    if args.write_baseline and args.baseline:
        parser.error("--write-baseline cannot be combined with --baseline")

    allowed = set(args.allow)
    base = Path.cwd()

    if args.diff:
        try:
            text = sys.stdin.read() if args.diff == "-" else Path(args.diff).read_text(
                encoding="utf-8"
            )
        except OSError as error:
            print(f"comment_audit: {args.diff}: {error}", file=sys.stderr)
            return 2
        findings, errors = scan_diff(text, allowed, base, args.strict)
        if errors:
            return 2
    else:
        names = args.paths or ["-"]
        if "-" in names and sys.stdin.isatty():
            parser.error("no piped input and no path to scan")
        findings = []
        paths = []
        for name in names:
            if name == "-":
                findings.extend(scan_stdin(args.stdin_name, allowed, args.strict))
                continue
            path = Path(name)
            if not path.exists():
                print(f"comment_audit: {name}: not a file or directory", file=sys.stderr)
                return 2
            paths.append(path)
        found, errors = scan_paths(paths, allowed, base, args.strict)
        findings.extend(found)
        if errors:
            return 2

    if args.write_baseline:
        count = write_baseline(Path(args.write_baseline), findings)
        print(f"comment_audit: wrote {count} finding(s) to {args.write_baseline}", file=sys.stderr)
        return 0

    if args.baseline:
        try:
            findings = filter_baseline(findings, read_baseline(Path(args.baseline)))
        except (OSError, ValueError) as error:
            print(f"comment_audit: {error}", file=sys.stderr)
            return 2

    report(findings)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
