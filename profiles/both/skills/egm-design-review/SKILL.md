---
name: egm-design-review
description: Use before implementing a nontrivial design or multi-file change. Runs a zero-context comprehension check, an implementation-readiness checklist, and a bounded review convergence rule. Read-only; does not edit code.
---
<!-- SPDX-License-Identifier: MIT -->

# EGM design review

A lightweight version of the Elephant-Goldfish review ideas. It checks whether
a spec is self-contained enough for a fresh session to implement, not whether it
sounds convincing.

Use it for a multi-file feature, a migration, an auth or data boundary, or any
design that is expensive to reverse. Skip it for a one-line fix or a task whose
acceptance already removes the ambiguity.

## Inputs

- `Target`: the task `Plan`, design doc, or decision memo.
- `Referenced files`: the files the target explicitly names. Read them; do not
  guess.
- `Scope`: the part of the target under review, if it is split into a feature
  section and an implementation section.

## Rules

- Read-only. Do not edit the target, code, tests, or task state.
- A fresh context is required. If you cannot create one, stop and say so. A
  review in the author's context is not the comprehension check.
- Do not invent blockers to look thorough. “No material findings” is valid.
- Do not rewrite the design. Report the gap and the smallest useful fix.
- The operator or `devils-advocate` decides what to apply. This skill does not
  auto-fix.

## Step 1: Comprehension check

In a fresh context, read only the target, the files it references, and this
skill. Then write, in your own words:

1. **What this proposes** in two to five sentences.
2. **How the existing system works, according to the document**, in two to five
   sentences.

If you cannot write either paraphrase, that section is a blocker. A list of
undefined terms is not enough; the parts must connect.

Then list the gaps that would stop a competent engineer from implementing the
target without asking a question:

- an undefined project term or acronym;
- an unstated prerequisite, environment, permission, or migration;
- a referenced file, symbol, signature, or route that does not match the source;
- a behavior that is described but has no owner, failure path, or test.

## Step 2: Readiness checklist

Check the target for each item that applies:

- **Files:** exact paths to create, modify, or delete.
- **Interfaces:** function or route signatures, request and response shapes, and
  who calls them.
- **Data:** schema, migration, backfill, rollback, and existing rows.
- **Failure:** retries, timeouts, partial writes, recovery, and user-visible
  errors.
- **Security:** authorization at every read and write, tenant or ownership
  checks, and secret handling.
- **Tests:** the failing test first, the edge cases, and the command that proves
  the task.
- **Observability:** the log, metric, or trace that shows the feature working or
  failing.
- **Rollout:** feature flag, compatibility window, or rollback.

An item is a gap only when it applies to the target. Do not demand a migration
for a docs change.

## Step 3: Findings

Return one line per finding:

```text
[Blocker|Major|Nit] <section or file:line> - <gap> - <smallest useful fix>
```

- **Blocker:** an implementer cannot proceed correctly without a decision or a
  missing fact.
- **Major:** the implementer can proceed, but a likely failure path, security
  boundary, or test is missing.
- **Nit:** clarity or style; never blocks.

Deduplicate. If two findings have the same cause, report the cause once.

## Step 4: Convergence

Keep a short ledger across rounds:

- **Settled:** contested or accepted without a fix. Do not re-open at the same
  scope unless new evidence appears.
- **Fixed:** a fix was applied. Re-open if the same issue returns at the same
  scope.
- **Clean round:** no unsettled blocker or major. Nits do not make a round
  unclean.
- **Converged:** two consecutive clean rounds.
- **Cap:** five rounds. At the cap, list the open findings and ask the operator
  to accept, continue, or return to drafting.
- **Churn:** a new finding at the scope of an applied fix that would be resolved
  by reverting the fix. Stop and report it.

## Output

1. The two paraphrases from Step 1, kept even when there are no findings.
2. Findings ordered blocker, major, nit.
3. The round status: clean, converged, capped, or churn.
4. What you could not verify.

Do not claim the design is correct. Say what the review covered and what it did
not.

## Attribution

Inspired by
[`google/elephant-goldfish-model`](https://github.com/google/elephant-goldfish-model)
at commit `403d888` (Apache-2.0). This is an original lightweight adaptation;
no upstream prompt text is copied.
