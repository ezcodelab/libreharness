<!-- SPDX-License-Identifier: MIT -->

# Security policy

## Supported versions

| Version | Supported |
|---|---|
| 1.0.0-rc.1 and later 1.0.x release candidates | Yes, best effort |
| Earlier development snapshots | No |

This is a local release candidate. There is no public repository, no security
team, and no response-time guarantee yet. Do not treat this file as a promise
of a service-level agreement.

## Reporting a vulnerability

Do not open a public issue with exploit details, a secret, a private path, or
personal data.

When the public repository exists, use its private vulnerability reporting
form. If that form is not available, open a minimal public issue asking the
maintainer for a private channel, and include no technical detail beyond the
affected area.

This candidate has no project security alias yet. Before publication, replace
this paragraph with a project-owned address or the repository's private
reporting form. Do not use a personal address.

Include:

- the affected version or commit;
- the platform and Python or Node version;
- a minimal reproduction with placeholders;
- the impact and the trust boundary crossed;
- whether a secret or personal data may have been exposed.

Do not include a live key. If a key was exposed, rotate it first, then describe
the shape and location, not the value.

## No bug bounty

There is no bug bounty, payment, or guaranteed credit. A maintainer will
acknowledge a valid report when possible and will credit the reporter if the
reporter agrees.

## Jev key guidance

Jev is optional. The queue, commands, skills, plugins, and tests work without a
key.

- Prefer `JEV_API_KEY` in the environment for a short session, or
  `JEV_KEY_FILE` pointing at a mode 600 file.
- The reference client also checks `OPENCODE_API_KEY`, `TYPESAFE_API_KEY`, and
  `~/.config/opencode/jev.key` in that order after `JEV_API_KEY`. Use one
  source, not several.
- Never commit a key, put it in a task, paste it into a prompt, or send it to a
  custom endpoint you do not trust.
- The client sends the key only to the configured endpoint. It does not print
  the key. It does print errors from the service, so read an error before
  sharing it.
- Use HTTPS. The reference client does not reject a plain HTTP endpoint, so
  the choice is yours.
- Rotate a key immediately if it appears in a diff, a log, a session export, or
  a public issue. Removing the line is not enough; assume it is compromised.

## Secret handling in the harness

- `auto-intake` refuses to store a prompt that matches its secret patterns and
  redacts secret-shaped and PII-shaped text in titles.
- The Jev review client refuses a diff or task that matches a secret-shaped
  pattern unless `--allow-secret-shaped` is passed. That flag is for a
  deliberate, reviewed exception, not a convenience. The plan client rejects a
  secret-shaped plan state. Triage does not apply the guard to its close state
  in rc.1.
- The queue does not encrypt task files. Use filesystem permissions and full
  disk encryption if the state contains sensitive work.
- State should be mode 700 and key files mode 600. The queue uses the process
  umask; set `umask 077` if your default is permissive.

## What is out of scope

- A provider's logging, retention, or training policy. That is between you and
  the provider you choose.
- A malicious repository, prompt injection, or tool output that convinces an
  agent to run a command. Review commands and permissions.
- Third-party plugins, custom Jev adapters, and external MCP servers.
- Windows in 1.0.0.
- A leaked key that was already committed before this policy existed. Rotate
  it and treat the exposure as real.

See [docs/security-privacy.md](docs/security-privacy.md) for the data boundary
and egress details.
