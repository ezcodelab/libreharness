<!-- SPDX-License-Identifier: MIT -->
# Spec shape for a goal

Use when a goal has two to six children. A single task keeps the flat acceptance
checklist in its packet.

Adapted from `github/spec-kit` (`spec-template.md`, MIT).

## Child shape

```text
### P1 <child name>

Independent test: <one command or observable action that proves this child>
Acceptance scenarios:
- Given <state>, when <action>, then <outcome>
- Given <state>, when <action>, then <outcome>
Not in this child: <the adjacent work this slice deliberately leaves out>
Clarify: [NEEDS CLARIFICATION: <question>] or none
Success signal: <measurable outcome, not an implementation choice>
```

## Rules

- Order children P1 to Pn. P1 is the smallest useful slice.
- Each child is independently implementable, testable, and shippable.
- A child that cannot name its independent test is too vague. Split it or mark
  the unknown.
- Use `[NEEDS CLARIFICATION: ...]` instead of inventing a requirement. Resolve
  it before the child is claimed.
- Success signals are outcomes. "Account creation completes in under two
  minutes" beats "add a cache".
- Dependencies become `depends_on`, not prose.
- One child, one reviewable diff. If it cannot be reviewed in one sitting, split
  it.
- The goal's own acceptance is the cross-child outcome that survives when every
  child lands.
