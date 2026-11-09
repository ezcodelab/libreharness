---
name: state-audit
description: Audit explicit and implicit state machines, document states, invariants, and transitions in one file, and fix confirmed invalid transitions with regression tests. Use for queues, retries, locks, sessions, lifecycle, recovery, concurrency, or stuck/duplicate/lost work.
---
<!-- SPDX-License-Identifier: MIT -->

# State machine audit

Use when behavior depends on state: queues, workers, retries, locks, sessions,
orders, connections, recovery, or any "stuck", "duplicate", "lost", or
"impossible" bug. The deliverable is one maintained document plus grouped,
tested fixes.

## 1. Inventory every machine

Read the code and tests. Do not infer a machine from a name.

List each explicit machine (enum, status field, state column) and each implicit
machine (booleans, nullable fields, ordered steps, ownership, locks, retry
counters, queues, sessions, connection lifecycles). For each record:

- owner and entry points: `file:line`;
- states, including error and terminal states;
- invariants that must hold in every state;
- transitions: from, event or guard, to, side effects;
- persistence and recovery: what survives a crash, restart, or replay;
- concurrency: who may act, what is serialized, what is retried.

If the inventory is large, write the document first and stop at grouped issues.

## 2. Write one document

Write or update `docs/state-machines.md` in the project. Use one section per
machine and a findings table at the top:

```text
# State machines
Status: <date>, <scope>, <commit>. Residual risks: <...>.

## Findings
| ID | Machine | Invalid path | Impact | Evidence | Status | Test |

## <Machine>
- Owner: file:line
- Kind: explicit | implicit
- States: ...
- Invariants: ...
- Transitions:
  | From | Event / guard | To | Side effects |
- Recovery and concurrency: ...
```

Use `CONFIRMED`, `SUSPECTED`, `UNVERIFIED`, and `FIXED` as finding statuses. A
finding is `CONFIRMED` only with a reachable code path and a failing test,
repro, or deterministic command. `SUSPECTED` is a lead, not a bug claim.

## 3. Hunt reachable invalid paths

For each machine, test the paths the code can actually reach:

- every transition from every state, including error and terminal states;
- retries and duplicate delivery: same event twice, at-least-once, replay;
- concurrency: two workers, two requests, lock expiry, interleaving;
- crash or restart between steps; partial writes, cancellation, timeouts;
- stale reads, missing rows, null/default fallbacks, out-of-order events;
- recovery and compensation, including "resume" and "retry all".

Record `file:line` evidence and the test or repro. Do not invent an impossible
path; state the precondition that makes it reachable.

## 4. Rank and group

Rank confirmed findings by impact: data loss or corruption, duplicate or lost
work, stuck recovery, security, then UX. Group findings that share a root cause,
not by symptom. One group is one fix and one regression test; do not patch every
symptom separately. If the audit is too large, stop after the document and the
grouped issue list.

## 5. Fix and prove

Fix the highest-impact group at the shared cause. Add a regression test that
fails on the old behavior and passes on the fix; if a test is impossible, say
why and keep the finding open. Run the project check. Update the document's
status, evidence, and residual risks. Do not claim an unrun check.

## 6. Hand off

Report the document path, confirmed/fixed/suspected counts, the exact commands
and results, and what remains unproven. Re-run the audit when a state
transition, retry, lock, or lifecycle changes. A stale document is a false
green.

## Stop conditions

Stop and report instead of editing when:

- the audit needs production data, live credentials, or a shared system;
- the fix needs a schema, auth, public API, or deployment decision;
- the document would be speculative because the code cannot be traced;
- the same finding fails review twice on the same axis.
