# SPDX-License-Identifier: MIT
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pr_guard


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

    def test_github_failures_are_explicit(self) -> None:
        with mock.patch.object(pr_guard.shutil, "which", return_value=None):
            with self.assertRaises(pr_guard.GuardError) as caught:
                pr_guard.require_github(self.repo)
        self.assertIn("GitHub CLI (gh) is required", str(caught.exception))
        self.assertIn("shipping inapplicable", str(caught.exception))

        failed = subprocess.CompletedProcess(
            ["gh", "auth", "status"], 1, "", "not logged in"
        )
        with mock.patch.object(pr_guard.shutil, "which", return_value="/usr/bin/gh"):
            with mock.patch.object(pr_guard.subprocess, "run", return_value=failed):
                with self.assertRaises(pr_guard.GuardError) as caught:
                    pr_guard.require_github(self.repo)
        self.assertIn("not authenticated", str(caught.exception))
        self.assertIn("not logged in", str(caught.exception))

    def test_large_diff_and_many_files_pass(self) -> None:
        self.commit("widget.py", "\n".join(f"line_{i} = {i}" for i in range(601)))
        for index in range(21):
            self.commit(f"file_{index}.txt", "one\n")
        result = self.check()
        self.assertTrue(result["ok"], result["problems"])
        self.assertEqual(result["files"], 22)

    def test_title_and_body_contract(self) -> None:
        self.commit("widget.py", "value = 1\n")
        bad_title = self.check(title="fix widget")
        self.assertFalse(bad_title["ok"])
        self.assertTrue(any("title" in item for item in bad_title["problems"]))
        missing = self.check("## Why\nOnly a why.\n")
        self.assertFalse(missing["ok"])
        self.assertTrue(any("## Verification" in item for item in missing["problems"]))
        long_body = self.check(BODY + ("line\n" * 40))
        self.assertTrue(long_body["ok"], long_body["problems"])

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

        def checks(pr, repo, head):
            calls.append(("checks", pr, repo, head))

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
        self.assertEqual(
            calls[0],
            ("checks", "1", self.repo, "a" * 40),
        )
        self.assertEqual(calls[1], ("merge", "1", "a" * 40, self.repo))

    def test_check_wait_uses_reviewed_head_and_bounded_wait(self) -> None:
        with mock.patch.object(
            pr_guard.check_wait, "wait_for_checks", return_value=[]
        ) as wait:
            pr_guard.wait_checks("1", self.repo, "a" * 40)
        wait.assert_called_once_with(
            pr="1",
            head="a" * 40,
            repo_path=self.repo,
            timeout=300,
            interval=20,
        )

    def test_check_wait_reports_stalled_checks(self) -> None:
        with mock.patch.object(
            pr_guard.check_wait,
            "wait_for_checks",
            side_effect=pr_guard.check_wait.CheckWaitError(
                "required checks still pending after 300s: links=in_progress/success"
            ),
        ):
            with self.assertRaises(pr_guard.GuardError) as caught:
                pr_guard.wait_checks("1", self.repo, "a" * 40)
        self.assertIn("links=in_progress/success", str(caught.exception))

    def test_land_recognizes_concurrent_auto_merge(self) -> None:
        unknown = {**PR_DATA, "mergeable": "UNKNOWN"}
        merged = {**PR_DATA, "state": "MERGED", "mergedAt": "now"}
        views = iter([PR_DATA, unknown, merged])
        result = pr_guard.land(
            "1",
            "a" * 40,
            repo=self.repo,
            base="main",
            view=lambda _pr, _repo: next(views),
            checks=lambda _pr, _repo, _head: None,
            merge=lambda *_args: None,
            pause=lambda _seconds: None,
        )
        self.assertTrue(result["ok"], result.get("problems"))
        self.assertEqual(result["state"], "MERGED")

    def test_land_waits_briefly_for_unknown_mergeability(self) -> None:
        unknown = {**PR_DATA, "mergeable": "UNKNOWN"}
        views = iter([PR_DATA, unknown, PR_DATA, {**PR_DATA, "state": "MERGED", "mergedAt": "now"}])
        merged = []
        result = pr_guard.land(
            "1",
            "a" * 40,
            repo=self.repo,
            base="main",
            view=lambda _pr, _repo: next(views),
            checks=lambda _pr, _repo, _head: None,
            merge=lambda *args: merged.append(args),
            pause=lambda _seconds: None,
        )
        self.assertTrue(result["ok"], result["problems"])
        self.assertEqual(len(merged), 1)

    def test_land_reports_actionable_check_failure(self) -> None:
        def checks(_pr, _repo, _head):
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
            checks=lambda _pr, _repo, _head: None,
            merge=lambda *args: merged.append(args),
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["next"], "rereview")
        self.assertEqual(merged, [])


if __name__ == "__main__":
    unittest.main()
