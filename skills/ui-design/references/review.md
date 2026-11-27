<!-- SPDX-License-Identifier: MIT -->
# UI review

Review UI evidence from the running product against the project system and
approved references.

1. Read the project's tokens, components, design docs, and the callers of the
   changed feature.
2. Find the project's `verify-<app>` skill and feature map. Use existing
   evidence only when it matches the current tree and affected journey.
   Otherwise run the mapped journey and capture screenshots, a short recording,
   or a trace from the real surface.
3. Read approved references from `$UI_REFERENCES_DIR` when set, otherwise from
   the project's `docs/ui/` directory. List what you compare against.
4. If the surface cannot be driven or observed, mark the review UNVERIFIED and
   report the missing launch, drive, or capture step. Use the `verification`
   skill to repair the path. Do not make the operator the manual browser bridge.
5. For variants, compare the same viewport, content, and must-hold states side
   by side. State the observable difference and ask the operator to choose. For
   a contained change, compare before and after.
6. Report only deviations the evidence shows:
   - missing or invented tokens, components, spacing, type, radius, or icons
   - hierarchy, state, focus, contrast, keyboard, touch, or long-content failure
   - copy that names implementation details or does not name the user outcome
   - a final-screen-only claim where the journey or failure path is unproven
7. Output **Blocking**, **Evidence**, **Quick wins**, **Keep**, and the selected
   variant when one exists. Name artifact paths for the task Evidence. Do not
   edit code in this review.
