<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Named principles

These are short names for rules the harness already follows. Use a name to
steer a decision; then say which decision it changed. A citation with no
decision behind it is noise.

The list is deliberately small. Add a principle only when two real failures
share it and the existing names do not.

The named format is adapted from Cursor's pstack (MIT). The wording and
examples here are LibreHarness's own.

## Attack the premise

**Use when** two or more fixes that share one premise have failed the same
gate.

Write the shared premise as one sentence. Find an observation that would come
out differently if it were false, and make it. If the evidence contradicts the
premise, the cause is elsewhere. Do not write a third fix on the same premise.

**Changes the decision:** stops a fix loop and turns it into a diagnosis.

## Prove it works

**Use when** a task is about to be declared done.

Check the real artifact: run the feature, read the written value, inspect the
diff, or replay the failing case. A passing build, a file timestamp, or an
agent's self-report is a proxy. Keep the command and output as evidence. When
the check cannot run, say what remains unproven and what would prove it.

**Changes the decision:** turns "done" into a check that can fail.

## Sequence verifiable units

**Use when** work spans several steps, files, commits, or lanes.

End each unit in a verifiable state before starting the next. Keep one task to
one reviewable diff. Stack follow-ups instead of growing a branch. The order
should let a reviewer verify each step without trusting the summary.

**Changes the decision:** splits a batch into a sequence whose claims can be
checked separately.

## Explain the number

**Use when** a speed, cost, token, latency, or eval number is about to be
reported or acted on.

Name what limits the result. Rule out errors, skipped or cached work, an
untuned side, and run-to-run noise. Run both sides with the same settings and
report the run count, range, and limiter. If you cannot name the limiter, the
result is inconclusive.

**Changes the decision:** prevents a plausible number from becoming a claim.

## Guard the context window

**Use when** reading many files, collecting long outputs, or planning a
fan-out.

Route bulk reading to subagents and keep their findings in the main thread.
Summarize before a phase boundary. Write a handoff while the context still
contains what the next session needs. Do not carry a finished phase's raw
output forward.

**Changes the decision:** trades a large context for a small, durable summary.

## Separate before serializing shared state

**Use when** two or more actors might write the same file, branch, key, or
record.

Eliminate the sharing first: disjoint files, separate worktrees, separate
state directories. Add a lock or a queue only when one shared writer is a real
invariant. A lock around avoidable sharing is complexity, not safety.

**Changes the decision:** replaces coordination with isolation.

## Subtract before you add

**Use when** adding an abstraction, option, validator, or compatibility layer.

Remove dead code, redundant checks, and stub references first. Build on the
simpler base. Prefer deletion to a new layer. If the new thing does not earn
its place after the subtraction, do not add it.

**Changes the decision:** shrinks the diff before it grows.

## Encode lessons in structure

**Use when** the operator corrects the same mistake twice, or a lesson keeps
being repeated in prose.

Fix it at the highest level that works: architecture, then types, then a lint
whose error names the fix, then a test, and docs last. Prove the check fails on
a real past mistake. A rule that only lives in a document is the fallback for
judgment calls, not the first choice.

**Changes the decision:** turns a repeated correction into an enforced check.

## Using the names

- **In a brief:** name the principles that shape the acceptance checks.
- **In a review:** name the one that changed a finding or a verdict.
- **In a close:** record the principle that changed the next action, not a
  list of principles that were merely relevant.
- **In a plan:** use a name to justify a split, a deletion, or a proof.
