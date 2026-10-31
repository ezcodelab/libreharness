---
description: Review a UI screenshot against references and the ui-design rules
---
<!-- SPDX-License-Identifier: MIT -->
Review the UI shown in: $ARGUMENTS

1. Load the `ui-design` skill.
2. Read the approved references from `$UI_REFERENCES_DIR` when set, otherwise
   from the project's `docs/ui/` directory. List what you are comparing against.
3. If you can see the image(s), compare at the supplied widths and report only
   deviations:
   - developer identifiers or labels that explain the layout
   - more than one primary action; weak hierarchy; inconsistent spacing,
     type, radius, colour or icon set
   - copy that is vague, marketing-like, or restates the label
   - missing empty/loading/error/focus/long-content states
   - contrast, focus visibility, keyboard path, touch target
   - a generic-default look that does not answer the specific subject: warm
     cream plus serif plus terracotta, acid green on near-black, broadsheet
     hairline columns, identical rounded SaaS cards, all-caps eyebrows,
     middle-dot metadata, or decorative entrance motion. Name the missing
     subject-specific choice, not just the style.
4. If you cannot see images, say so and run the text checklist instead
   (labels, copy, states). Ask for the screenshot as an attachment or a DOM
   snapshot; do not guess.
5. Output: **Blocking**, **Quick wins**, **Keep**. No code edits in this turn.
