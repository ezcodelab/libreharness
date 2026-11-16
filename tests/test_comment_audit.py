# SPDX-License-Identifier: MIT
from __future__ import annotations

import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "bin/comment_audit.py"

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

    def test_stdin_is_scanned(self) -> None:
        result = self.run_audit(stdin="# TODO: later\n")

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout, "<stdin>:1: todo: TODO: later\n")


if __name__ == "__main__":
    unittest.main()
