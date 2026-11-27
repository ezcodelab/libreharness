<!-- SPDX-License-Identifier: MIT -->
# Rule ledger

One row per encoded rule: the correction, the level that makes it impossible, the
check, and the past mistake the check fails on. `/close` and the periodic tune append here.
`AGENTS.md` keeps only suite-level rows.

| Date | Rule | Level | Check | Past mistake |
|---|---|---|---|---|
| 2026-11-19 | A skill entry file stays at or under 120 lines | retired | (check removed) | `skills/shipping/SKILL.md` shipped at 124 lines; the cap forced reference prose out of its skill |
| 2026-11-19 | No em dash, en dash, or curly quote in instruction files | check | `node tests/harness-ratchets.test.mjs` | 43 violations across skills, commands, and agents |
| 2026-11-19 | `AGENTS.md` carries no task routing | check | `node tests/harness-ratchets.test.mjs` | the local config duplicated workflow prose the plugin also injected |

Rows are append-only. Retire a rule by marking its row `retired` with the commit
that removed the check; do not delete the history.
