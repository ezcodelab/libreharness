---
name: no-comments
description: Strip comment alibis before review. Use before committing or reviewing a diff. Removes narration, commented-out code, dead markers, and workaround justifications, and turns each claimed constraint into a type, lint, test, or runtime check.
---
<!-- SPDX-License-Identifier: MIT -->

# No comments

A comment that explains a workaround is the workaround's alibi. Delete the
comment, then make the code self-evident or make the constraint executable.

## Scope

The caller's files or diff. Default: `git diff` against the merge base, plus the
working tree. Code comments and prose docs are in scope. The portable audit
covers high-confidence comment classes; tautology, stale prose, and suppressions
stay a review read.

## Keep exceptions

These may stay. When unsure, delete.

- A legal or license header, including SPDX.
- A constraint forced by an external dependency, platform, vendor, or protocol we
  cannot change, with a link to the upstream issue or spec, or a `file:line` in a
  pinned dependency.
- `prettier-ignore`, `shellcheck disable=`, or a formatter directive whose rule is
  style-only.
- A doc comment that defines a public API contract.
- An issue, CVE, or RFC link that records a constraint code cannot express.

A lint or type suppression on a correctness or safety rule is not an exception.
Look up the rule, remove the suppression, and fix the code.

## Docs

Apply the same test to prose in the caller's diff. A new doc needs a reason the
task named; otherwise delete it. One fact has one owner: link to that owner
instead of restating the rule in README, CONTRIBUTING, AGENTS, and docs at once.
Move a non-obvious, still-binding decision to an ADR or design note; do not turn
every deleted comment into a new doc. Delete stale commands, versions, and links.
Run `unslop` on what remains.

## Steps

1. Read the diff. Mark each comment on a changed line `KILL` or `KEEP` with the
   exception that applies.
2. `KILL` covers: narration of the change, restating the code, phase and step
   banners, commented-out code, `TODO`/`FIXME`/`XXX` with no owner, a workaround
   with no external reference, and `do not remove/change` without a reference.
3. Delete the comment. Do not shorten it into a smaller alibi. In docs, delete
   the unsolicited or duplicated passage instead of rewording it.
4. If deletion hides a real constraint, mark the exact symbol `MUST KILL` and
   reshape it: a branded type, a narrow API, a lint whose error names the fix, a
   runtime check, or a failing test.
5. Run the audit on the saved review diff, then on untracked files:
   `python3 "${HARNESS_HOME:-$HOME/.config/opencode}/bin/comment_audit.py" --diff /tmp/opencode/review-$TASK.diff`
   and
   `git ls-files -z --others --exclude-standard | xargs -0 -r python3 "${HARNESS_HOME:-$HOME/.config/opencode}/bin/comment_audit.py"`.
   A finding is deleted, reshaped, or kept with an external reference. Add
   `--baseline <file>` only for recorded debt outside the diff.
6. Report: files touched, deletions, docs deleted, `MUST KILL` symbols with one
   line each, and kept comments with the exception that applies.

## Exit

No unreferenced workaround comment remains in the diff, no unsolicited or
duplicated doc remains, and every `MUST KILL` symbol either has its reshape or an
open task naming the work. Do not report a comment as enforced when only the
prose changed.
