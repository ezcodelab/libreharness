<!-- SPDX-License-Identifier: MIT -->
# Feature map

One file per user-facing feature of the harness, from the operator's point of
view. The smoke skill drives the first one; the rest are the map for later runs.

| Feature | What it proves |
|---|---|
| [plugin-and-queue-smoke](plugin-and-queue-smoke.md) | A prompt becomes a task that closes with evidence, and the board exists |
| [playbook-routing](playbook-routing.md) | Intake routes a prompt to one playbook and loads `goal` only when needed |

A feature file is current only when a run drove it. Mark an unproven claim `[T]`,
not `[V]`.
