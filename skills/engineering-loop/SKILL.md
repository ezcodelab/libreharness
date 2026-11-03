---
name: engineering-loop
description: Risk-scaled process for nontrivial work — external APIs, secrets or auth, schema and data changes, security tradeoffs, multi-file design, or when "done" means production behavior. Read the repo state, gate only what applies, pick one path, prove the claim, and keep lessons only when they pay off.
---
<!-- SPDX-License-Identifier: MIT -->

# Engineering loop

Use for nontrivial work. Skip typos, one-liners and pure copy: make the change, check it, done.

## 0. Intake

State the task, the success condition, and what is explicitly out of scope.
If the work is nontrivial, spans a session, or may run in parallel, create or
claim a task with the `work-queue` skill (`/goal`, `/queue`, `/lane`). A task
is the durable unit; the chat is not. For a multi-step outcome, use `/goal` to
create the umbrella and child tasks; they still use this loop.

If the ask is broad, narrow it and say what you deferred. For a nontrivial
task, run `/brief <task>` (or produce the same one page: scope, invariants,
evidence, definition of done, past lessons).

## 1. Brain

Read the project `AGENTS.md`, `DECISIONS.md` / REFUSES, the coverage doc for
anything you touch, and recent lessons — not the whole diary. Prefer these
files over chat memory. Load only the context the task needs.

At a pause, a phase boundary, a model switch, or around 60% context: run
`/handoff` and write State / Decisions / Files / Checks / Open / Next / Context
(under 40 lines, no secrets). On resume, `/takeover`: read the packet, handoff,
project rules, and the named files; run the named check before trusting a
“done” claim.

## 2. Gates (only the ones that apply)

- **External API:** create/read/update/delete routes, auth scheme, and how a
  new secret is learned (response body, config read, restore, file,
  impossible).
- **Data:** source of record, migrations, backward compatibility.
- **Security:** list observed constraints. Proposed refusals are proposals
  until the owner accepts them; do not invent hard policy.
- **Evidence:** what would prove the success condition.

If a critical unknown blocks a safe design: run a bounded research/probe, ask
one clarifying question, or stop with a concrete next step. A gate failure is
a decision about which fallback is honest, not a dead end.

## 3. Plan

Record the choice where it persists (repo decisions), with PASS/FAIL and the
fallback. Prefer one path; do not build competing designs for the same
constraint. If no path meets the constraint, document that and stop.

For parallel work, write the ownership map first: lanes, files/interfaces,
dependencies, branches/worktrees, merge order. Use `parallel-lanes`; cap at two
or three lanes. Shared files and the state get one owner. For a goal with more
than two children or a one-way door, run the advisory `jev_plan.py --goal <id>`
critique before execution.

## 4. Implement

One vertical slice that proves the hard part — not every variant at once. Stay
inside the task scope. If the interface or acceptance changes, update the task
before editing.

## 5. Prove

Run checks that match the claim. Unit tests alone do not prove production
behavior; live or measured evidence does. Record the command, result, and
timestamp in the task's Evidence section. Label anything still unverified as
`[T]` with a plan.

## 6. Review

Run `/review <task>`. It builds the task-aware review packet, runs Jev first,
and adds `devils-advocate` only when Jev flags risk or the change touches auth,
secrets, data, a public API, recovery/concurrency, or a release. A failing
quality axis sends the change back with concrete fixes, not a warning.

The merged tree is reviewed, not just each lane; a green lane is not a green integration.

## 7. Integrate and reap

`/close` integrates reviewed lanes in the declared order, reruns the full
check, and reaps clean merged worktrees. One integrator owns the merge; do not
push or force-push without approval. If integration or reaping cannot complete,
leave the task `review` or `blocked` with the failing command.

## 8. Capture the lesson

Append one entry to the project's `docs/process-lessons.md` after every
completed task. Use `/close`: it integrates, reaps, runs the final review and
Jev triage, appends one entry, updates the task, and may stage a project skill
under the project's `skills/` directory. If there is no queue task or diff and
the operator stated a preference, append it directly to the project ledger. If
nothing surprised you, say that in one line — do not invent a discovery.

When a gate fails or an approach is rejected, also add or harden a REFUSE or a
checklist item where it persists (repo decisions, or the gate/coverage doc), so
the next agent does not re-explore it. A lesson without a rule change is just a
diary entry.

Tag `Promote-to-global` on the Rule line when the lesson is portable — process,
or a personal workflow/design preference — not product or stack dogma.
Promotion happens in a tuning turn, with the operator's approval — not by
editing global config mid-task.

## 9. Tuning (operator-triggered, or after a major wave)

1. Find what to delete: obsolete paths, docs, options, and process steps that
   did not pay off. Leaner beats more rules.
2. Read `${HARNESS_STATE}/metrics/workflow-log.csv`, the queue report, and the
   `Promote-to-global` lessons; propose at most 5 patches to the global AGENTS
   or a global skill, as a diff.
3. The operator accepts or rejects. Nothing is promoted in the turn it is
   proposed.
4. Runtime skills live in `${HARNESS_HOME}/skills/`. A promoted skill is a Git
   change there; the state keeps the evidence, not a second copy.

