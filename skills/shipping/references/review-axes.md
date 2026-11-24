<!-- SPDX-License-Identifier: MIT -->
# Two review axes

A change can pass one axis and fail the other. Report them separately so neither
masks the other.

Adapted from `mattpocock/skills` (`code-review`, MIT).

## Spec

Does the diff implement the originating task or goal?

- Read the task packet, not the diff's own description.
- Missing or partial requirement: quote the acceptance line.
- Unrequested behaviour: name the scope creep and the requirement it is not.
- Present but wrong: point at the requirement and the code path.

## Standards

Does the diff follow this repository's rules?

- A documented repo rule always wins.
- When the repo documents none, use the smell baseline as judgement calls, never
  hard violations:
  Mysterious Name, Duplicated Code, Feature Envy, Data Clumps, Primitive
  Obsession, Repeated Switches, Shotgun Surgery, Divergent Change, Speculative
  Generality, Message Chains, Middle Man, Refused Bequest.
- Skip anything tooling already enforces.
- Each smell names the smell and quotes the hunk.

## Use

The review artifact stays deterministic and gates the task. A model second
opinion runs only when the operator asks for one in the current turn.

When it does:

- Run Spec and Standards as separate readers with separate contexts.
- Aggregate side by side under `## Spec` and `## Standards`.
- Do not rerank or pick one winner across axes.
- Label each finding CONFIRMED, REFUTED, or UNVERIFIED with its evidence.
- A second opinion cannot add checks or turn UNVERIFIED into PASS.
