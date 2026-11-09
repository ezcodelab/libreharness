<!-- SPDX-License-Identifier: MIT -->

# Contributing

This is the 1.1.0 release tree. The public repository is
`https://github.com/ezcodelab/libreharness`; contributions are welcome.

## Development setup

Requirements: Linux, Git, Python 3.10 or newer, and Node 20 or newer
for plugin tests. No Python package is required. `npm install` is only needed
for editor types from the development dependency; the tests run without
`node_modules`.

```sh
git clone <repository-url> libreharness
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

## Tests and checks

Run these before sending a change:

```sh
python3 -m compileall -q bin tests
python3 -m unittest discover -s tests -p 'test_*.py' -v
node tests/auto-intake.test.mjs
node tests/goal-watch.test.mjs
node tests/review-protocol.test.mjs
node tests/security-guard.test.mjs
node tests/installer.test.mjs
python3 bin/docs_lint.py . --skills-dir skills
node --check plugins/auto-intake.js
node --check plugins/close-reminder.js
node --check plugins/goal-watch.js
node --check plugins/security-guard.js
python3 -m json.tool opencode.example.json >/dev/null
npm pack --dry-run
```

The Python suite uses temporary state roots. The Node tests use temporary
directories and mocks. No test should make a live model call or need a Jev key.

If you add a Python test, use `unittest`, not a new test framework. If you add
a Node test, use `node:test` or the existing assert style. Keep state in a
temporary directory and clean it up.

## Commits

Use a Conventional Commits prefix: `feat:`, `fix:`, `docs:`, `test:`,
`chore:`, or `refactor:`. Keep one reviewable change per commit. Sign off
with `git commit -s`.

## Style

- Prefer the standard library and Node built-ins. Do not add a dependency for
  a few lines.
- Keep the Markdown queue format backward compatible within a minor release.
- Put a new behavior behind an explicit flag or environment variable when it
  changes an existing workflow.
- Do not hardcode a model ID in core code or the example config. The user
  chooses the provider and model.
- Keep shell commands quoted. Do not interpolate untrusted input into a shell
  string.
- Add an SPDX header to every new file: `# SPDX-License-Identifier: MIT` for
  Python and shell, `// SPDX-License-Identifier: MIT` for JavaScript and MJS,
  `<!-- SPDX-License-Identifier: MIT -->` for project Markdown, and
  `<!-- SPDX-License-Identifier: CC-BY-4.0 -->` for Markdown under `docs/`.
- Documentation uses plain English and ASCII punctuation. Do not add an em
  dash. Do not include a private home path, hostname, token, or personal data.

## No secrets

Never commit a key, token, password, private key, session export, or `.env`
file. Do not paste one into an issue, a task, a handoff, a lesson, a test
fixture, or a log. Use a placeholder and describe the shape instead.

`auto-intake` and the Jev client have secret-shaped input guards. Those guards
are a last line of defense, not permission to include a secret. If you believe
a secret was committed, stop, rotate it, and report it through the process in
[SECURITY.md](SECURITY.md).

## Developer Certificate of Origin

Sign off every commit:

```sh
git commit -s -m "docs: clarify the queue state root"
```

The sign-off certifies that you wrote the change or have the right to submit
it under the project license. A separate contributor license agreement is not
required. In 1.0.0 the sign-off is recommended, not enforced by CI. A pull
request without it may still be reviewed, but maintainers may ask for it.

By contributing, you agree that your contribution is licensed under the same
terms as the path it touches: MIT for code and configuration, CC BY 4.0 for
narrative documentation under `docs/`.

## Pull request checklist

- [ ] One task, one reviewable diff. The change does not mix unrelated work.
- [ ] The task has scope, acceptance, and evidence in the queue.
- [ ] Tests were run, and the exact command and result are in the pull request.
- [ ] New behavior has a test or a measured check.
- [ ] No secret, private path, hostname, personal data, or generated state.
- [ ] New files have the correct SPDX header.
- [ ] Documentation links resolve and the docs lint passes.
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
an explicit accepted risk. Jev's opinion is advisory; it does not replace the
reviewer's decision.

## Adding a skill

1. Create `skills/<name>/SKILL.md` with `name` and `description` frontmatter.
2. Keep it under 120 lines. The skill budget is eight; the current set is six.
3. Write the trigger in the description, not only in the body.
4. Test it with the method in [docs/skill-eval.md](docs/skill-eval.md).
5. Do not promote a skill on a hunch. A neutral result is a reason to delete or
   leave it project-local.

## Adding a plugin

1. Put a bundled plugin in `plugins/<name>.js` and add a test under `tests/`.
2. Use Node built-ins only. Resolve paths from `HARNESS_HOME` and state from
   `HARNESS_STATE`.
3. Never block a session when the plugin is misconfigured. Log one short
   warning and continue.
4. Add the disable switch and document it in [docs/plugins.md](docs/plugins.md).
5. Run `node --check` on the file.

## Release changes

Release and governance decisions follow [GOVERNANCE.md](GOVERNANCE.md). A
release needs a changelog entry, passing checks, and no unbacked performance
claim. A benchmark claim also needs the protocol, raw data, analysis script,
and limitations.
