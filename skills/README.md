<!-- SPDX-License-Identifier: MIT -->
# Skills

This is the only skill map. Load a skill on demand; `engineering-loop` is the
entry point and picks the playbook.

| Skill | Use |
|---|---|
| `engineering-loop` | Entry point and playbook router for non-trivial work |
| `goal` | Multi-deliverable goal planning and execution |
| `parallel-lanes` | Independent lanes with disjoint ownership |
| `shipping` | Ready PR, review artifact, exact-head CI, merge |
| `state-audit` | States, invariants, transitions, regression tests |
| `ui-design` | UI and UX work |
| `unslop-ui` | End-to-end UI baseline, A/B choice, implementation, ship |
| `unslop` | Prose only: replies, PR bodies, docs, commit messages |
| `no-comments` | Remove comment and doc alibis before review |
| `correct` | Repeated mistake classes become checks |
| `verification` | Prove real app behavior |
| `work-queue` | Durable tasks with scope, acceptance, and evidence |

`engineering-loop` maps a request to `investigation`, `bug-fix`, `feature`,
`refactoring`, `perf`, `hillclimb`, `autonomous-multiphase`, or `correct`. The
checklists live in `engineering-loop/references/playbooks.md`. Per-rule
encodings live in `correct/references/rule-ledger.md`.
