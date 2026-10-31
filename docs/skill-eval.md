<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Skill evaluation loop

Status: procedure, 2026-10-30. Use before promoting a project skill or
keeping a global skill that has no measured value.

This is a small, manual experiment, not a benchmark. It answers two questions:

1. Does the skill trigger when it should?
2. Does loading it improve the output enough to justify its context and
   maintenance cost?

It uses existing OpenCode subagents. It does not port the Claude
`skill-creator` scripts, which call `claude -p` and write `.claude/commands/`.

## When to run

- Before `/tune` promotes a project skill.
- When a global skill has not been used for 60 days and deletion is proposed.
- When a skill's description changes and trigger behavior may change.

Do not run it on every task. It is a promotion and deletion gate, not a review
step.

The global skill budget is eight skills and 120 lines per skill. An evaluation
that passes but would exceed the budget is not a promotion; delete or merge a
skill first. See [skills.md](skills.md).

## Prepare

1. Pick one skill and one small fixture repository or task set.
2. Write 5 to 10 golden prompts that should trigger the skill. Include at least
   two prompts that should **not** trigger it, so over-triggering is visible.
3. Freeze the fixture, the model, the provider, the OpenCode version, and the
   skill text. Record the skill hash.
4. Use a fresh temporary `HOME` and a fresh checkout for every run. Do not reuse
   a session or a cache between arms.

## Arms

| Arm | What the agent receives |
|---|---|
| `without` | The same fixture and prompt, without the skill installed or discoverable |
| `with` | The same fixture and prompt, with the skill installed, or explicitly loaded by ID |

Run one session at a time. Do not run the arms in parallel.

Minimum: one repetition per prompt per arm (10 to 20 runs for 5 to 10 prompts).
For a promotion that changes global config, use two repetitions and report the
spread. More repetitions are better, but do not pretend 5 prompts are a
statistically powerful study.

Randomize the order with a recorded seed so learning effects are visible.

## Capture

For each run record:

- skill id and hash;
- arm, prompt id, repetition, order, seed;
- whether the skill was advertised and whether it was loaded (trigger, 0 or 1);
- task pass, 0 or 1, against a written acceptance check;
- quality score, 0 to 2, against the same rubric for both arms;
- input, output, and cache tokens;
- cost from the session record;
- wall time;
- the final diff or answer path.

Use the OpenCode session API, or the equivalent CLI export for your pinned
OpenCode version, to capture the session id and model. Store the raw session
JSON outside the public tree if it contains private paths.

## Grade

Use a fresh-context subagent that does not know which arm produced the output.
Give it the prompt, the acceptance check, and the 0 to 2 rubric. Do not let the
implementing agent grade its own work.

Rubric:

- **0:** fails the acceptance check or misses the point.
- **1:** passes, but with a material weakness or an unnecessary detour.
- **2:** passes cleanly, with the skill's intended behavior and no extra work.

The grader should return one line per run and a short reason. If the two arms
are indistinguishable, say so.

## Decide

Promote only when all are true:

- the skill triggers on the intended prompts and not on the negative prompts;
- the `with` arm has a higher pass rate or a higher median quality score;
- no safety, scope, or cost regression appears;
- the result is reported with its sample size and limitations.

If the result is neutral or negative, delete the skill or leave it
unadopted in the project. Do not keep a skill because it sounds useful.

## Report

Add one entry to the task evidence or to the project's process ledger:

```text
skill: <id> <hash>
prompts: <n> (<positive>/<negative>)
runs: <n> per arm
trigger: <with-rate> / <without-rate>
pass: <with-rate> vs <without-rate>
quality: <with-median> vs <without-median>
cost: <with> vs <without>
decision: promote | keep project | delete
limits: <sample size, fixture, model, one-off effects>
```

Do not publish private prompts, diffs, or session paths. A public example must
use a synthetic fixture.

## What this does not prove

- It does not prove the skill generalizes beyond the fixture.
- It does not prove a small sample is statistically significant.
- It does not measure long-term maintenance cost.
- It does not replace review, tests, or the evidence gate.

Use it to make a better deletion or promotion decision, not to manufacture a
performance claim.
