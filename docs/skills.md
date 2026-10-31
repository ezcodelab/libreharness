<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Skills

Skills are reusable procedures that OpenCode advertises to the model and loads
on demand. The harness ships five. They are process, not product code.

## The five skills

| Skill | Trigger | Lines in rc.1 |
|---|---|---|
| [engineering-loop](../skills/engineering-loop/SKILL.md) | Nontrivial work: external API, secrets or auth, schema or data, security tradeoff, multi-file design, or "done" means production behavior | 119 |
| [goal](../skills/goal/SKILL.md) | A multi-step outcome, optionally unattended; create an umbrella and child tasks, run the queue, stop on a one-way door or blocker | 80 |
| [parallel-lanes](../skills/parallel-lanes/SKILL.md) | Split work across two or three agents or sessions; define slices, ownership, worktrees, merge order, and integration | 73 |
| [ui-design](../skills/ui-design/SKILL.md) | UI or UX work: layout, component, styling, visual review, or interface copy | 88 |
| [work-queue](../skills/work-queue/SKILL.md) | Work that is nontrivial, spans sessions, or runs in parallel; create and maintain durable tasks | 81 |

Line counts are for the current candidate and will drift. The budget is
enforced by the lint, not by this table.

## What a skill contains

A skill is a directory under `skills/` with one `SKILL.md`:

```text
skills/
└── <name>/
    └── SKILL.md
```

The file starts with frontmatter:

```yaml
---
name: <name>
description: <when to use it, in one or two sentences>
---
```

The `description` is the trigger. OpenCode shows it to the model before the
body is loaded. A vague description causes over-triggering or no trigger at
all. Put the concrete situation in the description, not only in the body.

The body is the procedure. It should be short enough to load on demand and
specific enough to change the next action. Do not paste a whole policy manual
into a skill.

## Budget

`bin/docs_lint.py` enforces two limits when run with `--skills-dir`:

| Limit | Default | Current |
|---|---|---|
| Number of skills | 8 | 5 |
| Lines per skill | 120 | 119 maximum |

```sh
python3 bin/docs_lint.py . --skills-dir skills
```

The budget is a context and maintenance limit, not a style preference. A skill
is loaded on demand, but its description is always advertised, and a large
skill costs tokens when loaded. If a new skill would exceed the budget, merge
or delete one first. Do not raise the limit to avoid a decision.

## Global versus project

| Scope | Location | Use |
|---|---|---|
| Global | `$HARNESS_HOME/skills/<name>/SKILL.md` | A portable procedure used across projects |
| Project | `<project>/.opencode/skills/<name>/SKILL.md` | A procedure specific to one repository |

OpenCode walks up from the working directory to the git worktree for project
skills. It also reads the global config directory. A project skill with the same
name as a global skill is a conflict to resolve, not a reason to keep both.

Promote a project skill to global only after the evaluation in
[skill-eval.md](skill-eval.md). A skill that sounds useful is not evidence.

## When a skill triggers

The model sees the skill descriptions and calls the `skill` tool when one
matches. Triggering is probabilistic. To improve it:

- name the task shape, not the technology: "review a change that touches auth"
  is better than "security";
- include the words a user is likely to use;
- keep the description free of private project names and model names;
- test positive and negative prompts, as described in
  [skill-eval.md](skill-eval.md).

The harness does not force a skill to load. A command may instruct the model to
use one, but the model still decides.

## How to add a skill

1. Copy an existing skill directory and rename it.
2. Write the frontmatter. Keep `name` equal to the directory name.
3. Write the trigger in `description`. Keep it to one or two sentences.
4. Write the procedure with a clear first action and a stop condition.
5. Keep it under 120 lines. Remove history, private examples, and project
   names.
6. Run the docs lint.
7. Evaluate it with five to ten prompts, with and without the skill.
8. Keep it project-local unless the evaluation supports promotion.

Do not add a skill for a one-off task. Do not add a skill that restates the
project `AGENTS.md`. Do not add a skill that hides a safety rule in a long
story.

## How to delete a skill

Delete when:

- it has not triggered in 60 days and no task needs it;
- its procedure is now in `AGENTS.md` or a command;
- its evaluation is neutral or negative;
- it duplicates another skill.

Deletion is cheaper than maintenance. Remove the directory and update the
docs. A stale skill is a context tax on every session.

## Skills and commands

A command is an explicit user action. A skill is a procedure the model may load
when the description matches. They work together: `/review` says to use the
engineering-loop and work-queue skills, but the skill body supplies the
procedure.

Do not put a command's entire text into a skill. Do not put a skill's
conditional logic into a command. Keep the command short and the skill
reusable.

## Next

- [Skill evaluation](skill-eval.md)
- [Workflow](workflow.md)
- [Command reference](command-reference.md)
