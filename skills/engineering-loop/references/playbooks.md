<!-- SPDX-License-Identifier: MIT -->
# Playbooks

Loaded by `skills/engineering-loop/SKILL.md`. Copy the matching section into the
todo list verbatim, then work it. Each section is a checklist, not an essay.

## investigation

1. State the question as a falsifiable claim.
2. Trace entry points, data flow, and state transitions; cite `file:line`.
3. Read the tests and say what they actually assert.
4. Separate measured facts from inferred claims.
5. Report the smallest next step. Make no edits.

## bug-fix

1. Reproduce on the matching surface; save the failing output.
2. List candidate causes and rule them out with runtime evidence.
3. Write the failing test or repro before the fix.
4. Fix the first place the system went wrong. No symptom guards.
5. Rerun the repro, then the full check. Paste both outputs.
6. Put the failing repro commit before the fix commit in history.

## feature

1. Name the data shape, state machine, and boundary parser. Use `/brief` only
   for multi-deliverable or ambiguous scope.
2. Build the smallest vertical slice that proves the hard part.
3. Parse each external input once at the boundary and pass typed values inward.
4. Run `no-comments` and `unslop` on the diff.
5. Prove the behavior on the real artifact with `verification`.
6. Record the command and result in the task Evidence.

## refactoring

1. Pin current behavior with a characterization test or equivalence harness.
2. Name the target shape and the structure the code is missing.
3. Subtract dead code, one-caller wrappers, and redundant validators first.
4. Migrate every caller and delete the old API in the same wave.
5. Prove behavior is unchanged and reader load went down. Revert otherwise.

## perf

1. Capture a baseline and the exact command that produced it.
2. Name the limiter; rule out skipped work, tuning, noise, and measurement error.
3. Profile or trace to the first slow step.
4. Fix that step. One change per measurement.
5. Re-run the same workload and report the delta.

## hillclimb

1. Write the target metric, the stop predicate, and the measurement command.
2. Record the baseline and the noise floor.
3. Loop: one hypothesis, one change, one measurement.
4. Keep a win as one commit with its number. Revert a loss.
5. Stop at the target, the plateau, or a rising cost. Report what remains.

## autonomous-multiphase

1. Load the `goal` skill. Write a falsifiable done predicate and the phases.
2. Sequence the riskiest unknown and the verification harness first.
3. Give each phase one verifiable unit and one commit.
4. Log every decision and tradeoff in the task, not the transcript.
5. Verify each unit before the next. Do not batch checks at the end.
6. Pause only for irreversible actions: deploy, data deletion, force-push, an
   auth or CI gate change, or a message to an external person.
7. Before stopping, write the handoff and the exact next action.

## correct

1. Mine commits, reverts, review send-backs, and lessons for mistake classes.
2. A class counts after two occurrences.
3. Fix at the highest level that works: architecture, then types, then a lint
   whose error names the fix, then a behavior test, and docs last.
4. Prove the new check fails on a real past mistake.
5. Append the rule to `references/rule-ledger.md`. Never grow `AGENTS.md`.
