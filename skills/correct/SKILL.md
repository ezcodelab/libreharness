---
name: correct
description: Turn a repeated agent mistake into a check. Use from /close or /tune when the same correction appears twice, or when the operator names it. Fix at the highest level that works and prove the new check fails on the past mistake.
---
<!-- SPDX-License-Identifier: MIT -->

# Correct

Assume the next agent sees only the files it opens, copies the nearest example,
and takes the shortest path that compiles. Change the repo so the wrong path stops
working.

## Inverted pyramid

Fix each class at the highest level that works. Do not drop a level because it is
easier.

1. **Architecture.** Give each piece of state one owner and each task one supported
   way. Hide internals so the wrong import fails. Replace hand-synced copies with
   one source of truth. Delete the old path an agent would copy.
2. **Types.** Make the bad state unrepresentable: a union instead of two booleans,
   a brand instead of a bare string, a parsed value instead of raw JSON.
3. **Lint or check.** Add the rule to `tests/harness-ratchets.test.mjs` or the
   project's lint, and make the error name the file, type, or function to use
   instead. If the pattern is already widespread, baseline the count and fail only
   on new ones.
4. **Test.** Assert the behavior a user observes, so the test fails when the
   behavior breaks and survives an internal change.
5. **Prose.** Last, and only for judgment calls. Nothing fails when an agent skips
   it. Write it with `references/skill-writing.md`.

## Steps

1. Gather evidence: commits, reverts, review send-backs,
   `docs/process-lessons.md`, and comments that justify a workaround. A class
   counts after two occurrences.
2. For each class, name the level that makes it impossible, not just harder.
3. Implement the check. Prove it fails on the real past mistake: run it against the
   old code, or add a fixture copied from the real failure. Paste the failure.
4. Fix the code the check now rejects. Re-run the check and the full suite.
5. Append one row to `references/rule-ledger.md`: date, rule, level, check command,
   and the past mistake it fails on.
6. Never add a row to the `AGENTS.md` Rule enforcement table. It holds four
   suite-level checks; per-rule detail belongs in the ledger.

## Ownership

`correct` runs only when the operator names it, or from `/close` and `/tune` after
a mistake class repeats twice. An in-flight `bug-fix`, `feature`, or `refactoring`
does not switch into `correct`. It records the candidate and leaves the sweep to
the next close or tune.

## Exit

Each touched class has a check, the check fails on the past mistake and passes on
the fix, the full suite is green, and the ledger has one row per class.
