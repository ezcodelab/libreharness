---
description: Audit explicit and implicit state machines, document transitions, and fix confirmed invalid paths with regression tests
---
<!-- SPDX-License-Identifier: MIT -->
State-machine audit: $ARGUMENTS

Use the state-audit and engineering-loop skills. This is the default audit for
stateful code, not a general review. Do not edit code before the document and
the ranked findings exist.

1. Scope. `$ARGUMENTS` names a repository, path, subsystem, or machine. If it is
   empty, use the current repository. Read the code and tests; list every
   explicit and implicit machine with its owner, entry points, states,
   invariants, transitions, persistence, recovery, and concurrency. Do not infer
   a machine from a name.
2. Write or update `docs/state-machines.md` in the project. Include a findings
   table with ID, machine, invalid path, impact, evidence, status, and test, then
   one section per machine with states, invariants, and a transition table.
3. Trace invalid states and transitions the code can actually reach: retries,
   duplicate delivery, concurrent callers, lock expiry, crash or restart,
   partial failure, cancellation, timeouts, stale reads, and out-of-order
   events. Mark `CONFIRMED` only with `file:line` evidence and a failing test,
   repro, or deterministic command; otherwise use `SUSPECTED` or `UNVERIFIED`.
4. Rank by impact and group by root cause. If the audit is too large, stop after
   the document and grouped issues; do not fix everything in one turn.
5. Fix the highest-impact group at the shared cause. Add a regression test that
   fails on the old behavior. Run the project check and record the command and
   result.
6. Update the document's status, fixed findings, and residual risks. Report the
   document path, counts, evidence, and what remains unproven. If a task id was
   given, append the evidence to the queue; do not mark it done unless its
   acceptance is met.
