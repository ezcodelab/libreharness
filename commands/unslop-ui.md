---
description: Run the complete UI unslop loop for one surface with one A/B selection gate
---
<!-- SPDX-License-Identifier: MIT -->
Unslop UI: $ARGUMENTS

Run one surface through the full loop. The only operator stop is choosing A or B
after both variants have evidence. Do not pause for routine progress,
confirmation, review, close, or ship. Stop early only for a dirty worktree, a
missing runtime path you cannot repair, an irreversible action, or genuinely
ambiguous scope.

## 1. Resolve one surface and one task

Require a surface in the arguments. If it is empty, stop once with
`/unslop-ui <screen-or-component>`.

Read the project `AGENTS.md`, UI contract, UI system, feature map, tokens,
components, and callers of the surface. Find the project's real UI launch,
capture, and smoke commands.

Reuse an inbox or active task for the same surface. Otherwise create one:

```text
tasks new \
  "Unslop <surface> UI" --project "<project>" --tags ui \
  --scope "Change one UI surface using the product system and runtime evidence." \
  --acceptance "- [ ] Baseline evidence covers the required states and widths.
- [ ] Two variants use the same data, states, widths, and model.
- [ ] The selected variant is implemented with product tokens and components.
- [ ] The project UI check, full check, and review artifact pass."
```

Write exactly one `Data shape:` JSON line and one allowlisted `Verify:` line into
the task Plan. `Verify` is the project's full check, not a unit-only substitute.
If the branch is `main` or `master`, create `feature/ui-<surface-slug>`. Claim
there. If the worktree is dirty, stop and name the files; do not hide the change
in a stash.

## 2. Establish the real baseline

Use the project's existing verification path. If none can launch, drive, and
observe the real surface, use the `verification` skill to create one before any
UI edit.

Run the baseline full check and the real UI journey. Save evidence under
`/tmp/opencode/unslop-ui/<task>/baseline/`. Capture the affected journeys and
must-hold states at 1440, 1024, and 390, plus any width the project contract
requires. Cover empty, loading, error, partial, disabled, focus, long name, and
long list where they apply. Use synthetic data and never capture a secret,
credential, production URL, or private value.

Read the current implementation and produce a short map in the task: surface
job, primary action, tokens, components, states, observed defects, and evidence
gaps. Do not edit UI code in this stage.

## 3. Review the baseline and choose one problem

Follow the procedure in
the `design-review` command against the
baseline artifacts. This is an internal analysis step, not a stop. Report only
observed deviations. Identify the single highest impact structural or system
defect. Do not turn the whole screen into a redesign list.

Define two short-lived variants for that one problem:

- **A:** the smallest change that fixes the evidence within the current system.
- **B:** a stronger structural change using the same tokens and components.

No new token or component unless the baseline proves the existing system cannot
carry the case. No new design document. No permanent variant lane.

## 4. Build both variants

Use the same model, synthetic data, states, and viewport sizes for A and B.
Build them sequentially in this task. Keep each recoverable as a patch or commit
under `/tmp/opencode/unslop-ui/<task>/variants/`. Do not run parallel lanes that
edit the same files. Do not merge either variant.

Run the project's real UI check for each variant and capture the same evidence
set under `variants/a/` and `variants/b/`. If a variant cannot run, mark it
unverified and do not present it as a choice.

## 5. Stop for the only human choice

Present A and B side by side with:

- the observed baseline defect each fixes;
- artifact paths for the same state and viewport pair;
- the visible tradeoff;
- anything either variant leaves unverified.

Ask exactly: `Reply A or B.` Then stop. Do not implement, merge, commit to the
feature branch, review, or ship before the reply. Do not choose for the operator.
If the reply is not A or B, ask once for the letter.

## 6. Implement the selection

Apply the selected variant and remove the losing one. Keep the surface scope.
Use the product tokens and components. Preserve the API and behavior unless the
task acceptance explicitly changes them.

If the change alters the UI system, update the existing project contract,
system document, and gallery in the same change. If it only fixes an existing
pattern, do not manufacture documentation.

## 7. Verify and converge

Run, in order:

1. the project's UI unit, type, and structural audit commands;
2. the project's real browser journey and accessibility check;
3. the full project check from the task Verify line.

Capture the final journey and states under `/tmp/opencode/unslop-ui/<task>/final/`
at the same widths as the baseline. Compare before and after. A green full check
that does not drive the UI does not prove the UI.

Follow the final design-review procedure from `commands/design-review.md`. Fix
only confirmed blockers, then rerun the same checks. There is no second abstract
pass.

## 8. Record, review, close, ship

Record the selected variant, baseline and final artifact paths, commands, and
results in the task Evidence. Check acceptance only where the evidence supports
it.

Follow the review procedure in
the `review` command. Run the task Verify
and the real UI check through the `tasks` tool, then move the task to `review`.
These are internal steps; do not ask the operator to invoke another command.

Write the structured handoff, call `tasks` with `validate`, and follow the close
procedure in `commands/close.md`. Open one ready PR, wait for required CI on the
exact head, and merge only the reviewed head through the `shipping` skill.

If the same visual or interaction defect repeats, encode it in a project token,
component API, lint, audit, or real journey check. Do not add another design
essay.

Return one final report: chosen variant, files changed, evidence paths, checks,
PR state, and anything still unverified. Stop only after merge or a declared
blocker.
