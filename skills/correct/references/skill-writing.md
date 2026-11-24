<!-- SPDX-License-Identifier: MIT -->
# Writing a skill

A skill is two documents: the frontmatter description that every session loads,
and the body that loads only when the description fires. Write for both.

Adapted from `mattpocock/skills` (`writing-for-agents`, MIT).

## Two budgets

- **Context load** is the always-on cost: a description, an `AGENTS.md` line, a
  pointer. It is spent every turn, whether or not the skill fires.
- **Cognitive load** is the human's cost: which documents exist and when to
  reach for each. Spend it where human judgement matters, not on indexing.

## Descriptions

The description is a context pointer. Its wording, not its target, decides when
the agent reaches the material.

- Front-load the leading trigger word.
- One trigger per distinct branch. Synonyms that rename one branch are one
  branch written twice.
- State what the skill is for, then the branches that should fire it.
- Name a competing skill only where the two are routinely confused.
- Cut identity that the body already carries.

## Information hierarchy

Rank material by how soon the agent needs it.

1. **In-file step**: what the agent does, in order.
2. **In-file reference**: flat rules consulted on demand.
3. **Disclosed reference**: a `references/` file behind a pointer, loaded only
   when its branch fires.

Put what every branch needs inline. Push branch-specific detail behind a
pointer. That is progressive disclosure, not a token trick: it keeps the steps
visible.

## Completion criteria

Every step ends on a condition that tells the agent it is done. A vague bound
invites premature completion.

- **Clarity**: can done be told from not-done?
- **Demand**: how much does the criterion require? "Every modified caller
  accounted for" forces legwork where "list the changes" does not.

Prefer a bound that is both checkable and exhaustive. If the bound is
irreducibly fuzzy, split the sequence across a real handoff so the next steps do
not pull attention forward.

## Leading words

A leading word is a compact concept the model already holds: `red`, `tracer
bullet`, `one-way door`, `converge`. Repeat the token, not a sentence defining
it. It anchors behaviour in fewer tokens.

Prefer a pretrained word to a coined one. A made-up word recruits no prior and
pays its definition every time it appears.

## Pruning

- Keep each meaning in one authoritative place. Duplication costs maintenance
  and inflates its rank.
- The environment is a source of truth. `package.json`, `--help`, and the tree
  are cheaper than a stale cache in prose.
- Delete a whole sentence that does not change behaviour. Do not shave words
  from it.
- Prompt the positive target. A prohibition drags the forbidden behaviour into
  context; keep one only when it is a hard guardrail, and pair it with the
  target.
- Hunt sediment: stale layers that survive because deleting feels risky.

## LibreHarness checks

- Prose is ASCII.
- The frontmatter `name` matches the directory and the description is present.
- One verifiable unit per step, with the check named.
- No comment alibis. A constraint becomes a type, lint, test, or runtime check.
