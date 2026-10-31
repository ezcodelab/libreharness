---
description: Manual lesson capture (legacy; /close is the canonical task close)
---
<!-- SPDX-License-Identifier: MIT -->
Harvest the task just completed. Operator's words, if any: $ARGUMENTS

Follow the `engineering-loop` skill §8 and the project's `AGENTS.md`.

1. If `$ARGUMENTS` is empty and the task is not obvious from this session,
   ask one question and stop.
2. If `$ARGUMENTS` is not empty, it is the operator's wording. Put it in the
   Rule line verbatim, in quotes. Do not paraphrase, shorten, or "improve" it.
   A preference rather than a task event gets `Surprise: none — the operator
   stated a preference` and `Cost: none`; do not invent a discovery to fit the
   template.
3. Append one entry to the project's `docs/process-lessons.md`, in its existing
   format: a dated heading, then Surprise / Cost / Rule / Doc updated. Create
   the file if the project has none.
4. If the task failed a gate or rejected an approach, also add or harden a
   REFUSE or checklist item where it persists, and name the file.
5. Tag `Promote-to-global` on the Rule line when the rule is portable —
   process, or a personal workflow/design preference — not product or stack
   dogma. If you cannot tell whether it is global or project-specific, ask.
6. Show the entry and stop. Do not refactor anything.
