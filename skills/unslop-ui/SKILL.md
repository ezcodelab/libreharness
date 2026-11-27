---
name: unslop-ui
description: Run one UI surface through baseline evidence, two variants, one A/B operator choice, implementation, verification, review, and ship. Use for an end-to-end UI unslop loop, not for a contained visual fix.
---
<!-- SPDX-License-Identifier: MIT -->
# Unslop UI

Load `ui-design`, `verification`, `work-queue`, and `shipping`. Use
`ui-design/references/review.md` for the review criteria. The only operator stop
is choosing A or B after both variants have evidence. Stop early only for a
dirty worktree, an unrepaired runtime path, an irreversible action, or genuinely
ambiguous scope.

## 1. One surface, one task

Require one surface. Read the project `AGENTS.md`, UI contract, UI system,
feature map, tokens, components, and the callers of the surface. Find the
project's real UI launch, capture, and smoke commands.

Reuse an inbox or active task for the same surface. Otherwise call `tasks` with
`new` and the surface scope. Write one `Data shape:` line and one allowlisted
`Verify:` line into the task Plan using the `work-queue` brief reference. If the
branch is `main` or `master`, create `feature/ui-<surface-slug>` and claim there.
If the worktree is dirty, stop and name the files; do not stash the change.

## 2. Baseline

Use the project's real verification path. If none can launch, drive, and observe
the surface, use the `verification` skill before editing UI.

Run the baseline full check and the real UI journey. Save evidence under
`<os-temp>/unslop-ui/<task>/baseline/`. Cover the affected journeys and
must-hold states at 1440, 1024, and 390, plus any project width. Include empty,
loading, error, partial, disabled, focus, long name, and long list where they
apply. Use synthetic data; never capture a secret, credential, production URL,
or private value.

Read the implementation and record a short map in the task: surface job,
primary action, tokens, components, states, observed defects, and evidence gaps.
Do not edit UI code in this stage.

## 3. One problem, two variants

Apply `ui-design/references/review.md` to the baseline. Report only observed
deviations. Identify the single highest-impact structural or system defect and
define two short-lived variants:

- **A:** the smallest change that fixes the evidence within the current system.
- **B:** a stronger structural change using the same tokens and components.

No new token or component unless the baseline proves the system cannot carry the
case. No new design document. No permanent variant lane.

## 4. Build both variants

Use the same model, synthetic data, states, and viewport sizes for A and B.
Build them sequentially in the task. Keep each recoverable as a patch or commit
under `<os-temp>/unslop-ui/<task>/variants/`. Do not run parallel lanes that
edit the same files. Do not merge either variant.

Run the project's real UI check for each variant and capture the same evidence
set under `variants/a/` and `variants/b/`. Mark a variant unverified if it cannot
run; do not present it as a choice.

## 5. A/B gate

Present A and B side by side with the baseline defect each fixes, artifact paths
for the same state and viewport pair, the visible tradeoff, and anything left
unverified. Ask exactly `Reply A or B.` Then stop. Do not implement, merge,
commit to the feature branch, review, or ship before the reply. Do not choose for
the operator. If the reply is not A or B, ask once for the letter.

## 6. Implement the selection

Apply the selected variant and remove the losing one. Keep the surface scope.
Use product tokens and components. Preserve API and behavior unless the task
acceptance changes them. If the UI system changes, update the existing contract,
system document, and gallery in the same change; do not manufacture docs for a
contained fix.

## 7. Verify

Run, in order:

1. the project's UI unit, type, and structural audit commands;
2. the real browser journey and accessibility check;
3. the full project check from the task Verify line.

Capture the final journey and states under `<os-temp>/unslop-ui/<task>/final/`
at the baseline widths. Compare before and after. A green full check that does
not drive the UI does not prove the UI.

Apply `ui-design/references/review.md` to the final artifacts. Fix only confirmed
blockers, then rerun the same checks. There is no second abstract pass.

## 8. Record, review, close, ship

Record the selected variant, artifact paths, commands, and results in the task
Evidence. Check acceptance only where evidence supports it. Call `tasks` with
`review` and the real UI check, then move the task to review. Write the handoff
from the `work-queue` reference, call `tasks` with `validate`, and follow the
`shipping` skill to open one ready PR, wait for required CI on the exact head, and
merge only the reviewed head.

If the same visual or interaction defect repeats, encode it in a token, component
API, lint, audit, or real journey check. Do not add another design essay.

## Exit

Report the chosen variant, files changed, evidence paths, checks, PR state, and
anything still unverified. Stop only after merge or a declared blocker.
