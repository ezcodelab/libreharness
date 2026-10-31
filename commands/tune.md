---
description: Propose deletions and at most five portable AGENTS or skill patches from measured evidence
---
<!-- SPDX-License-Identifier: MIT -->
Tuning turn. Do not do feature work, and do not edit global config yet.

1. Run the docs and skill-budget check:
   `python3 "${HARNESS_HOME:-$HOME/.config/opencode}/bin/docs_lint.py" . --skills-dir "${HARNESS_HOME:-$HOME/.config/opencode}/skills"`.
2. Read the queue report and metrics:
   `python3 "${HARNESS_HOME:-$HOME/.config/opencode}/bin/tasks.py" report`
   and `${HARNESS_STATE:-$HOME/.local/state/libreharness}/metrics/workflow-log.csv`.
   Look for rework, stale active tasks, blocked work, and lanes that did not pay
   off.
3. Propose deletions first: obsolete paths, docs, options, or steps that did not
   pay off. Leaner beats more rules.
4. Propose at most five patches to `AGENTS.md`, the `engineering-loop` skill,
   the `ui-design` skill, or another skill under `${HARNESS_HOME}/skills/` as a
   unified diff. For each, quote the evidence, name the target, and say what it
   replaces or deletes.
5. Prefer folding a rule into an existing bullet over adding a new one. For a
   skill promotion, run `docs/skill-eval.md` first and include the trigger rate,
   pass delta, sample size, and limits. A neutral or negative result is a
   deletion candidate, not a promotion.
6. Stop for approval. Nothing is promoted in this turn.
7. After the operator approves or rejects, record the date in the metrics file.
