---
name: engineering-loop
description: Entry point for every non-trivial change. Matches the task to one playbook, copies its steps into the todo list, and gates the result on real-artifact proof. Use for bug fixes, features, refactors, perf work, hillclimbs, investigations, and unattended runs.
---
<!-- SPDX-License-Identifier: MIT -->

# Engineering loop

Non-trivial means any of: more than one file, a behavior change, a schema, auth,
secrets, an external API, or "done" means production behavior. A typo, a
one-line fix, or pure copy skips this skill.

## First reply

Restate the goal and the smallest change that meets it. Then route.

## Playbook router

Match the request to one row, open `references/playbooks.md`, and copy that
section's steps into the todo list before touching code.

| Playbook | Use when | Proof |
|---|---|---|
| `investigation` | The whole request is read-only | `file:line` citations, no edits |
| `bug-fix` | A defect or regression | failing repro first, then green on the same surface |
| `feature` | New or changed behavior | the real artifact shows the new behavior |
| `refactoring` | Structure moves, behavior holds | the pinned contract stays green |
| `perf` | One measured slowness | before and after on the same workload |
| `hillclimb` | A sustained loop toward a target metric | every kept commit beats the baseline |
| `autonomous-multiphase` | An unattended run or multi-PR phases | every unit verified before the next |
| `correct` | A mistake class that repeated | the new check fails on the past mistake |

Routing rules:

- **Any code edit in scope** routes a defect to `bug-fix` and every other edit to
  `feature`. `investigation` is only for a request that is read-only end to end.
  "Explain X and fix Y" is a `bug-fix` or a `feature`, never an investigation.
- A user-named playbook wins. Ignore an unknown playbook name and route by
  content.
- `correct` is never selected from free text. Enter it only when the operator
  names it, or from `/close` and `/tune` after a mistake class repeats twice.
  Never divert an in-flight `bug-fix`, `feature`, or `refactoring` into it.
- Multi-deliverable or unattended work also loads the `goal` skill. A single task
  does not.

## Fallback

No row fits: use `feature` for an edit and `investigation` for a pure question.
State the fallback and the reason in one line. Do not invent a playbook.

## Non-negotiables

1. **Data shape first.** Across a function or module boundary, name the types, the
   state machine, and the boundary parser before writing logic. Put that sketch in
   the brief or the task Plan.
2. **Smallest complete change.** Delete dead weight first. No speculative
   abstraction, compatibility shim, or second path.
3. **One verifiable unit per commit.** Each commit ends in a check you ran.
4. **No comment alibis.** Before review, run `no-comments` on the diff. A
   constraint that needs a comment becomes a type, lint, test, or runtime check.
5. **Prose is part of the change.** Run `unslop` on the reply, the PR body, and
   the commit message. Label evidence as measured, inferred, or guess.
6. **Proof beats compilation.** `verification` drives the real artifact or the
   named formal check. A unit test alone does not prove user-visible behavior.
7. **Evidence first.** `/review` runs before `/close` and records observed
   checks in the review artifact. A second opinion is an explicit operator
   request, never a risk label, path guess, or default.
8. **Encode repeats.** A failure class seen twice becomes a check whose error names
   the fix, added through `correct` and recorded in the rule ledger.

## Exit gates

Stop and report instead of claiming done when:

- the acceptance check cannot run in this environment;
- a one-way door appears: schema, auth boundary, public API, infrastructure, a
  dependency, or a release;
- the same check fails twice on the same axis;
- the next action would deploy, delete data, force-push, or message a customer.

Otherwise continue. For one reviewable diff, write the task acceptance, Data
shape, and Verify lines, then implement in the same turn. Use `/brief` when the
scope spans several deliverables or remains ambiguous. Verify, `/review`,
`/close`, and ship through `shipping`.
