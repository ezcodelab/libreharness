<!-- SPDX-License-Identifier: MIT -->
1. Mine commits, reverts, review send-backs, and lessons for mistake classes.
2. A class counts after two occurrences.
3. Fix at the highest level that works: architecture, then types, then a lint
   whose error names the fix, then a behavior test, and docs last.
4. Prove the new check fails on a real past mistake.
5. Append the rule to `references/rule-ledger.md`. Never grow `AGENTS.md`.
