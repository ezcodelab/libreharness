<!-- SPDX-License-Identifier: MIT -->

# Contributing

The public repository is `https://github.com/ezcodelab/libreharness`.
Contributions are welcome.

## Development setup

Requirements: Linux, Git, Python 3.10 or newer, and Node 20 or newer. No Python
package is required. `npm install` is required for the Node tests because
`src/plugin.js` imports `@opencode/plugin`; the Python suite runs without
`node_modules`.

```sh
git clone https://github.com/ezcodelab/libreharness
cd libreharness
python3 --version
node --version
```

Use a temporary state root for experiments:

```sh
export HARNESS_HOME="$PWD"
export HARNESS_STATE="$(mktemp -d)"
```

Do not run queue commands against a state root that contains work you care
about while developing.

## Checks

Run these before sending a change:

```sh
python3 -m compileall -q bin tests
python3 -m unittest discover -s tests -p 'test_*.py' -v
npm run test:node
node --check src/plugin.js
node --check plugins/auto-intake.js
node --check plugins/goal-watch.js
node --check plugins/usage-ledger.js
python3 -m json.tool package.json >/dev/null
npm pack --dry-run
npx --yes markdownlint-cli2@0.18.1 '**/*.md'
```

CI also runs `lychee` for offline links, `gitleaks` for secrets, `shellcheck`
for shell files, and `actionlint` for workflows. The Markdown rule set is in
`.markdownlint-cli2.jsonc`; it is correctness-only, so style preferences do not
fail a pull request.

The Python suite uses temporary state roots. The Node tests use temporary
directories and mocks. No test makes a live model call or needs a key.

If you add a Python test, use `unittest`. If you add a Node test, use the
existing `assert` style. Keep state in a temporary directory and clean it up.

## Commits

Use a Conventional Commits prefix: `feat:`, `fix:`, `docs:`, `test:`,
`chore:`, or `refactor:`. Keep one reviewable change per commit. Sign off with
`git commit -s`.

## Style

- Prefer the standard library and Node built-ins. Do not add a dependency for a
  few lines.
- Keep the Markdown queue format backward compatible within a minor release.
- Do not hardcode a model ID in core code or the example config. The user
  chooses the provider and model.
- Keep shell commands quoted. Do not interpolate untrusted input into a shell
  string.
- Add an SPDX header to every new file: `# SPDX-License-Identifier: MIT` for
  Python and shell, `// SPDX-License-Identifier: MIT` for JavaScript and MJS,
  and `<!-- SPDX-License-Identifier: MIT -->` for Markdown.
- Documentation uses plain English and ASCII punctuation. Do not include a
  private home path, hostname, token, or personal data.

## No secrets

Never commit a key, token, password, private key, session export, or `.env` file.
Do not paste one into an issue, a task, a handoff, a lesson, a test fixture, or a
log. Use a placeholder and describe the shape instead.

`auto-intake` has a secret-shaped input guard. That guard is a last line of
defense, not permission to include a secret. If you believe a secret was
committed, stop, rotate it, and report it through the process in
[SECURITY.md](SECURITY.md).

## Developer Certificate of Origin

Sign off every commit:

```sh
git commit -s -m "docs: clarify the queue state root"
```

The sign-off certifies that you wrote the change or have the right to submit it
under the project license. A separate contributor license agreement is not
required. The sign-off is recommended, not enforced by CI.

By contributing, you agree that your contribution is licensed under the MIT
License.

## Pull request checklist

- [ ] One task, one reviewable PR. The change does not mix unrelated work.
- [ ] The PR is at most 600 changed lines, 20 files, and 40 body lines.
- [ ] The title is `type(scope): subject`; the body has `Why`, `What changed`,
      `Scope`, optional `Tradeoffs`, `Blast Radius`, and `Verification`.
- [ ] The task has scope, acceptance, and evidence in the queue.
- [ ] Tests were run, and the exact command and result are in the pull request.
- [ ] The owner stays through required checks and merge, or records one blocker.
- [ ] New behavior has a test or a measured check.
- [ ] No secret, private path, hostname, personal data, or generated state.
- [ ] New files have the correct SPDX header.
- [ ] Markdown links resolve and the Markdown check passes.
- [ ] The changelog is updated for a user-visible change.
- [ ] The commit is signed off with `git commit -s`.

## Review

A maintainer reviews for correctness, safety, scope, and evidence. Review is
proportional to risk. A change to auth, secrets, data, a public interface, or
recovery behavior gets an independent review. A typo does not.

Review comments use these labels:

- **CONFIRMED:** a defect with a source, sink or failure point, and guard.
- **REFUTED:** checked and not a defect.
- **UNVERIFIED:** a warning that needs more evidence, not a blocking finding.

A confirmed high-severity finding blocks. A lower-severity finding is a fix or
an explicit accepted risk. The review artifact records observed checks; it does
not replace the reviewer's decision.

## Adding a skill

1. Create `skills/<name>/SKILL.md` with `name` and `description` frontmatter.
2. Keep it inside the line budget enforced by
   `tests/harness-ratchets.test.mjs`. Split a skill when its triggers or
   procedure are distinct.
3. Write the trigger in the description, not only in the body.
4. Prove it pays off on one real task with and without the skill. A neutral
   result is a reason to delete it or keep it project-local.

## Adding a plugin

1. Put a bundled plugin in `plugins/<name>.js` and add a test under `tests/`.
2. Use Node built-ins only. Resolve code from `HARNESS_HOME` and state from
   `HARNESS_STATE`.
3. Never block a session when the plugin is misconfigured. Log one short
   warning and continue.
4. Add a disable switch and document it in
   [docs/reference.md](docs/reference.md#plugins).
5. Run `node --check` on the file.

## Release changes

A release needs a changelog entry, passing checks, and no unbacked performance
claim. A benchmark claim needs raw data, an analysis script, and limitations.
