<!-- SPDX-License-Identifier: MIT -->
# Handoff

Write or replace the task's `## Handoff` section with exactly these labels:

- **State:** done, in progress, or blocked by ...
- **Decisions:** the choice and why; link the decision record
- **Files:** paths changed, and the one or two that matter most
- **Checks:** command, result, timestamp; "not run" is valid
- **Open:** unresolved questions, risks, and what would change the plan
- **Next:** one bounded next action, with the command or file
- **Context:** links to the task, index section, decision, and review

Keep it a bounded state transfer. No secrets, tokens, values, logs, or
transcript. Cite paths and shapes. Write the handoff file first, then save it
with `tasks handoff <id> --file <path>`; do not edit the section by hand. Run
`tasks handoff <id> --check` and stop if it is incomplete.
