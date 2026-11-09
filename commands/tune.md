---
description: Propose deletions and at most five portable AGENTS or skill patches from measured evidence
---
<!-- SPDX-License-Identifier: MIT -->
Tuning turn. Use this after a work wave, not as a task finish. Do not do
feature work, and do not edit global config yet.

1. Run the docs and skill-budget check:
   `python3 "${HARNESS_HOME:-$HOME/.config/opencode}/bin/docs_lint.py" . --skills-dir "${HARNESS_HOME:-$HOME/.config/opencode}/skills"`.
2. Run the `state-audit` skill over the project or the area changed since the
   last tune. Update `docs/state-machines.md`, group confirmed invalid
   transitions by root cause, and propose the highest-impact group. Do not fix
   feature code in this turn.
3. Read the queue report and metrics:
   `python3 "${HARNESS_HOME:-$HOME/.config/opencode}/bin/tasks.py" report`
   and `${HARNESS_STATE:-$HOME/.local/state/libreharness}/metrics/workflow-log.csv`.
   Look for rework, stale active tasks, blocked work, and lanes that did not pay
   off.
4. Mine repeated corrections. Read close lessons, review comments, reverts, and
   queue logs. A class counts after two occurrences. For each class, fix at the
   highest level that works: architecture, then types, then a lint whose error
   names the fix, then a test, and docs last. Prove each new check fails on a
   real past mistake. Do not add a new command when `/tune` or `/close` can own
   the rule.
5. Propose deletions first: obsolete paths, docs, options, or steps that did not
   pay off. Leaner beats more rules.
6. Propose at most five patches to `AGENTS.md`, the `engineering-loop` skill,
   the `ui-design` skill, another skill under `${HARNESS_HOME}/skills/`, or the
   named principles in `docs/principles.md`, as a unified diff. For each, quote
   the evidence, name the target, and say what it replaces or deletes.
7. Prefer folding a rule into an existing bullet over adding a new one. For a
   skill promotion, run `docs/skill-eval.md` first and include the trigger rate,
   pass delta, sample size, and limits. A neutral or negative result is a
   deletion candidate, not a promotion.
8. Stop for approval. Nothing is promoted in this turn.
9. After the operator approves or rejects, record the date in the metrics file.
