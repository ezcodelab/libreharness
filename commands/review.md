---
description: Deterministic review: record observed checks and inspect reach and state impact
---
<!-- SPDX-License-Identifier: MIT -->
Review the working diff. Task: $ARGUMENTS

This is a check, not a finish step. `/close` is the finish gate. Use the
`engineering-loop`, `work-queue`, `no-comments`, and `shipping` skills. Do not
edit code in this turn.

1. If `$ARGUMENTS` is a task id or prefix, read the packet and summary. Let
   `TASK` be the id, or `session-$$` when there is no task. Write the task,
   scope, acceptance, and known evidence to
   `/tmp/opencode/review-task-$TASK.txt`. A review without acceptance is
   incomplete.
2. Save the diff to `/tmp/opencode/review-$TASK.diff`: the task base if set,
   otherwise the working and staged diff. Say which base you used. An empty
   diff is not a review; ask what to review.
3. Run the `comment_audit` tool with
   `{ diff: "/tmp/opencode/review-$TASK.diff", untracked: true }`; add
   `strict: true` when `.comment-audit-strict` exists. A tool error is a
   send-back. Apply `no-comments`: delete, smallest root-cause fix, or
   encode-then-delete; reject unrelated rewrites and symptom guards.
4. Call `tasks` with
   `args: ["review", "<id>", "--run", "<Verify>", "--run", "<focused check>"]`.
   The artifact must bind the exact HEAD, the diff, and the task contract, and
   every recorded exit must be zero. A missing, stale, failed, truncated, or
   unproven artifact blocks.
5. State the blast radius: callers, importers, tests, fixtures, config, exports,
   and wire-format consumers. Name the one safety fact and its runnable proof,
   or mark it **UNVERIFIED**. If the diff changes a state machine, retry, lock,
   session, queue, concurrency, or lifecycle path, require the `state-audit`
   document and a regression test.
6. Write **PASS** or **UNVERIFIED** in the artifact. Label findings
   **CONFIRMED**, **REFUTED**, or **UNVERIFIED** with a source, sink or failure
   point, and guard. Only a confirmed P0/P1 or a comment-discipline finding
   blocks. A model second opinion requires an operator request and cannot create
   a PASS. Use `skills/shipping/references/review-axes.md` for the axes.
7. Update the queue, not code: pass with `tasks status <id> review --note
   "review artifact PASS at <sha>"`; send back with `tasks log <id> "review
   send-back: <one line>"` and leave it active. Show the verdict and stop.
