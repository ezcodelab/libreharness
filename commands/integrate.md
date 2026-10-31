---
description: Integrate reviewed lanes in order and prove the merged tree
---
<!-- SPDX-License-Identifier: MIT -->
Integrate: $ARGUMENTS

Use the parallel-lanes, work-queue, and engineering-loop skills. One
integrator owns this turn; do not let a lane push or rewrite history.

1. Require one or more task ids (or an explicit branch list). Read each task
   packet. Refuse to integrate a task that is not `review`/`done`, has no
   Evidence, or has a failing review. Mark the integration blockers.
2. Build the ownership/merge map from the tasks: branch, base, merge order,
   shared files, and the one integration branch. If two tasks claim the same
   file or interface, stop and serialize.
3. Verify each branch is committed and clean. Merge in the declared order into
   the integration branch. On a conflict: stop, report the files and both
   intents, and leave the tree in a resumable state; do not guess a resolution.
4. After all merges, run the full project check on the merged tree (for Credarr:
   `make check`; add `make ui-smoke` when UI changed). A per-lane green is not
   enough.
5. Run `/review <integration-task>` on the merged diff. If it sends back, do
   not mark the lanes done; record the finding and return to the owning lane.
6. Update each lane task with its evidence and the integration result. Create
   or update one integration task with the merge order, conflicts, final
   command, and handoff.
7. Do not push, force-push, or deploy. Report: merged branches, checks, review
   verdict, remaining risk, and the exact next action.
