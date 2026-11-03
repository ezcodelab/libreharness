---
description: Tiered quality review — Jev screen, devil's advocate only when risk warrants
---
<!-- SPDX-License-Identifier: MIT -->
Review the working diff. Task: $ARGUMENTS

Use the engineering-loop and work-queue skills. Do not edit code in this turn.

1. If `$ARGUMENTS` is a task id (or unique prefix), read the task packet and
   summary. Let `TASK` be the id, or `session-$$` (the shell PID) when there is
   no task; never use a fixed task-less name. Write the task summary to
   `/tmp/opencode/review-task-$TASK.txt` with the shell tool.
   Otherwise write the stated task, scope, acceptance, and known evidence to
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
3. Preflight the free model:
   `python3 "${HARNESS_HOME:-$HOME/.config/opencode}/bin/jev_review.py" --check`
   - exit 4 → **stop**. Say: "Free Jev is gone. Update `DEFAULT_MODEL` in
     `bin/jev_review.py` to `jev-1.13` (paid), or pass the same `--model` to
     both the check and the review; no review was run." Do not silently start
     paying.
   - exit 3 → note "Jev unavailable" and go to step 5 (subagent fallback).
4. Run Jev:
   `python3 "${HARNESS_HOME:-$HOME/.config/opencode}/bin/jev_review.py" --diff /tmp/opencode/review-$TASK.diff --task-file /tmp/opencode/review-task-$TASK.txt`
   Record the exit code and scores. If the task has no recorded evidence under
   its Evidence heading, add a finding: the diff has no verification claim to
   review.
5. Run the `devils-advocate` agent only if **any** of these is true:
   - Jev exit 2 (a failing axis, ship/scope/tests, or secret leak);
   - the diff touches auth, secrets, credentials, data migrations, a public
     API, recovery/concurrency, or billing;
   - the operator said "strict", "release", or "full review";
   - Jev was unavailable (exit 3).
   Otherwise skip it and say: "Jev passed; devils-advocate skipped (low risk)."
   When it runs, give it the task acceptance, the diff, the test evidence, and
   the flagged axes. Require one verdict per finding:
   **CONFIRMED**, **REFUTED**, or **UNVERIFIED**, with the source, sink or
   failure point, and guard cited as `file:line`. Ask for the six
   silent-failure checks. It reviews; it does not fix.
6. Name the one safety fact. For every non-trivial diff, state the single fact
   the change is safe because of. Require a runnable proof such as a test,
   script, or command output; if it cannot be proved, mark it **UNVERIFIED**.
   A plausible explanation is not evidence.
7. Verdict:
   - Only a **CONFIRMED** devils P0/P1 blocks. A P2/P3 confirmed finding is a
     fix or an explicit accepted risk, not an automatic send-back.
   - **UNVERIFIED** is a warning, not a defect. Ask for the missing source,
     sink, guard, or test evidence; do not present it as confirmed.
   - **REFUTED** is dropped from the blocking list. Mention it only to show
     what was checked.
   - For a CONFIRMED P0/P1, run one fresh opposite-lens devils-advocate pass
     focused on reachability and defenses before the final verdict. If the
     second pass refutes it, downgrade to UNVERIFIED and record why. Do not run
     the second pass for routine findings.
   - Jev exit 2 still sends back with concrete fixes per flagged axis. If the
     subagent found nothing on a flagged axis, call it an unexplained warning,
     not a confirmed defect, and still ask for a rerun after the fix.
   - Jev exit 0 and no confirmed blocking finding → report what passed,
     residual risks, and what remains unproven.
8. If a task id was used, update the queue (not code):
   - pass: `tasks.py status <id> review --note "Jev pass; devils: <none|findings>"`;
   - send back: `tasks.py log <id> "review send-back: <one line>"`, leave it
     active.
9. Show the verdict and stop. Do not promote lessons; `/close` does that.
