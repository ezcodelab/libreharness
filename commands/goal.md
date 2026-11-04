---
description: The single task entry — execute a small task, or plan/review/run a multi-step goal
---
<!-- SPDX-License-Identifier: MIT -->
Request: $ARGUMENTS

Use the goal, work-queue, parallel-lanes, and engineering-loop skills.

## Existing goal or single task

1. If `$ARGUMENTS` is an existing `kind: goal` task id, execute it:
   `goal-status`, then `tasks.py goal-start <goal-id> --repo "$PWD"` once. It
   creates up to three lanes for ready children with disjoint `owns`; if it
   reports serial, work in the current tree. Then `/brief <child>`, implement,
   test, `/review`, `/close`. Do not ask the operator to run `/lane` for each
   child; `/lane` is only for manual or existing-task isolation.
   Stop on a one-way door, blocker, two same-axis send-backs, a merge conflict,
   a push/deploy, or ambiguous acceptance.
2. If `$ARGUMENTS` is an existing `kind: task` id with status `inbox` or
   `ready`, first decide whether the packet is **one reviewable diff**. If it is
   more than one, plan it as a goal with this task's title/scope as the first
   child, then stop at the plan; mark the original task `abandoned --note
   "superseded by goal <id>"` only after the plan is created.
   Otherwise this is the **small-task fast path**:
   - read the packet; if Scope/Acceptance are placeholders, fill them from the
     request or ask one question; run `tasks.py status <id> ready --note "goal confirmed"`;
   - claim it: `tasks.py claim <id> --owner <session-or-lane>`; if another owner
     holds it, stop;
   - execute: `/brief`, implement, run checks, `/review`, `/close`. Use `/lane`
     only when you deliberately want a manual worktree for this one task.
     Do **not** create a goal or a plan for one small task.
3. If `$ARGUMENTS` is empty, ask one question: "What observable outcome means
   this is done?" Then stop. If the request is trivial, say so and skip the
   queue.

## Plan mode (multi-deliverable)

1. Read the matching project page, `AGENTS.md`, `DECISIONS.md` standing rules,
   `docs/README.md` if present, the relevant tree/tests, and up to three lessons.
2. If this is actually one bounded change, create a single task directly with
   `tasks.py new "<title>" --project <name> --scope "<scope>" --acceptance "<checks>"`,
   then execute it as the small-task path. Do not create a goal. Otherwise split
   by deliverable/review boundary into 2–6 children. A one-way door is a
   decision-memo child (`owns: []`), not an implementation.
3. Each child gets scope, observable acceptance, dependencies, `owns` paths, and
   a lane. Lanes: 2–3, disjoint owns, one owner per shared file. If two children
   need the same path, combine or serialize.
4. Write `/tmp/opencode/goal-plan.json`:

```json
{
  "goal": {
    "title": "Outcome",
    "project": "demo",
    "scope": "One sentence.",
    "acceptance": "- observable check",
    "priority": 1,
    "autorun": false,
    "max_continuations": 12
  },
  "children": [
    {
      "key": "readme",
      "title": "README audit",
      "scope": "What this child changes.",
      "acceptance": "- command runs",
      "priority": 1,
      "depends_on": [],
      "owns": ["README.md"],
      "lane": "docs"
    }
  ],
  "lanes": [{"name": "docs", "tasks": ["readme"]}]
}
```

Set `autorun: true` only when the operator asks to leave it alone.
5. Validate and bind:
   `python3 "${HARNESS_HOME:-$HOME/.config/opencode}/bin/tasks.py" plan --file /tmp/opencode/goal-plan.json --dry-run --json`
   Fix every validator error; save the returned `hash` to
   `/tmp/opencode/goal-plan.sha256`.
6. Show goal, children, lanes, dependencies, owns, one-way doors, autorun, and
   hash. Stop. Nothing is created yet.

## Go mode

If `$ARGUMENTS` starts with `go`:
1. Require `/tmp/opencode/goal-plan.json` and `.sha256`.
2. Dry-run with `--expect-hash "$(cat /tmp/opencode/goal-plan.sha256)"` to prove
   the reviewed plan is unchanged.
3. Create with `plan --file /tmp/opencode/goal-plan.json --expect-hash
   "$(cat /tmp/opencode/goal-plan.sha256)"` (add `--unattended` for `go
   --unattended`); show the goal id.
4. Run `tasks.py goal-start <goal-id> --repo "$PWD"` once. It uses the reviewed
   lane map and creates up to three lanes for ready children. If it reports
   serial, work the ready children in the current tree. Then execute as in
   section 1.
5. `go` is the approval; there is no separate apply step. Do not re-plan
   silently.
