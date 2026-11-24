---
name: unslop
description: Cut AI tells from replies, PR bodies, commit messages, and docs. Use before sending prose or reviewing writing. Removes filler, hedging, metaphor, and formatting tells while keeping every fact.
---
<!-- SPDX-License-Identifier: MIT -->

# Unslop

Edit text to remove AI patterns. Scan for the patterns below, then rewrite. Keep
the meaning and the intended tone.

This skill is about writing. Code cleanup, dead-code removal, and anti-pattern
sweeps belong to `engineering-loop` and `correct`.

## Prose rules

1. No trailing "-ing" phrase that adds no fact.
2. No vague attribution. Name the source or delete the claim.
3. No AI vocabulary: additionally, crucial, delve, enhance, foster, landscape,
   pivotal, showcase, testament, underscore, vibrant.
4. Say "is" or "has", not "serves as", "stands as", "boasts", or "features".
5. No "not just X, but Y". State the point.
6. Do not force ideas into threes.
7. One name per thing. Repeat it.
8. No "from X to Y" unless X and Y sit on a real scale.
9. No em dash, en dash, or hyphen used as a dash. Use a period or a comma.
10. A colon goes before a list or an example, never mid-sentence as a connector.
11. Do not bold every proper noun or acronym.
12. No bold label and colon that restates its line.
13. Sentence case headings.
14. No decorative emojis.
15. Straight quotes.
16. No chatbot phrases.
17. No praise or agreement openers. Answer directly.
18. Cut filler. "In order to" becomes "to".
19. Use a hedge only when the uncertainty is real: "may".
20. No generic conclusion. State the specific plan or fact.
21. No abstract metaphor nouns: substrate, wedge, vector, nexus, primitive,
    surface, scaffolding, paradigm, north star, flywheel, harness.
22. Say what it does, not how it feels. Name the mechanism or the number.
23. One idea per sentence. Split a sentence the reader must reread.
24. Active voice. Name the actor unless it is unknown or does not matter.
25. Cut adverbs or use a stronger verb. Give the number.
26. Use the plain word: "use", not "utilize" or "leverage".
27. No metaphor, aphorism, or personified code where a literal phrase exists.
28. Write whole sentences with their articles and verbs.

## Evidence labels

Every claim about the system carries one label:

- `[measured]`: a command, output, or number you ran.
- `[inferred]`: a conclusion drawn from measured facts.
- `[guess]`: a hunch with no evidence yet.

## Check

Run `tests/harness-ratchets.test.mjs` when the repo has it. It enforces the ASCII
punctuation subset in the scoped instruction files. The rest is a read, not a
regex.

## Exit

The text keeps every fact, names its evidence, and reads as if a person wrote it
in one pass.
