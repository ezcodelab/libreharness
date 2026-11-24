# SPDX-License-Identifier: MIT
#!/usr/bin/env python3
"""Durable work queue for AI-assisted engineering.

One Markdown file per task under work/tasks, a generated BOARD.md, and a
small dependency graph. No database, no server, no third-party package.

A task is the unit of context: one task should fit one agent session and one
reviewable diff. The queue is the source of truth for ownership and state;
the project repository is the source of truth for the work itself.
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import datetime as dt
import fcntl
import hashlib
import json
import os
import posixpath
import re
import shlex
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(
    os.environ.get(
        "HARNESS_STATE",
        Path.home() / ".local/state/libreharness",
    )
).expanduser()
WORK = ROOT / "work"
TASKS = WORK / "tasks"
LOCK = WORK / ".lock"
BOARD = WORK / "BOARD.md"
METRICS = ROOT / "metrics/workflow-log.csv"

STATUSES = ("inbox", "ready", "active", "blocked", "review", "done", "abandoned")
FINAL = {"done", "abandoned"}
FIELD_ORDER = (
    "id",
    "title",
    "project",
    "kind",
    "status",
    "priority",
    "owner",
    "parent",
    "session",
    "lane",
    "owns",
    "branch",
    "worktree",
    "base",
    "depends_on",
    "reviewer",
    "autorun",
    "max_continuations",
    "blocked_reason",
    "created",
    "updated",
    "tags",
)
SECTION_ORDER = (
    "Scope",
    "Out of scope",
    "Acceptance",
    "Context",
    "Plan",
    "Evidence",
    "Handoff",
    "Log",
)


def today() -> str:
    return dt.date.today().isoformat()


def slugify(text: str, limit: int = 48) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (slug[:limit].rstrip("-") or "task")


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end < 0:
        return {}, text
    meta: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()
    return meta, text[end + 4 :].lstrip("\n")


def split_sections(body: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []
    for line in body.splitlines():
        match = re.match(r"^##\s+(.+?)\s*$", line)
        if match:
            if current is not None:
                sections[current] = "\n".join(buf).strip()
            current = match.group(1).strip()
            buf = []
        elif current is not None:
            buf.append(line)
    if current is not None:
        sections[current] = "\n".join(buf).strip()
    return sections


def task_path(root: Path, task_id: str) -> Path:
    return root / "work/tasks" / f"{task_id}.md"


def read_task(path: Path) -> dict:
    meta, body = split_frontmatter(path.read_text())
    sections = split_sections(body)
    title = meta.get("title") or path.stem
    return {"path": path, "meta": meta, "sections": sections, "title": title}


def atomic_write(path: Path, text: str) -> None:
    """A crash must not leave a half-written task or board."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(handle, "w") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def write_task(task: dict) -> None:
    meta = task["meta"]
    meta["updated"] = today()
    ordered = [key for key in FIELD_ORDER if key in meta] + [
        key for key in meta if key not in FIELD_ORDER
    ]
    lines = ["---"] + [f"{key}: {meta[key]}" for key in ordered] + ["---", ""]
    lines += [f"# {task['title']}", ""]
    known = [name for name in SECTION_ORDER if name in task["sections"]]
    extra = [name for name in task["sections"] if name not in SECTION_ORDER]
    for name in known + extra:
        lines += [f"## {name}", "", task["sections"].get(name, "").rstrip(), ""]
    atomic_write(task["path"], "\n".join(lines).rstrip() + "\n")


def all_tasks(root: Path) -> list[dict]:
    base = root / "work/tasks"
    if not base.is_dir():
        return []
    tasks = []
    for path in sorted(base.glob("*.md")):
        task = read_task(path)
        task["meta"].setdefault("id", path.stem)
        tasks.append(task)
    return tasks


def children_of(root: Path, goal_id: str) -> list[dict]:
    return [task for task in all_tasks(root) if task["meta"].get("parent") == goal_id]


def goal_task(
    root: Path,
    title: str,
    *,
    project: str = "general",
    priority: int = 1,
    scope: str = "",
    acceptance: str = "",
    tags: str = "goal",
    session: str = "",
    autorun: bool = False,
    max_continuations: int | None = None,
) -> dict:
    return new_task(
        root,
        title,
        project=project,
        priority=priority,
        scope=scope,
        acceptance=acceptance,
        tags=tags,
        status="active",
        kind="goal",
        owner="goal",
        session=session,
        autorun=autorun,
        max_continuations=max_continuations,
    )


def goal_status(root: Path, key: str, as_json: bool = False) -> int:
    goal = find_task(root, key)
    if goal["meta"].get("kind") != "goal":
        raise SystemExit(f"error: {goal['meta']['id']} is not a goal")
    children = children_of(root, goal["meta"]["id"])
    counts = {status: 0 for status in STATUSES}
    for child in children:
        status = child["meta"].get("status", "")
        if status in counts:
            counts[status] += 1
    ready = []
    for child in children:
        if child["meta"].get("status") != "ready":
            continue
        unblocked, _ = is_unblocked(root, child)
        if unblocked:
            ready.append(child["meta"]["id"])
    open_children = [
        child["meta"]["id"]
        for child in children
        if child["meta"].get("status") not in FINAL
    ]
    result = {
        "goal": goal["meta"]["id"],
        "status": goal["meta"].get("status"),
        "autorun": goal["meta"].get("autorun") == "true",
        "children": len(children),
        "counts": counts,
        "ready": ready,
        "open": open_children,
        "closable": bool(children) and not open_children,
    }
    if as_json:
        print(json.dumps(result, indent=2))
        return 0
    print(f"goal: {result['goal']} ({result['status']})")
    print(f"children: {len(children)}")
    print("  " + "  ".join(f"{status}: {counts[status]}" for status in STATUSES))
    print("ready: " + (", ".join(ready) if ready else "none"))
    print("open: " + (", ".join(open_children) if open_children else "none"))
    print("closable: " + ("yes" if result["closable"] else "no"))
    return 0


def running_goals(root: Path, as_json: bool = False, include_all: bool = False) -> int:
    goals = [
        task
        for task in all_tasks(root)
        if task["meta"].get("kind") == "goal"
        and task["meta"].get("status") == "active"
        and (include_all or task["meta"].get("autorun") == "true")
    ]
    if as_json:
        print(json.dumps([task["meta"] for task in goals], indent=2))
    else:
        print_tasks(goals)
    return 0


def find_task(root: Path, key: str) -> dict:
    key = key.strip()
    exact = task_path(root, key)
    if exact.is_file():
        return read_task(exact)
    matches = [task for task in all_tasks(root) if task["meta"].get("id", task["path"].stem).startswith(key)]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise SystemExit(f"error: no task matching {key!r}")
    raise SystemExit(
        "error: ambiguous task prefix: "
        + ", ".join(task["meta"].get("id", task["path"].stem) for task in matches)
    )


def dependencies(task: dict) -> list[str]:
    value = task["meta"].get("depends_on", "")
    return [item.strip() for item in value.split(",") if item.strip()]


def is_unblocked(root: Path, task: dict) -> tuple[bool, list[str]]:
    open_deps = []
    for dep in dependencies(task):
        try:
            other = find_task(root, dep)
        except SystemExit:
            open_deps.append(f"{dep} (missing)")
            continue
        if other["meta"].get("status") not in FINAL:
            open_deps.append(dep)
    return not open_deps, open_deps


@contextlib.contextmanager
def locked(root: Path, filename: str = ".lock"):
    lock_path = root / "work" / filename
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def append_log(task: dict, text: str) -> None:
    log = task["sections"].get("Log", "").rstrip()
    line = f"- {today()} — {text}"
    task["sections"]["Log"] = (log + "\n" + line).strip()


def new_task(
    root: Path,
    title: str,
    *,
    project: str = "general",
    priority: int = 2,
    depends_on: str = "",
    scope: str = "",
    acceptance: str = "",
    tags: str = "",
    status: str = "ready",
    kind: str = "task",
    parent: str = "",
    owner: str = "",
    session: str = "",
    lane: str = "",
    owns: str = "",
    autorun: bool = False,
    max_continuations: int | None = None,
) -> dict:
    if status not in STATUSES:
        raise SystemExit(f"error: unknown status {status!r}")
    if kind not in ("task", "goal"):
        raise SystemExit(f"error: unknown kind {kind!r}")
    if kind == "goal" and parent:
        raise SystemExit("error: a goal cannot have a parent")
    if parent:
        parent_task = find_task(root, parent)
        if parent_task["meta"].get("kind") != "goal":
            raise SystemExit(f"error: parent {parent} is not a goal")
    base_id = f"{dt.date.today():%Y%m%d}-{slugify(title)}"
    task_id = base_id
    counter = 2
    while task_path(root, task_id).exists():
        task_id = f"{base_id}-{counter}"
        counter += 1
    meta = {
        "id": task_id,
        "title": title.strip(),
        "project": project.strip() or "general",
        "kind": kind,
        "status": status,
        "priority": str(max(0, min(4, priority))),
        "owner": owner,
        "parent": parent,
        "session": session,
        "lane": lane,
        "owns": ",".join(item.strip() for item in owns.split(",") if item.strip()),
        "branch": "",
        "worktree": "",
        "base": "",
        "depends_on": ",".join(
            item.strip() for item in depends_on.split(",") if item.strip()
        ),
        "reviewer": "",
        "autorun": "true" if autorun else "false",
        "max_continuations": "" if max_continuations is None else str(max(0, max_continuations)),
        "blocked_reason": "",
        "created": today(),
        "updated": today(),
        "tags": ",".join(item.strip() for item in tags.split(",") if item.strip()),
    }
    sections = {
        "Scope": scope.strip() or "TBD — clarify before claiming.",
        "Out of scope": "",
        "Acceptance": acceptance.strip() or "- [ ] TBD — make this testable.",
        "Context": "",
        "Plan": "",
        "Evidence": "",
        "Handoff": "",
        "Log": f"- {today()} — created",
    }
    task = {
        "path": task_path(root, task_id),
        "meta": meta,
        "sections": sections,
        "title": title.strip(),
    }
    task["path"].parent.mkdir(parents=True, exist_ok=True)
    with locked(root):
        # Re-check under the write lock: two intakes can race the exists() loop.
        while task_path(root, task_id).exists():
            task_id = f"{base_id}-{counter}"
            counter += 1
        meta["id"] = task_id
        task["path"] = task_path(root, task_id)
        write_task(task)
    write_board(root)
    return task


PLAN_KEY = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def plan_error(message: str) -> None:
    raise SystemExit(f"plan: {message}")


def plan_bool(value, name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.lower() in ("true", "false"):
        return value.lower() == "true"
    plan_error(f"goal.{name} must be true or false")


def normalized_owns(value: str) -> str:
    cleaned = value.strip().replace("\\", "/")
    if not cleaned:
        return ""
    while cleaned.startswith("./"):
        cleaned = cleaned[2:]
    return posixpath.normpath(cleaned)


def paths_overlap(first: str, second: str) -> bool:
    return (
        first == second
        or first.startswith(second + "/")
        or second.startswith(first + "/")
    )


def validate_plan(root: Path, plan: dict) -> dict:
    if not isinstance(plan, dict):
        plan_error("the plan must be a JSON object")
    goal_conf = plan.get("goal")
    if not isinstance(goal_conf, dict):
        plan_error("missing 'goal' object")
    for field in ("title", "scope", "acceptance"):
        if not str(goal_conf.get(field, "")).strip():
            plan_error(f"goal.{field} is required")
    try:
        goal_priority = int(goal_conf.get("priority", 1))
    except (TypeError, ValueError):
        plan_error("goal.priority must be an integer")
    if not 0 <= goal_priority <= 4:
        plan_error("goal.priority must be 0..4")
    raw_continuations = goal_conf.get("max_continuations")
    if raw_continuations in (None, ""):
        max_continuations = None
    else:
        try:
            max_continuations = int(raw_continuations)
        except (TypeError, ValueError):
            plan_error("goal.max_continuations must be an integer")
        if max_continuations < 0:
            plan_error("goal.max_continuations must be >= 0")

    children = plan.get("children")
    if not isinstance(children, list) or not children:
        plan_error("'children' must be a non-empty list")
    by_key: dict[str, dict] = {}
    for index, child in enumerate(children):
        if not isinstance(child, dict):
            plan_error(f"children[{index}] must be an object")
        key = str(child.get("key", "")).strip()
        if not PLAN_KEY.match(key):
            plan_error(f"child key {key!r} must be lowercase kebab-case")
        if key in by_key:
            plan_error(f"duplicate child key {key!r}")
        for field in ("title", "scope", "acceptance"):
            if not str(child.get(field, "")).strip():
                plan_error(f"{key}.{field} is required")
        try:
            priority = int(child.get("priority", 2))
        except (TypeError, ValueError):
            plan_error(f"{key}.priority must be an integer")
        if not 0 <= priority <= 4:
            plan_error(f"{key}.priority must be 0..4")
        deps = child.get("depends_on", [])
        owns = child.get("owns", [])
        if not isinstance(deps, list) or not all(isinstance(dep, str) for dep in deps):
            plan_error(f"{key}.depends_on must be a list of keys")
        if not isinstance(owns, list) or not all(isinstance(own, str) for own in owns):
            plan_error(f"{key}.owns must be a list of paths")
        lane = str(child.get("lane", "")).strip()
        normalized_owns_list: list[str] = []
        for own in owns:
            path = normalized_owns(own)
            if not path:
                continue
            if path in ("..", ".") or path.startswith("../") or Path(path).is_absolute():
                plan_error(f"{key}.owns must be repo-relative, not {own!r}")
            normalized_owns_list.append(path)
        by_key[key] = {
            "key": key,
            "title": str(child["title"]).strip(),
            "scope": str(child["scope"]).strip(),
            "acceptance": str(child["acceptance"]).strip(),
            "priority": priority,
            "depends_on": deps,
            "owns": normalized_owns_list,
            "lane": lane,
            "tags": str(child.get("tags", "")).strip(),
        }

    for key, child in by_key.items():
        for dep in child["depends_on"]:
            if dep == key:
                plan_error(f"{key} depends on itself")
            if dep not in by_key:
                plan_error(f"{key} depends on missing key {dep!r}")

    state: dict[str, int] = {}
    order: list[str] = []

    def visit(key: str, trail: list[str]) -> None:
        if state.get(key) == 2:
            return
        if state.get(key) == 1:
            plan_error("dependency cycle: " + " -> ".join(trail + [key]))
        state[key] = 1
        for dep in by_key[key]["depends_on"]:
            visit(dep, trail + [key])
        state[key] = 2
        order.append(key)

    for key in by_key:
        visit(key, [])

    owners: list[tuple[str, str]] = []
    for key, child in by_key.items():
        for path in child["owns"]:
            for other_key, other_path in owners:
                if other_key != key and paths_overlap(path, other_path):
                    plan_error(
                        f"path {path!r} overlaps {other_path!r} "
                        f"owned by {other_key} and {key}"
                    )
            owners.append((key, path))

    # A plan must not take a path that a live task already owns. This read is
    # under .plan.lock, but task writers use .lock; validate() catches the
    # narrow cross-lock race afterwards.
    for existing in all_tasks(root):
        if existing["meta"].get("status") in FINAL:
            continue
        existing_owns = [
            normalized_owns(value)
            for value in existing["meta"].get("owns", "").split(",")
            if value.strip()
        ]
        for key, child in by_key.items():
            for path in child["owns"]:
                for owned in existing_owns:
                    if paths_overlap(path, owned):
                        plan_error(
                            f"{key} path {path!r} is already owned by live task "
                            f"{existing['meta'].get('id')} ({owned})"
                        )

    lanes = plan.get("lanes", [])
    if not isinstance(lanes, list):
        plan_error("'lanes' must be a list")
    lane_names: set[str] = set()
    assigned: dict[str, str] = {}
    normalized_lanes: list[dict] = []
    for index, lane in enumerate(lanes):
        if not isinstance(lane, dict):
            plan_error(f"lanes[{index}] must be an object")
        name = str(lane.get("name", "")).strip()
        if not name or name in lane_names:
            plan_error(f"lane name {name!r} must be unique and non-empty")
        lane_names.add(name)
        tasks_in_lane = lane.get("tasks", [])
        if not isinstance(tasks_in_lane, list):
            plan_error(f"lane {name}.tasks must be a list")
        for key in tasks_in_lane:
            if key not in by_key:
                plan_error(f"lane {name} names missing task {key!r}")
            if key in assigned:
                plan_error(f"{key} is in both {assigned[key]} and {name}")
            child_lane = by_key[key]["lane"]
            if child_lane and child_lane != name:
                plan_error(f"{key}.lane is {child_lane!r}, not {name!r}")
            by_key[key]["lane"] = name
            assigned[key] = name
        normalized_lanes.append({"name": name, "tasks": list(tasks_in_lane)})
    for key, child in by_key.items():
        if child["lane"] and lane_names and child["lane"] not in lane_names:
            plan_error(f"{key}.lane {child['lane']!r} is not declared in lanes")
        if child["lane"] and not lane_names:
            plan_error(f"{key}.lane is set but 'lanes' is empty")
        if not child["lane"] and lane_names and key not in assigned:
            plan_error(f"{key} is not assigned to a declared lane")

    return {
        "goal": {
            "title": str(goal_conf["title"]).strip(),
            "project": str(goal_conf.get("project", "general")).strip() or "general",
            "priority": goal_priority,
            "scope": str(goal_conf["scope"]).strip(),
            "acceptance": str(goal_conf["acceptance"]).strip(),
            "tags": str(goal_conf.get("tags", "goal")).strip(),
            "session": str(goal_conf.get("session", os.environ.get("OPENCODE_SESSION_ID", ""))),
            "autorun": plan_bool(goal_conf.get("autorun", False), "autorun"),
            "max_continuations": max_continuations,
        },
        "children": [by_key[key] for key in order],
        "lanes": normalized_lanes,
    }


def print_plan(plan: dict) -> None:
    goal = plan["goal"]
    print(f"goal: {goal['title']} ({goal['project']}, priority {goal['priority']})")
    print(f"scope: {goal['scope']}")
    print(f"acceptance: {goal['acceptance']}")
    print(
        f"autorun: {goal['autorun']}   max_continuations: {goal['max_continuations']}"
    )
    print(f"children: {len(plan['children'])}")
    for child in plan["children"]:
        deps = ", ".join(child["depends_on"]) or "-"
        owns = ", ".join(child["owns"]) or "-"
        print(
            f"  {child['key']:<20} p{child['priority']} "
            f"lane={child['lane'] or '-':<10} deps={deps} owns={owns}"
        )
    if plan["lanes"]:
        print("lanes:")
        for lane in plan["lanes"]:
            print(f"  {lane['name']}: {', '.join(lane['tasks'])}")


def create_plan(
    root: Path,
    plan: dict,
    dry_run: bool = False,
    as_json: bool = False,
    autorun_override: bool | None = None,
) -> dict:
    if dry_run:
        normalized = validate_plan(root, plan)
        if autorun_override is not None:
            normalized["goal"]["autorun"] = autorun_override
        if not as_json:
            print_plan(normalized)
            print("plan: valid (dry run, nothing written)")
        return {
            "goal": None,
            "goal_config": normalized["goal"],
            "children": {},
            "lanes": normalized["lanes"],
        }

    # Serialize validation + creation. This is process-atomic for files we have
    # tracked; not crash-atomic: a killed process can leave a partial plan.
    with locked(root, ".plan.lock"):
        normalized = validate_plan(root, plan)
        if autorun_override is not None:
            normalized["goal"]["autorun"] = autorun_override
        return _write_plan(root, normalized)


def _write_plan(root: Path, normalized: dict) -> dict:
    goal_conf = normalized["goal"]
    goal = goal_task(
        root,
        goal_conf["title"],
        project=goal_conf["project"],
        priority=goal_conf["priority"],
        scope=goal_conf["scope"],
        acceptance=goal_conf["acceptance"],
        tags=goal_conf["tags"],
        session=goal_conf["session"],
        autorun=goal_conf["autorun"],
        max_continuations=goal_conf["max_continuations"],
    )
    created = [goal["path"]]
    mapping: dict[str, str] = {}
    try:
        for child in normalized["children"]:
            deps = [mapping[key] for key in child["depends_on"]]
            task = new_task(
                root,
                child["title"],
                project=goal_conf["project"],
                priority=child["priority"],
                depends_on=",".join(deps),
                scope=child["scope"],
                acceptance=child["acceptance"],
                tags=child["tags"],
                parent=goal["meta"]["id"],
                lane=child["lane"],
                owns=",".join(child["owns"]),
            )
            mapping[child["key"]] = task["meta"]["id"]
            created.append(task["path"])
    except BaseException:
        # Tracked paths plus any child that reached disk before its board write.
        for candidate in all_tasks(root):
            meta = candidate["meta"]
            if (
                meta.get("id") == goal["meta"]["id"]
                or meta.get("parent") == goal["meta"]["id"]
            ):
                created.append(candidate["path"])
        for path in created:
            try:
                path.unlink()
            except OSError as exc:
                print(f"plan: cleanup failed for {path}: {exc}", file=sys.stderr)
        try:
            write_board(root)
        except OSError as exc:
            print(f"plan: board cleanup failed: {exc}", file=sys.stderr)
        raise
    result = {
        "goal": goal["meta"]["id"],
        "children": mapping,
        "lanes": normalized["lanes"],
    }
    return result


def normalized_path(value: str) -> str:
    return str(Path(value).expanduser().resolve()) if value else ""


def claim_task(
    root: Path,
    key: str,
    *,
    owner: str,
    branch: str = "",
    base: str = "",
    worktree: str = "",
    repo: Path | None = None,
    force: bool = False,
) -> dict:
    with locked(root):
        task = find_task(root, key)
        if task["meta"].get("kind") == "goal":
            raise SystemExit(
                f"error: {task['meta']['id']} is a goal; claim its child tasks"
            )
        planned_repo = repo or (Path(worktree) if worktree else None) or Path.cwd()
        validate_task_plan(task, planned_repo)
        status = task["meta"].get("status", "ready")
        if status == "active" and task["meta"].get("owner") == owner:
            print(f"already claimed by {owner}: {task['meta']['id']}")
            return task
        if status not in ("ready", "inbox", "blocked"):
            raise SystemExit(
                f"error: {task['meta']['id']} is {status}; claim only ready/inbox/blocked"
            )
        if status == "blocked" and not force:
            raise SystemExit(
                f"error: {task['meta']['id']} is blocked: "
                f"{task['meta'].get('blocked_reason', 'no reason')}"
            )
        unblocked, open_deps = is_unblocked(root, task)
        if not unblocked and not force:
            raise SystemExit("error: open dependencies: " + ", ".join(open_deps))
        worktree = normalized_path(worktree)
        for other in all_tasks(root):
            if other["meta"].get("id") == task["meta"].get("id"):
                continue
            if other["meta"].get("status") not in ("active", "review"):
                continue
            for field, value, other_value in (
                ("branch", branch, other["meta"].get("branch", "")),
                ("worktree", worktree, normalized_path(other["meta"].get("worktree", ""))),
            ):
                if value and other_value == value:
                    raise SystemExit(
                        f"error: {field} {value!r} is already owned by "
                        f"{other['meta'].get('id')}"
                    )
        task["meta"]["status"] = "active"
        task["meta"]["owner"] = owner
        if branch:
            task["meta"]["branch"] = branch
        if base:
            task["meta"]["base"] = base
        if worktree:
            task["meta"]["worktree"] = worktree
        task["meta"]["blocked_reason"] = ""
        append_log(task, f"claimed by {owner}")
        write_task(task)
    write_board(root)
    return task


PLACEHOLDER_EVIDENCE = {"none", "n/a", "na", "tbd", "ok", "pass", "done", "tests pass"}


def valid_evidence(text: str) -> bool:
    normalized = " ".join(text.lower().split()).strip(" .")
    return bool(normalized) and normalized not in PLACEHOLDER_EVIDENCE


def unchecked_acceptance(task: dict) -> list[str]:
    """Acceptance items that still say "- [ ]"; done means all of them checked."""
    section = task["sections"].get("Acceptance", "")
    return [
        line.strip()
        for line in section.splitlines()
        if line.strip().startswith("- [ ]")
    ]


def deferred_sections(task: dict) -> list[str]:
    """Named follow-up lists that still contain work; done means none."""
    names = ("Deferred", "Follow-ups", "Followups")
    return [
        name
        for name, body in task["sections"].items()
        if name in names
        and body.strip().lower() not in ("", "none", "n/a", "no")
    ]


def set_status(
    root: Path,
    key: str,
    status: str,
    *,
    note: str = "",
    evidence: str = "",
    repo: Path | None = None,
) -> dict:
    if status not in STATUSES:
        raise SystemExit(f"error: unknown status {status!r}")
    with locked(root):
        task = find_task(root, key)
        was_done = task["meta"].get("status") == "done"
        if status == "review" and task["meta"].get("status") != "review":
            worktree = task["meta"].get("worktree", "")
            target = (
                repo
                or (Path(worktree).expanduser() if worktree else None)
                or Path.cwd()
            )
            if validate_review(root, task["meta"]["id"], Path(target)) != 0:
                raise SystemExit(
                    "error: review gate blocked; record a PASS artifact with "
                    "tasks.py review --run"
                )
        if status == "done" and not was_done:
            if task["meta"].get("status") not in ("active", "review"):
                raise SystemExit(
                    "error: done needs a claimed task in active/review, not "
                    f"{task['meta'].get('status')}"
                )
            acceptance = task["sections"].get("Acceptance", "").strip()
            if not acceptance:
                raise SystemExit("error: done needs an Acceptance section")
            if "TBD" in acceptance.upper():
                raise SystemExit(
                    "error: done needs concrete acceptance, not a TBD placeholder"
                )
            deferred = deferred_sections(task)
            if deferred:
                raise SystemExit(
                    "error: done has a non-empty deferred section: "
                    + ", ".join(deferred)
                )
            unchecked = unchecked_acceptance(task)
            if unchecked:
                preview = "; ".join(unchecked[:3])
                raise SystemExit(
                    "error: done needs every acceptance item checked "
                    f"(still open: {preview})"
                )
            if not valid_evidence(evidence):
                raise SystemExit(
                    "error: done needs real evidence, not a placeholder "
                    "('none', 'ok', 'tests pass', ...)"
                )
            if task["meta"].get("kind") != "goal":
                worktree = task["meta"].get("worktree", "")
                target = (
                    repo
                    or (Path(worktree).expanduser() if worktree else None)
                    or Path.cwd()
                )
                if validate_review(root, task["meta"]["id"], Path(target)) != 0:
                    raise SystemExit(
                        "error: done needs a PASS review artifact at the current "
                        "HEAD and diff"
                    )
            if task["meta"].get("kind") == "goal":
                children = children_of(root, task["meta"]["id"])
                if not children:
                    raise SystemExit("error: a goal needs at least one child task")
                open_children = [
                    child["meta"]["id"]
                    for child in children
                    if child["meta"].get("status") not in FINAL
                ]
                if open_children:
                    raise SystemExit(
                        "error: goal has open children: " + ", ".join(open_children)
                    )
        task["meta"]["status"] = status
        if status == "blocked":
            task["meta"]["blocked_reason"] = note or "blocked"
        elif status != "blocked":
            task["meta"]["blocked_reason"] = ""
        if status == "done":
            if not evidence.strip():
                raise SystemExit("error: done needs --evidence (a check, result, or [T])")
            current = task["sections"].get("Evidence", "").rstrip()
            task["sections"]["Evidence"] = (current + "\n" + evidence.strip()).strip()
            if not was_done:
                append_metric(root, task)
        if note:
            append_log(task, f"{status}: {note}")
        else:
            append_log(task, status)
        write_task(task)
    write_board(root)
    return task


def append_metric(root: Path, task: dict) -> None:
    path = root / "metrics/workflow-log.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    task_id = task["meta"].get("id", "")
    if path.exists():
        with path.open(newline="") as handle:
            if any(row.get("task") == task_id for row in csv.DictReader(handle)):
                return
    new = not path.exists() or path.stat().st_size == 0
    meta = task["meta"]
    created = meta.get("created", "")
    done = today()
    try:
        days = (dt.date.fromisoformat(done) - dt.date.fromisoformat(created)).days
    except ValueError:
        days = ""
    evidence = " ".join(task["sections"].get("Evidence", "").split())[:160]
    with path.open("a", newline="") as handle:
        writer = csv.writer(handle)
        if new:
            writer.writerow(
                ["date", "task", "project", "created", "days", "status", "evidence"]
            )
        writer.writerow(
            [done, task_id, meta.get("project", ""), created, days, "done", evidence]
        )


REVIEW_VERDICTS = ("PASS", "UNVERIFIED")
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def review_path(root: Path, task_id: str) -> Path:
    return root / "work/reviews" / f"{task_id}.json"


def plan_verify(task: dict) -> str:
    values = [
        match.group(1).strip()
        for line in task["sections"].get("Plan", "").splitlines()
        if (match := re.match(r"^Verify:\s*(.+?)\s*$", line))
    ]
    if len(values) != 1:
        raise SystemExit(
            f"review: {task['meta'].get('id')} needs exactly one 'Verify:' line in its Plan"
        )
    return values[0]


def plan_data_shape(task: dict) -> str:
    values = [
        match.group(1).strip()
        for line in task["sections"].get("Plan", "").splitlines()
        if (match := re.match(r"^Data shape:\s*(.+?)\s*$", line))
    ]
    if len(values) != 1:
        raise SystemExit(
            f"claim: {task['meta'].get('id')} needs exactly one 'Data shape:' line in its Plan"
        )
    return values[0]


DECLARATION_PATTERNS = {
    ".py": (r"^\s*(?:async\s+)?def {symbol}\(", r"^\s*class {symbol}\b"),
    ".js": (
        r"^\s*export\s+(?:default\s+)?(?:async\s+)?(?:function|class|const|let|var)\s+{symbol}\b",
    ),
    ".mjs": (
        r"^\s*export\s+(?:default\s+)?(?:async\s+)?(?:function|class|const|let|var)\s+{symbol}\b",
    ),
    ".cjs": (
        r"^\s*export\s+(?:default\s+)?(?:async\s+)?(?:function|class|const|let|var)\s+{symbol}\b",
    ),
    ".jsx": (
        r"^\s*export\s+(?:default\s+)?(?:async\s+)?(?:function|class|const|let|var)\s+{symbol}\b",
    ),
    ".ts": (
        r"^\s*export\s+(?:default\s+)?(?:async\s+)?(?:function|class|const|let|var|type|interface)\s+{symbol}\b",
    ),
    ".tsx": (
        r"^\s*export\s+(?:default\s+)?(?:async\s+)?(?:function|class|const|let|var|type|interface)\s+{symbol}\b",
    ),
}


def validate_data_shape(value: str, task: dict, repo: Path) -> None:
    task_id = task["meta"].get("id")
    if value.startswith("{") or value.startswith("["):
        try:
            data = json.loads(value)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"claim: {task_id} Data shape is not valid JSON: {exc}")
        if not isinstance(data, (dict, list)) or not data:
            raise SystemExit(
                f"claim: {task_id} Data shape JSON must be a non-empty object or array"
            )
        return
    if value.startswith("none"):
        match = re.fullmatch(r"none\s*-\s*(\S.*)", value)
        if not match:
            raise SystemExit(
                f"claim: {task_id} Data shape 'none' needs a concrete reason: none - <reason>"
            )
        tags = {
            tag.strip()
            for tag in task["meta"].get("tags", "").split(",")
            if tag.strip()
        }
        if not tags & {"docs", "chore"}:
            raise SystemExit(
                f"claim: {task_id} may use 'none' only with a docs or chore tag"
            )
        return
    match = re.fullmatch(r"path\s+(\S+)#([A-Za-z_$][\w$]*)", value)
    if not match:
        raise SystemExit(
            f"claim: {task_id} Data shape must be JSON, 'path <file>#<symbol>', "
            "or 'none - <reason>'"
        )
    relative, symbol = match.groups()
    raw = Path(relative)
    if raw.is_absolute() or ".." in raw.parts:
        raise SystemExit(
            f"claim: {task_id} Data shape path must be repo-relative: {relative}"
        )
    repo = repo.resolve()
    path = (repo / raw).resolve()
    if not inside(path, repo) or not path.is_file():
        raise SystemExit(
            f"claim: {task_id} Data shape path is missing inside the repository: {relative}"
        )
    patterns = DECLARATION_PATTERNS.get(path.suffix)
    if not patterns:
        raise SystemExit(
            f"claim: {task_id} Data shape path supports Python and JavaScript/TypeScript files"
        )
    anchor = re.escape(symbol)
    for line in path.read_text().splitlines():
        for pattern in patterns:
            if re.match(pattern.format(symbol=anchor), line):
                return
    raise SystemExit(
        f"claim: {task_id} Data shape symbol {symbol!r} is not declared in {relative}"
    )


def validate_task_plan(task: dict, repo: Path) -> None:
    validate_data_shape(plan_data_shape(task), task, repo)
    verify = plan_verify(task)
    validate_command(command_argv(verify, "claim"), repo.resolve(), "claim")


def command_argv(command: str, label: str = "review") -> list[str]:
    try:
        argv = shlex.split(command)
    except ValueError as exc:
        raise SystemExit(f"{label}: cannot parse command {command!r}: {exc}")
    if not argv:
        raise SystemExit(f"{label}: empty command")
    return argv


def allowed_command(argv: list[str]) -> bool:
    program = argv[0]
    if program == "npm":
        if argv[1:] == ["test"]:
            return True
        return (
            len(argv) >= 3
            and argv[1] == "run"
            and (argv[2].startswith("test:") or argv[2].startswith("lint:"))
        )
    if program == "node":
        if len(argv) != 2:
            return False
        return (
            (argv[1].startswith("tests/") and argv[1].endswith(".test.mjs"))
            or argv[1] == ".opencode/skills/verify-libreharness/scripts/smoke.mjs"
        )
    if program == "python3":
        return len(argv) >= 3 and argv[1] == "-m" and argv[2] == "unittest"
    if program == "pytest":
        return True
    if program == "ruff":
        return len(argv) >= 2 and argv[1] == "check"
    if program == "make":
        return argv[1:] == ["check"]
    if program == "cargo":
        return argv[1:] == ["test"]
    if program == "go":
        return argv[1:] == ["test", "./..."]
    if program == "npx":
        return (
            len(argv) >= 3
            and argv[1] == "--no-install"
            and argv[2] == "markdownlint-cli2"
        )
    return False


def inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def validate_command(argv: list[str], repo: Path, label: str = "review") -> list[str]:
    repo = repo.resolve()
    if not allowed_command(argv):
        raise SystemExit(
            f"{label}: command is not on the project-verification allowlist: "
            + " ".join(argv)
        )
    for argument in argv[1:]:
        if argument.startswith("-") or "/" not in argument:
            continue
        raw = Path(argument)
        if any(character in argument for character in "*?["):
            prefix = argument.split("*")[0].split("?")[0].split("[")[0]
            raw = Path(prefix or ".")
        resolved = raw.resolve() if raw.is_absolute() else (repo / raw).resolve()
        if not inside(resolved, repo):
            raise SystemExit(
                f"{label}: path outside the repository: {argument}"
            )
    return argv


def git_head(repo: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise SystemExit(f"review: not a git repository: {repo}")
    head = result.stdout.strip()
    if not SHA40.match(head):
        raise SystemExit(f"review: cannot resolve HEAD in {repo}")
    return head


def git_bytes(repo: Path, args: list[str], label: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
    )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", "replace").strip()
        raise SystemExit(f"review: cannot {label}: {detail or 'git failed'}")
    return result.stdout


def review_diff(repo: Path) -> str:
    repo = repo.resolve()
    head = git_head(repo)
    diff = git_bytes(
        repo,
        ["diff", "--binary", "--no-ext-diff", "HEAD", "--"],
        "read the reviewed diff",
    )
    untracked = git_bytes(
        repo,
        ["ls-files", "--others", "--exclude-standard", "-z"],
        "list untracked files",
    )
    digest = hashlib.sha256()
    digest.update(b"head\0")
    digest.update(head.encode("ascii"))
    digest.update(b"\0diff\0")
    digest.update(diff)
    digest.update(b"\0untracked\0")
    for raw in sorted(item for item in untracked.split(b"\0") if item):
        relative = os.fsdecode(raw)
        path = (repo / relative).resolve()
        if not inside(path, repo) or not path.is_file():
            raise SystemExit(f"review: untracked path is not a repository file: {relative}")
        object_id = git_bytes(
            repo,
            ["hash-object", "--no-filters", "--", relative],
            "hash an untracked file",
        ).strip()
        digest.update(raw)
        digest.update(b"\0")
        digest.update(object_id)
        digest.update(b"\0")
    return digest.hexdigest()


def validate_review(root: Path, task_id: str, repo: Path) -> int:
    path = review_path(root, task_id)
    problems: list[str] = []
    data = None
    if not path.is_file():
        problems.append(f"missing review artifact: {path}")
    else:
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            problems.append(f"malformed review artifact {path}: {exc}")
    if data is not None:
        if not isinstance(data, dict):
            problems.append("review artifact must be a JSON object")
            data = None
    if data is not None:
        if data.get("task") != task_id:
            problems.append(
                f"artifact task {data.get('task')!r} does not match {task_id!r}"
            )
        head = data.get("head")
        if not isinstance(head, str) or not SHA40.match(head):
            problems.append("artifact head must be a full 40-character git sha")
        else:
            current_head = git_head(repo)
            if head != current_head:
                problems.append(
                    f"artifact head {head} is stale; current HEAD is {current_head}"
                )
        diff_sha256 = data.get("diff_sha256")
        if not isinstance(diff_sha256, str) or not SHA256.match(diff_sha256):
            problems.append("artifact diff_sha256 must be a 64-character hex digest")
        elif diff_sha256 != review_diff(repo):
            problems.append("artifact diff is stale; the working diff changed")
        verdict = data.get("verdict")
        if verdict not in REVIEW_VERDICTS:
            problems.append(f"unknown verdict {verdict!r}")
        checks = data.get("checks")
        if not isinstance(checks, list):
            problems.append("artifact checks must be a list")
            checks = []
        seen_verify = 0
        verify = ""
        try:
            task = find_task(root, task_id)
            verify = plan_verify(task)
        except SystemExit as exc:
            problems.append(str(exc))
        for item in checks:
            if not isinstance(item, dict):
                problems.append("each check must be an object")
                continue
            command = item.get("command")
            exit_code = item.get("exit")
            if not isinstance(command, str) or not command.strip():
                problems.append("each check needs a command")
                continue
            if isinstance(exit_code, bool) or not isinstance(exit_code, int):
                problems.append(f"{command}: exit must be an integer")
                continue
            if exit_code != 0:
                problems.append(f"{command}: observed exit {exit_code}")
            if verify and command == verify:
                seen_verify += 1
        if verdict == "PASS":
            if not checks:
                problems.append("PASS needs at least one observed check")
            if verify and seen_verify != 1:
                problems.append(
                    f"PASS needs the task Verify command exactly once: {verify}"
                )
        elif verdict == "UNVERIFIED":
            problems.append("verdict is UNVERIFIED; close and shipping are blocked")
    if problems:
        print(f"review: UNVERIFIED: {task_id}")
        for problem in problems:
            print(f"- {problem}")
        return 1
    print(f"review: PASS {task_id} at {data['head']}")
    return 0


def review_task(
    root: Path,
    key: str,
    *,
    repo: Path,
    runs: list[str] | None = None,
    unverify: bool = False,
) -> int:
    repo = repo.resolve()
    if not (repo / ".git").exists() and not (repo / ".git").is_file():
        raise SystemExit(f"review: not a git repository: {repo}")
    task = find_task(root, key)
    task_id = task["meta"]["id"]
    if unverify:
        head = git_head(repo)
        checks: list[dict] = []
        path = review_path(root, task_id)
        try:
            previous = json.loads(path.read_text())
            if isinstance(previous, dict) and isinstance(previous.get("checks"), list):
                checks = previous["checks"]
        except (OSError, json.JSONDecodeError):
            pass
        atomic_write(
            path,
            json.dumps(
                {
                    "task": task_id,
                    "head": head,
                    "diff_sha256": review_diff(repo),
                    "recorded_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                    "verdict": "UNVERIFIED",
                    "checks": checks,
                },
                indent=2,
            )
            + "\n",
        )
        return validate_review(root, task_id, repo)
    runs = list(runs or [])
    if not runs:
        return validate_review(root, task_id, repo)
    verify = plan_verify(task)
    validated: list[tuple[str, list[str]]] = []
    for command in runs:
        argv = command_argv(command)
        validate_command(argv, repo)
        validated.append((command.strip(), argv))
    if not any(command == verify for command, _ in validated):
        raise SystemExit(
            "review: the task Verify command must be one of --run: " + verify
        )
    head_before = git_head(repo)
    checks = []
    for command, argv in validated:
        result = subprocess.run(argv, cwd=repo)
        checks.append({"command": command, "exit": result.returncode})
        print(f"review: {command} -> exit {result.returncode}")
    head_after = git_head(repo)
    passed = head_before == head_after and all(
        item["exit"] == 0 for item in checks
    )
    atomic_write(
        review_path(root, task_id),
        json.dumps(
            {
                "task": task_id,
                "head": head_after,
                "diff_sha256": review_diff(repo),
                "recorded_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "verdict": "PASS" if passed else "UNVERIFIED",
                "checks": checks,
            },
            indent=2,
        )
        + "\n",
    )
    return validate_review(root, task_id, repo)


def priority_of(task: dict) -> int:
    try:
        return int(task["meta"].get("priority", "2") or 2)
    except ValueError:
        return 2


def write_board(root: Path) -> None:
    path = root / "work/BOARD.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    tasks = all_tasks(root)
    lines = [
        "# Work board",
        "",
        "Generated by `bin/tasks.py`; edit task files under `work/tasks/`, not this file.",
        f"Updated: {today()}",
        "",
    ]
    for status, title in (
        ("active", "Active"),
        ("review", "Review / integrate"),
        ("ready", "Ready"),
        ("blocked", "Blocked"),
        ("inbox", "Inbox"),
        ("done", "Done (newest 10)"),
        ("abandoned", "Abandoned (newest 5)"),
    ):
        items = [task for task in tasks if task["meta"].get("status") == status]
        items.sort(
            key=lambda task: (
                priority_of(task),
                task["meta"].get("updated", ""),
            )
        )
        if status == "done":
            items = sorted(items, key=lambda task: task["meta"].get("updated", ""), reverse=True)[:10]
        if status == "abandoned":
            items = sorted(items, key=lambda task: task["meta"].get("updated", ""), reverse=True)[:5]
        lines += [f"## {title} ({len(items)})", ""]
        if not items:
            lines += ["_none_", ""]
            continue
        lines.append("| P | Task | Project | Owner | Branch | Updated |")
        lines.append("|---|---|---|---|---|---|")
        for task in items:
            meta = task["meta"]
            title_text = meta.get("title", task["title"]).replace("|", "\\|")
            lines.append(
                f"| {meta.get('priority', '2')} | `{meta.get('id', task['path'].stem)}` "
                f"{title_text} | {meta.get('project', '')} | {meta.get('owner', '')} "
                f"| {meta.get('branch', '')} | {meta.get('updated', '')} |"
            )
        lines.append("")
    atomic_write(path, "\n".join(lines).rstrip() + "\n")


def print_tasks(tasks: list[dict]) -> None:
    if not tasks:
        print("no tasks")
        return
    width = max(44, max(len(task["meta"].get("id", task["path"].stem)) for task in tasks) + 2)
    print(f"{'id':<{width}}{'status':<10}{'p':>2}  {'project':<16} title")
    for task in tasks:
        meta = task["meta"]
        print(
            f"{meta.get('id', task['path'].stem):<{width}}{meta.get('status', ''):<10}"
            f"{meta.get('priority', '2'):>2}  {meta.get('project', ''):<16} {meta.get('title', task['title'])}"
        )


def packet(task: dict) -> str:
    meta = task["meta"]
    lines = [
        f"TASK {meta.get('id', task['path'].stem)} — {meta.get('title', task['title'])}",
        f"Project: {meta.get('project', '')}   Status: {meta.get('status', '')}   "
        f"Priority: {meta.get('priority', '2')}",
        f"Owner: {meta.get('owner', '')}   Branch: {meta.get('branch', '')}   "
        f"Worktree: {meta.get('worktree', '')}",
        f"Base: {meta.get('base', '') or 'not recorded'}",
        f"Depends on: {meta.get('depends_on', '') or 'none'}",
        f"Task file: {task['path']}",
        "",
    ]
    for name in SECTION_ORDER:
        if name == "Log":
            continue
        value = task["sections"].get(name, "").strip()
        if value:
            lines += [f"## {name}", value, ""]
    log = task["sections"].get("Log", "").strip()
    if log:
        lines += ["## Recent log", "\n".join(log.splitlines()[-5:]), ""]
    return "\n".join(lines).rstrip()


def summary(task: dict) -> str:
    meta = task["meta"]
    parts = [
        f"{meta.get('id', '')}: {meta.get('title', task['title'])}",
        f"Scope: {' '.join(task['sections'].get('Scope', '').split())}",
        f"Acceptance: {' '.join(task['sections'].get('Acceptance', '').split())}",
        f"Evidence: {' '.join(task['sections'].get('Evidence', '').split()) or 'none recorded'}",
    ]
    return "\n".join(parts)


def validate(root: Path) -> int:
    problems: list[str] = []
    tasks = all_tasks(root)
    by_id: dict[str, dict] = {}
    for task in tasks:
        meta = task["meta"]
        task_id = meta.get("id", task["path"].stem)
        if task_id != task["path"].stem:
            problems.append(f"{task['path'].name}: id {task_id!r} does not match filename")
        if task_id in by_id:
            problems.append(f"duplicate id: {task_id}")
        by_id[task_id] = task
        if meta.get("status") not in STATUSES:
            problems.append(f"{task_id}: invalid status {meta.get('status')!r}")
        if meta.get("kind", "task") not in ("task", "goal"):
            problems.append(f"{task_id}: invalid kind {meta.get('kind')!r}")
        if meta.get("status") == "active" and not meta.get("owner"):
            problems.append(f"{task_id}: active without owner")
        if meta.get("status") == "done" and not task["sections"].get("Evidence", "").strip():
            problems.append(f"{task_id}: done without Evidence")
    for task_id, task in by_id.items():
        meta = task["meta"]
        parent = meta.get("parent", "")
        if parent:
            if parent not in by_id:
                problems.append(f"{task_id}: parent {parent} is missing")
            elif by_id[parent]["meta"].get("kind") != "goal":
                problems.append(f"{task_id}: parent {parent} is not a goal")
        if meta.get("kind") == "goal" and parent:
            problems.append(f"{task_id}: a goal cannot have a parent")
        if meta.get("kind") == "goal" and meta.get("status") == "done":
            children = [
                child
                for child in by_id.values()
                if child["meta"].get("parent") == task_id
            ]
            if not children:
                problems.append(f"{task_id}: goal has no children")
            for child in children:
                if child["meta"].get("status") not in FINAL:
                    problems.append(
                        f"{task_id}: goal is done but child {child['meta']['id']} is {child['meta'].get('status')}"
                    )
    owners: dict[tuple[str, str], str] = {}
    for task_id, task in by_id.items():
        if task["meta"].get("status") not in ("active", "review"):
            continue
        for field in ("branch", "worktree"):
            value = task["meta"].get(field, "")
            if field == "worktree":
                value = normalized_path(value)
            if not value:
                continue
            key = (field, value)
            if key in owners:
                problems.append(
                    f"{task_id}: {field} {value!r} is already owned by {owners[key]}"
                )
            else:
                owners[key] = task_id

    owned_paths: list[tuple[str, str]] = []
    for task_id, task in by_id.items():
        if task["meta"].get("status") in FINAL:
            continue
        for value in task["meta"].get("owns", "").split(","):
            path = normalized_owns(value)
            if not path:
                continue
            for other_id, other_path in owned_paths:
                if other_id != task_id and paths_overlap(path, other_path):
                    problems.append(
                        f"{task_id}: path {path!r} overlaps {other_path!r} "
                        f"owned by {other_id}"
                    )
            owned_paths.append((task_id, path))

    graph: dict[str, list[str]] = {}
    for task_id, task in by_id.items():
        graph[task_id] = []
        for dep in dependencies(task):
            if dep not in by_id:
                problems.append(f"{task_id}: depends on missing {dep}")
            else:
                graph[task_id].append(dep)

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str, trail: list[str]) -> None:
        if node in visited:
            return
        if node in visiting:
            problems.append("dependency cycle: " + " -> ".join(trail + [node]))
            return
        visiting.add(node)
        for dep in graph.get(node, []):
            visit(dep, trail + [node])
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node, [])

    if problems:
        print("validation: FAIL")
        for problem in problems:
            print(f"- {problem}")
        return 1
    print(f"validation: OK ({len(tasks)} tasks)")
    return 0


def metric_days(root: Path) -> dict[str, int]:
    path = root / "metrics/workflow-log.csv"
    if not path.is_file():
        return {}
    result: dict[str, int] = {}
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                result[row.get("task", "")] = int(row.get("days", ""))
            except (TypeError, ValueError):
                continue
    return result


def report(root: Path, as_json: bool = False) -> int:
    tasks = all_tasks(root)
    counts = {status: 0 for status in STATUSES}
    projects: dict[str, int] = {}
    cycle_days: list[int] = []
    done_days = metric_days(root)
    for task in tasks:
        status = task["meta"].get("status", "")
        if status in counts:
            counts[status] += 1
        project = task["meta"].get("project", "")
        projects[project] = projects.get(project, 0) + 1
        if status == "done":
            if task["meta"].get("id") in done_days:
                cycle_days.append(done_days[task["meta"]["id"]])
                continue
            try:
                cycle_days.append(
                    (
                        dt.date.fromisoformat(task["meta"].get("updated", ""))
                        - dt.date.fromisoformat(task["meta"].get("created", ""))
                    ).days
                )
            except ValueError:
                pass
    active = [task for task in tasks if task["meta"].get("status") == "active"]
    oldest = ""
    if active:
        oldest = min(task["meta"].get("created", "") for task in active)
    result = {
        "tasks": len(tasks),
        "counts": counts,
        "projects": projects,
        "active_oldest": oldest,
        "median_cycle_days": statistics.median(cycle_days) if cycle_days else None,
        "wip_limit": 3,
        "wip_ok": len(active) <= 3,
    }
    if as_json:
        print(json.dumps(result, indent=2))
        return 0
    print(f"tasks: {len(tasks)}")
    print("  " + "  ".join(f"{status}: {counts[status]}" for status in STATUSES))
    if projects:
        print("projects: " + ", ".join(f"{name} {count}" for name, count in sorted(projects.items())))
    print(f"WIP: {len(active)}/3" + ("" if result["wip_ok"] else " — over limit"))
    if oldest:
        print(f"oldest active: {oldest}")
    if result["median_cycle_days"] is not None:
        print(f"median cycle (done): {result['median_cycle_days']:.1f} days")
    return 0


def run_git(args: list[str], cwd: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(cwd), *args],
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise SystemExit(f"error: git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout.strip()


def lane_targets(
    task: dict,
    repo: Path,
    *,
    name: str = "",
    path: str = "",
) -> tuple[str, str, Path]:
    repo = repo.resolve()
    name = slugify(name or task["meta"].get("id", "task").split("-", 1)[-1])
    branch = f"feature/{name}"
    worktree = Path(path).expanduser() if path else repo.parent / f"{repo.name}-{name}"
    return name, branch, worktree


def lane_task(
    root: Path,
    key: str,
    *,
    repo: Path,
    name: str = "",
    base: str = "",
    path: str = "",
    setup: str = "",
    owner: str = "",
    quiet: bool = False,
) -> dict:
    task = find_task(root, key)
    if task["meta"].get("kind") == "goal":
        raise SystemExit("error: a goal is an umbrella; lane its child tasks")
    status = task["meta"].get("status", "ready")
    if status not in ("ready", "inbox"):
        raise SystemExit(f"error: {task['meta']['id']} is {status}; lane needs ready/inbox")
    unblocked, open_deps = is_unblocked(root, task)
    if not unblocked:
        raise SystemExit("error: open dependencies: " + ", ".join(open_deps))
    repo = repo.resolve()
    if not (repo / ".git").exists() and not (repo / ".git").is_file():
        raise SystemExit(f"error: {repo} is not a git repository")
    name, branch, worktree = lane_targets(task, repo, name=name, path=path)
    base = base or run_git(["rev-parse", "--abbrev-ref", "HEAD"], repo)
    if base == "HEAD":
        base = run_git(["rev-parse", "HEAD"], repo)
    if worktree.exists():
        raise SystemExit(f"error: worktree path already exists: {worktree}")
    existing = run_git(["branch", "--list", branch], repo)
    if existing:
        raise SystemExit(f"error: branch already exists: {branch}")
    run_git(["worktree", "add", "-b", branch, str(worktree), base], repo)
    owner = owner or name
    try:
        claim_task(
            root,
            key,
            owner=owner,
            branch=branch,
            base=base,
            worktree=str(worktree),
            repo=repo,
        )
    except SystemExit as exc:
        # The worktree is new and clean; remove it *and its new branch* so a
        # retry is not blocked. Check the removal instead of claiming success.
        removed = subprocess.run(
            ["git", "-C", str(repo), "worktree", "remove", str(worktree)],
            text=True,
            capture_output=True,
        )
        if removed.returncode != 0:
            print(
                f"claim failed and worktree cleanup failed ({removed.stderr.strip()}): {worktree}",
                file=sys.stderr,
            )
        deleted = subprocess.run(
            ["git", "-C", str(repo), "branch", "-D", branch],
            text=True,
            capture_output=True,
        )
        if deleted.returncode != 0:
            print(
                f"claim failed and branch cleanup failed ({deleted.stderr.strip()}): {branch}",
                file=sys.stderr,
            )
        if removed.returncode == 0 and deleted.returncode == 0:
            print(f"claim failed; cleaned up {worktree} and {branch}: {exc}", file=sys.stderr)
        else:
            print(f"claim failed; cleanup incomplete: {exc}", file=sys.stderr)
        raise
    if setup:
        result = subprocess.run(
            shlex.split(setup),
            cwd=worktree,
            text=True,
        )
        if result.returncode != 0:
            raise SystemExit(f"error: setup failed ({setup}) in {worktree}")
    if not quiet:
        print(f"lane: {branch} -> {worktree}")
        print()
        print(packet(find_task(root, key)))
    return find_task(root, key)


def goal_start(
    root: Path,
    key: str,
    *,
    repo: Path,
    max_lanes: int | None = None,
    serial: bool = False,
    as_json: bool = False,
) -> dict:
    """Start ready goal children in lanes, or report that work is serial."""
    goal = find_task(root, key)
    if goal["meta"].get("kind") != "goal":
        raise SystemExit(f"error: {goal['meta']['id']} is not a goal")
    if goal["meta"].get("status") in FINAL:
        raise SystemExit(f"error: goal {goal['meta']['id']} is already {goal['meta']['status']}")
    if max_lanes is not None and max_lanes < 1:
        raise SystemExit("error: --max-lanes must be at least 1")
    repo = repo.resolve()
    if not (repo / ".git").exists() and not (repo / ".git").is_file():
        raise SystemExit(f"error: {repo} is not a git repository")

    with locked(root, ".plan.lock"):
        ready_all: list[dict] = []
        laneable: list[tuple[dict, list[str]]] = []
        for child in sorted(
            children_of(root, goal["meta"]["id"]),
            key=lambda item: (priority_of(item), item["meta"].get("id", "")),
        ):
            if child["meta"].get("status") not in ("ready", "inbox"):
                continue
            unblocked, _ = is_unblocked(root, child)
            if not unblocked:
                continue
            ready_all.append(child)
            owns = [
                normalized_owns(value)
                for value in child["meta"].get("owns", "").split(",")
                if value.strip()
            ]
            if owns:
                laneable.append((child, owns))

        selected = laneable if max_lanes is None else laneable[:max_lanes]
        should_lane = not serial and bool(selected) and (
            len(selected) >= 2 or max_lanes == 1
        )
        laneable_ids = [child["meta"]["id"] for child, _ in laneable]
        ready_ids = [child["meta"]["id"] for child in ready_all]
        laneable_set = set(laneable_ids)
        skipped = [
            child["meta"]["id"]
            for child in ready_all
            if child["meta"]["id"] not in laneable_set
        ]

        if not should_lane:
            if serial:
                reason = "requested by --serial"
            elif not laneable:
                reason = "no ready child with an owned path"
            else:
                reason = "fewer than two independent ready children"
            result = {
                "goal": goal["meta"]["id"],
                "mode": "serial",
                "reason": reason,
                "ready": ready_ids,
                "laneable": laneable_ids,
                "skipped": skipped,
                "lanes": [],
                "deferred": [],
            }
        else:
            for index, (left, left_owns) in enumerate(selected):
                for right, right_owns in selected[index + 1 :]:
                    for left_path in left_owns:
                        for right_path in right_owns:
                            if paths_overlap(left_path, right_path):
                                raise SystemExit(
                                    "error: lane ownership overlaps: "
                                    f"{left['meta']['id']} owns {left_path}, "
                                    f"{right['meta']['id']} owns {right_path}"
                                )

            # Preflight every selected lane before creating any worktree.
            for child, _ in selected:
                _, branch, worktree = lane_targets(child, repo)
                if worktree.exists():
                    raise SystemExit(f"error: worktree path already exists: {worktree}")
                if run_git(["branch", "--list", branch], repo):
                    raise SystemExit(f"error: branch already exists: {branch}")

            created = []
            for child, _ in selected:
                lane = child["meta"].get("lane") or "lane"
                task = lane_task(
                    root,
                    child["meta"]["id"],
                    repo=repo,
                    owner=f"lane-{lane}",
                    quiet=True,
                )
                created.append(
                    {
                        "task": task["meta"]["id"],
                        "lane": lane,
                        "branch": task["meta"]["branch"],
                        "worktree": task["meta"]["worktree"],
                        "owner": task["meta"]["owner"],
                    }
                )
            result = {
                "goal": goal["meta"]["id"],
                "mode": "lanes",
                "reason": "",
                "ready": ready_ids,
                "laneable": laneable_ids,
                "skipped": skipped,
                "lanes": created,
                "deferred": [] if max_lanes is None else [
                    child["meta"]["id"] for child, _ in laneable[max_lanes:]
                ],
            }

    if as_json:
        return result

    print(f"goal: {result['goal']} ({result['mode']})")
    if result["mode"] == "lanes":
        for item in result["lanes"]:
            print(
                f"  lane {item['task']}: {item['branch']} -> {item['worktree']} "
                f"({item['owner']})"
            )
        if result["deferred"]:
            print("deferred: " + ", ".join(result["deferred"]))
        if result["skipped"]:
            print("not lane-able: " + ", ".join(result["skipped"]))
        print("next: work each lane; run tasks.py goal-status after review")
    else:
        print(f"reason: {result['reason']}")
        if result["ready"]:
            print("ready: " + ", ".join(result["ready"]))
            print("next: work the ready children in this tree; do not create lanes")
        else:
            print("next: run tasks.py goal-status; no ready child is available")
    return result


def worktree_repo(worktree: Path) -> Path:
    common = run_git(["rev-parse", "--git-common-dir"], worktree)
    common_path = Path(common)
    if not common_path.is_absolute():
        common_path = (worktree / common_path).resolve()
    return common_path.parent


def reap_task(
    root: Path,
    task: dict,
    *,
    repo: Path | None = None,
    dry_run: bool = False,
) -> dict:
    """Remove one clean lane whose branch is merged somewhere else."""
    meta = task["meta"]
    task_id = meta["id"]
    worktree_value = meta.get("worktree", "")
    if not worktree_value:
        return {"task": task_id, "outcome": "none", "reason": "no worktree"}
    worktree = Path(worktree_value).expanduser()
    if not worktree.exists():
        return {"task": task_id, "outcome": "none", "reason": "worktree missing"}
    if meta.get("status") not in ("review", "done", "abandoned"):
        return {
            "task": task_id,
            "outcome": "retained",
            "reason": f"status is {meta.get('status', 'unknown')}",
        }
    try:
        repo = (repo or worktree_repo(worktree)).resolve()
    except SystemExit as exc:
        return {"task": task_id, "outcome": "retained", "reason": str(exc)}
    try:
        if run_git(["status", "--porcelain", "--ignored"], worktree):
            return {
                "task": task_id,
                "outcome": "retained",
                "reason": "dirty or ignored files in worktree",
            }
        branch = meta.get("branch", "")
        if not branch:
            return {"task": task_id, "outcome": "retained", "reason": "no branch"}
        contains = run_git(
            ["branch", "--contains", branch, "--format=%(refname:short)"], repo
        )
        others = [
            line.strip()
            for line in contains.splitlines()
            if line.strip() and line.strip() != branch
        ]
        if not others:
            return {
                "task": task_id,
                "outcome": "retained",
                "reason": "branch not merged into another branch",
            }
        if dry_run:
            return {
                "task": task_id,
                "outcome": "would-remove",
                "reason": "clean and merged",
            }
        try:
            run_git(["worktree", "remove", str(worktree)], repo)
        except SystemExit as exc:
            return {
                "task": task_id,
                "outcome": "retained",
                "reason": f"worktree removal failed: {exc}",
            }
        try:
            run_git(["branch", "-D", branch], repo)
        except SystemExit as exc:
            task["meta"]["worktree"] = ""
            append_log(task, f"worktree reaped; branch remains: {branch}")
            write_task(task)
            return {
                "task": task_id,
                "outcome": "retained",
                "reason": f"worktree removed; branch remains: {exc}",
            }
        task["meta"]["worktree"] = ""
        task["meta"]["branch"] = ""
        append_log(task, f"lane reaped: {branch}")
        write_task(task)
        return {
            "task": task_id,
            "outcome": "removed",
            "reason": "clean and merged",
        }
    except SystemExit as exc:
        return {"task": task_id, "outcome": "retained", "reason": str(exc)}


def reap(
    root: Path,
    key: str,
    *,
    repo: Path | None = None,
    dry_run: bool = False,
    as_json: bool = False,
) -> int:
    task = find_task(root, key)
    if task["meta"].get("kind") == "goal":
        tasks = children_of(root, task["meta"]["id"])
    else:
        tasks = [task]
    results = [reap_task(root, item, repo=repo, dry_run=dry_run) for item in tasks]
    removed = [item for item in results if item["outcome"] in ("removed", "would-remove")]
    retained = [item for item in results if item["outcome"] == "retained"]
    skipped = [item for item in results if item["outcome"] == "none"]
    if as_json:
        print(
            json.dumps(
                {
                    "task": task["meta"]["id"],
                    "removed": removed,
                    "retained": retained,
                    "skipped": skipped,
                },
                indent=2,
            )
        )
    else:
        print(f"reap: {task['meta']['id']}")
        for item in removed:
            print(f"  {item['outcome']}: {item['task']} ({item['reason']})")
        for item in retained:
            print(f"  retained: {item['task']} ({item['reason']})")
        for item in skipped:
            print(f"  skipped: {item['task']} ({item['reason']})")
        if not removed and not retained and not skipped:
            print("  no worktrees")
    if removed and not dry_run:
        write_board(root)
    return 1 if retained else 0


def remove_lane(root: Path, key: str, *, repo: Path | None = None, force: bool = False) -> None:
    task = find_task(root, key)
    meta = task["meta"]
    worktree = Path(meta.get("worktree", "")).expanduser()
    if not meta.get("worktree") or not worktree.exists():
        raise SystemExit(f"error: {meta.get('id')} has no existing worktree")
    repo = (repo or worktree_repo(worktree)).resolve()
    if meta.get("status") not in ("review", "done", "abandoned") and not force:
        raise SystemExit(
            f"error: {meta.get('id')} is {meta.get('status')}; move it to review/done first or use --force"
        )
    dirty = run_git(["status", "--porcelain"], worktree)
    if dirty and not force:
        raise SystemExit("error: worktree has uncommitted changes; commit or use --force")
    branch = meta.get("branch", "")
    base = meta.get("base", "HEAD")
    if branch and base:
        merged = run_git(["branch", "--merged", base], repo)
        if branch not in [line.strip().lstrip("*+ ") for line in merged.splitlines()]:
            if not force:
                raise SystemExit(
                    f"error: {branch} is not merged into {base}; merge it or use --force"
                )
    args = ["worktree", "remove", str(worktree)]
    if force:
        args.insert(2, "--force")
    run_git(args, repo)
    if branch:
        run_git(["branch", "-D" if force else "-d", branch], repo)
    print(f"removed worktree: {worktree}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT), help="state root (tests use this)")
    sub = parser.add_subparsers(dest="command", required=True)

    new = sub.add_parser("new")
    new.add_argument("title")
    new.add_argument("--project", default="general")
    new.add_argument("--priority", type=int, default=2)
    new.add_argument("--depends-on", default="")
    new.add_argument("--scope", default="")
    new.add_argument("--acceptance", default="")
    new.add_argument("--tags", default="")
    new.add_argument("--status", default="ready", choices=STATUSES)
    new.add_argument("--parent", default="")
    new.add_argument("--session", default="")

    goal = sub.add_parser("goal")
    goal.add_argument("title")
    goal.add_argument("--project", default="general")
    goal.add_argument("--priority", type=int, default=1)
    goal.add_argument("--scope", default="")
    goal.add_argument("--acceptance", default="")
    goal.add_argument("--tags", default="goal")
    goal.add_argument("--session", default=os.environ.get("OPENCODE_SESSION_ID", ""))
    goal.add_argument("--autorun", action="store_true")
    goal.add_argument("--unattended", action="store_true")
    goal.add_argument("--max-continuations", type=int, default=None)

    goal_status_parser = sub.add_parser("goal-status")
    goal_status_parser.add_argument("task")
    goal_status_parser.add_argument("--json", action="store_true")

    goal_start_parser = sub.add_parser("goal-start")
    goal_start_parser.add_argument("task")
    goal_start_parser.add_argument("--repo", default=".")
    goal_start_parser.add_argument("--max-lanes", type=int, default=None)
    goal_start_parser.add_argument("--serial", action="store_true")
    goal_start_parser.add_argument("--json", action="store_true")

    goals = sub.add_parser("goals")
    goals.add_argument("--all", action="store_true", help="include non-autorun goals")
    goals.add_argument("--json", action="store_true")

    plan = sub.add_parser("plan")
    plan.add_argument("--file", required=True)
    plan.add_argument("--dry-run", action="store_true")
    plan.add_argument("--json", action="store_true")
    plan.add_argument("--expect-hash", help="refuse unless the file hash matches")
    plan.add_argument("--unattended", action="store_true")

    listing = sub.add_parser("list")
    listing.add_argument("--status")
    listing.add_argument("--project")
    listing.add_argument("--json", action="store_true")

    sub.add_parser("ready")
    sub.add_parser("report")
    sub.add_parser("validate")
    sub.add_parser("board")

    show = sub.add_parser("show")
    show.add_argument("task")
    show.add_argument("--packet", action="store_true")
    show.add_argument("--summary", action="store_true")

    claim = sub.add_parser("claim")
    claim.add_argument("task")
    claim.add_argument("--owner", required=True)
    claim.add_argument("--branch", default="")
    claim.add_argument("--base", default="")
    claim.add_argument("--worktree", default="")
    claim.add_argument("--repo", default="")
    claim.add_argument("--force", action="store_true")

    status = sub.add_parser("status")
    status.add_argument("task")
    status.add_argument("status", choices=STATUSES)
    status.add_argument("--note", default="")
    status.add_argument("--evidence", default="")
    status.add_argument("--repo", default="")

    review = sub.add_parser("review")
    review.add_argument("task")
    review.add_argument("--repo", default=".")
    review.add_argument("--run", action="append", default=[])
    review.add_argument("--unverify", action="store_true")

    handoff = sub.add_parser("handoff")
    handoff.add_argument("task")
    handoff.add_argument("--file", help="file to read; default stdin")
    handoff.add_argument("--text", default="")

    log = sub.add_parser("log")
    log.add_argument("task")
    log.add_argument("text")

    lane = sub.add_parser("lane")
    lane.add_argument("task")
    lane.add_argument("--repo", default=".")
    lane.add_argument("--name", default="")
    lane.add_argument("--base", default="")
    lane.add_argument("--path", default="")
    lane.add_argument("--setup", default="")
    lane.add_argument("--owner", default="")

    reap_parser = sub.add_parser("reap")
    reap_parser.add_argument("task")
    reap_parser.add_argument("--repo")
    reap_parser.add_argument("--dry-run", action="store_true")
    reap_parser.add_argument("--json", action="store_true")

    remove = sub.add_parser("remove-lane")
    remove.add_argument("task")
    remove.add_argument("--repo")
    remove.add_argument("--force", action="store_true")

    args = parser.parse_args()
    root = Path(args.root).resolve()
    (root / "work/tasks").mkdir(parents=True, exist_ok=True)

    if args.command == "new":
        task = new_task(
            root,
            args.title,
            project=args.project,
            priority=args.priority,
            depends_on=args.depends_on,
            scope=args.scope,
            acceptance=args.acceptance,
            tags=args.tags,
            status=args.status,
            parent=args.parent,
            session=args.session,
        )
        print(task["meta"]["id"])
        return 0
    if args.command == "goal":
        task = goal_task(
            root,
            args.title,
            project=args.project,
            priority=args.priority,
            scope=args.scope,
            acceptance=args.acceptance,
            tags=args.tags,
            session=args.session,
            autorun=args.autorun or args.unattended,
            max_continuations=args.max_continuations,
        )
        print(task["meta"]["id"])
        return 0
    if args.command == "goal-status":
        return goal_status(root, args.task, as_json=args.json)
    if args.command == "goal-start":
        result = goal_start(
            root,
            args.task,
            repo=Path(args.repo),
            max_lanes=args.max_lanes,
            serial=args.serial,
            as_json=args.json,
        )
        if args.json:
            print(json.dumps(result, indent=2))
        return 0
    if args.command == "goals":
        return running_goals(root, as_json=args.json, include_all=args.all)
    if args.command == "plan":
        plan_path = Path(args.file).expanduser()
        try:
            raw = plan_path.read_bytes()
            plan_data = json.loads(raw)
        except (OSError, json.JSONDecodeError) as exc:
            raise SystemExit(f"plan: cannot read {plan_path}: {exc}")
        digest = hashlib.sha256(raw).hexdigest()
        if args.expect_hash is not None and args.expect_hash != digest:
            raise SystemExit(
                "plan: hash mismatch; the plan changed since review. "
                f"expected {args.expect_hash}, got {digest}"
            )
        result = create_plan(
            root,
            plan_data,
            dry_run=args.dry_run,
            as_json=args.json,
            autorun_override=True if args.unattended else None,
        )
        result["hash"] = digest
        if args.json:
            print(json.dumps(result, indent=2))
        elif result["goal"]:
            print(f"goal: {result['goal']}")
            for key, task_id in result["children"].items():
                print(f"  {key}: {task_id}")
        return 0
    if args.command == "list":
        items = all_tasks(root)
        if args.status:
            items = [task for task in items if task["meta"].get("status") == args.status]
        if args.project:
            items = [task for task in items if task["meta"].get("project") == args.project]
        if args.json:
            print(json.dumps([{"meta": task["meta"], "title": task["title"]} for task in items], indent=2))
        else:
            print_tasks(items)
        return 0
    if args.command == "ready":
        items = []
        for task in all_tasks(root):
            if task["meta"].get("status") != "ready":
                continue
            unblocked, _ = is_unblocked(root, task)
            if unblocked:
                items.append(task)
        print_tasks(items)
        return 0
    if args.command == "report":
        return report(root)
    if args.command == "validate":
        return validate(root)
    if args.command == "board":
        write_board(root)
        print(f"wrote {root / 'work/BOARD.md'}")
        return 0
    if args.command == "show":
        task = find_task(root, args.task)
        if args.summary:
            print(summary(task))
        elif args.packet:
            print(packet(task))
        else:
            print(task["path"].read_text(), end="")
        return 0
    if args.command == "claim":
        task = claim_task(
            root,
            args.task,
            owner=args.owner,
            branch=args.branch,
            base=args.base,
            worktree=args.worktree,
            repo=Path(args.repo) if args.repo else None,
            force=args.force,
        )
        print(f"claimed: {task['meta']['id']} by {args.owner}")
        return 0
    if args.command == "status":
        task = set_status(
            root,
            args.task,
            args.status,
            note=args.note,
            evidence=args.evidence,
            repo=Path(args.repo) if args.repo else None,
        )
        print(f"{task['meta']['id']}: {args.status}")
        return 0
    if args.command == "review":
        return review_task(
            root,
            args.task,
            repo=Path(args.repo),
            runs=args.run,
            unverify=args.unverify,
        )
    if args.command == "handoff":
        text = args.text
        if not text:
            text = Path(args.file).read_text() if args.file else sys.stdin.read()
        if not text.strip():
            raise SystemExit("error: empty handoff")
        with locked(root):
            task = find_task(root, args.task)
            task["sections"]["Handoff"] = text.strip()
            append_log(task, "handoff written")
            write_task(task)
        write_board(root)
        print(f"handoff: {task['meta']['id']}")
        return 0
    if args.command == "log":
        with locked(root):
            task = find_task(root, args.task)
            append_log(task, args.text)
            write_task(task)
        write_board(root)
        print(f"log: {task['meta']['id']}")
        return 0
    if args.command == "lane":
        lane_task(
            root,
            args.task,
            repo=Path(args.repo),
            name=args.name,
            base=args.base,
            path=args.path,
            setup=args.setup,
            owner=args.owner,
        )
        return 0
    if args.command == "reap":
        return reap(
            root,
            args.task,
            repo=Path(args.repo) if args.repo else None,
            dry_run=args.dry_run,
            as_json=args.json,
        )
    if args.command == "remove-lane":
        remove_lane(
            root,
            args.task,
            repo=Path(args.repo) if args.repo else None,
            force=args.force,
        )
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
