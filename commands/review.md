---
description: Deterministic review: record observed checks and inspect reach and state impact
---
<!-- SPDX-License-Identifier: MIT -->
Review the working diff. Task: $ARGUMENTS

This is a check, not a finish step. `/close` runs the final review and, for a
goal, integrates reviewed lanes before closing. Use the engineering-loop and
work-queue skills. Do not edit code in this turn.

1. If `$ARGUMENTS` is a task id (or unique prefix), read the task packet and
   summary. Let `TASK` be the id, or `session-$$` (the shell PID) when there is
   no task; never use a fixed task-less name. Write the task summary to
   `/tmp/opencode/review-task-$TASK.txt` with the shell tool. Otherwise write
   the stated task, scope, acceptance, and known evidence to
   `/tmp/opencode/review-task-$TASK.txt` with the write tool. A review without
   the acceptance criteria is incomplete; say so.
2. Save the diff to `/tmp/opencode/review-$TASK.diff`, in this order, and say
   which base you used:
   - task `base` is set: `git diff "<base>"...HEAD`;
   - otherwise `git diff`, then `git diff --staged`;
   - for an integration or already-committed lane: `git diff <target-base>...HEAD`
     (the merge target, not the lane's own tip);
   - if all are empty, ask what to review. Never review an unrelated leftover
     change from another lane.
3. Comment discipline (blocking): read the changed files for narration, stale
   comments, commented-out code, and workaround justifications without an
   external reference. A new unreferenced `workaround`, `do not remove/change`,
   `TODO`/`FIXME`, or correctness lint or type suppression is a send-back. The fix
   is the smallest root-cause reshape, or a type, lint, test, or runtime check,
   not a shorter comment. An inline `comment-discipline: allow <reason>` or a
   linked issue accepts a deliberate case. Run `node tests/harness-ratchets.test.mjs`
   when the repo has it.
4. Deterministic checks first. Read the task Plan's `Data shape:` and `Verify:`
   lines, then record the real exits:
   `python3 "${HARNESS_HOME:-$HOME/.config/opencode}/bin/tasks.py" review <id> --repo "$PWD" --run "<Verify>" --run "<focused check>"`
   The command runs argv without a shell and writes
   `$HARNESS_STATE/work/reviews/<id>.json` with the exact HEAD and a digest of
   the reviewed diff, including untracked files. A missing or stale head or
   diff, an unreachable check, a non-zero exit, a different Verify command, or
   an empty list blocks. If there is no task id, run the same
   commands directly and say they are not recorded. A product task whose real
   check cannot be expressed in the allowlist stops unverified; do not point
   Verify at an unrelated harness check.
5. Blast radius and the one safety fact. For every changed shared symbol, list
   its callers, importers, tests, fixtures, config, exports, and wire-format
   consumers, and read the unchanged callers the diff does not show. State the
   single fact the change is safe because of, with a runnable proof such as a
   test, script, or command output. If a fact cannot be proved, mark it
   **UNVERIFIED**. A plausible explanation is not evidence.
6. State impact. If the diff adds or changes a state machine, retry, lock,
   session, queue, concurrency, or lifecycle path, require the `state-audit`
   skill's `docs/state-machines.md` to be updated and a regression test for
   every confirmed invalid transition. A missing document is a warning for a
   stateless diff and a send-back for a lifecycle, retry, concurrency, or
   recovery change.
7. Verdict. The review artifact must say PASS; the command revalidates it. Label
   each finding **CONFIRMED**, **REFUTED**, or **UNVERIFIED**, with a source,
   sink or failure point, and guard. Only a confirmed P0/P1 blocks, and so does
   a comment-discipline finding from step 3. A P2/P3 is a fix or an explicit
   accepted risk. Do not accept feedback sycophantically or just because a
   reviewer raised it. A model second opinion runs only when the operator asks
   for one in this turn; it cannot add checks or PASS. If it is incomplete,
   failed, truncated, or unproven, run
   `tasks.py review <id> --repo "$PWD" --unverify` and keep the task open.
   There is no second abstract pass. A green artifact is not proof: run the
   acceptance check on the real artifact.
8. If a task id was used, update the queue (not code):
   - pass: `tasks.py status <id> review --note "review artifact PASS at <sha>"`;
   - send back: `tasks.py log <id> "review send-back: <one line>"`, leave it
     active.
9. Show the verdict and stop.
