# SPDX-License-Identifier: MIT
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))
import pr_guard  # noqa: E402


BODY = """## Why
The widget fails.
## What changed
Fix the widget.
## Scope
Widget only.
## Blast Radius
Widget callers.
## Verification
python3 -m unittest tests.test_tasks -v
"""

PR_DATA = {
    "state": "OPEN",
    "isDraft": False,
    "baseRefName": "main",
    "headRefOid": "a" * 40,
    "title": "fix(widget): close the retry gap",
    "body": BODY,
    "additions": 10,
    "deletions": 2,
    "files": [{"path": "widget.py"}],
    "mergeable": "MERGEABLE",
    "mergedAt": None,
    "url": "https://example.invalid/pr/1",
}


class PrGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"
        self.repo.mkdir()
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "user.name", "Test")
        self.git("config", "commit.gpgsign", "false")
        (self.repo / "base.txt").write_text("base\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "base")
        self.git("switch", "-c", "feature")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def git(self, *args: str) -> None:
        subprocess.run(
            ["git", "-C", str(self.repo), *args],
            check=True,
            capture_output=True,
        )

    def commit(self, name: str, text: str) -> None:
        (self.repo / name).write_text(text)
        self.git("add", name)
        self.git("commit", "-q", "-m", f"add {name}")

    def check(self, body: str = BODY, title: str = "fix(widget): close the retry gap"):
        path = Path(self.tmp.name) / "body.md"
        path.write_text(body)
        return pr_guard.local_check(
            self.repo,
            base="main",
            title=title,
            body_file=path,
        )

    def test_small_ready_pr_passes(self) -> None:
        self.commit("widget.py", "value = 1\n")
        result = self.check()
        self.assertTrue(result["ok"], result["problems"])
        self.assertEqual(result["files"], 1)
        self.assertEqual(result["next"], "open")

    def test_large_diff_requires_split(self) -> None:
        self.commit("widget.py", "\n".join(f"line_{i} = {i}" for i in range(601)))
        result = self.check()
        self.assertFalse(result["ok"])
        self.assertEqual(result["next"], "split")
        self.assertTrue(any("changed lines" in item for item in result["problems"]))

    def test_too_many_files_requires_split(self) -> None:
        for index in range(21):
            self.commit(f"file_{index}.txt", "one\n")
        result = self.check()
        self.assertFalse(result["ok"])
        self.assertEqual(result["next"], "split")
        self.assertTrue(any("21 files" in item for item in result["problems"]))

    def test_title_and_body_contract(self) -> None:
        self.commit("widget.py", "value = 1\n")
        bad_title = self.check(title="fix widget")
        self.assertFalse(bad_title["ok"])
        self.assertTrue(any("title" in item for item in bad_title["problems"]))
        missing = self.check("## Why\nOnly a why.\n")
        self.assertFalse(missing["ok"])
        self.assertTrue(any("## Verification" in item for item in missing["problems"]))
        too_long = self.check(BODY + ("line\n" * 40))
        self.assertFalse(too_long["ok"])
        self.assertTrue(any("limit is 40" in item for item in too_long["problems"]))

    def test_dirty_worktree_is_not_openable(self) -> None:
        self.commit("widget.py", "value = 1\n")
        (self.repo / "widget.py").write_text("value = 2\n")
        result = self.check()
        self.assertFalse(result["ok"])
        self.assertTrue(any("not clean" in item for item in result["problems"]))

    def test_pr_metadata_blocks_draft_and_moved_head(self) -> None:
        draft = {**PR_DATA, "isDraft": True, "headRefOid": "b" * 40}
        problems, next_action = pr_guard.pr_checks(
            draft, expected_head="a" * 40, base="main"
        )
        self.assertEqual(next_action, "fix")
        self.assertTrue(any("draft" in item for item in problems))
        self.assertTrue(any("head moved" in item for item in problems))

    def test_land_waits_for_checks_and_merges_exact_head(self) -> None:
        views = iter([PR_DATA, PR_DATA, {**PR_DATA, "state": "MERGED", "mergedAt": "now"}])
        calls = []

        def view(_pr, _repo):
            return next(views)

        def checks(pr, repo):
            calls.append(("checks", pr, repo))

        def merge(pr, head, repo):
            calls.append(("merge", pr, head, repo))

        result = pr_guard.land(
            "1",
            "a" * 40,
            repo=self.repo,
            base="main",
            view=view,
            checks=checks,
            merge=merge,
        )
        self.assertTrue(result["ok"], result["problems"])
        self.assertEqual(result["state"], "MERGED")
        self.assertEqual(calls[0][0], "checks")
        self.assertEqual(calls[1], ("merge", "1", "a" * 40, self.repo))

    def test_land_reports_actionable_check_failure(self) -> None:
        def checks(_pr, _repo):
            raise pr_guard.GuardError("lint failed")

        result = pr_guard.land(
            "1",
            "a" * 40,
            repo=self.repo,
            base="main",
            view=lambda _pr, _repo: PR_DATA,
            checks=checks,
            merge=lambda *_args: None,
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["next"], "fix")
        self.assertIn("lint failed", result["problems"][0])

    def test_land_never_merges_a_moved_head(self) -> None:
        views = iter([PR_DATA, {**PR_DATA, "headRefOid": "b" * 40}])
        merged = []
        result = pr_guard.land(
            "1",
            "a" * 40,
            repo=self.repo,
            base="main",
            view=lambda _pr, _repo: next(views),
            checks=lambda _pr, _repo: None,
            merge=lambda *args: merged.append(args),
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["next"], "rereview")
        self.assertEqual(merged, [])


if __name__ == "__main__":
    unittest.main()
