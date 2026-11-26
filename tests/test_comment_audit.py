# SPDX-License-Identifier: MIT
from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "bin/comment_audit.py"
ANCHOR_F = hashlib.sha256(b"def f():").hexdigest()[:12]

DIRTY = textwrap.dedent(
    """\
    # SPDX-License-Identifier: MIT
    # Phase 1: load the data
    # TODO: replace the stub
    # FIXME: handle empty input
    # XXX: fragile while the cache warms
    # print("debug")
    # do not remove: it makes the tests pass


    def load():
        return {}
    """
)

CLEAN = textwrap.dedent(
    '''\
    # SPDX-License-Identifier: MIT
    """Parse counts.

    Phase 1 and TODO in this docstring are documentation, not comments.
    """


    def parse(raw):
        # The upstream service omits the field instead of sending zero, so an
        # absent value must be treated as zero rather than rejected.
        # https://example.test/spec
        return int(raw or 0)
    '''
)


class CommentAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write(self, name: str, text: str) -> Path:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def run_audit(self, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(AUDIT), *args],
            input=stdin,
            text=True,
            capture_output=True,
            cwd=self.root,
            check=False,
        )

    def git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-c", "user.name=Test", "-c", "user.email=test@example.test", *args],
            text=True,
            capture_output=True,
            cwd=self.root,
            check=True,
        )

    def test_dirty_fixture_reports_expected_findings(self) -> None:
        self.write("dirty.py", DIRTY)

        result = self.run_audit("dirty.py")

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(
            result.stdout.splitlines(),
            [
                "dirty.py:2: phase-narration: Phase 1: load the data",
                "dirty.py:3: todo: TODO: replace the stub",
                "dirty.py:4: todo: FIXME: handle empty input",
                "dirty.py:5: todo: XXX: fragile while the cache warms",
                'dirty.py:6: commented-out-code: print("debug")',
                "dirty.py:7: workaround-justification: do not remove: it makes the tests pass",
            ],
        )

    def test_clean_fixture_passes(self) -> None:
        self.write("clean.py", CLEAN)

        result = self.run_audit("clean.py")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")

    def test_inline_allow_suppresses_only_that_comment(self) -> None:
        self.write(
            "allowed.py",
            textwrap.dedent(
                """\
                # SPDX-License-Identifier: MIT
                # TODO: remove after migration; comment-discipline: allow issue 42 tracks it
                # Phase 2: cleanup
                def finish():
                    return None
                """
            ),
        )

        result = self.run_audit("allowed.py")

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(
            result.stdout.splitlines(),
            ["allowed.py:3: phase-narration: Phase 2: cleanup"],
        )

    def test_allow_flag_skips_one_rule(self) -> None:
        self.write("dirty.py", DIRTY)

        result = self.run_audit("--allow", "todo", "dirty.py")

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertNotIn(": todo:", result.stdout)
        self.assertIn("phase-narration", result.stdout)
        self.assertIn("commented-out-code", result.stdout)
        self.assertIn("workaround-justification", result.stdout)

    def test_external_reason_allows_constraint_comments(self) -> None:
        self.write(
            "vendor.py",
            textwrap.dedent(
                """\
                # SPDX-License-Identifier: MIT
                # Workaround for the proxy stripping the header:
                # https://example.test/issues/7
                # Do not remove: issue #12 requires the header.
                def call():
                    return None
                """
            ),
        )

        result = self.run_audit("vendor.py")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout, "")

    def test_bare_issue_and_rfc_reference_allows_constraint(self) -> None:
        self.write(
            "vendor.py",
            "# Workaround required by #42 and RFC 9110.\ndef call():\n    return None\n",
        )

        result = self.run_audit("vendor.py")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_suppression_debt_in_python(self) -> None:
        self.write(
            "suppressed.py",
            textwrap.dedent(
                """\
                # type: ignore[attr-defined]
                # noqa: E501
                # pylint: disable=unused-import
                # nosec
                def f():
                    return 1
                """
            ),
        )

        result = self.run_audit("suppressed.py")

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(
            result.stdout.splitlines(),
            [
                "suppressed.py:1: suppression-debt: type: ignore[attr-defined]",
                "suppressed.py:2: suppression-debt: noqa: E501",
                "suppressed.py:3: suppression-debt: pylint: disable=unused-import",
                "suppressed.py:4: suppression-debt: nosec",
            ],
        )

    def test_suppression_debt_in_javascript_and_shell(self) -> None:
        self.write(
            "suppressed.js",
            "// eslint-disable-next-line no-console\nconst x = 1;\n// @ts-ignore\nconst y = 2;\n//nolint:gosec\nconst z = 3;\n// istanbul ignore next\nconst w = 4;\n",
        )
        self.write("suppressed.sh", "# shellcheck disable=SC2086\necho $x\n")

        js = self.run_audit("suppressed.js")
        shell = self.run_audit("suppressed.sh")

        self.assertEqual(js.returncode, 1, js.stderr)
        self.assertEqual(
            js.stdout.splitlines(),
            [
                "suppressed.js:1: suppression-debt: eslint-disable-next-line no-console",
                "suppressed.js:3: suppression-debt: @ts-ignore",
                "suppressed.js:5: suppression-debt: nolint:gosec",
                "suppressed.js:7: suppression-debt: istanbul ignore next",
            ],
        )
        self.assertEqual(shell.returncode, 1, shell.stderr)
        self.assertEqual(
            shell.stdout.splitlines(),
            ["suppressed.sh:1: suppression-debt: shellcheck disable=SC2086"],
        )

    def test_suppression_allow_marker_and_external_reason(self) -> None:
        self.write(
            "allowed.py",
            textwrap.dedent(
                """\
                # type: ignore  # comment-discipline: allow vendor stub has no types
                # noqa: E501
                # comment-discipline: allow line length is pinned by the formatter
                # pylint: disable=unused-import
                # https://example.test/issues/7
                def f():
                    return 1
                """
            ),
        )

        result = self.run_audit("allowed.py")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_style_directives_are_not_suppression_debt(self) -> None:
        self.write("style.py", "# fmt: off\n# isort: skip\ndef f():\n    return 1\n")
        self.write("style.js", "// prettier-ignore\nconst x = 1;\n")

        python = self.run_audit("style.py")
        javascript = self.run_audit("style.js")

        self.assertEqual(python.returncode, 0, python.stdout + python.stderr)
        self.assertEqual(javascript.returncode, 0, javascript.stdout + javascript.stderr)

    def test_strict_flags_a_prose_comment(self) -> None:
        self.write("prose.py", "# The retry loop needs a fresh token.\ndef f():\n    return 1\n")

        result = self.run_audit("--strict", "prose.py")

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(
            result.stdout.splitlines(),
            ["prose.py:1: comment-disallowed: The retry loop needs a fresh token."],
        )

    def test_strict_flags_a_normal_block_comment(self) -> None:
        self.write("prose.js", "/* The retry loop needs a fresh token. */\nconst x = 1;\n")

        result = self.run_audit("--strict", "prose.js")

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(
            result.stdout.splitlines(),
            [
                "prose.js:1: comment-disallowed: The retry loop needs a fresh token.",
            ],
        )

    def test_strict_is_off_by_default(self) -> None:
        self.write("prose.py", "# The retry loop needs a fresh token.\ndef f():\n    return 1\n")

        result = self.run_audit("prose.py")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_strict_reports_the_real_rule_first(self) -> None:
        self.write("prose.py", "# TODO: fix\ndef f():\n    return 1\n")

        result = self.run_audit("--strict", "prose.py")

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ["prose.py:1: todo: TODO: fix"])

    def test_strict_keeps_legal_api_external_and_allow_comments(self) -> None:
        self.write(
            "kept.js",
            textwrap.dedent(
                """\
                /* SPDX-License-Identifier: MIT */
                /** Public API. */
                function f() {}
                // https://example.test/spec
                const x = 1;
                // comment-discipline: allow generated binding
                const y = 2;
                // v4.4.0
                const z = 3;
                /**
                 * Public API block.
                 */
                function g() {}
                /// Rust-style public API.
                function h() {}
                """
            ),
        )

        result = self.run_audit("--strict", "kept.js")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_strict_diff_flags_only_new_comments(self) -> None:
        self.write("example.py", "# old explanation\ndef f():\n    return 1\n")
        self.git("init")
        self.git("add", "example.py")
        self.git("commit", "-m", "base")
        self.write(
            "example.py",
            "# old explanation\ndef f():\n    # new explanation\n    return 1\n",
        )
        patch = self.root / "change.diff"
        patch.write_text(self.git("diff").stdout, encoding="utf-8")

        result = self.run_audit("--strict", "--diff", str(patch))

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(
            result.stdout.splitlines(),
            ["example.py:3: comment-disallowed: new explanation"],
        )

    def test_javascript_block_comment_and_commented_out_code(self) -> None:
        self.write("bad.js", "/* TODO: remove */\n// const x = 2;\nconst url = 'https://example.test';\n")

        result = self.run_audit("bad.js")

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(
            result.stdout.splitlines(),
            [
                "bad.js:1: todo: TODO: remove",
                "bad.js:2: commented-out-code: const x = 2;",
            ],
        )

    def test_prose_is_not_commented_out_code(self) -> None:
        self.write(
            "notes.py",
            textwrap.dedent(
                """\
                # from EMA21, and still within the near-level band.
                # Application (Frontend + Backend)
                # tier="security" -> 90 days
                def f():
                    return 1
                """
            ),
        )

        result = self.run_audit("notes.py")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout, "")

    def test_numbered_yaml_list_is_not_phase_narration(self) -> None:
        self.write("config.yaml", "# 1. Traefik access logs\n# 2. sshd log\n")

        result = self.run_audit("config.yaml")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout, "")

    def test_explicit_step_is_phase_narration(self) -> None:
        self.write("steps.py", "# Step 1: load the data\ndef f():\n    return 1\n")

        result = self.run_audit("steps.py")

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(
            result.stdout.splitlines(),
            ["steps.py:1: phase-narration: Step 1: load the data"],
        )

    def test_numbered_list_is_not_phase_narration(self) -> None:
        self.write("steps.py", "# 1. Load the data\ndef f():\n    return 1\n")

        result = self.run_audit("steps.py")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout, "")

    def test_directory_scan_skips_dependencies(self) -> None:
        self.write("src/a.py", "# TODO: a\n")
        self.write("node_modules/b.js", "// TODO: b\n")

        result = self.run_audit(".")

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ["src/a.py:1: todo: TODO: a"])

    def test_baseline_ratchets_existing_debt(self) -> None:
        self.write("debt.py", "# TODO: one\n# TODO: two\ndef f():\n    return 1\n")
        baseline = self.root / "baseline.txt"

        written = self.run_audit("--write-baseline", str(baseline), "debt.py")
        self.assertEqual(written.returncode, 0, written.stderr)
        self.assertEqual(
            baseline.read_text(encoding="utf-8").splitlines(),
            [
                f"1\tdebt.py\ttodo\tTODO: one\t{ANCHOR_F}",
                f"1\tdebt.py\ttodo\tTODO: two\t{ANCHOR_F}",
            ],
        )

        clean = self.run_audit("--baseline", str(baseline), "debt.py")
        self.assertEqual(clean.returncode, 0, clean.stdout + clean.stderr)

        self.write("debt.py", "\n# TODO: one\n# TODO: two\ndef f():\n    return 1\n")
        shifted = self.run_audit("--baseline", str(baseline), "debt.py")
        self.assertEqual(shifted.returncode, 0, shifted.stdout + shifted.stderr)

        self.write("debt.py", "\n# TODO: one\n# TODO: two\ndef f():\n    # TODO: three\n    return 1\n")
        new = self.run_audit("--baseline", str(baseline), "debt.py")
        self.assertEqual(new.returncode, 1, new.stderr)
        self.assertEqual(new.stdout.splitlines(), ["debt.py:5: todo: TODO: three"])

    def test_baseline_counts_duplicates(self) -> None:
        baseline = self.root / "baseline.txt"
        baseline.write_text("1\tdebt.py\ttodo\tTODO: one\t\n", encoding="utf-8")
        self.write("debt.py", "# TODO: one\n# TODO: one\n")

        result = self.run_audit("--baseline", str(baseline), "debt.py")

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ["debt.py:2: todo: TODO: one"])

    def test_old_baseline_format_is_rejected(self) -> None:
        baseline = self.root / "baseline.txt"
        baseline.write_text("1\tdebt.py\ttodo\tTODO: one\n", encoding="utf-8")
        self.write("debt.py", "# TODO: one\ndef f():\n    return 1\n")

        result = self.run_audit("--baseline", str(baseline), "debt.py")

        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("old four-column baseline", result.stderr)

    def test_baseline_rejects_a_context_swap(self) -> None:
        self.write("debt.py", "# TODO: one\ndef f():\n    return 1\n\ndef g():\n    return 2\n")
        baseline = self.root / "baseline.txt"
        written = self.run_audit("--write-baseline", str(baseline), "debt.py")
        self.assertEqual(written.returncode, 0, written.stderr)

        self.write("debt.py", "def f():\n    return 1\n\n# TODO: one\ndef g():\n    return 2\n")
        moved = self.run_audit("--baseline", str(baseline), "debt.py")

        self.assertEqual(moved.returncode, 1, moved.stderr)
        self.assertEqual(moved.stdout.splitlines(), ["debt.py:4: todo: TODO: one"])

    def test_baseline_rejects_an_anchor_code_change(self) -> None:
        self.write("debt.py", "# TODO: one\ndef f():\n    return 1\n")
        baseline = self.root / "baseline.txt"
        written = self.run_audit("--write-baseline", str(baseline), "debt.py")
        self.assertEqual(written.returncode, 0, written.stderr)

        self.write("debt.py", "# TODO: one\ndef h():\n    return 1\n")
        changed = self.run_audit("--baseline", str(baseline), "debt.py")

        self.assertEqual(changed.returncode, 1, changed.stderr)
        self.assertEqual(changed.stdout.splitlines(), ["debt.py:1: todo: TODO: one"])

    def test_diff_reports_only_added_lines(self) -> None:
        self.write("example.py", "# TODO: old debt\ndef f():\n    return 1\n")
        self.git("init")
        self.git("add", "example.py")
        self.git("commit", "-m", "base")
        self.write("example.py", "# TODO: old debt\ndef f():\n    # TODO: new debt\n    return 1\n")
        patch = self.root / "change.diff"
        patch.write_text(self.git("diff").stdout, encoding="utf-8")

        result = self.run_audit("--diff", str(patch))

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ["example.py:3: todo: TODO: new debt"])

    def test_diff_flags_a_new_suppression(self) -> None:
        self.write("example.py", "def f():\n    return 1\n")
        self.git("init")
        self.git("add", "example.py")
        self.git("commit", "-m", "base")
        self.write("example.py", "def f():\n    # noqa: E501\n    return 1\n")
        patch = self.root / "change.diff"
        patch.write_text(self.git("diff").stdout, encoding="utf-8")

        result = self.run_audit("--diff", str(patch))

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(
            result.stdout.splitlines(),
            ["example.py:2: suppression-debt: noqa: E501"],
        )

    def test_diff_scans_a_new_file(self) -> None:
        self.git("init")
        self.write("new.py", "# TODO: new\n")
        self.git("add", "new.py")
        patch = self.root / "change.diff"
        patch.write_text(self.git("diff", "--cached").stdout, encoding="utf-8")

        result = self.run_audit("--diff", str(patch))

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ["new.py:1: todo: TODO: new"])

    def test_diff_missing_file_exits_two(self) -> None:
        patch = self.root / "change.diff"
        patch.write_text(
            "--- /dev/null\n+++ b/missing.py\n@@ -0,0 +1 @@\n+# TODO: nope\n",
            encoding="utf-8",
        )

        result = self.run_audit("--diff", str(patch))

        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("not a file", result.stderr)

    def test_diff_with_no_added_findings_passes(self) -> None:
        self.write("example.py", "def f():\n    return 1\n")
        self.git("init")
        self.git("add", "example.py")
        self.git("commit", "-m", "base")
        self.write("example.py", "def f():\n    return 2\n")
        patch = self.root / "change.diff"
        patch.write_text(self.git("diff").stdout, encoding="utf-8")

        result = self.run_audit("--diff", str(patch))

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout, "")

    def test_stdin_is_scanned(self) -> None:
        result = self.run_audit(stdin="# TODO: later\n")

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout, "<stdin>:1: todo: TODO: later\n")

    def test_missing_file_exits_two(self) -> None:
        result = self.run_audit("missing.py")

        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("not a file", result.stderr)


if __name__ == "__main__":
    unittest.main()
