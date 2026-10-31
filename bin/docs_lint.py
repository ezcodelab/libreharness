# SPDX-License-Identifier: MIT
#!/usr/bin/env python3
"""Deterministic Markdown checks: links, index presence, hot-note age."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote

LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
SKIP_DIRS = {".git", "node_modules", ".venv", "dist", "__pycache__", ".pytest_cache"}
SKIP_SCHEMES = ("http://", "https://", "mailto:", "tel:", "data:", "#")


def markdown_files(root: Path):
    for path in root.rglob("*.md"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        yield path


def clean_target(raw: str) -> str:
    target = raw.strip()
    if target.startswith("<") and ">" in target:
        target = target[1 : target.index(">")]
    target = target.split(" ")[0]
    return unquote(target.split("#", 1)[0])


def check_links(root: Path) -> list[dict]:
    problems = []
    for path in markdown_files(root):
        text = path.read_text(errors="replace")
        for line_no, line in enumerate(text.splitlines(), 1):
            for match in LINK.finditer(line):
                raw = match.group(1).strip()
                if not raw or raw.startswith(SKIP_SCHEMES):
                    continue
                target = clean_target(raw)
                if not target:
                    continue
                resolved = (path.parent / target).resolve()
                if not resolved.exists():
                    problems.append(
                        {
                            "file": str(path.relative_to(root)),
                            "line": line_no,
                            "target": raw,
                            "reason": "missing",
                        }
                    )
    return problems


def check_skills(path: Path, max_skills: int, max_lines: int) -> list[dict]:
    problems: list[dict] = []
    if not path.is_dir():
        return [{"file": str(path), "reason": "skills directory missing"}]
    skills = sorted(path.glob("*/SKILL.md"))
    if len(skills) > max_skills:
        problems.append(
            {
                "file": str(path),
                "reason": f"{len(skills)} skills exceeds budget {max_skills}",
            }
        )
    for skill in skills:
        line_count = len(skill.read_text(errors="replace").splitlines())
        if line_count > max_lines:
            problems.append(
                {
                    "file": str(skill),
                    "reason": f"{line_count} lines exceeds {max_lines}",
                }
            )
    return problems


def check_hot(hot: Path, max_age_days: int) -> list[dict]:
    if not hot.is_file():
        return [{"file": str(hot), "reason": "hot note missing"}]
    age = datetime.now(timezone.utc).timestamp() - hot.stat().st_mtime
    days = age / 86400
    if days > max_age_days:
        return [
            {
                "file": str(hot),
                "reason": f"stale: {days:.1f} days old (max {max_age_days})",
            }
        ]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".", help="directory to scan")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--require-index", action="store_true")
    parser.add_argument("--hot", help="path to hot.md")
    parser.add_argument("--max-age-days", type=int, default=7)
    parser.add_argument("--skills-dir", help="global skills directory to audit")
    parser.add_argument("--max-skills", type=int, default=8)
    parser.add_argument("--max-skill-lines", type=int, default=120)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    problems = check_links(root)

    if args.require_index and not (root / "docs/INDEX.md").is_file():
        problems.append({"file": "docs/INDEX.md", "reason": "missing"})
    if args.hot:
        problems.extend(check_hot(Path(args.hot), args.max_age_days))
    if args.skills_dir:
        problems.extend(
            check_skills(
                Path(args.skills_dir).expanduser(),
                args.max_skills,
                args.max_skill_lines,
            )
        )

    if args.json:
        print(json.dumps({"root": str(root), "problems": problems}, indent=2))
    else:
        print(f"docs lint: {root}")
        print(f"markdown files: {sum(1 for _ in markdown_files(root))}")
        if problems:
            for problem in problems:
                location = problem.get("file", "?")
                if "line" in problem:
                    location = f"{location}:{problem['line']}"
                print(f"- {location}: {problem['reason']} {problem.get('target', '')}".rstrip())
        else:
            print("no problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
