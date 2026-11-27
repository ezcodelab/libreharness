<!-- SPDX-License-Identifier: MIT -->

# Manual certification procedure

Use this procedure only when the host cannot be driven headlessly. The operator
performs every step on the target operating system and records the actual
commands and results. A bare MCP client call is not host certification.

## Prepare

1. Create a disposable Git repository and a disposable `HARNESS_STATE`
   directory.
2. Install LibreHarness through the host's native plugin mechanism.
3. Confirm the host lists every canonical skill exactly once.
4. Confirm the host exposes `tasks`, `comment_audit`, and `pr_guard`.
5. Ask the host, in its own session, to call the `tasks` tool with
   `args: ["list"]`. Record the observed tool result.
6. For OpenCode, run the full intake, claim, review, and close journey on Linux,
   macOS, and Windows. Mark shipping inapplicable only when the disposable task
   scope explicitly requires no pull request.

## Record evidence

Write a temporary evidence file outside the repository:

```json
{
  "host": "codex",
  "hostVersion": "recorded version",
  "client": "optional client surface",
  "os": "linux",
  "manualProcedure": "docs/certification/manual-procedure.md",
  "install": "PASS",
  "discovery": { "skills": "PASS", "tools": "PASS" },
  "toolRoundTrip": "PASS",
  "journey": "NOT_RUN",
  "limitations": [
    "Certified for native installation, discovery, and MCP tool calls.",
    "The full engineering workflow has not been certified on this host."
  ],
  "commandLog": [
    { "command": "native install command", "result": "observed result" },
    { "command": "host tool call", "result": "observed result" }
  ]
}
```

Use only `linux`, `darwin`, or `win32` for `os`. Use `PASS` or `FAIL` for install,
discovery, and the tool round trip. Use `PASS`, `FAIL`, or `NOT_RUN` for the
journey.

## Write the certificate

Run on the same host and operating system:

```sh
node tests/certify-host.mjs --evidence <os-temp>/<host>-evidence.json
```

The command rejects missing evidence, mismatched hosts or operating systems,
failed checks, and empty command logs. It writes
`docs/certification/<host>-<os>.json`. Commit that file through the normal review
and shipping path.
