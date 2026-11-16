---
name: unslop
description: Audit a codebase for the patterns agents copy, remove anti-patterns, and add a ratchet that prevents new ones. Use for "unslop", "clean this repo for agents", "reduce slop", or "make this a high-quality input".
---
<!-- SPDX-License-Identifier: MIT -->

# Unslop

Unslop is subtraction plus enforcement, not a rewrite. The codebase is the
largest input an agent receives; every surviving anti-pattern is a template.
Make the correct pattern the easiest pattern.

Choose one mode. Audit is read-only. Fix changes one pattern per reviewable
diff.

## Audit

1. **Scope and baseline.** Record the repo, languages, existing gates, and the
   files agents copy most: core types, shared helpers, API clients, UI
   primitives, and state machines. Start from fan-in, imports, and repeated
   shapes, not from a whole-repo read.
2. **Inventory with evidence.** Look for:
   - dead code, unused exports, duplicate helpers, and old APIs;
   - broad `except`/`catch`, swallowed errors, and fallback defaults;
   - ad-hoc config, environment, secret, or network access outside a boundary;
   - stringly-typed states, booleans that encode a machine, and invalid-state
     combinations;
   - phase-narration comments, workaround justifications, and commented-out
     code;
   - stale or contradictory `AGENTS.md`, README, skills, and docs;
   - lint/type suppressions and TODOs with no owner;
   - tests that assert private structure, depend on order, or cannot fail.
3. **Rank** each pattern by copy risk and fix cost. Prefer the pattern agents
   copy most, not the one that is easiest to grep.
4. **Return one page:** baseline counts, top 10 patterns with `file:line`,
   a ratchet plan, fix order, and what not to touch. Do not edit in audit mode.

## Fix

1. **One pattern per diff.** Name the pattern, the replacement, and the check
   that will prevent it from returning. Keep unrelated cleanup out.
2. **Add the ratchet first.** Use a lint rule with an actionable message, a
   type, a test, or a CI check. Prove it fails on a real old example. If the
   existing violations are many, baseline the count and fail only on new ones,
   then burn down the baseline.
3. **Delete the old examples.** Remove dead code, duplicate helpers, and old
   APIs before adding a rule about them. Migrate callers, then delete the old
   path. An agent copies what exists faster than it reads a rule.
4. **Encode the domain.** Replace invalid-state combinations with a type,
   enum, schema, or small state machine. Validate at system boundaries; trust
   internal types. Ban constructs that need nuance to use safely, or hide them
   behind one narrow API.
5. **Clean the prose.** Keep comments only for a non-obvious why. Delete
   narration, restatement, and workaround justifications without an external
   reference. Keep one source of truth for rules. Use `bin/comment_audit.py`
   when the repo provides it.
6. **Test behavior.** Add a regression test for the old failure and a
   property-based test for an invariant where useful. Remove test-only setters
   and mocks that hide the real boundary.
7. **Prove it.** Show the new check failing on the old pattern and passing on
   the replacement, then run the full project check. No mass reformat and no
   unrelated rewrite.

## Good targets

- A shared helper with many callers that hides a bad default.
- A hand-rolled state field with impossible combinations.
- A boundary that trusts unvalidated external input.
- A comment that justifies a workaround instead of naming an issue.
- A stale rule that every reviewer has to restate.

## Stop conditions

Stop and report instead of editing when:

- no baseline or owner exists for the pattern;
- the fix needs a schema, auth, public API, or production decision;
- the repo cannot be isolated or the check would mutate shared state;
- the same pattern fails review twice on the same axis;
- the scope is a whole-repo rewrite, not one enforceable pattern.

## Evidence standard

Unslop claims are measured, not felt. Record the before/after occurrence count,
the exact check that fails on the old example, and the full project check. Name
the principle that shaped the decision: usually "Subtract before you add" or
"Encode lessons in structure".
