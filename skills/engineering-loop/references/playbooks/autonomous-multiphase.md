<!-- SPDX-License-Identifier: MIT -->
1. Load the `goal` skill. Write a falsifiable done predicate and the phases.
2. Sequence the riskiest unknown and the verification harness first.
3. Give each phase one verifiable unit and one commit.
4. Log every decision and tradeoff in the task, not the transcript.
5. Verify each unit before the next. Do not batch checks at the end.
6. Pause only for irreversible actions: deploy, data deletion, force-push, an
   auth or CI gate change, or a message to an external person.
7. Before stopping, write the handoff and the exact next action.
