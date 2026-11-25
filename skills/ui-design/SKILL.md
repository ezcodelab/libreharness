---
name: ui-design
description: Use for any UI or UX work: layouts, components, styling, visual review, or interface copy, including new screens and "does this look right" checks. The project's tokens, components, callers, and runtime evidence take precedence over this portable guidance.
---
<!-- SPDX-License-Identifier: MIT -->

# UI design language

Read the project's tokens, primitives, components, design docs, and the callers
of the feature before choosing a layout or style. Those files win where they
are more specific.

## Principles

1. **One system.** Use the project's spacing, type, radius, border, color, icon,
   and motion tokens. A new token or component needs a product reason and proof
   that an existing one cannot carry the case.
2. **Structure before decoration.** Name the user task, information order, and
   interaction path before adding visual treatment. Remove an element before
   restyling it.
3. **States are design.** Empty, loading, error, disabled, focus, hover,
   selected, long-content, and failure states are part of the screen. No dead
   frames and no plausible-looking zeroes.
4. **Copy is UI.** Name the thing and the action in the operator's words. Do not
   show internal field names, routes, slugs, IDs, or stack traces.
5. **Accessibility is not optional.** Contrast, visible focus, keyboard paths,
   real labels, touch targets, and reduced motion hold before visual polish.
6. **Motion explains.** Animate a state change, not an entrance.

## Before you build

- List the affected user journeys, the must-hold states, and the observable end
  state. If the existing structure cannot carry them, fix structure first.
- Reuse an existing component or variant. A new pattern must name what the
  current system cannot express.
- Do not accept the first visual direction. For a new direction or unresolved
  layout, build short-lived variants and capture the same views and states for
  each. Choose from side-by-side evidence with the operator. For a contained
  change, compare before and after.
- Use the project's runnable verification path for evidence: screenshots from
  the real surface, a short recording, or a journey trace. A final screenshot
  alone is not proof. A model's visual self-score is not evidence.
- When no agent-runnable path exists, use the `verification` skill to create or
  repair one, or mark the UI work UNVERIFIED. Do not make the operator the
  manual bridge to the browser.

## Review

- The change uses product tokens and components, or names the accepted reason
  for a new one.
- One primary action; hierarchy and states survive empty and long content.
- Copy names user controls and outcomes, not implementation details.
- Evidence covers the affected journey and must-hold states. Variants use the
  same viewport and state set.
- Report what the artifacts show. Do not approve from a description of why the
  layout feels right.

When the same visual or interaction mistake repeats, encode it in a product
token, component API, lint, or journey check before adding prose here.
