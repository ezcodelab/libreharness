<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Process lessons

One dated entry per completed task. Keep it short: what surprised us, what it
cost, the rule that changes the next decision, and the doc that now carries it.

Use this format:

```text
## YYYY-MM-DD - short title

Surprise: ...
Cost: ...
Rule: ...
Doc updated: ...
Promote-to-global: yes | no
```

The project ledger starts empty in the public tree. Project-specific and
benchmark-experiment lessons stay in the local brain archive, not here.

## 2026-11-04 - LibreHarness 1.0.0 npm release

Surprise: npm's CLI web-auth URL expires in about 60 seconds, and a phone
passkey returned "Something went wrong" in that flow after staged approval
worked.
Cost: two failed direct-publish attempts and one manual stage/approve.
Rule: bootstrap a new package with `npm stage publish` and approve on
npmjs.com when the account uses a phone passkey; reserve direct `npm publish`
for a desktop authenticator.
Doc updated: `docs/release.md` (staged-first bootstrap), `docs/README.md`
(published status).
Promote-to-global: no
