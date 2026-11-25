<!-- SPDX-License-Identifier: MIT -->

# Security policy

## Supported versions

| Version | Supported |
|---|---|
| 2.0.x | Yes, best effort |
| 1.x | No |

This is the 2.0.0 release tree. The public repository is
`https://github.com/ezcodelab/libreharness`, and there is no security team or
response-time guarantee. Do not treat this file as a promise of a service-level
agreement.

## Reporting a vulnerability

Do not open a public issue with exploit details, a secret, a private path, or
personal data.

Use the GitHub repository's private vulnerability reporting form at
<https://github.com/ezcodelab/libreharness/security/advisories/new>. If that form
is not available, open a minimal public issue asking the maintainer for a
private channel, and include no technical detail beyond the affected area. Do
not use a personal address.

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

## Secret handling in the harness

- `auto-intake` refuses to store a prompt that matches its secret patterns and
  redacts secret-shaped and PII-shaped text in titles.
- The out-of-band review client refuses a diff or task that matches a
  secret-shaped pattern unless `--allow-secret-shaped` is passed. That flag is
  for a deliberate, reviewed exception, not a convenience.
- The queue does not encrypt task files. Use filesystem permissions and full
  disk encryption if the state contains sensitive work.
- State should be mode 700 and key files mode 600. The queue uses the process
  umask; set `umask 077` if your default is permissive.

## Development tool downloads

Repository checks use `npm run check:local`, which downloads pinned lychee,
gitleaks, actionlint, and shellcheck release archives from their upstream
projects. `bin/devtool.py` verifies each archive against a recorded SHA-256
before extracting one executable into `$XDG_CACHE_HOME/libreharness/tools`.
The plugin runtime never downloads or runs these tools.

## What is out of scope

- A provider's logging, retention, or training policy. That is between you and
  the provider you choose.
- A malicious repository, prompt injection, or tool output that convinces an
  agent to run a command. Review commands and permissions.
- Third-party plugins, custom review adapters, and external MCP servers.
- macOS and Windows are not supported; Linux is the only supported platform.
- A leaked key that was already committed before this policy existed. Rotate
  it and treat the exposure as real.

See [docs/reference.md](docs/reference.md#security-and-privacy) for the data
boundary and egress details.
