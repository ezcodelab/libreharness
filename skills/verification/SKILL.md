---
name: verification
description: Create, maintain, or formally check a project-local proof. Use for "verify this", "drive the app", "audit the verify skill", or "model-check this invariant" when a direct test, type check, or lint is not enough.
---
<!-- SPDX-License-Identifier: MIT -->

# Verification

Pick one mode from the request and the repo. Do not use this skill when a
direct test, type check, lint, or command already proves the claim.

- **Create** when the project has no scripted way to launch, drive, and observe
  the real surface.
- **Maintain** when a `verify-<app>` skill or feature map already exists and may
  have drifted.
- **Formal** when the risk is concurrency, retries, locks, a state machine, a
  parser, unsafe code, or another case tests rarely reach.

## Create

1. **Interview the repo, not the user.** Answer from code: surface, exact local
   launch and readiness, how an agent can drive it, what evidence proves the
   result, and whether two instances can run side by side. If the checkout does
   not build or start, fix that or report the blocker before generating.
2. **Generate `.opencode/skills/verify-<app>/SKILL.md`** with sections grounded
   in the repo, no placeholders: Launch, Doctor, Drive, Evidence, Cleanup,
   Helpers. Prefer existing Playwright, Cypress, PTY, or HTTP harnesses. Stable
   handles beat coordinates. Cleanup kills only what the run started and never
   removes the evidence.
3. **Seed a feature map** at `features/README.md` and one file per top
   user-facing feature. Each file states sub-features, how a user reaches it,
   how to drive it, and the observable end state. Never weaken a journey to make
   it pass.
4. **Prove the generated skill once**: launch, doctor, drive one mapped feature,
   capture evidence, clean up, then confirm the evidence survives. A skill that
   was never executed is a draft.
5. **Hand off** the paths, the proof command and result, and what remains
   unverified. Point at Maintain for upkeep.

## Maintain

1. **Locate** the project-local verify skill and its feature map. Several
   candidates: ask which one. None: use Create.
2. **Index hygiene.** Fix missing, extra, duplicate, or dead map entries.
3. **Source wave.** One read-only reader per feature file, concurrently. Each
   explains the feature from source, cites likely drift, and returns one live
   recipe. Readers do not drive or edit.
4. **Live pass.** One coordinator drives every feature. Doctor before the first
   drive and after any surprise; reset or relaunch when doctor cannot see a
   wedged state. Evidence survives every cleanup. Every failed iteration is
   cleaned up. A harness fix is re-driven live before it ships.
5. **Triage.** Wrong or missing user-POV text is doc drift: fix the map. Working
   behavior the harness cannot drive is a harness gap: fix the harness. Broken
   app behavior is a product bug: report it, do not edit product code.
6. **Outcome.** Name `clean` (no change), `changed` (one reviewable PR of proven
   corrections), or `blocked` (say exactly what blocked coverage).

## Formal

1. **Choose the target from the code.** Pick the promise where a break harms
   users and tests rarely reach the case. Do not pick the easiest property.
2. **Let the question choose the tool.** A bad event order usually needs a model
   checker over a small model; TLA+ is the default for that. A code-level
   property usually needs a verifier or property-based test with generated
   inputs. A property at every size can need a proof. Say why the tool fits.
3. **Make it true to the code.** Every model step points to code a reviewer can
   open. An indivisible code step stays indivisible in the model. Use this
   repo's names.
4. **Make it able to fail.** Show each property failing on a broken variant,
   such as a removed check or a reordered step. A check never seen failing
   proves nothing.
5. **Record the contract.** State the property and harm in one plain sentence
   each, the bounds and assumptions, the exact command and pinned tool version,
   the covered files and functions, and the commit last confirmed in sync.
6. **Read counterexamples as states.** For a TLA+ model, render the shortest
   path to the broken rule as a Mermaid statechart and replay it against the
   real code. If a step cannot happen in the code, fix the model; if every step
   can, it is a bug. Report the counterexample in the code's words.
7. **Hand off** what is verified, what is not, and the sync commit. Point at
   Maintain after changes that did not recheck it.

## Evidence standard

A proof is a real user path or formal property plus the resulting observable
state, with the command and output kept for a reviewer. A passing unit test, a
screenshot of the final screen alone, or "it compiles" is not enough for
user-visible behavior. Name the principle that shaped the proof: usually
"Prove it works" or "Sequence verifiable units".

## Stop conditions

Stop and report instead of inventing a green check when:

- the app does not build or start from a clean checkout;
- there is no stable way to drive or observe the surface;
- the only instance is shared and cannot be isolated;
- the check would mutate production, shared data, or an external account;
- the evidence cannot survive cleanup;
- a formal model cannot be traced to code, or the property is too vague to fail;
- the chosen formal tool cannot be installed or run reproducibly.
