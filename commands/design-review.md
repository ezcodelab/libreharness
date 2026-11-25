---
description: Compare UI evidence from the running product against references, tokens, and the ui-design rules
---
<!-- SPDX-License-Identifier: MIT -->
Review the UI for: $ARGUMENTS

1. Load the `ui-design` skill. Read the project's tokens, components, design
   docs, and the callers of the changed feature.
2. Find the project's `verify-<app>` skill and feature map. Use its existing
   evidence only when the artifact matches the current tree and affected
   journey. Otherwise run the mapped journey and capture screenshots, a short
   recording, or a trace from the real surface.
3. Read approved references from `$UI_REFERENCES_DIR` when set, otherwise from
   the project's `docs/ui/` directory. List what you compare against.
4. If the surface cannot be driven or observed, mark the review UNVERIFIED and
   report the missing launch, drive, or capture step. Use `verification` to
   repair the path. Do not ask the operator for a manual screenshot as the
   default bridge.
5. For variants, compare the same viewport, content, and must-hold states side
   by side. State the observable difference and ask the operator to choose.
   For a contained change, compare before and after.
6. Report only deviations the evidence shows:
   - missing or invented tokens, components, spacing, type, radius, or icons
   - hierarchy, state, focus, contrast, keyboard, touch, or long-content failure
   - copy that names implementation details or does not name the user outcome
   - a final-screen-only claim where the journey or failure path is unproven
7. Output **Blocking**, **Evidence**, **Quick wins**, **Keep**, and the selected
   variant when one exists. Name artifact paths for the task Evidence. No code
   edits in this turn.
