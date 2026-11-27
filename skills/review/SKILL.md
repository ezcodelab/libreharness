---
name: review
description: Review a working diff against task acceptance, record observed checks, and inspect reach and state impact. Use before closing or shipping a nontrivial change.
---
<!-- SPDX-License-Identifier: MIT -->

# Review gate

Review the working diff. Use the task id or prefix supplied with this invocation.
When none is supplied, use the current session task.

This is a check, not a finish step. Closing is the finish gate. Use the
`engineering-loop`, `work-queue`, `no-comments`, and `shipping` skills. Do not
edit code in this turn.

1. Read the task packet and summary. Write the task, scope, acceptance, and
   known evidence to a fresh directory beneath the operating system temporary
   directory. Resolve that directory with the host's Node runtime when needed.
   A review without acceptance is incomplete.
2. Save the diff in the same directory: the task base if set, otherwise the
   working and staged diff. Say which base you used. An empty diff is not a
   review; ask what to review.
3. Run the `comment_audit` tool with the diff path and `untracked: true`; add
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
   a PASS. Use the `shipping` skill's review-axis reference.
7. Update the queue, not code: pass with `tasks status <id> review --note
   "review artifact PASS at <sha>"`; send back with `tasks log <id> "review
   send-back: <one line>"` and leave it active. Show the verdict and stop.
