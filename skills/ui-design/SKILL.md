---
name: ui-design
description: Use for any UI or UX work — layouts, components, styling, visual review, or interface copy, including new screens, redesigns, and "does this look right" checks. Encodes the operator's portable design language; the project's tokens, components and design docs take precedence.
---
<!-- SPDX-License-Identifier: MIT -->

# UI design language

The operator's taste, portable across projects. Read the project's existing
tokens, components and design doc first; they win where they are more specific.

## Principles

1. **Less is more.** Every element earns its place or leaves. Remove before you
   add. Density means more signal per screen, not more chrome.
2. **Structure over labels.** If a label is needed to explain the layout, the
   layout is wrong. A label names a control or a value; it does not teach the
   screen. Accessibility labels, destructive-action confirmations, ambiguous
   icons and table headers are not explanations — keep them.
3. **One design language.** One spacing scale, one type scale, one radius and
   border vocabulary, one button hierarchy, one icon set. Use the project's
   tokens and components; never invent a per-page color, font, shadow or
   spacing value.
4. **States are design.** Empty, loading, error, disabled, focus, hover and
   selected are part of the screen, not an afterthought. No dead frames, no
   plausible-looking zeroes.
5. **Copy is UI.** Short, plain, specific. Name the thing and the action. No
   marketing, no exclamation marks, no "successfully".
6. **No developer identifiers.** Never show internal API field names, database
   columns, route paths, class or mechanism names, slugs, or stack traces. Say
   what the operator controls, in their words. If a value has no human name, it
   does not belong on the screen.
7. **Accessibility is not optional.** Contrast, visible focus, keyboard paths,
   real labels, reduced motion. A visual choice that breaks these loses.
8. **Motion explains, never decorates.** Animate a state change, not an
   entrance. Respect `prefers-reduced-motion`.

## Before you build

- Does an existing component or token already do this? If yes, use it.
- Can the element be removed instead of restyled? If yes, remove it.
- Is this a new pattern or a variant of an existing one? Prefer the variant —
  and a new component joins the system or does not ship.
- What are the empty, loading, error and long-content cases?
- Write a compact design plan before code: 4 to 6 named colors, the typefaces
  and their roles, one layout concept, and 3 to 5 principles. Then review the
  plan: if a choice is what you would produce for any similar brief, revise it
  and say what changed. The project's tokens and components still win.

## Generic-default check

These are common generated defaults, not forbidden styles. Use one only when
the brief asks for it:

- warm cream, high-contrast serif, and a terracotta accent;
- near-black with one acid-green or vermilion accent;
- broadsheet hairline columns with zero radius;
- identical rounded SaaS cards with the same soft shadow;
- all-caps eyebrow labels above every heading;
- middle-dot metadata strings;
- decorative fade-and-slide entrances on every section.

If the design would look the same for a toy, a dashboard, and a bank, it is a
default rather than a choice for this subject.

## Review checklist

- One primary action; the rest are secondary or quiet.
- Labels name things; none explain the layout.
- No developer identifiers in labels, statuses, empty states or errors.
- No new colors, spacing, radii, shadows or fonts outside the tokens.
- Every state is designed and every control has a focus style.
- Long names, empty lists and failures do not break the layout.
- Remove one element: does the screen still work? If yes, leave it removed.

## Red flags

Badge soup, a paragraph of help text under every control, mixed icon weights,
three button styles for one action, a modal for a simple choice,
placeholder-only labels, color as the only signal, per-page CSS variables,
decorative gradients or shadows, raw field names (`api_key`, `user_id`), slugs,
IDs or stack traces in operator copy.

## Extending this

Project tokens and components live in the repo, not here. To add a rule:
`/close` with the rule in the operator's words, then `/tune` to promote it into
this file. One line per rule; delete rules that stop paying off. This file is
global: edit it only with the operator's approval.
