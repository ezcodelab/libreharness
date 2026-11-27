---
name: no-comments
description: Strip comment alibis before review. Use before committing or reviewing a diff. Removes narration, commented-out code, dead markers, workaround justifications, and unproven suppressions, and turns each claimed constraint into a type, lint, test, or runtime check.
---
<!-- SPDX-License-Identifier: MIT -->

# No comments

A comment that explains a workaround is the workaround's alibi. Delete the
comment, then make the code self-evident or make the constraint executable.

## Scope

The caller's files or diff. Default: `git diff` against the merge base, plus the
working tree. Code comments and prose docs are in scope. The installed
`comment-audit` covers high-confidence comment and suppression classes.
Tautology and stale prose stay a review read.

## Entrypoint

Plugin setup exposes the audit at
`$XDG_CONFIG_HOME/opencode/bin/comment-audit`, defaulting to
`~/.config/opencode/bin/comment-audit`. The npm package exposes the same wrapper
as `bin/comment-audit`. Do not call a clone path and do not reimplement a rule.

```sh
audit="${XDG_CONFIG_HOME:-$HOME/.config}/opencode/bin/comment-audit"
"$audit" .                        # full inventory
"$audit" --diff <patch>           # added lines only
"$audit" --strict --diff <patch>  # clean-repo ratchet
```

## Keep exceptions

These may stay. When unsure, delete.

- A legal or license header, including SPDX.
- A constraint forced by an external dependency, platform, vendor, or protocol we
  cannot change, with a link to the upstream issue or spec, or a `file:line` in a
  pinned dependency.
- A formatter directive whose rule is style-only, such as `prettier-ignore`,
  `fmt: off`, or `isort: skip`.
- A doc comment that defines a public API contract.
- An issue, CVE, or RFC link that records a constraint code cannot express.
- A suppression with a scoped `comment-discipline: allow <reason>` marker or a
  linked external constraint.

Every other suppression is `suppression-debt`. This includes `eslint-disable`,
`@ts-ignore`, `@ts-expect-error`, `type: ignore`, `noqa`, `pylint: disable`,
`nosec`, `shellcheck disable`, and `nolint`. Remove the need for the rule or
prove the rule is style-only and name that proof in the marker.

## Docs

Apply the same test to prose in the caller's diff. A new doc needs a reason the
task named; otherwise delete it. One fact has one owner: link to that owner
instead of restating the rule in README, CONTRIBUTING, AGENTS, and docs at once.
Move a non-obvious, still-binding decision to an ADR or design note; do not turn
every deleted comment into a new doc. Delete stale commands, versions, and links.
Run `unslop` on what remains.

## Semantic kills

Tautologies, stale notes, and true workaround sermons are judgment. The audit
does not guess with NLP rules. For each accepted finding choose one outcome:
delete it, make the smallest in-scope root-cause fix, or encode the constraint in
a type, test, lint, or runtime check and then delete it. Do not rewrite unrelated
application logic, bolt on a symptom guard, or keep the sermon as policy. If the
fix is out of scope, open a task and leave the finding explicit; uncertain keeps
die.

## Baselines

Use `--baseline` for recorded inventory, not to launder a diff. A baseline
records path, rule, text, and a context anchor, so a pure line shift passes and a
move to another code context fails. Regenerate the baseline only after a
deliberate cleanup.

## Steps

1. Read the diff. Mark each comment on a changed line `KILL` or `KEEP` with the
   exception that applies.
2. `KILL` covers: narration of the change, restating the code, phase and step
   banners, commented-out code, `TODO`/`FIXME`/`XXX` with no owner, a workaround
   with no external reference, a `do not remove/change` without a reference, and
   an unproven suppression.
3. Delete the comment. Do not shorten it into a smaller alibi. In docs, delete
   the unsolicited or duplicated passage instead of rewording it.
4. If deletion hides a real constraint, mark the exact symbol `MUST KILL` and
   reshape it: a branded type, a narrow API, a lint whose error names the fix, a
   runtime check, or a failing test.
5. Run the audit on the saved review diff, then on untracked files:
   `"${XDG_CONFIG_HOME:-$HOME/.config}/opencode/bin/comment-audit" --diff /tmp/opencode/review-$TASK.diff`
   and
   `git ls-files -z --others --exclude-standard | xargs -0 -r "${XDG_CONFIG_HOME:-$HOME/.config}/opencode/bin/comment-audit"`.
   Add `--strict` when `.comment-audit-strict` exists in the repo; every new
   comment then needs a keep or an allow marker. A finding is deleted, reshaped,
   or kept with an external reference. Add `--baseline <file>` only for recorded
   debt outside the diff.
6. Report: files touched, deletions, docs deleted, `MUST KILL` symbols with one
   line each, and kept comments with the exception that applies.
7. Run the same audit through the repository merge path. In LibreHarness and
   GitHub callers, `.github/workflows/comment-audit.yml` is the pinned owner; do
   not add a per-repo copy of the script.

## Exit

No unreferenced workaround comment remains in the diff, no unsolicited or
duplicated doc remains, and every `MUST KILL` symbol either has its reshape or an
open task naming the work. Do not report a comment as enforced when only the
prose changed.
